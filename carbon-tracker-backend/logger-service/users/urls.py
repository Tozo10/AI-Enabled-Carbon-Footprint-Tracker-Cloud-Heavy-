from django.urls import path
from . import views

urlpatterns = [
    # Logger Service handles carbon tracking & data retrieval
    path('api/log-activity/', views.log_activity_api, name='log_activity_api'),
    path('api/my-activities/', views.get_user_activities_api, name='get_user_activities_api'),
    path('api/speech-to-text/', views.speech_to_text_api, name='stt'),
]
