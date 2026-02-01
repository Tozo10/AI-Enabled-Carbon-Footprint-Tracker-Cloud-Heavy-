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

# --- HELPER: DYNAMIC FALLBACK CLASSIFIER ---
def fallback_classify(text):
    """
    Acts as a safety net if the AI Service is down or fails to extract data.
    """
    text = text.lower()
    
    # Extract first number found in text
    numbers = re.findall(r"[-+]?\d*\.\d+|\d+", text)
    qty = float(numbers[0]) if numbers else 1.0

    category = 'Unknown'
    unit = 'unit'

    # Keyword mapping for broad categories
    if any(x in text for x in ['eat', 'ate', 'drink', 'food', 'meal', 'burger', 'apple', 'rice', 'chicken']):
        category = 'FOOD'
        unit = 'serving'
    elif any(x in text for x in ['drive', 'drove', 'ride', 'took', 'cab', 'bus', 'train', 'flight', 'fly', 'car']):
        category = 'TRANSPORT'
        unit = 'km'
    elif any(x in text for x in ['light', 'electricity', 'power', 'kwh', 'ac', 'fan', 'use', 'used']):
        category = 'ENERGY'
        unit = 'kWh'

    # Try to match specific keys from the SQLite EmissionFactor table
    try:
        known_keys = list(EmissionFactor.objects.values_list('key', flat=True))
    except Exception:
        known_keys = []

    found_key = None
    known_keys.sort(key=len, reverse=True) # Check longest keys first
    for db_key in known_keys:
        if db_key in text:
            found_key = db_key
            break
    
    if found_key:
        return category, found_key, qty, unit
    
    # Default fallbacks per category
    if category == 'FOOD': return 'FOOD', 'food', qty, 'serving'
    if category == 'TRANSPORT': return 'TRANSPORT', 'car', qty, 'km'
    if category == 'ENERGY': return 'ENERGY', 'electricity', qty, 'kWh'

    return 'Unknown', None, 0, None

# --- SHARED PROCESSING LOGIC ---
def process_text_to_carbon(input_text, username):
    """
    Core engine that splits text into sentences, analyzes them, 
    calculates carbon, and saves to the Cloudant history.
    """
    # 1. Clean and split input into sentences
    raw_lines = input_text.split('\n')
    sentences = []
    for line in raw_lines:
        line = line.strip()
        if not line: continue
        if "." in line: line = line.replace(".", ". ")
        sub_sentences = nltk.tokenize.sent_tokenize(line)
        sentences.extend(sub_sentences)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 2]
    
    logged_activities = []
    failed_sentences = []
    total_session_co2 = 0.0
    current_time = int(time.time())

    for sentence in sentences:
        clean_text = sentence.strip()
        analysis_results = None
        
        # A. Try AI Service (FastAPI Microservice)
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

        # B. Extraction & Fallback logic
        activity_type, key, quantity, unit = 'Unknown', None, 0, None

        if analysis_results and "error" not in analysis_results:
            activity_type = analysis_results.get('activity_type', 'Unknown')
            key = analysis_results.get('key')
            quantity = analysis_results.get('quantity')
            unit = analysis_results.get('unit')

        if activity_type == 'Unknown' or not key:
            activity_type, key, quantity, unit = fallback_classify(clean_text)

        # C. Calculation using SQLite Factors
        if activity_type == 'Unknown' or not key:
            failed_sentences.append(f"{clean_text} (Not Recognized)")
            continue

        co2e = calculate_co2e(key, quantity, unit)
        total_session_co2 += co2e

        # D. Cloudant Persistence
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
        
        try:
            save_activity_log(cloudant_doc)
            cloudant_doc['_id'] = f"temp_{int(time.time())}_{len(logged_activities)}" 
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
@permission_classes([AllowAny]) 
def log_activity_api(request):
    input_text = request.data.get('input_text')
    username = request.data.get('username')
    if not input_text or not username:
        return Response({"message": "Missing input"}, status=status.HTTP_400_BAD_REQUEST)
    return process_text_to_carbon(input_text, username)


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
        return process_text_to_carbon(transcript, username)

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