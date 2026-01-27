import time
from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from decouple import config

# IBM Watson SDK Imports for Speech to Text
from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

from . import nlp_service
from .carbon_calculator import calculate_co2e
from .cloudant_db import save_activity_log, get_user_logs_cloudant

# Helper to initialize the Speech to Text Service
def get_stt_service():
    """
    Initializes the IBM Watson Speech to Text service using credentials from .env
    """
    apikey = config("STT_APIKEY")
    url = config("STT_URL")
    authenticator = IAMAuthenticator(apikey)
    stt = SpeechToTextV1(authenticator=authenticator)
    stt.set_service_url(url)
    return stt

# --- 1. AUTHENTICATION VIEWS ---

@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    """
    Handles user login via SQLite (Django Auth).
    """
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
    """
    Handles user registration via SQLite (Django Auth).
    """
    username = request.data.get('username')
    password = request.data.get('password')
    if not username or not password:
        return Response({"message": "Username and password required"}, status=status.HTTP_400_BAD_REQUEST)
    
    if User.objects.filter(username=username).exists():
        return Response({"message": "Username taken"}, status=status.HTTP_400_BAD_REQUEST)
        
    user = User.objects.create_user(username=username, password=password)
    login(request, user)
    return Response({"status": "success", "username": user.username}, status=status.HTTP_201_CREATED)


# --- 2. ACTIVITY LOGGING (IBM CLOUDANT) ---

@api_view(['POST'])
@permission_classes([AllowAny]) 
def log_activity_api(request):
    """
    Processes activity text with WatsonX NLP and saves results to IBM Cloudant.
    """
    input_text = request.data.get('input_text')
    username = request.data.get('username')

    if not input_text or not username:
        return Response({"message": "Missing input text or username"}, status=status.HTTP_400_BAD_REQUEST)

    # 1. Analyze with NLP Service (WatsonX)
    analysis_results = nlp_service.analyze_activity_text(input_text)
    if not analysis_results:
        return Response({"message": "AI could not understand the input"}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Extract Data & Calculate CO2e
    activity_type = analysis_results.get('activity_type', 'Unknown')
    key = analysis_results.get('key', 'car' if activity_type == 'TRANSPORT' else None)
    quantity = analysis_results.get('quantity')
    unit = analysis_results.get('unit')
    
    co2e = calculate_co2e(key, quantity, unit)

    # 3. Save to IBM Cloudant
    current_time = int(time.time())
    cloudant_doc = {
        "username": username,
        "input_text": input_text,
        "activity_type": activity_type,
        "key": key,
        "quantity": quantity,
        "unit": unit,
        "co2e": co2e,
        "timestamp": current_time, 
        "date_readable": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(current_time))
    }
    
    try:
        save_activity_log(cloudant_doc)
        return Response({
            "status": "success",
            "activity": input_text,
            "co2e_kg": co2e,
            "message": f"Saved to Cloudant: {co2e}kg CO2"
        }, status=status.HTTP_201_CREATED)
    except Exception as e:
        print(f"Cloudant Save Error: {e}")
        return Response({"message": f"Cloudant Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# --- 3. DATA RETRIEVAL (IBM CLOUDANT) ---

@api_view(['GET'])
@permission_classes([AllowAny])
def get_user_activities_api(request):
    """
    Fetches activity history from IBM Cloudant and sorts by time (newest first).
    """
    username = request.GET.get('username')
    if not username:
        return Response({"message": "Username required"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        # Fetch from our Cloudant helper
        docs = get_user_logs_cloudant(username)
        
        # Safe sorting helper to handle potential mixed data types
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


# --- 4. MULTI-MODAL: SPEECH TO TEXT (IBM WATSON STT) ---

@api_view(['POST'])
@permission_classes([AllowAny])
def speech_to_text_api(request):
    """
    Receives an audio file (blob) and returns the text transcript using IBM Watson STT.
    """
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response({"message": "No audio file provided"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        stt = get_stt_service()
        
        # Recognize speech from the uploaded audio file
        # Browsers usually record in webm/wav; 'audio/wav' is standard for the BroadBand model.
        response = stt.recognize(
            audio=audio_file,
            content_type='audio/wav', 
            model='en-US_BroadbandModel'
        ).get_result()

        transcript = ""
        if response.get('results'):
            # Combine all transcribed alternatives into a single string
            transcript = " ".join([res['alternatives'][0]['transcript'] for res in response['results']])
            
        return Response({
            "status": "success",
            "transcript": transcript.strip()
        }, status=status.HTTP_200_OK)

    except Exception as e:
        print(f"STT Error: {e}")
        return Response({"message": f"Speech to Text Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)