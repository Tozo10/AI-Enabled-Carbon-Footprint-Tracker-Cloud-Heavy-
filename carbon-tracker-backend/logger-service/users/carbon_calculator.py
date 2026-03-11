import logging

logger = logging.getLogger("logger_service")

try:
    from .models import EmissionFactor
except ImportError:
    EmissionFactor = None

# ─────────────────────────────────────────────────────────────────────────────
#  EMISSION FACTOR DEFAULTS
#
#  Used ONLY when a key is not found in the Django DB.
#  Keys are lowercase to match the iexact lookup normalization.
#  Values match your Django admin entries exactly.
#  Add new items to Django admin — they automatically take priority.
# ─────────────────────────────────────────────────────────────────────────────
EMISSION_DEFAULTS = {
    # ── YOUR CURRENT DB ENTRIES (emergency offline fallback) ─────────────────
    "apple":                        0.06,    # kg CO₂e / kg
    "pear":                         0.43,    # kg CO₂e / kg
    "buffalo_milk_packet":          1.70,    # kg CO₂e / litre
    "paneer_indian":                8.20,    # kg CO₂e / kg
    "wheat_atta_india":             1.15,    # kg CO₂e / kg
    "rice_white_india":             3.55,    # kg CO₂e / kg
    "indian_railways_sleeper":      0.02,    # kg CO₂e / km
    "indian_railways_sleeper_train": 0.02,   # kg CO₂e / km
    "bus_city_nonac_india":         0.05,    # kg CO₂e / km
    "two_wheeler_petrol_100cc":     0.045,   # kg CO₂e / km
    "bike_100cc":                   0.045,   # kg CO₂e / km
    "auto_rickshaw_cng":            0.08,    # kg CO₂e / km
    "lpg_cooking_india":            2.98,    # kg CO₂e / kg
    "lpg_cooking_gas_india":        2.98,    # kg CO₂e / kg
    "electricity_india_grid":       0.71,    # kg CO₂e / kWh

    # ── FOOD (not yet in your DB — add via Django admin when ready) ───────────
    "chicken_curry_indian":         6.90,
    "chicken":                      6.90,
    "beef":                        27.00,
    "mutton":                      39.20,
    "lamb":                        39.20,
    "pork":                         7.60,
    "fish":                         3.49,
    "egg":                          4.80,
    "milk":                         3.15,
    "cheese":                      13.50,
    "butter":                      11.90,
    "bread":                        1.00,
    "roti":                         0.90,
    "dal":                          0.90,
    "potato":                       0.46,
    "tomato":                       1.44,
    "onion":                        0.50,
    "banana":                       0.86,
    "orange":                       0.43,
    "coffee":                      17.00,
    "tea":                          0.34,
    "chocolate":                   18.70,
    "sugar":                        3.00,
    "food":                         2.50,   # generic fallback

    # ── ADDITIONAL FOOD ITEMS ─────────────────────────────────────────────────
    # Fast food / Western
    "burger":                       3.50,    # kg CO₂e / piece (~200g beef+bun)
    "pizza":                        1.60,    # kg CO₂e / slice (~150g)
    "sandwich":                     1.20,    # kg CO₂e / piece
    "pasta":                        1.20,    # kg CO₂e / kg
    "noodles":                      1.10,    # kg CO₂e / kg
    "maggi":                        1.10,    # kg CO₂e / kg (instant noodles)

    # Indian snacks / meals
    "samosa":                       0.80,    # kg CO₂e / piece (~100g)
    "idli":                         0.40,    # kg CO₂e / piece (~50g rice+dal)
    "dosa":                         0.60,    # kg CO₂e / piece (~100g)
    "vada":                         0.50,    # kg CO₂e / piece
    "poha":                         0.60,    # kg CO₂e / kg
    "upma":                         0.65,    # kg CO₂e / kg
    "paratha":                      0.90,    # kg CO₂e / piece (~80g wheat+oil)
    "chapati":                      0.90,    # kg CO₂e / piece (same as roti)
    "puri":                         1.00,    # kg CO₂e / piece (fried)
    "dhokla":                       0.50,    # kg CO₂e / kg
    "khichdi":                      1.20,    # kg CO₂e / kg (rice+dal)
    "rajma":                        0.90,    # kg CO₂e / kg
    "chole":                        0.85,    # kg CO₂e / kg
    "pav_bhaji":                    1.40,    # kg CO₂e / plate
    "biryani":                      3.20,    # kg CO₂e / plate (~300g rice+chicken)
    "halwa":                        2.10,    # kg CO₂e / kg (wheat+ghee+sugar)
    "kheer":                        2.80,    # kg CO₂e / kg (milk+rice+sugar)
    "lassi":                        1.50,    # kg CO₂e / litre

    # Fruits & Vegetables
    "mango":                        0.50,    # kg CO₂e / kg
    "grapes":                       0.90,    # kg CO₂e / kg
    "watermelon":                   0.30,    # kg CO₂e / kg
    "papaya":                       0.40,    # kg CO₂e / kg
    "guava":                        0.35,    # kg CO₂e / kg
    "pomegranate":                  0.60,    # kg CO₂e / kg
    "lemon":                        0.40,    # kg CO₂e / kg
    "carrot":                       0.40,    # kg CO₂e / kg
    "spinach":                      0.20,    # kg CO₂e / kg
    "cauliflower":                  0.40,    # kg CO₂e / kg
    "cabbage":                      0.30,    # kg CO₂e / kg
    "brinjal":                      0.35,    # kg CO₂e / kg
    "eggplant":                     0.35,    # kg CO₂e / kg
    "capsicum":                     0.60,    # kg CO₂e / kg
    "cucumber":                     0.25,    # kg CO₂e / kg
    "peas":                         0.80,    # kg CO₂e / kg

    # Dairy & Beverages
    "curd":                         1.60,    # kg CO₂e / kg
    "dahi":                         1.60,    # kg CO₂e / kg
    "ghee":                        15.00,    # kg CO₂e / kg (clarified butter)
    "ice_cream":                    3.50,    # kg CO₂e / kg
    "juice":                        0.80,    # kg CO₂e / litre
    "cold_drink":                   0.40,    # kg CO₂e / litre (soda/cola)
    "soda":                         0.40,    # kg CO₂e / litre
    "cola":                         0.40,    # kg CO₂e / litre
    "water_bottle":                 0.15,    # kg CO₂e / litre (packaged)

    # Nuts & Dry fruits
    "almond":                       3.50,    # kg CO₂e / kg
    "cashew":                       3.00,    # kg CO₂e / kg
    "peanut":                       2.00,    # kg CO₂e / kg
    "groundnut":                    2.00,    # kg CO₂e / kg
    "walnut":                       3.50,    # kg CO₂e / kg

    # ── TRANSPORT (not yet in your DB) ────────────────────────────────────────
    "car_petrol":                   0.192,
    "car_diesel":                   0.171,
    "car_electric":                 0.053,
    "car_cng":                      0.140,
    "car":                          0.192,
    "two_wheeler_petrol":           0.060,
    "two_wheeler_electric":         0.015,
    "motorbike":                    0.114,
    "bus_city_ac_india":            0.082,
    "bus":                          0.089,
    "metro_india":                  0.031,
    "train_india":                  0.041,
    "flight_domestic":              0.255,
    "flight_international":         0.195,
    "flight":                       0.255,
    "taxi":                         0.211,
    "cycle":                        0.000,
    "walk":                         0.000,

    # ── ENERGY (not yet in your DB) ───────────────────────────────────────────
    "png_cooking":                  2.204,
    "natural_gas":                  2.204,
    "firewood":                     1.900,
    "coal":                         2.420,
    "diesel_generator":             2.680,

    # ── WASTE ─────────────────────────────────────────────────────────────────
    "plastic_waste":                6.000,
    "food_waste":                   0.500,
    "paper_waste":                  1.290,
    "ewaste":                      20.000,
    "waste":                        0.500,
}


def calculate_co2e(key, quantity, unit=None, request_user=None):
    """
    Calculates CO₂ equivalent for a given activity.

    DB lookup priority:
      1. 'verified' status factor  (admin-approved, highest trust)
      2. User's own 'pending' custom factor
      3. Any other DB record (legacy seeded data)
      4. EMISSION_DEFAULTS dict   (offline fallback)

    All quantities are assumed to already be in base units (kg, km, kWh)
    by the time they reach this function — unit conversion happens in views.py.

    Returns: (co2e_kg: float, is_verified: bool)
    """
    logger.debug("Calculator: key='%s', qty=%s, unit=%s", key, quantity, unit)

    if not key or quantity is None:
        return 0.0, False

    try:
        quantity = float(quantity)
    except (ValueError, TypeError):
        logger.warning("Invalid quantity '%s' for key '%s'", quantity, key)
        return 0.0, False

    if quantity < 0:
        logger.warning("Negative quantity %.4f for key '%s' — returning 0", quantity, key)
        return 0.0, False

    factor_value = 0.0
    is_verified  = False

    # ── STEP 1: Django database ───────────────────────────────────────────────
    if EmissionFactor:
        try:
            factors = EmissionFactor.objects.filter(key__iexact=key)

            if factors.exists():
                # 1a. Verified by admin
                ef = (
                    factors.filter(status='verified').first()
                    or factors.filter(is_verified_factor=True).first()
                )

                # 1b. User's own pending custom factor
                if not ef and request_user:
                    ef = factors.filter(status='pending', added_by=request_user).first()

                # 1c. Any record (legacy seeded data without status field)
                if not ef:
                    ef = factors.first()

                if ef:
                    factor_value = float(ef.co2e_per_unit)
                    is_verified  = (
                        getattr(ef, 'status', None) == 'verified'
                        or bool(getattr(ef, 'is_verified_factor', False))
                    )
                    logger.debug("DB hit: factor=%.4f, verified=%s", factor_value, is_verified)

        except Exception as db_err:
            logger.error("DB query error for key '%s': %s", key, db_err)
            # Safety net for schema issues (e.g. missing 'status' column)
            try:
                ef = EmissionFactor.objects.filter(key__iexact=key).first()
                if ef:
                    factor_value = float(ef.co2e_per_unit)
                    is_verified  = (
                        getattr(ef, 'status', None) == 'verified'
                        or bool(getattr(ef, 'is_verified_factor', False))
                    )
                    logger.debug("DB fallback hit: factor=%.4f", factor_value)
            except Exception:
                pass

    # ── STEP 2: EMISSION_DEFAULTS dict ───────────────────────────────────────
    if factor_value == 0.0:
        lookup = str(key).lower().strip()
        factor_value = EMISSION_DEFAULTS.get(lookup, 0.0)

        # Try base key (e.g. "bus_city_nonac_india" not found → try "bus")
        if factor_value == 0.0:
            base = lookup.split('_')[0]
            factor_value = EMISSION_DEFAULTS.get(base, 0.0)

        if factor_value != 0.0:
            is_verified = False
            logger.debug("Defaults hit: key='%s', factor=%.4f", lookup, factor_value)
        else:
            logger.warning("No emission factor found for key='%s'", key)

    result = round(quantity * factor_value, 4)
    logger.debug("Result: %.6f × %.4f = %.4f kg CO₂e", quantity, factor_value, result)
    return result, is_verified
