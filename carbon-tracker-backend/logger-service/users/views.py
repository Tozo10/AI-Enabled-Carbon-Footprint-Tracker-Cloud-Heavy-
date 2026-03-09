import time
import nltk
import requests
import re
import traceback
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from decouple import config
from rest_framework import status
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import EmissionFactor
from .serializers import EmissionFactorSerializer
# Fuzzy Matching Import
from thefuzz import fuzz

# Internal Modules
from .carbon_calculator import calculate_co2e
from .cloudant_db import save_activity_log, get_user_logs_cloudant
from .models import EmissionFactor  

# IBM Watson STT Imports
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# Ensure NLTK tokenizer is ready for sentence splitting
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)

# Helper for Speech to Text initialization
def get_stt_service():
    apikey = config("STT_APIKEY")
    url = config("STT_URL")
    authenticator = IAMAuthenticator(apikey)
    stt = SpeechToTextV1(authenticator=authenticator)
    stt.set_service_url(url)
    return stt


# --- NEW HELPER: INTELLIGENT NUMBER PARSER ---
# Handles conflicts where users type "two" instead of "2"
WORD_NUM_DICT = {
    'zero': 0, 'one': 1, 'a': 1, 'an': 1, 'two': 2, 'three': 3, 'four': 4, 
    'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
    'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
    'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70, 
    'eighty': 80, 'ninety': 90, 'hundred': 100, 'half': 0.5, 'quarter': 0.25,
    'twice': 2
}

def extract_quantity(text):
    """Extracts quantities, handling digits, decimals, and English words perfectly."""
    text_lower = text.lower()
    
    # 1. First, check for actual numerical digits (e.g., 5, 2.5)
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", text_lower)
    if numbers:
        return float(numbers[0])
        
    # 2. If no digits, check for word-based numbers (e.g., "two", "half")
    words = re.findall(r'\b[a-z]+\b', text_lower)
    for word in words:
        if word in WORD_NUM_DICT:
            return float(WORD_NUM_DICT[word])
            
    # Default fallback if no quantity is found at all
    return 1.0


# --- HELPER: DYNAMIC FALLBACK CLASSIFIER (UPGRADED WITH SMART FUZZY MATCHING) ---
def fallback_classify(text):
    """
    Acts as a safety net if the AI Service is down or fails to extract data.
    Now uses thefuzz to handle typos and safely split complex DB keys (e.g., 'Paneer_Indian').
    """
    text_lower = text.lower()
    
    # Extract precise number from text/words using the new parser
    qty = extract_quantity(text_lower)

    category = 'Unknown'
    unit = 'unit'
    
    # Break text into isolated words for fuzzy comparison
    words = re.findall(r'\b[a-z]+\b', text_lower)

    def matches_category(keywords, threshold=80):
        for w in words:
            for k in keywords:
                if fuzz.ratio(w, k) >= threshold:
                    return True
        return False

    # Keyword mapping for broad categories
    food_keys = ['eat', 'ate', 'drink', 'food', 'meal', 'burger', 'apple', 'rice', 'chicken']
    transport_keys = ['drive', 'drove', 'ride', 'took', 'cab', 'bus', 'train', 'flight', 'fly', 'car']
    energy_keys = ['light', 'electricity', 'power', 'kwh', 'ac', 'fan', 'use', 'used']

    if matches_category(food_keys):
        category = 'FOOD'
        unit = 'serving'
    elif matches_category(transport_keys):
        category = 'TRANSPORT'
        unit = 'km'
    elif matches_category(energy_keys):
        category = 'ENERGY'
        unit = 'kWh'

    # Try to match specific keys from the SQLite EmissionFactor table
    try:
        known_keys = list(EmissionFactor.objects.values_list('key', flat=True))
    except Exception:
        known_keys = []

    found_key = None
    best_score = 0
    
    for db_key in known_keys:
        # Convert "Paneer_Indian" to "paneer indian" for safer matching
        clean_db_key = db_key.lower().replace('_', ' ')
        
        # 1. Exact phrase match (e.g., if user somehow types "paneer indian")
        if clean_db_key in text_lower:
            found_key = db_key
            best_score = 100
            break
            
        # 2. Smart Fuzzy match (Checks input words against parts of the DB key)
        # This splits "paneer indian" into ['paneer', 'indian']
        key_parts = clean_db_key.split() 
        for word in words:
            for part in key_parts:
                # Skip tiny words to avoid false positive matches
                if len(part) <= 2: continue 
                
                score = fuzz.ratio(word, part)
                if score > best_score:
                    best_score = score
                    found_key = db_key
                
    # Enforce the 80% confidence threshold
    if best_score < 80:
        found_key = None
    
    if found_key:
        return category, found_key, qty, unit
    
    # Default fallbacks per category
    if category == 'FOOD': return 'FOOD', 'food', qty, 'serving'
    if category == 'TRANSPORT': return 'TRANSPORT', 'car', qty, 'km'
    if category == 'ENERGY': return 'ENERGY', 'electricity', qty, 'kWh'

    return 'Unknown', None, 0, None


# --- SHARED PROCESSING LOGIC ---
def process_text_to_carbon(input_text, user_obj): # Changed 'username' to 'user_obj' to get request.user
    """
    Core engine that splits text, analyzes, calculates, and saves.
    """
    username = user_obj.username # Extract name for Cloudant
    
    normalized_text = input_text.replace('\n', '. ')
    normalized_text = re.sub(r'(?<!\d),(?!\d)', '. ', normalized_text)
    normalized_text = normalized_text.replace(', ', '. ')
    normalized_text = re.sub(r'\b(and then|and i|and also)\b', '.', normalized_text, flags=re.IGNORECASE)

    sentences = nltk.tokenize.sent_tokenize(normalized_text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 2]
    
    logged_activities = []
    failed_sentences = []
    total_session_co2 = 0.0
    current_time = int(time.time())

    for sentence in sentences:
        clean_text = sentence.strip()
        analysis_results = None
        
        # A. AI Service call (logic remains same)
        try:
            ai_response = requests.post(
                "http://ai_engine:8001/analyze", 
                json={"username": username, "input_text": clean_text},
                timeout=5
            )
            if ai_response.status_code == 200:
                data = ai_response.json()
                analysis_results = data.get("extracted")
        except Exception as e:
            print(f"AI Service not reachable: {e}")

        activity_type, key, quantity, unit = 'Unknown', None, 0, None

        if analysis_results and "error" not in analysis_results:
            activity_type = analysis_results.get('activity_type', 'Unknown')
            key = analysis_results.get('key')
            
            raw_qty = analysis_results.get('quantity')
            
            # --- UPDATED QUANTITY FIX ---
            # Safely check if AI returned a valid number greater than 0
            is_valid_qty = False
            try:
                if raw_qty is not None and float(raw_qty) > 0:
                    is_valid_qty = True
            except (ValueError, TypeError):
                pass
                
            if not is_valid_qty:
                # Forces our perfect number parser to step in if AI fails or returns 0
                quantity = extract_quantity(clean_text) 
            else:
                quantity = float(raw_qty)
            # ---------------------------
                
            unit = analysis_results.get('unit')

        if activity_type == 'Unknown' or not key:
            activity_type, key, quantity, unit = fallback_classify(clean_text)

        if activity_type == 'Unknown' or not key:
            failed_sentences.append(f"{clean_text} (Not Recognized)")
            continue

        # --- CHANGE 1: Get 'is_verified' from calculator ---
        # Pass the user_obj so the calculator can check their 'Pending' factors
        co2e, is_verified = calculate_co2e(key, quantity, unit, request_user=user_obj)
        total_session_co2 += co2e

        # --- CHANGE 2: Save 'is_verified' to the log ---
        cloudant_doc = {
            "username": username,
            "input_text": clean_text,
            "activity_type": activity_type,
            "key": key,
            "quantity": quantity,
            "unit": unit,
            "co2e": co2e,
            "is_verified": is_verified, # Added this
            "timestamp": current_time, 
            "date_readable": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time)),
            "source_group_id": f"batch_{current_time}"
        }
        
        try:
            save_activity_log(cloudant_doc)
            cloudant_doc['id'] = f"temp{int(time.time())}_{len(logged_activities)}" 
            logged_activities.append(cloudant_doc)
        except Exception as e:
            print(f"Cloudant Save Fail: {e}")
            failed_sentences.append(clean_text)

    return Response({
        "status": "success",
        "transcript": input_text,
        "logs_count": len(logged_activities),
        "total_co2e_kg": round(total_session_co2, 2),
        "activities": logged_activities,
        "failed_sentences": failed_sentences,
        "message": f"Processed: {len(logged_activities)} activities recorded."
    }, status=status.HTTP_201_CREATED)

# --- 1. LOG ACTIVITY (TEXT) ---
@api_view(['POST'])
@permission_classes([IsAuthenticated]) # Ensure this is IsAuthenticated, not AllowAny
def log_activity_api(request):
    input_text = request.data.get('input_text')
    if not input_text:
        return Response({"message": "Missing input"}, status=status.HTTP_400_BAD_REQUEST)
    # Pass request.user instead of just username string
    return process_text_to_carbon(input_text, request.user)

# --- 2. LOG ACTIVITY (AUDIO - DIRECT LOGGING) ---
@api_view(['POST'])
@permission_classes([AllowAny])
def log_activity_audio_api(request):
    """
    Handles browser audio blobs, transcribes, and calculates footprint directly.
    """
    audio_file = request.FILES.get('audio')
    username = request.data.get('username')

    if not audio_file or not username:
        return Response({"message": "Missing audio file or username"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        stt = get_stt_service()
        response = stt.recognize(
            audio=audio_file,
            content_type='audio/webm', 
            model='en-US_Multimedia'
        ).get_result()

        transcript = ""
        if response.get('results'):
            transcript = " ".join([res['alternatives'][0]['transcript'] for res in response['results']])
        
        if not transcript:
            return Response({"message": "No speech detected in audio."}, status=status.HTTP_400_BAD_REQUEST)

        print(f"LOG: Transcription successful: '{transcript}'")
        return process_text_to_carbon(transcript, request.user)

    except Exception as e:
        print(f"STT API Error: {e}")
        return Response({"message": f"Transcription Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- 3. RETRIEVE HISTORY ---
@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_activities_api(request):
    username = request.GET.get('username')
    if not username:
        return Response({"message": "Username required"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        docs = get_user_logs_cloudant(username)
        # Ensure latest activities are at the top
        docs.sort(key=lambda x: float(x.get('timestamp', 0)), reverse=True)
        return Response({"status": "success", "count": len(docs), "activities": docs})
    except Exception as e:
        return Response({"message": f"History retrieval failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([AllowAny])
def get_leaderboard_api(request):
    """
    Fetches all logs from Cloudant and aggregates CO2 per user.
    """
    try:
        from .cloudant_db import get_cloudant_client
        client = get_cloudant_client()
        if not client:
            return Response({"message": "Cloudant connection failed"}, status=500)

        db_name = "activity-logs"
        # Fetch all documents (for a small/medium project scale)
        # For production, you'd use a Cloudant Design Document / View
        result = client.post_all_docs(db=db_name, include_docs=True).get_result()
        rows = result.get('rows', [])

        user_totals = {}

        for row in rows:
            doc = row.get('doc')
            if doc and 'username' in doc and 'co2e' in doc:
                uname = doc['username']
                co2 = float(doc['co2e'])
                user_totals[uname] = user_totals.get(uname, 0) + co2

        # Format and sort for the leaderboard (Top 5)
        formatted_leaderboard = []
        # Sorting by total CO2 reduced/tracked
        sorted_users = sorted(user_totals.items(), key=lambda x: x[1], reverse=True)[:5]

        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        for index, (name, total) in enumerate(sorted_users):
            formatted_leaderboard.append({
                "rank": index + 1,
                "name": name,
                "contribution": f"{round(total, 2)} kg CO₂",
                "medal": medals[index] if index < len(medals) else str(index + 1)
            })

        return Response({"status": "success", "leaderboard": formatted_leaderboard})
    except Exception as e:
        return Response({"message": str(e)}, status=500)

# --- 4. STANDALONE TRANSCRIPTION (FOR TEXTBOX POPULATION) ---
@api_view(['POST'])
@permission_classes([AllowAny])
def speech_to_text_api(request):
    """
    Transcribes audio and returns ONLY the text. Used for populating the frontend textbox.
    """
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response({"message": "No audio"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        stt = get_stt_service()
        response = stt.recognize(
            audio=audio_file,
            content_type='audio/webm', 
            model='en-US_Multimedia'
        ).get_result()
        transcript = ""
        if response.get('results'):
            transcript = " ".join([res['alternatives'][0]['transcript'] for res in response['results']])
        return Response({"status": "success", "transcript": transcript.strip()})
    except Exception as e:
        return Response({"message": f"Transcription failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_custom_factor(request):
    serializer = EmissionFactorSerializer(data=request.data)
    if serializer.is_valid():
        # Set status to pending and link to the current user
        serializer.save(
            status='pending',
            added_by=request.user
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)