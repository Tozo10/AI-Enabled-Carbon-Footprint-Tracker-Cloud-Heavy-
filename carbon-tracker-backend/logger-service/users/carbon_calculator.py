def calculate_co2e(key, quantity, unit, request_user=None):
    print(f"DEBUG: Input Key='{key}', Qty={quantity}, Unit='{unit}'")
    
    if not key or quantity is None:
        return 0.0, False

    try:
        # Normalize: 'Paneer Indian' -> 'paneer_indian'
        raw_key = str(key).lower().strip()
        search_key = raw_key.replace(" ", "_") 
        
        quantity = float(quantity)
        factor_value = 0.0
        is_verified = False

        if EmissionFactor:
            # 1. Look for the normalized underscore key (Paneer_Indian)
            ef = EmissionFactor.objects.filter(key__iexact=search_key, status='verified').first()
            
            # 2. Look for the raw space key (Paneer Indian)
            if not ef:
                ef = EmissionFactor.objects.filter(key__iexact=raw_key, status='verified').first()

            # 3. Look for User-Added Pending Data
            if not ef and request_user:
                ef = EmissionFactor.objects.filter(
                    key__iexact=search_key, 
                    status='pending', 
                    added_by=request_user
                ).first()

            if ef:
                factor_value = ef.co2e_per_unit
                is_verified = (ef.status == 'verified')
        
        # Fallback to defaults if DB fails
        if factor_value == 0.0:
            defaults = {"paneer": 8.2, "electricity": 0.5, "car": 0.19}
            factor_value = defaults.get(raw_key, 0.0)
            is_verified = False 

        return round(quantity * factor_value, 2), is_verified

    except Exception as e:
        print(f"Error: {e}")
        return 0.0, False