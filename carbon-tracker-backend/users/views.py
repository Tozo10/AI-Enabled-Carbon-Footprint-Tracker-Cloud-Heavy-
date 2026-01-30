import time
import nltk
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from decouple import config

# IBM Watson SDK Imports
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

from . import nlp_service
from .carbon_calculator import calculate_co2e
from .cloudant_db import save_activity_log, get_user_logs_cloudant

# Ensure NLTK tokenizer is downloaded (do this once)
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    nltk.download('punkt', quiet=True)
    nltk.download('punkt_tab', quiet=True)

# Helper to initialize STT
def get_stt_service():
    apikey = config("STT_APIKEY")
    url = config("STT_URL")
    authenticator = IAMAuthenticator(apikey)
    stt = SpeechToTextV1(authenticator=authenticator)
    stt.set_service_url(url)
    return stt

# --- 1. AUTHENTICATION VIEWS (Unchanged) ---
@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    username = request.data.get('username')
    password = request.data.get('password')
    user = authenticate(username=username, password=password)
    if user is not None:
        login(request, user)
        return Response({"status": "success", "username": user.username}, status=status.HTTP_200_OK)
    return Response({"status": "error", "message": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_api(request):
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({"message": "Username and password required"}, status=status.HTTP_400_BAD_REQUEST)
    
    if User.objects.filter(username=username).exists():
        return Response({"message": "Username taken"}, status=status.HTTP_400_BAD_REQUEST)
        
    user = User.objects.create_user(username=username, password=password)
    login(request, user)
    return Response({"status": "success", "username": user.username}, status=status.HTTP_201_CREATED)


# --- 2. ACTIVITY LOGGING (WITH DEBUGGING) ---

@api_view(['POST'])
@permission_classes([AllowAny]) 
def log_activity_api(request):
    """
    Parses a block of text, splits sentences, analyzes, and logs to Cloudant.
    Now includes DEBUG prints to trace missing values.
    """
    input_text = request.data.get('input_text')
    username = request.data.get('username')

    if not input_text or not username:
        return Response({"message": "Missing input text or username"}, status=status.HTTP_400_BAD_REQUEST)

    # 1. Split sentences
    sentences = nltk.tokenize.sent_tokenize(input_text)
    
    logged_activities = []
    failed_sentences = []
    total_session_co2 = 0.0

    current_time = int(time.time())

    print(f"DEBUG: Starting batch for user '{username}' with text: '{input_text}'")

    # 2. Loop through each sentence
    for sentence in sentences:
        clean_text = sentence.strip()
        if len(clean_text) < 3:
            continue
            
        print(f"--------------------------------------------------")
        print(f"DEBUG: Processing sentence: '{clean_text}'")

        # A. Analyze
        analysis_results = nlp_service.analyze_activity_text(clean_text)
        print(f"DEBUG: NLP Result raw: {analysis_results}")

        if not analysis_results:
            print("DEBUG: NLP failed (returned None or empty).")
            failed_sentences.append(clean_text)
            continue

        # B. Extract & Calculate
        activity_type = analysis_results.get('activity_type', 'Unknown')
        key = analysis_results.get('key')
        quantity = analysis_results.get('quantity')
        unit = analysis_results.get('unit')
        
        # Default key if NLP missed it (e.g. assume car for transport)
        if not key and activity_type == 'TRANSPORT':
            key = 'car'
            print("DEBUG: Key missing, defaulting to 'car'")
            
        print(f"DEBUG: Calculator Inputs -> Key: {key}, Qty: {quantity}, Unit: {unit}")

        co2e = calculate_co2e(key, quantity, unit)
        print(f"DEBUG: Calculator Output -> CO2: {co2e}")

        total_session_co2 += co2e

        # C. Prepare Document
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
        
        # D. Save to Cloudant
        try:
            save_activity_log(cloudant_doc)
            cloudant_doc['_id'] = "saved_just_now"
            logged_activities.append(cloudant_doc)
            print("DEBUG: Saved successfully to Cloudant.")
            
        except Exception as e:
            print(f"ERROR: Cloudant Save Failed: {e}")
            failed_sentences.append(clean_text)

    # 3. Final Response
    if not logged_activities and failed_sentences:
        return Response({
            "status": "error", 
            "message": "Could not understand any sentences.",
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


# --- 3. DATA RETRIEVAL (Unchanged) ---
@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_activities_api(request):
    username = request.GET.get('username')
    if not username:
        return Response({"message": "Username required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        docs = get_user_logs_cloudant(username)
        
        def get_sort_key(doc):
            val = doc.get('timestamp', 0)
            try:
                return int(val)
            except (ValueError, TypeError):
                return 0

        docs.sort(key=get_sort_key, reverse=True)
        
        formatted_activities = []
        for doc in docs:
            formatted_activities.append({
                "id": doc.get("_id"),
                "input_text": doc.get("input_text", ""),
                "activity_type": doc.get("activity_type", "Unknown"),
                "quantity": doc.get("quantity", 0),
                "unit": doc.get("unit", ""),
                "co2e": doc.get("co2e", 0),
                "date": doc.get("date_readable", "N/A")
            })

        return Response({
            "status": "success",
            "count": len(formatted_activities),
            "activities": formatted_activities
        }, status=status.HTTP_200_OK)
        
    except Exception as e:
        print(f"Fetch Error: {e}")
        return Response({"message": f"Error fetching from Cloud: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- 4. MULTI-MODAL: SPEECH TO TEXT (Unchanged) ---
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
        print(f"STT Error: {e}")
        return Response({"message": f"Speech to Text Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)