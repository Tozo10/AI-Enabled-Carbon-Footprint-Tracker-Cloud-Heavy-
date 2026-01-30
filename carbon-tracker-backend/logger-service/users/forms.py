# users/forms.py
from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Activity

# ... CustomUserCreationForm might be here ...

class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = ['input_text']