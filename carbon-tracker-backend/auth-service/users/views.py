from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

# --- AUTHENTICATION VIEWS ONLY ---

@api_view(['POST'])
@permission_classes([AllowAny])
def login_api(request):
    """
    Handles user login.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    user = authenticate(username=username, password=password)
    
    if user is not None:
        login(request, user)
        return Response({
            "status": "success", 
            "username": user.username
        }, status=status.HTTP_200_OK)
        
    return Response({
        "status": "error", 
        "message": "Invalid credentials"
    }, status=status.HTTP_401_UNAUTHORIZED)

@api_view(['POST'])
@permission_classes([AllowAny])
def register_api(request):
    """
    Handles user registration.
    """
    username = request.data.get('username')
    password = request.data.get('password')
    
    if not username or not password:
        return Response({
            "message": "Username and password required"
        }, status=status.HTTP_400_BAD_REQUEST)
    
    if User.objects.filter(username=username).exists():
        return Response({
            "message": "Username taken"
        }, status=status.HTTP_400_BAD_REQUEST)
        
    # Create the user
    user = User.objects.create_user(username=username, password=password)
    
    # Log them in immediately
    login(request, user)
    
    return Response({
        "status": "success", 
        "username": user.username
    }, status=status.HTTP_201_CREATED)