from django.db import models
from django.contrib.auth.models import User

class Activity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    input_text = models.TextField()
    activity_type = models.CharField(max_length=100, blank=True, null=True)
    key = models.CharField(max_length=100, blank=True, null=True) 
    quantity = models.FloatField(blank=True, null=True) 
    unit = models.CharField(max_length=50, blank=True, null=True) 
    co2e = models.FloatField(blank=True, null=True)
    # --- ADD THIS: Essential for the UI Tick mark ---
    is_verified = models.BooleanField(default=False) 
    
    class Meta:
        verbose_name_plural = "Activities"
    def __str__(self):
        return f'{self.user.username} - {self.input_text[:50]}'
    
class EmissionFactor(models.Model):
    STATUS_CHOICES = [
        ('verified', 'Verified'),
        ('pending', 'Pending'),
    ]

    activity_type = models.CharField(max_length=100) 
    key = models.CharField(max_length=100, unique=True) 
    co2e_per_unit = models.FloatField() 
    unit = models.CharField(max_length=50)
    
    # Cleaned up fields
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    added_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True, blank=True)
    source_reference = models.TextField(blank=True, null=True)
    
    # This helps the calculator logic determine "Verified" status quickly
    is_verified_factor = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.key} [{self.status}]"