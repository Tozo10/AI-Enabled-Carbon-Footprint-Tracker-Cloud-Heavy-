from django.shortcuts import get_object_or_404
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status

from .models import Activity
from . import nlp_service
from .carbon_calculator import calculate_co2e

# --- 1. LOGIN VIEW (API) ---
@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    """
    Receives JSON: {"username": "...", "password": "..."}
    Returns JSON: {"status": "success", "username": "..."}
    """
    username = request.data.get('username')
    password = request.data.get('password')

    user = authenticate(username=username, password=password)

    if user is not None:
        login(request, user)  # Starts a session on the server
        return Response({
            "status": "success",
            "message": "Login successful",
            "username": user.username
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            "status": "error",
            "message": "Invalid username or password"
        }, status=status.HTTP_401_UNAUTHORIZED)


# --- 2. REGISTER/SIGNUP VIEW (API) ---
@api_view(['POST'])
@permission_classes([AllowAny])
def register_api(request):
    """
    Receives JSON: {"username": "...", "password": "..."}
    Creates a new user and logs them in.
    """
    username = request.data.get('username')
    password = request.data.get('password')

    if not username or not password:
        return Response({"message": "Username and password required"}, status=status.HTTP_400_BAD_REQUEST)

    if User.objects.filter(username=username).exists():
        return Response({"message": "Username already taken"}, status=status.HTTP_400_BAD_REQUEST)

    # Create the user
    user = User.objects.create_user(username=username, password=password)
    user.save()
    
    # Log them in immediately
    login(request, user)

    return Response({
        "status": "success", 
        "username": user.username,
        "message": "User created successfully"
    }, status=status.HTTP_201_CREATED)


# --- 3. LOG ACTIVITY VIEW (API) ---
@api_view(['POST'])
# Note: For now, we allow any connection, but ideally, you use @permission_classes([IsAuthenticated])
# if you are sending the session cookie or token from React.
@permission_classes([AllowAny]) 
def log_activity_api(request):
    """
    Receives JSON: {"username": "...", "input_text": "I drove 10km"}
    Runs NLP -> Calculator -> Saves to DB -> Returns Result
    """
    input_text = request.data.get('input_text')
    username = request.data.get('username') # React sends this now

    if not input_text:
        return Response({"message": "No input text provided"}, status=status.HTTP_400_BAD_REQUEST)

    # Find the user to associate the activity with
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        # Fallback: If no username sent, try request.user (if session auth is working)
        if request.user.is_authenticated:
            user = request.user
        else:
            return Response({"message": "User not found or not logged in"}, status=status.HTTP_401_UNAUTHORIZED)

    # 1. Analyze with NLP Service
    analysis_results = nlp_service.analyze_activity_text(input_text)
    
    if not analysis_results:
        return Response({"message": "Could not understand the activity"}, status=status.HTTP_400_BAD_REQUEST)

    # 2. Extract Data
    activity_type = analysis_results.get('activity_type', 'Unknown')
    key = analysis_results.get('key')
    distance = analysis_results.get('distance')
    unit = analysis_results.get('unit')

    # 3. Calculate Carbon Footprint
    calculated_co2e = calculate_co2e(key, distance, unit)

    # 4. Save to Database
    activity = Activity.objects.create(
        user=user,
        input_text=input_text,
        activity_type=activity_type,
        key=key,
        distance=distance,
        unit=unit,
        co2e=calculated_co2e
    )

    # 5. Return JSON to React
    return Response({
        "status": "success",
        "activity": input_text,
        "co2e_kg": calculated_co2e,
        "message": f"Logged: {activity_type} resulting in {calculated_co2e}kg CO2"
    }, status=status.HTTP_201_CREATED)