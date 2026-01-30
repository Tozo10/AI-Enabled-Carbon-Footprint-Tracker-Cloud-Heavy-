import time
import nltk
import requests
import re
import traceback  # For detailed error reporting
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from decouple import config

# Internal Modules
from .carbon_calculator import calculate_co2e
from .cloudant_db import save_activity_log, get_user_logs_cloudant
# --- Access the Database Table directly ---
from .models import EmissionFactor  

# IBM Watson STT Imports
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# Ensure NLTK tokenizer is ready
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)

# Helper for Speech to Text
def get_stt_service():
    apikey = config("STT_APIKEY")
    url = config("STT_URL")
    authenticator = IAMAuthenticator(apikey)
    stt = SpeechToTextV1(authenticator=authenticator)
    stt.set_service_url(url)
    return stt

# --- HELPER: DYNAMIC FALLBACK CLASSIFIER ---
def fallback_classify(text):
    """
    1. Decides Category based on verbs/keywords.
    2. Decides KEY by checking what actually exists in the DB.
    """
    text = text.lower()
    
    # Step 1: Extract Quantity (e.g., "2 apples" -> 2.0)
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", text)
    qty = float(numbers[0]) if numbers else 1.0

    # Step 2: Determine Category (Broad Guess)
    category = 'Unknown'
    unit = 'unit' # Default unit

    # FOOD Keywords
    if any(x in text for x in ['eat', 'ate', 'drink', 'food', 'meal', 'burger', 'apple', 'rice', 'chicken']):
        category = 'FOOD'
        unit = 'serving'
    # TRANSPORT Keywords
    elif any(x in text for x in ['drive', 'drove', 'ride', 'took', 'cab', 'bus', 'train', 'flight', 'fly', 'car']):
        category = 'TRANSPORT'
        unit = 'km'
    # ENERGY Keywords
    elif any(x in text for x in ['light', 'electricity', 'power', 'kwh', 'ac', 'fan', 'use', 'used']):
        category = 'ENERGY'
        unit = 'kWh'

    # Step 3: DYNAMIC KEY FINDER
    try:
        known_keys = list(EmissionFactor.objects.values_list('key', flat=True))
    except Exception:
        known_keys = []

    found_key = None
    
    # Check if any known DB key is inside the user's text.
    known_keys.sort(key=len, reverse=True)
    
    for db_key in known_keys:
        if db_key in text:
            found_key = db_key
            break
    
    # If we found a specific key in the DB, return it immediately!
    if found_key:
        return category, found_key, qty, unit
    
    # Step 4: Defaults (Only if DB match failed)
    if category == 'FOOD': return 'FOOD', 'food', qty, 'serving'
    if category == 'TRANSPORT': return 'TRANSPORT', 'car', qty, 'km'
    if category == 'ENERGY': return 'ENERGY', 'electricity', qty, 'kWh'

    return 'Unknown', None, 0, None


# --- 1. ACTIVITY LOGGING ---

@api_view(['POST'])
@permission_classes([AllowAny]) 
def log_activity_api(request):
    """
    1. Receives text.
    2. Aggressively splits into sentences.
    3. Sends to AI.
    4. If AI fails, uses Dynamic Fallback.
    5. Saves to DB.
    """
    input_text = request.data.get('input_text')
    username = request.data.get('username')

    if not input_text or not username:
        return Response({"message": "Missing input text or username"}, status=status.HTTP_400_BAD_REQUEST)

    # --- AGGRESSIVE SPLITTING LOGIC ---
    raw_lines = input_text.split('\n')
    sentences = []
    for line in raw_lines:
        line = line.strip()
        if not line: continue
        if "." in line: line = line.replace(".", ". ")
        sub_sentences = nltk.tokenize.sent_tokenize(line)
        sentences.extend(sub_sentences)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 2]
    
    print(f"DEBUG: Final Processed Input List: {sentences}")
    # ---------------------------------------------

    logged_activities = []
    failed_sentences = []
    total_session_co2 = 0.0
    current_time = int(time.time())

    for sentence in sentences:
        clean_text = sentence.strip()
        print(f"DEBUG: Sending to AI Service: '{clean_text}'")

        # --- STEP 1: ASK AI SERVICE ---
        analysis_results = None
        try:
            ai_response = requests.post(
                "http://ai-service:5000/analyze", 
                json={"text": clean_text},
                timeout=5
            )
            if ai_response.status_code == 200:
                analysis_results = ai_response.json()
            else:
                print(f"AI Service Error {ai_response.status_code}: {ai_response.text}")

        except requests.exceptions.RequestException as e:
            print(f"AI Connection Error: {e}")
            # Do not continue; proceed to fallback

        # Extract Data
        activity_type = 'Unknown'
        key = None
        quantity = 0
        unit = None

        if analysis_results and "error" not in analysis_results:
            activity_type = analysis_results.get('activity_type', 'Unknown')
            key = analysis_results.get('key')
            quantity = analysis_results.get('quantity')
            unit = analysis_results.get('unit')

        # --- STEP 2: SAFETY NET (DYNAMIC FALLBACK) ---
        if activity_type == 'Unknown' or not key:
            print(f"DEBUG: AI failed for '{clean_text}'. Trying Dynamic Fallback...")
            activity_type, key, quantity, unit = fallback_classify(clean_text)

        # --- STEP 3: FINAL CHECK ---
        if activity_type == 'Unknown' or not key:
            print(f"DEBUG: Skipping completely unknown activity: {clean_text}")
            failed_sentences.append(f"{clean_text} (Not Recognized)")
            continue

        print(f"DEBUG: Valid Activity Found: {activity_type} - {key} - {quantity}")

        # Calculate CO2 locally
        co2e = calculate_co2e(key, quantity, unit)
        total_session_co2 += co2e

        # Create Record
        cloudant_doc = {
            "username": username,
            "input_text": clean_text,
            "activity_type": activity_type,
            "key": key,
            "quantity": quantity,
            "unit": unit,
            "co2e": co2e,
            "timestamp": current_time, 
            "date_readable": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time)),
            "source_group_id": f"batch_{current_time}"
        }
        
        # Save to DB
        try:
            save_activity_log(cloudant_doc)
            cloudant_doc['_id'] = f"temp_{int(time.time())}_{len(logged_activities)}" 
            logged_activities.append(cloudant_doc)
        except Exception as e:
            print(f"DB Save Error: {e}")
            failed_sentences.append(clean_text)

    # Final Response Logic
    if not logged_activities and failed_sentences:
        return Response({
            "status": "error", 
            "message": "Could not analyze sentences.",
            "failed_inputs": failed_sentences
        }, status=status.HTTP_400_BAD_REQUEST)

    return Response({
        "status": "success",
        "logs_count": len(logged_activities),
        "total_co2e_kg": round(total_session_co2, 2),
        "activities": logged_activities,
        "failed_sentences": failed_sentences,
        "message": f"Successfully logged {len(logged_activities)} activities."
    }, status=status.HTTP_201_CREATED)


# --- 2. DATA RETRIEVAL (FIXED & ROBUST) ---
@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_activities_api(request):
    username = request.GET.get('username')
    print(f"DEBUG: Requesting logs for: {username}") # Initial debug print

    if not username:
        return Response({"message": "Username required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        docs = get_user_logs_cloudant(username)
        
        # --- FIX: Safe Sorting that handles Strings vs Integers ---
        # We force 'float' conversion so '123' and 123 both become numbers.
        docs.sort(key=lambda x: float(x.get('timestamp', 0)), reverse=True)
        # ---------------------------------------------------------

        return Response({
            "status": "success",
            "count": len(docs),
            "activities": docs
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        # --- DEBUG CRASH REPORTER ---
        print("\n!!!!!!!! CRASH REPORT !!!!!!!!")
        print(f"ERROR TYPE: {type(e)}")
        print(f"ERROR MESSAGE: {str(e)}")
        traceback.print_exc() # Prints line numbers
        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!\n")
        # ----------------------------
        return Response({"message": f"Error fetching logs: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- 3. SPEECH TO TEXT ---
@api_view(['POST'])
@permission_classes([AllowAny])
def speech_to_text_api(request):
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response({"message": "No audio file provided"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        stt = get_stt_service()
        response = stt.recognize(
            audio=audio_file,
            content_type='audio/wav', 
            model='en-US_BroadbandModel'
        ).get_result()

        transcript = ""
        if response.get('results'):
            transcript = " ".join([res['alternatives'][0]['transcript'] for res in response['results']])
            
        return Response({
            "status": "success",
            "transcript": transcript.strip()
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({"message": f"STT Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)