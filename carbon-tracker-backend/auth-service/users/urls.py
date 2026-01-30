from django.urls import path
from . import views

urlpatterns = [
    # Auth Service only handles Login and Registration
    path('api/login/', views.login_api, name='login_api'),
    path('api/register/', views.register_api, name='register_api'),
]