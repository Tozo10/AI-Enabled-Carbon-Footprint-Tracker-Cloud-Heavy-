from django.urls import path
from . import views

urlpatterns = [
    # API Endpoints for React Connection
    path('api/login/', views.login_api, name='login_api'),
    path('api/register/', views.register_api, name='register_api'),
    path('api/log-activity/', views.log_activity_api, name='log_activity_api'),
]