# carbon-tracker-backend/users/carbon_calculator.py

try:
    from .models import EmissionFactor
except ImportError:
    EmissionFactor = None

def calculate_co2e(key, quantity, unit):
    print(f"DEBUG: --- CALCULATOR STARTED ---")
    print(f"DEBUG: Input Key='{key}', Qty={quantity}, Unit='{unit}'")

    if not key or quantity is None:
        return 0.0

    try:
        # 1. Normalize & Synonyms
        raw_key = str(key).lower().strip()
        quantity = float(quantity)
        
        # MAPPING: "cab" -> "car"
        synonyms = {
            "cab": "car", "taxi": "car", "uber": "car", "ride": "car",
            "bus": "public_transport", "metro": "public_transport", "train": "public_transport",
            "burger": "beef", "steak": "beef", "meat": "beef",
            "power": "electricity", "lights": "electricity"
        }

        # Use synonym if exists, otherwise use raw key
        normalized_key = synonyms.get(raw_key, raw_key)
        print(f"DEBUG: Normalized '{raw_key}' -> '{normalized_key}'")

        # 2. Define Factors (Fallback)
        # These are used if the Database is empty or fails
        factors = {
            "car": 0.19,
            "diesel_car": 0.17,
            "public_transport": 0.04,
            "flight": 0.25,
            "beef": 15.5,
            "poultry": 1.8,
            "electricity": 0.5
        }

        # 3. Get Factor
        factor_value = 0.0
        
        # Try Database First
        if EmissionFactor:
            try:
                ef = EmissionFactor.objects.get(key__iexact=normalized_key)
                factor_value = ef.co2e_per_unit
                print(f"DEBUG: Found in DB: {factor_value}")
            except:
                print("DEBUG: Not in DB, checking fallback list...")

        # Try Fallback Second (if DB failed)
        if factor_value == 0.0:
            factor_value = factors.get(normalized_key, 0.0)
            print(f"DEBUG: Fallback Factor: {factor_value}")

        # 4. Calculate
        co2e = quantity * factor_value
        
        # Simple Unit Conversions
        if unit and unit.lower() in ['mile', 'miles']:
            co2e = co2e * 1.6  # Convert miles to km logic

        print(f"DEBUG: Final Result = {co2e}")
        return round(co2e, 2)

    except Exception as e:
        print(f"DEBUG: Calculator Error: {e}")
        return 0.0