from rest_framework import serializers
from .models import EmissionFactor

class EmissionFactorSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmissionFactor
        fields = ['activity_type', 'key', 'co2e_per_unit', 'unit', 'source_reference']