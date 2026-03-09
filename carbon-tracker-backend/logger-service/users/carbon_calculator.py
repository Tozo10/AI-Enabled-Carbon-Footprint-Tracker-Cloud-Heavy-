try:
    from .models import EmissionFactor
except ImportError:
    EmissionFactor = None

def calculate_co2e(key, quantity, unit, request_user=None):
    print(f"DEBUG: --- CALCULATOR STARTED ---")
    print(f"DEBUG: Input Key='{key}', Qty={quantity}, Unit='{unit}'")

    if not key or quantity is None:
        return 0.0, False

    try:
        quantity = float(quantity)
        factor_value = 0.0
        is_verified = False

        if EmissionFactor:
            ef = None
            
            try:
                # Get all factors matching the key (case-insensitive)
                # Note: views.py already passes the exact DB key (e.g., 'Paneer_Indian')
                factors = EmissionFactor.objects.filter(key__iexact=key)
                
                if factors.exists():
                    # 1. Prioritize explicitly 'verified' factors
                    verified_ef = factors.filter(status='verified').first()
                    
                    if verified_ef:
                        ef = verified_ef
                    else:
                        # 2. Look for the user's specific 'pending' custom factor
                        if request_user:
                            user_ef = factors.filter(status='pending', added_by=request_user).first()
                            if user_ef:
                                ef = user_ef
                        
                        # 3. Fallback for seeded data (if seed_india.py didn't set a status)
                        if not ef:
                            ef = factors.first()
                            
            except Exception as db_err:
                print(f"DEBUG: DB Filter Error (missing columns?): {db_err}")
                # Ultimate safety net for older database schemas
                ef = EmissionFactor.objects.filter(key__iexact=key).first()

            # Extract values if a database record was found
            if ef:
                factor_value = ef.co2e_per_unit
                # Safely determine verification status
                if hasattr(ef, 'status'):
                    is_verified = (ef.status == 'verified')
                else:
                    is_verified = True # Assume seeded core data is verified
                print(f"DEBUG: Found in DB: {factor_value} (Verified: {is_verified})")

        # Fallback to dictionary if DB fails or is completely empty
        if factor_value == 0.0:
            print("DEBUG: Not in DB, checking fallback list...")
            raw_key = str(key).lower().strip()
            
            # Expanded defaults to catch exact keys from your seed data
            defaults = {
                "paneer_indian": 8.2, 
                "paneer": 8.2, 
                "electricity_india_grid": 0.71,
                "electricity": 0.5, 
                "two_wheeler_petrol_100cc": 0.045,
                "auto_rickshaw_cng": 0.08,
                "bus_city_nonac_india": 0.05,
                "car": 0.19
            }
            
            factor_value = defaults.get(raw_key, 0.0)
            is_verified = False 
            print(f"DEBUG: Fallback Factor: {factor_value}")

        result = round(quantity * factor_value, 2)
        print(f"DEBUG: Final Result = {result} kg CO2e")
        return result, is_verified

    except Exception as e:
        print(f"DEBUG: Calculator Error: {e}")
        return 0.0, False