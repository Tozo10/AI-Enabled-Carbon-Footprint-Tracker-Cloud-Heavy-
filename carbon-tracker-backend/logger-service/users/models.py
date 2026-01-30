from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Activity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    input_text = models.TextField()
    activity_type = models.CharField(max_length=100, blank=True, null=True)
    key = models.CharField(max_length=100, blank=True, null=True) # e.g., 'cab', 'steak'
    quantity = models.FloatField(blank=True, null=True) 
    unit = models.CharField(max_length=50, blank=True, null=True) 
    co2e = models.FloatField(blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Activities"
    def __str__(self):
        return f'{self.user.username} - {self.input_text[:50]}'
    
class EmissionFactor(models.Model):
    activity_type = models.CharField(max_length=100) # e.g., TRANSPORT, FOOD
    key = models.CharField(max_length=100, unique=True) # e.g., 'petrol_car', 'steak', 'cab'
    co2e_per_unit = models.FloatField() # e.g., 0.21 (for kg CO2e per km)
    unit = models.CharField(max_length=50) # e.g., 'km', 'serving'

    def __str__(self):
        return f"{self.key} ({self.activity_type}): {self.co2e_per_unit} kg CO2e/{self.unit}"