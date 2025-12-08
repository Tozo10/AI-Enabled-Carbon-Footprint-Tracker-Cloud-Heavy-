# users/carbon_calculator.py
from .models import EmissionFactor

def calculate_co2e(key, quantity, unit):
    """
    Calculates CO2e based on key, quantity, and unit.
    """
    if not key or quantity is None:
        return None

    try:
        # Find the emission factor (case-insensitive)
        factor = EmissionFactor.objects.get(key__iexact=key)
        
        amount = float(quantity)
        co2e = 0.0

        # --- LOGIC FOR TRANSPORT ---
        if factor.activity_type == 'TRANSPORT':
            # Normalize to 'km' because our DB factors are usually in kgCO2e/km
            if unit and unit.lower() in ['mile', 'miles']:
                amount = amount * 1.60934
            
            # Math: Distance (km) * Factor
            co2e = amount * factor.co2e_per_unit

        # --- LOGIC FOR FOOD ---
        elif factor.activity_type == 'FOOD':
            # Normalize Weight (if user says '500g' but factor is 'kg')
            if unit and unit.lower() in ['g', 'gram', 'grams']:
                amount = amount / 1000.0  # Convert grams to kg
            
            # Note: If unit is 'serving' or 'item', we just take the amount as is (e.g., 2 steaks)
            
            # Math: Quantity * Factor
            co2e = amount * factor.co2e_per_unit

        # --- LOGIC FOR ENERGY ---
        elif factor.activity_type == 'ENERGY':
            # Math: Quantity (kWh) * Factor
            co2e = amount * factor.co2e_per_unit

        return round(co2e, 2)

    except EmissionFactor.DoesNotExist:
        print(f"Warning: No emission factor found for key: {key}")
        return None
    except Exception as e:
        print(f"Error during calculation: {e}")
        return None