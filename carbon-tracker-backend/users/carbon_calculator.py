# users/carbon_calculator.py
from .models import EmissionFactor

def calculate_co2e(key, distance, unit):
    """
    Calculates the CO2e for a given activity by looking up its emission factor.
    """
    if not key:
        return None

    try:
        # Find the correct emission factor in the database using the unique key
        factor = EmissionFactor.objects.get(key__iexact=key)

        # We have a factor, now let's calculate
        co2e = 0.0

        # 1. Handle distance-based activities (TRANSPORT)
        if factor.activity_type == 'TRANSPORT':
            if not distance:
                return None  # Can't calculate transport without distance

            calculated_distance = float(distance)

            # Unit Conversion: Convert everything to 'km' for a standard calculation
            if unit and unit.lower() in ['mile', 'miles']:
                calculated_distance *= 1.60934  # Convert miles to km

            # We assume the factor's 'co2e_per_unit' is always in 'km'
            co2e = calculated_distance * factor.co2e_per_unit

        # 2. Handle serving-based activities (FOOD)
        elif factor.activity_type == 'FOOD':
            # For food, we assume 1 serving unless otherwise specified
            # In the future, the AI could also extract quantity
            co2e = factor.co2e_per_unit  # e.g., 7.8 kg CO2e / 1 serving of steak

        # (You can add logic for 'ENERGY' here later)

        return co2e

    except EmissionFactor.DoesNotExist:
        print(f"Warning: No emission factor found for key: {key}")
        return None

    except Exception as e:
        print(f"Error during calculation: {e}")
        return None
