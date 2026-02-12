from django.urls import path
from . import views

urlpatterns = [
    # Logger Service handles carbon tracking & data retrieval
    path('api/log-activity/', views.log_activity_api, name='log_activity_api'),
    
    # ✅ Audio-based logging (The missing route causing the 404)
    path('api/log-activity-audio/', views.log_activity_audio_api, name='log_activity_audio'),
    path('api/my-activities/', views.get_user_activities_api, name='get_user_activities_api'),
    path('api/speech-to-text/', views.speech_to_text_api, name='stt'),
    path('api/leaderboard/', views.get_leaderboard_api, name='leaderboard_api'),
]
