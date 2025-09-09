from django.db import models
from django.contrib.auth.models import User
# Create your models here.

class Activity(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    input_text = models.TextField()
    activity_type = models.CharField(max_length=100, blank=True, null=True)
    co2e = models.FloatField(blank=True, null=True) # Carbon Footprint in kg CO2e
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Activities"
    def __str__(self):
        return f'{self.user.username} - {self.input_text[:50]}'