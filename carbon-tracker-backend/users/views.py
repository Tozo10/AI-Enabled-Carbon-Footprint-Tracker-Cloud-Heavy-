from django.shortcuts import render
from django.contrib.auth.views import LoginView
from django.urls import reverse_lazy
from django.views.generic import TemplateView 
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.views.generic.edit import FormView, CreateView
from django.shortcuts import redirect
from .models import Activity
from .forms import ActivityForm
from . import nlp_service
from .carbon_calculator import calculate_co2e
import json

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    fields = '__all__'
    redirect_authenticated_user = True

class HomeView(LoginRequiredMixin, TemplateView):
    template_name = 'home.html'

class RegisterView(FormView):
    template_name = 'users/register.html'
    form_class = UserCreationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('home')

    def form_valid(self, form):
        user = form.save()
        if user is not None:
            login(self.request, user)
        return super(RegisterView, self).form_valid(form)

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('home')
        return super(RegisterView, self).get(*args, **kwargs)
    def get_success_url(self):
        return reverse_lazy('home')



# This code just replaces your LogActivityView.

class LogActivityView(LoginRequiredMixin, CreateView):
    model = Activity
    form_class = ActivityForm
    template_name = 'users/log_activity.html'
    success_url = reverse_lazy('home')

    def form_valid(self, form):
       form.instance.user = self.request.user
       input_text = form.cleaned_data['input_text']
       analysis_results = nlp_service.analyze_activity_text(input_text)
       if analysis_results:
        # 1. Get all data from the AI
            activity_type = analysis_results.get('activity_type', 'Unknown')
            key = analysis_results.get('key')
            distance = analysis_results.get('distance')
            unit = analysis_results.get('unit')

        # 2. Save the extracted data to the instance
            form.instance.activity_type = activity_type
            form.instance.key = key
            form.instance.distance = distance
            form.instance.unit = unit

            # 3. Call the calculator to get the final CO2e
            calculated_co2e = calculate_co2e(key, distance, unit)

            # 4. Save the final calculation
            form.instance.co2e = calculated_co2e

       else:
            form.instance.activity_type = 'Analysis Failed'
       return super().form_valid(form)