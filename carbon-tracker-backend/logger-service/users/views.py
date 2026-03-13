import time
import logging
import nltk
import requests
import re
import traceback
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated, BasePermission
from rest_framework.response import Response
from rest_framework import status
from decouple import config

from .models import EmissionFactor
from .serializers import EmissionFactorSerializer
from thefuzz import fuzz

from .carbon_calculator import calculate_co2e
from .cloudant_db import save_activity_log, get_user_logs_cloudant

from ibm_watson import SpeechToTextV1
from ibm_cloud_sdk_core.authenticators import IAMAuthenticator

# ─────────────────────────────────────────────────────────────────────────────
#  LOGGING  — replaces all print(DEBUG) statements
#  Set LOG_LEVEL=DEBUG in .env for dev, LOG_LEVEL=WARNING for production
# ─────────────────────────────────────────────────────────────────────────────
LOG_LEVEL = config("LOG_LEVEL", default="DEBUG").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.DEBUG),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("logger_service")
AI_SERVICE_URL = config("AI_SERVICE_URL", default="http://ai_engine:5000/analyze")


class IsAuthenticatedOrOptions(BasePermission):
    def has_permission(self, request, view):
        if request.method == "OPTIONS":
            return True
        return bool(request.user and request.user.is_authenticated)

# ─────────────────────────────────────────────────────────────────────────────
#  NLTK SETUP
# ─────────────────────────────────────────────────────────────────────────────
for _resource in ['tokenizers/punkt', 'tokenizers/punkt_tab']:
    try:
        nltk.data.find(_resource)
    except LookupError:
        nltk.download(_resource.split('/')[-1], quiet=True)


# ─────────────────────────────────────────────────────────────────────────────
#  WORD → NUMBER MAPPING
# ─────────────────────────────────────────────────────────────────────────────
WORD_NUM_DICT = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
    'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
    'sixteen': 16, 'seventeen': 17, 'eighteen': 18, 'nineteen': 19, 'twenty': 20,
    'thirty': 30, 'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
    'eighty': 80, 'ninety': 90, 'hundred': 100,
    'half': 0.5, 'quarter': 0.25,
    'twice': 2, 'thrice': 3, 'couple': 2,
    'once': 1, 'double': 2, 'triple': 3,
}

# ─────────────────────────────────────────────────────────────────────────────
#  UNIT ALIASES  — user-typed → canonical
# ─────────────────────────────────────────────────────────────────────────────
UNIT_ALIASES = {
    # Weight
    'kg': 'kg', 'kilogram': 'kg', 'kilograms': 'kg', 'kgs': 'kg',
    'g': 'g', 'gram': 'g', 'grams': 'g', 'gm': 'g', 'gms': 'g',
    'mg': 'mg', 'milligram': 'mg',
    # Distance
    'km': 'km', 'kilometer': 'km', 'kilometres': 'km', 'kilometers': 'km', 'kms': 'km',
    'mile': 'mile', 'miles': 'mile',
    # Volume
    'litre': 'litre', 'liter': 'litre', 'litres': 'litre', 'liters': 'litre',
    'ml': 'ml', 'milliliter': 'ml', 'millilitre': 'ml',
    # Energy
    'kwh': 'kWh', 'kilowatt hour': 'kWh', 'kilowatt-hour': 'kWh',
    # Count
    'piece': 'piece', 'pieces': 'piece', 'slice': 'piece', 'slices': 'piece',
    'serving': 'piece', 'servings': 'piece',
    'plate': 'piece', 'bowl': 'piece', 'cup': 'piece', 'glass': 'piece',
    # Time
    'hour': 'hour', 'hours': 'hour', 'hr': 'hour', 'hrs': 'hour',
    # Generic count (NOT kWh — fixed the dual-meaning bug)
    'unit': 'unit', 'item': 'unit', 'items': 'unit',
}

# ─────────────────────────────────────────────────────────────────────────────
#  HINGLISH → ENGLISH TRANSLATION MAP
# ─────────────────────────────────────────────────────────────────────────────
HINGLISH_MAP = {
    # Food verbs
    'khaya': 'ate', 'khayi': 'ate', 'khana khaya': 'ate food',
    'piya': 'drank', 'pi': 'drank',
    'khana': 'food',
    # Food items
    'chawal': 'rice', 'doodh': 'milk', 'dahi': 'curd',
    'sabji': 'vegetables', 'sabzi': 'vegetables',
    'anda': 'egg', 'murgi': 'chicken',
    'machhli': 'fish', 'gosht': 'mutton',
    'chai': 'tea', 'adrak chai': 'tea',
    'aloo': 'potato', 'tamatar': 'tomato', 'pyaaz': 'onion',
    'aam': 'mango', 'kela': 'banana', 'angoor': 'grapes',
    'gajar': 'carrot', 'palak': 'spinach', 'gobi': 'cauliflower',
    'matar': 'peas', 'baingan': 'brinjal', 'shimla mirch': 'capsicum',
    'kheera': 'cucumber', 'band gobi': 'cabbage',
    'paratha khaya': 'ate paratha', 'dosa khaya': 'ate dosa',
    'idli khaya': 'ate idli', 'biryani khaya': 'ate biryani',
    'samosa khaya': 'ate samosa', 'rajma khaya': 'ate rajma',
    'chole khaye': 'ate chole', 'poha khaya': 'ate poha',
    # Transport verbs
    'gaya': 'travelled', 'gayi': 'travelled', 'gaye': 'travelled',
    'chala': 'drove', 'chali': 'drove',
    'gadi': 'car', 'gaadi': 'car',
    'petrol dala': 'filled petrol car',
    'auto liya': 'took auto',
    'bus liya': 'took bus', 'bus li': 'took bus',
    'train liya': 'took train', 'train li': 'took train',
    # Energy
    'bijli': 'electricity', 'bijli use ki': 'used electricity',
    'gas use ki': 'used gas', 'gas jalaya': 'used gas',
    'ac chalaya': 'used ac', 'fan chalaya': 'used fan',
    # Destinations (transport implied)
    'market gaya': 'travelled to market',
    'office gaya': 'travelled to office',
    'school gaya': 'travelled to school',
}

# ─────────────────────────────────────────────────────────────────────────────
#  CATEGORY KEYWORDS
# ─────────────────────────────────────────────────────────────────────────────
CATEGORY_KEYWORDS = {
    'FOOD': [
        'eat', 'ate', 'had', 'drink', 'drank', 'food', 'meal', 'snack',
        'breakfast', 'lunch', 'dinner', 'cooked', 'cook',
        'burger', 'pizza', 'rice', 'chicken', 'beef', 'mutton', 'fish',
        'egg', 'milk', 'paneer', 'dal', 'roti', 'bread', 'apple',
        'banana', 'pear', 'pears', 'coffee', 'tea', 'chocolate', 'cheese', 'butter',
        'vegetable', 'fruit', 'curry', 'biryani', 'sandwich', 'curd',
        # newly added
        'pasta', 'noodles', 'maggi', 'samosa', 'idli', 'dosa', 'vada',
        'poha', 'upma', 'paratha', 'chapati', 'puri', 'dhokla', 'khichdi',
        'rajma', 'chole', 'pav', 'bhaji', 'halwa', 'kheer', 'lassi',
        'ghee', 'ice cream', 'juice', 'soda', 'cola',
        'mango', 'grapes', 'watermelon', 'papaya', 'guava', 'orange',
        'carrot', 'spinach', 'cauliflower', 'cabbage', 'brinjal',
        'eggplant', 'capsicum', 'cucumber', 'peas', 'potato', 'tomato', 'onion',
        'almond', 'cashew', 'peanut', 'groundnut',
        # hinglish
        'aloo', 'tamatar', 'pyaaz', 'aam', 'kela', 'angoor',
        'gajar', 'palak', 'gobi', 'matar', 'baingan', 'kheera',
    ],
    'TRANSPORT': [
        'drive', 'drove', 'ride', 'rode', 'travel', 'travelled',
        'commute', 'commuted', 'fly', 'flew', 'cab', 'uber', 'ola',
        'bus', 'train', 'metro', 'flight', 'car', 'bike', 'scooter',
        'auto', 'rickshaw', 'cycle', 'walk', 'walked',
        'airport', 'station', 'trip', 'journey',
    ],
    'ENERGY': [
        'light', 'electricity', 'power', 'kwh', 'ac', 'fan',
        'heater', 'geyser', 'appliance', 'charging', 'charged', 'laptop',
        'tv', 'television', 'fridge', 'generator', 'solar', 'gas', 'lpg',
        'cooking', 'oven', 'microwave',
    ],
    'WASTE': [
        'waste', 'trash', 'garbage', 'plastic', 'recycle', 'recycled',
        'threw', 'discarded', 'disposed', 'paper', 'ewaste', 'landfill',
    ],
}

# Generic words excluded from category scoring (they caused false ENERGY hits)
EXCLUDED_FROM_SCORING = {
    'use', 'used', 'using', 'had', 'have', 'took', 'take',
    'went', 'go', 'gone', 'got', 'get',
}

ACTION_VERBS = (
    'used', 'use', 'ate', 'eat', 'had', 'drink', 'drank', 'drunk',
    'drove', 'drive', 'took', 'take', 'travelled', 'traveled', 'travel',
    'rode', 'ride', 'flew', 'fly', 'walked', 'walk', 'cooked', 'cook',
    'made', 'make',
    'burned', 'burnt', 'burn', 'charged', 'charge', 'consumed', 'consume',
    'wasted', 'waste', 'threw', 'throw', 'bought', 'buy', 'purchased',
    'purchase', 'ordered', 'order',
)

# ─────────────────────────────────────────────────────────────────────────────
#  SPECIFIC_KEY_MAP  →  trigger: (category, db_key, natural_unit)
#  DB keys must match your Django admin EXACTLY (lookup is case-insensitive).
# ─────────────────────────────────────────────────────────────────────────────
SPECIFIC_KEY_MAP = {
    # ── FOOD — in your DB ────────────────────────────────────────────────────
    'apple':          ('FOOD',      'apple',                    'piece'),
    'pear':           ('FOOD',      'pear',                     'piece'),
    'pears':          ('FOOD',      'pear',                     'piece'),
    'milk':           ('FOOD',      'Buffalo_Milk_Packet',      'litre'),
    'buffalo milk':   ('FOOD',      'Buffalo_Milk_Packet',      'litre'),
    'doodh':          ('FOOD',      'Buffalo_Milk_Packet',      'litre'),
    'paneer':         ('FOOD',      'Paneer_Indian',            'kg'),
    'wheat':          ('FOOD',      'Wheat_Atta_India',         'kg'),
    'atta':           ('FOOD',      'Wheat_Atta_India',         'kg'),
    'flour':          ('FOOD',      'Wheat_Atta_India',         'kg'),
    'rice':           ('FOOD',      'Rice_White_India',         'kg'),
    'chawal':         ('FOOD',      'Rice_White_India',         'kg'),
    'biryani':        ('FOOD',      'Rice_White_India',         'kg'),
    # ── FOOD — not yet in DB ─────────────────────────────────────────────────
    'chicken':        ('FOOD',      'chicken_curry_indian',     'piece'),
    'murgi':          ('FOOD',      'chicken_curry_indian',     'piece'),
    'dal':            ('FOOD',      'dal',                      'kg'),
    'roti':           ('FOOD',      'roti',                     'piece'),
    'bread':          ('FOOD',      'bread',                    'piece'),
    'egg':            ('FOOD',      'egg',                      'piece'),
    'eggs':           ('FOOD',      'egg',                      'piece'),
    'anda':           ('FOOD',      'egg',                      'piece'),
    'cheese':         ('FOOD',      'cheese',                   'kg'),
    'butter':         ('FOOD',      'butter',                   'kg'),
    'beef':           ('FOOD',      'beef',                     'kg'),
    'mutton':         ('FOOD',      'mutton',                   'kg'),
    'gosht':          ('FOOD',      'mutton',                   'kg'),
    'fish':           ('FOOD',      'fish',                     'kg'),
    'machhli':        ('FOOD',      'fish',                     'kg'),
    'coffee':         ('FOOD',      'coffee',                   'piece'),
    'tea':            ('FOOD',      'tea',                      'piece'),
    'chai':           ('FOOD',      'tea',                      'piece'),
    'chocolate':      ('FOOD',      'chocolate',                'kg'),
    'burger':         ('FOOD',      'burger',                   'piece'),
    'pizza':          ('FOOD',      'pizza',                    'piece'),
    'sandwich':       ('FOOD',      'sandwich',                 'piece'),
    'pasta':          ('FOOD',      'pasta',                    'kg'),
    'noodles':        ('FOOD',      'noodles',                  'kg'),
    'maggi':          ('FOOD',      'maggi',                    'kg'),
    'banana':         ('FOOD',      'banana',                   'piece'),
    'curd':           ('FOOD',      'curd',                     'kg'),
    'dahi':           ('FOOD',      'dahi',                     'kg'),
    'lassi':          ('FOOD',      'lassi',                    'litre'),
    'ghee':           ('FOOD',      'ghee',                     'kg'),
    'ice cream':      ('FOOD',      'ice_cream',                'kg'),
    'juice':          ('FOOD',      'juice',                    'litre'),
    'cold drink':     ('FOOD',      'cold_drink',               'litre'),
    'soda':           ('FOOD',      'soda',                     'litre'),
    'cola':           ('FOOD',      'cola',                     'litre'),
    # Indian snacks
    'samosa':         ('FOOD',      'samosa',                   'piece'),
    'idli':           ('FOOD',      'idli',                     'piece'),
    'dosa':           ('FOOD',      'dosa',                     'piece'),
    'vada':           ('FOOD',      'vada',                     'piece'),
    'poha':           ('FOOD',      'poha',                     'kg'),
    'upma':           ('FOOD',      'upma',                     'kg'),
    'paratha':        ('FOOD',      'paratha',                  'piece'),
    'chapati':        ('FOOD',      'chapati',                  'piece'),
    'puri':           ('FOOD',      'puri',                     'piece'),
    'dhokla':         ('FOOD',      'dhokla',                   'kg'),
    'khichdi':        ('FOOD',      'khichdi',                  'kg'),
    'rajma':          ('FOOD',      'rajma',                    'kg'),
    'chole':          ('FOOD',      'chole',                    'kg'),
    'pav bhaji':      ('FOOD',      'pav_bhaji',                'piece'),
    'biryani':        ('FOOD',      'biryani',                  'piece'),
    'halwa':          ('FOOD',      'halwa',                    'kg'),
    'kheer':          ('FOOD',      'kheer',                    'kg'),
    # Fruits
    'mango':          ('FOOD',      'mango',                    'piece'),
    'grapes':         ('FOOD',      'grapes',                   'kg'),
    'watermelon':     ('FOOD',      'watermelon',               'kg'),
    'papaya':         ('FOOD',      'papaya',                   'kg'),
    'guava':          ('FOOD',      'guava',                    'piece'),
    'orange':         ('FOOD',      'orange',                   'piece'),
    # Vegetables
    'carrot':         ('FOOD',      'carrot',                   'kg'),
    'spinach':        ('FOOD',      'spinach',                  'kg'),
    'cauliflower':    ('FOOD',      'cauliflower',              'piece'),
    'cabbage':        ('FOOD',      'cabbage',                  'piece'),
    'brinjal':        ('FOOD',      'brinjal',                  'kg'),
    'eggplant':       ('FOOD',      'eggplant',                 'kg'),
    'capsicum':       ('FOOD',      'capsicum',                 'kg'),
    'cucumber':       ('FOOD',      'cucumber',                 'piece'),
    'peas':           ('FOOD',      'peas',                     'kg'),
    'potato':         ('FOOD',      'potato',                   'kg'),
    'tomato':         ('FOOD',      'tomato',                   'kg'),
    'onion':          ('FOOD',      'onion',                    'kg'),
    # Nuts
    'almond':         ('FOOD',      'almond',                   'kg'),
    'cashew':         ('FOOD',      'cashew',                   'kg'),
    'peanut':         ('FOOD',      'peanut',                   'kg'),
    'groundnut':      ('FOOD',      'groundnut',                'kg'),
    # Generic
    'vegetables':     ('FOOD',      'food',                     'kg'),
    'sabji':          ('FOOD',      'food',                     'kg'),
    'sabzi':          ('FOOD',      'food',                     'kg'),
    # ── ENERGY — in your DB ───────────────────────────────────────────────────
    'cooking gas':    ('ENERGY',    'LPG_Cooking_Gas_India',    'kg'),
    'lpg':            ('ENERGY',    'LPG_Cooking_Gas_India',    'kg'),
    'gas':            ('ENERGY',    'LPG_Cooking_Gas_India',    'kg'),
    'cylinder':       ('ENERGY',    'LPG_Cooking_Gas_India',    'kg'),
    'electricity':    ('ENERGY',    'Electricity_India_Grid',   'kWh'),
    'bijli':          ('ENERGY',    'Electricity_India_Grid',   'kWh'),
    'power':          ('ENERGY',    'Electricity_India_Grid',   'kWh'),
    'current':        ('ENERGY',    'Electricity_India_Grid',   'kWh'),
    'ac':             ('ENERGY',    'Electricity_India_Grid',   'kWh'),
    'fan':            ('ENERGY',    'Electricity_India_Grid',   'kWh'),
    'heater':         ('ENERGY',    'Electricity_India_Grid',   'kWh'),
    'geyser':         ('ENERGY',    'Electricity_India_Grid',   'kWh'),
    'fridge':         ('ENERGY',    'Electricity_India_Grid',   'kWh'),
    'tv':             ('ENERGY',    'Electricity_India_Grid',   'kWh'),
    'laptop':         ('ENERGY',    'Electricity_India_Grid',   'kWh'),
    # ── ENERGY — not yet in DB ────────────────────────────────────────────────
    'png':            ('ENERGY',    'png_cooking',              'kg'),
    'coal':           ('ENERGY',    'coal',                     'kg'),
    'firewood':       ('ENERGY',    'firewood',                 'kg'),
    'generator':      ('ENERGY',    'diesel_generator',         'litre'),
    # ── TRANSPORT — in your DB ────────────────────────────────────────────────
    'indian railway': ('TRANSPORT', 'Indian_Railways_Sleeper_Train', 'km'),
    'train':          ('TRANSPORT', 'Indian_Railways_Sleeper_Train', 'km'),
    'railway':        ('TRANSPORT', 'Indian_Railways_Sleeper_Train', 'km'),
    'railways':       ('TRANSPORT', 'Indian_Railways_Sleeper_Train', 'km'),
    'sleeper':        ('TRANSPORT', 'Indian_Railways_Sleeper_Train', 'km'),
    'bus':            ('TRANSPORT', 'Bus_City_NonAC_India',     'km'),
    'two wheeler':    ('TRANSPORT', 'Bike_100cc',               'km'),
    'bike':           ('TRANSPORT', 'Bike_100cc',               'km'),
    'scooter':        ('TRANSPORT', 'Bike_100cc',               'km'),
    'scooty':         ('TRANSPORT', 'Bike_100cc',               'km'),
    'activa':         ('TRANSPORT', 'Bike_100cc',               'km'),
    'autorickshaw':   ('TRANSPORT', 'Auto_Rickshaw_CNG',        'km'),
    'auto rickshaw':  ('TRANSPORT', 'Auto_Rickshaw_CNG',        'km'),
    'auto':           ('TRANSPORT', 'Auto_Rickshaw_CNG',        'km'),
    'rickshaw':       ('TRANSPORT', 'Auto_Rickshaw_CNG',        'km'),
    # ── TRANSPORT — not yet in DB ─────────────────────────────────────────────
    'diesel car':     ('TRANSPORT', 'car_diesel',               'km'),
    'petrol car':     ('TRANSPORT', 'car_petrol',               'km'),
    'electric car':   ('TRANSPORT', 'car_electric',             'km'),
    'cng car':        ('TRANSPORT', 'car_cng',                  'km'),
    'car':            ('TRANSPORT', 'car_petrol',               'km'),
    'metro':          ('TRANSPORT', 'metro_india',              'km'),
    'cab':            ('TRANSPORT', 'taxi',                     'km'),
    'uber':           ('TRANSPORT', 'taxi',                     'km'),
    'ola':            ('TRANSPORT', 'taxi',                     'km'),
    'cycle':          ('TRANSPORT', 'cycle',                    'km'),
    'bicycle':        ('TRANSPORT', 'cycle',                    'km'),
    'walk':           ('TRANSPORT', 'walk',                     'km'),
    'walked':         ('TRANSPORT', 'walk',                     'km'),
    'flight':         ('TRANSPORT', 'flight_domestic',          'km'),
    'flew':           ('TRANSPORT', 'flight_domestic',          'km'),
    'fly':            ('TRANSPORT', 'flight_domestic',          'km'),
    'airplane':       ('TRANSPORT', 'flight_domestic',          'km'),
    # ── WASTE ─────────────────────────────────────────────────────────────────
    'plastic':        ('WASTE',     'plastic_waste',            'kg'),
    'paper':          ('WASTE',     'paper_waste',              'kg'),
    'ewaste':         ('WASTE',     'ewaste',                   'kg'),
}

# ─────────────────────────────────────────────────────────────────────────────
#  PIECE → KG CONVERSION  (average weight of one piece/serving)
# ─────────────────────────────────────────────────────────────────────────────
PIECE_TO_KG = {
    'apple':        0.182,   # medium apple
    'pear':         0.178,   # medium pear
    'banana':       0.120,
    'orange':       0.160,
    'mango':        0.300,   # medium mango
    'guava':        0.100,
    'chicken':      0.300,   # 1 serving/piece
    'murgi':        0.300,
    'egg':          0.060,
    'anda':         0.060,
    'roti':         0.040,   # 1 roti
    'bread':        0.030,   # 1 slice
    'burger':       0.200,
    'pizza':        0.150,   # per slice
    'sandwich':     0.180,
    'samosa':       0.100,   # 1 samosa
    'idli':         0.050,   # 1 idli
    'dosa':         0.100,   # 1 dosa
    'vada':         0.080,
    'paratha':      0.080,
    'chapati':      0.040,
    'puri':         0.040,
    'biryani':      0.350,   # 1 plate
    'pav_bhaji':    0.300,   # 1 plate
    'cauliflower':  0.600,   # 1 whole head
    'cabbage':      0.800,   # 1 whole head
    'cucumber':     0.200,   # 1 cucumber
    'coffee':       0.007,   # dry grounds per cup
    'tea':          0.002,   # dry leaves per cup
    'chai':         0.002,
}

# ─────────────────────────────────────────────────────────────────────────────
#  DB KEY CACHE  (5-minute TTL, avoids repeated full-table queries)
# ─────────────────────────────────────────────────────────────────────────────
_DB_KEY_CACHE      = None
_DB_KEY_CACHE_TIME = 0
DB_KEY_CACHE_TTL   = 300   # seconds
_USAGE_CACHE = {}
USAGE_CACHE_TTL = 300


def get_cached_emission_keys() -> list:
    global _DB_KEY_CACHE, _DB_KEY_CACHE_TIME
    now = time.time()
    if _DB_KEY_CACHE is None or (now - _DB_KEY_CACHE_TIME) > DB_KEY_CACHE_TTL:
        try:
            _DB_KEY_CACHE = list(EmissionFactor.objects.values_list('key', flat=True))
            _DB_KEY_CACHE_TIME = now
            logger.debug("DB key cache refreshed: %d keys loaded", len(_DB_KEY_CACHE))
        except Exception as e:
            logger.warning("DB key cache refresh failed: %s", e)
            _DB_KEY_CACHE = []
    return _DB_KEY_CACHE


AMBIGUITY_STOPWORDS = {
    'i', 'a', 'an', 'the', 'and', 'or', 'to', 'for', 'of', 'in', 'on', 'with',
    'my', 'your', 'our', 'their', 'his', 'her', 'this', 'that', 'these', 'those',
    'used', 'use', 'ate', 'eat', 'had', 'have', 'took', 'take', 'travelled',
    'traveled', 'travel', 'drove', 'drive', 'rode', 'ride', 'bought', 'buy',
    'ordered', 'order', 'consumed', 'consume', 'km', 'mile', 'miles', 'kg',
    'g', 'gram', 'grams', 'kwh', 'litre', 'liter', 'piece', 'pieces', 'serving',
    'servings', 'unit', 'units', 'cc',
}


def normalize_factor_label(key: str) -> str:
    label = (key or '').replace('_', ' ').strip()
    label = re.sub(r'(?i)\bnonac\b', 'non ac', label)
    label = re.sub(r'(?i)(\d+)\s*cc\b', r'\1cc', label)
    return re.sub(r'\s+', ' ', label).strip()


def normalize_matching_token(token: str) -> str:
    token = (token or '').lower().strip()
    if re.fullmatch(r'\d+cc|\d+\.\d+|\d+', token):
        return token
    if len(token) > 4 and token.endswith('ies'):
        return token[:-3] + 'y'
    if len(token) > 3 and token.endswith('s') and not token.endswith('ss'):
        return token[:-1]
    return token


def tokenize_for_matching(text: str) -> list:
    normalized = normalize_factor_label(text).lower()
    raw_tokens = re.findall(r'[a-z]+|\d+cc|\d+\.\d+|\d+', normalized)
    return [normalize_matching_token(token) for token in raw_tokens]


def normalize_text_for_matching(text: str) -> str:
    return " ".join(tokenize_for_matching(text))


def get_usage_counts(keys: list) -> dict:
    if not keys:
        return {}

    cache_key = tuple(sorted(keys))
    cached = _USAGE_CACHE.get(cache_key)
    now = time.time()
    if cached and (now - cached["ts"]) <= USAGE_CACHE_TTL:
        return cached["counts"]

    counts = {key: 0 for key in keys}
    try:
        from .cloudant_db import get_cloudant_client
        client = get_cloudant_client()
        if client:
            result = client.post_all_docs(db="activity-logs", include_docs=True).get_result()
            for row in result.get("rows", []):
                doc = row.get("doc") or {}
                key = doc.get("key")
                if key in counts:
                    counts[key] += 1
    except Exception as exc:
        logger.debug("Usage count lookup failed: %s", exc)

    _USAGE_CACHE[cache_key] = {"ts": now, "counts": counts}
    return counts


def build_ambiguity_options(candidates, usage_counts):
    if not candidates:
        return []

    highest_usage = max((usage_counts.get(item.key, 0) for item in candidates), default=0)
    options = []
    for item in candidates:
        usage_count = usage_counts.get(item.key, 0)
        options.append({
            "key": item.key,
            "label": normalize_factor_label(item.key),
            "unit": item.unit,
            "activity_type": item.activity_type,
            "usage_count": usage_count,
            "is_most_used": usage_count == highest_usage and highest_usage > 0,
        })
    return sorted(options, key=lambda opt: (-opt["usage_count"], opt["label"].lower()))


def resolve_ambiguous_factor(sentence: str, activity_type: str, inferred_key: str, clarification_key: str = None):
    if not inferred_key or activity_type == 'Unknown':
        return inferred_key, None

    if clarification_key:
        selected = EmissionFactor.objects.filter(
            activity_type__iexact=activity_type,
            key__iexact=clarification_key,
        ).first()
        if selected:
            return selected.key, None

    sentence_tokens = {
        token for token in tokenize_for_matching(sentence)
        if token not in AMBIGUITY_STOPWORDS and not token.isdigit()
    }
    key_tokens = {
        token for token in tokenize_for_matching(inferred_key)
        if token not in AMBIGUITY_STOPWORDS and not token.isdigit()
    }
    normalized_key_tokens = tokenize_for_matching(inferred_key)
    generic_key_tokens = {normalized_key_tokens[0]} if normalized_key_tokens else set()
    search_tokens = sentence_tokens or generic_key_tokens
    if not search_tokens:
        return inferred_key, None

    candidates = []
    for factor in EmissionFactor.objects.filter(activity_type__iexact=activity_type):
        factor_tokens = set(tokenize_for_matching(factor.key))
        overlap = (factor_tokens & search_tokens)
        if overlap:
            candidates.append((factor, factor_tokens, len(overlap)))

    if len(candidates) <= 1:
        return inferred_key, None

    candidates.sort(key=lambda item: (-item[2], normalize_factor_label(item[0].key).lower()))
    top_overlap = candidates[0][2]
    top_candidates = [item for item in candidates if item[2] == top_overlap]

    descriptor_matches = []
    for factor, factor_tokens, _ in top_candidates:
        descriptor_tokens = factor_tokens - generic_key_tokens
        explicit_descriptors = descriptor_tokens & sentence_tokens
        descriptor_matches.append((factor, explicit_descriptors))

    strong_matches = [item for item in descriptor_matches if item[1]]
    if len(strong_matches) == 1:
        return strong_matches[0][0].key, None

    ambiguous_factors = [item[0] for item in top_candidates]
    usage_counts = get_usage_counts([factor.key for factor in ambiguous_factors])
    return inferred_key, {
        "sentence": sentence,
        "activity_type": activity_type,
        "inferred_key": inferred_key,
        "message": f"Multiple matches found for '{sentence}'. Please choose one.",
        "options": build_ambiguity_options(ambiguous_factors, usage_counts),
    }


# ─────────────────────────────────────────────────────────────────────────────
#  STT SERVICE
# ─────────────────────────────────────────────────────────────────────────────
def get_stt_service():
    auth = IAMAuthenticator(config("STT_APIKEY"))
    stt  = SpeechToTextV1(authenticator=auth)
    stt.set_service_url(config("STT_URL"))
    return stt


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: HINGLISH TRANSLATION
# ─────────────────────────────────────────────────────────────────────────────
def apply_hinglish_translation(text: str) -> str:
    text_lower = text.lower()
    for phrase in sorted(HINGLISH_MAP.keys(), key=len, reverse=True):
        if phrase in text_lower:
            text_lower = text_lower.replace(phrase, HINGLISH_MAP[phrase])
    return text_lower


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: CONTEXT-AWARE QUANTITY EXTRACTION
#  Finds the number CLOSEST TO a unit keyword for maximum accuracy.
# ─────────────────────────────────────────────────────────────────────────────
def extract_quantity(text: str) -> tuple:
    """
    Returns (quantity: float, inferred: bool).
    inferred=True means nothing was found and 1.0 was assumed.

    Step order is critical:
      0. Fraction FIRST  — "1/2 kg" must return 0.5, not 2.0
      1. Number+unit     — handles multi-char units AND bare 'g' glued to digit
      2. Standalone num
      3. Word numbers
      4. Bare a/an = 1
      5. Fallback 1.0 (inferred)
    """
    text_lower = text.lower().strip()

    # 0. Written fraction FIRST: "1/2", "3/4", "1/2 kg lpg"
    frac = re.search(r'(?<!\d)(\d+)\s*/\s*(\d+)(?!\d)', text_lower)
    if frac:
        return round(int(frac.group(1)) / int(frac.group(2)), 4), False

    # 1. Number immediately before a multi-char unit keyword
    unit_pattern = (
        r'(\d+\.?\d*|\.\d+)\s*'
        r'(kg|kgs|grams|gram|gm|gms|mg|km|kms|kilometers|kilometres|miles?|'
        r'kWh|kwh|litres?|liters?|'
        r'piece|pieces|slice|slices|serving|servings|plate|bowl|cup|glass|'
        r'hour|hours|hr|hrs)'
        r'(?![a-z])'
    )
    matches = re.findall(unit_pattern, text_lower, re.IGNORECASE)
    if matches:
        return float(matches[0][0]), False

    # 1b. Digit immediately followed by bare 'g' (no space): "200g", "0.5g"
    g_match = re.search(r'(\d+\.?\d*)\s*g(?!r)(?![a-z])', text_lower)
    if g_match:
        return float(g_match.group(1)), False

    # 2. Any standalone number
    num = re.search(r'(\d+\.\d+|\d+|\.\d+)', text_lower)
    if num:
        return float(num.group(1)), False

    # 3. Word numbers (skip unit/article words)
    SKIP = {'kg','km','kwh','gram','g','litre','liter','unit','units',
            'serving','plate','piece','slice','glass','bowl','cup','a','an'}
    words = re.findall(r'\b[a-z]+\b', text_lower)
    total, found_any = 0.0, False
    for word in words:
        if word in SKIP:
            continue
        if word in WORD_NUM_DICT:
            total += WORD_NUM_DICT[word]
            found_any = True
    if found_any:
        return (total if total > 0 else 1.0), False

    # 4. Bare article "a"/"an" = 1
    if re.search(r'\b(a|an)\b', text_lower):
        return 1.0, False

    # 5. Nothing found — assume 1 and flag it
    return 1.0, True


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: UNIT DETECTION FROM SENTENCE TEXT
# ─────────────────────────────────────────────────────────────────────────────
def detect_unit_from_text(text: str):
    """
    Returns canonical unit string if an explicit unit is mentioned, else None.
    Handles:
      - 'g' glued to digit: "200g", "500g" (no word boundary)
      - 'ml' similarly glued
      - 'units' → kWh only in electricity context (fixes the dual-meaning bug)
    """
    text_lower = text.lower()

    # Check multi-char aliases first (normal word boundaries work fine)
    multi_char = [k for k in UNIT_ALIASES if len(k) > 1]
    for raw in sorted(multi_char, key=len, reverse=True):
        if re.search(r'\b' + re.escape(raw) + r'\b', text_lower):
            if raw in ('unit', 'units', 'items', 'item'):
                energy_words = {'electricity', 'bijli', 'power', 'current', 'kwh'}
                return 'kWh' if any(w in text_lower for w in energy_words) else 'unit'
            return UNIT_ALIASES[raw]

    # Single-char 'g' — may be glued to digit (no word boundary): "200g"
    if re.search(r'(?<!\w)kg\b|\bkg(?=\s|$)|\d\s*kg\b', text_lower):
        return 'kg'
    if re.search(r'\d\s*g(?!r)(?![a-z])', text_lower):
        return 'g'
    if re.search(r'\d\s*ml\b', text_lower):
        return 'ml'
    if re.search(r'\bkm\b', text_lower):
        return 'km'

    return None


def normalize_unit(raw_unit: str) -> str:
    if not raw_unit:
        return ''
    return UNIT_ALIASES.get(raw_unit.lower().strip(), raw_unit.strip())


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: BASE UNIT NORMALIZATION  (g→kg, mg→kg, ml→litre, mile→km)
# ─────────────────────────────────────────────────────────────────────────────
def normalize_to_base_unit(quantity: float, unit: str) -> tuple:
    u = (unit or '').lower().strip()
    if u == 'g':     return round(quantity / 1000, 6),       'kg'
    if u == 'mg':    return round(quantity / 1_000_000, 9),  'kg'
    if u == 'ml':    return round(quantity / 1000, 6),       'litre'
    if u == 'mile':  return round(quantity * 1.60934, 4),    'km'
    return quantity, unit


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: PIECE → KG CONVERSION
# ─────────────────────────────────────────────────────────────────────────────
def apply_piece_to_kg(key: str, quantity: float, unit: str) -> tuple:
    if unit != 'piece':
        return quantity, unit
    base = key.lower().split('_')[0]
    if base in PIECE_TO_KG:
        return round(quantity * PIECE_TO_KG[base], 4), 'kg'
    return quantity, unit


# ─────────────────────────────────────────────────────────────────────────────
#  HELPER: REMAP AI KEY → EXACT DJANGO ADMIN DB KEY
# ─────────────────────────────────────────────────────────────────────────────
def remap_ai_key(ai_key: str, ai_category: str) -> tuple:
    """
    The AI service returns its own key names that may not match Django admin.
    This maps them to exact DB keys via SPECIFIC_KEY_MAP.
    Returns (db_key, category, natural_unit).
    """
    if not ai_key:
        return ai_key, ai_category, 'unit'
    key_lower = normalize_text_for_matching(ai_key)
    for trigger in sorted(SPECIFIC_KEY_MAP.keys(), key=len, reverse=True):
        trigger_normalized = normalize_text_for_matching(trigger)
        if (
            trigger_normalized in key_lower
            or key_lower == trigger_normalized
            or (key_lower.split() and trigger_normalized == normalize_matching_token(key_lower.split()[0]))
        ):
            cat, db_key, nat_unit = SPECIFIC_KEY_MAP[trigger]
            logger.debug("AI key remapped: '%s' → '%s' (%s)", ai_key, db_key, cat)
            return db_key, cat, nat_unit
    return ai_key, ai_category, 'unit'


# ─────────────────────────────────────────────────────────────────────────────
#  CLASSIFIER: LOCAL FALLBACK
# ─────────────────────────────────────────────────────────────────────────────
def fallback_classify(text: str) -> tuple:
    """
    Returns (activity_type, db_key, quantity, unit, qty_inferred).
    Priority:
      1. SPECIFIC_KEY_MAP  (authoritative — category + key + unit set together)
      2. Category keyword scoring (fuzzy; generic words excluded)
      3. DB fuzzy key search (5-min cached)
      4. Generic category fallback
    """
    text_translated = apply_hinglish_translation(text)
    text_lower      = text_translated.lower()
    normalized_text = normalize_text_for_matching(text_lower)
    words           = tokenize_for_matching(text_lower)
    quantity, qty_inferred = extract_quantity(text_lower)
    detected_unit   = detect_unit_from_text(text_lower)

    # ── STEP 1: SPECIFIC_KEY_MAP ─────────────────────────────────────────────
    for trigger in sorted(SPECIFIC_KEY_MAP.keys(), key=len, reverse=True):
        trigger_normalized = normalize_text_for_matching(trigger)
        if re.search(r'\b' + re.escape(trigger_normalized) + r'\b', normalized_text):
            category, db_key, natural_unit = SPECIFIC_KEY_MAP[trigger]
            unit = detected_unit if detected_unit else natural_unit
            logger.debug("SPECIFIC_KEY_MAP: trigger='%s' → %s / %s / %s",
                         trigger, category, db_key, unit)
            return category, db_key, quantity, unit, qty_inferred

    # ── STEP 2: Category keyword scoring ────────────────────────────────────
    scores = {cat: 0 for cat in CATEGORY_KEYWORDS}
    for cat, keywords in CATEGORY_KEYWORDS.items():
        for word in words:
            if word in EXCLUDED_FROM_SCORING:
                continue
            for kw in keywords:
                if fuzz.ratio(word, kw) >= 82:
                    scores[cat] += 1

    best_cat = max(scores, key=scores.get)
    if scores[best_cat] == 0:
        return 'Unknown', None, 0, None, False

    DEFAULT_UNITS = {'FOOD': 'kg', 'TRANSPORT': 'km', 'ENERGY': 'kWh', 'WASTE': 'kg'}
    unit = detected_unit or DEFAULT_UNITS.get(best_cat, 'unit')

    # ── STEP 3: DB fuzzy key search (cached) ────────────────────────────────
    found_key, best_score = None, 0
    for db_key in get_cached_emission_keys():
        clean = normalize_text_for_matching(db_key)
        if clean in normalized_text:
            found_key = db_key
            break
        for word in words:
            for part in [p for p in clean.split() if len(p) > 2]:
                score = fuzz.ratio(word, part)
                if score > best_score and score >= 80:
                    best_score = score
                    found_key  = db_key

    # ── STEP 4: Generic fallback ─────────────────────────────────────────────
    if not found_key:
        GENERIC = {
            'FOOD': 'food', 'TRANSPORT': 'car_petrol',
            'ENERGY': 'Electricity_India_Grid', 'WASTE': 'waste',
        }
        found_key = GENERIC.get(best_cat)

    return best_cat, found_key, quantity, unit, qty_inferred


# ─────────────────────────────────────────────────────────────────────────────
#  TEXT NORMALIZER
# ─────────────────────────────────────────────────────────────────────────────
def normalize_input_text(raw: str) -> str:
    text = raw.strip()
    text = text.replace('\r\n', '. ').replace('\n', '. ').replace('\r', '. ')
    text = re.sub(r'^\s*[-•*]\s+', '', text, flags=re.MULTILINE)
    text = text.replace(';', '.').replace(' / ', '. ')
    # Hindi/Hinglish conjunctions → sentence boundary
    text = re.sub(r'\baur\b', ' . ', text, flags=re.IGNORECASE)   # Hindi 'and'
    text = re.sub(r'\btatha\b', ' . ', text, flags=re.IGNORECASE) # Hindi 'and also'
    text = re.sub(r'\band\s+i\b', '. I', text, flags=re.IGNORECASE)
    text = re.sub(
        r'\band\s+(used|use|ate|eat|had|drink|drank|drunk|drove|drive|took|take|'
        r'travelled|traveled|travel|rode|ride|flew|fly|walked|walk|cooked|cook|made|make|'
        r'burned|burnt|burn|charged|charge|consumed|consume|wasted|waste|threw|throw|'
        r'bought|buy|purchased|purchase|ordered|order)\b',
        r'. \1', text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'\b(and then|and also|after that|then i|then|also|moreover|additionally)\b',
        '. ', text, flags=re.IGNORECASE
    )
    text = re.sub(
        r'\bor\s+(?=(?:i\s+)?(?:' + '|'.join(ACTION_VERBS) + r')\b)',
        '. ', text, flags=re.IGNORECASE
    )
    text = re.sub(r',\s*(?=[a-zA-Z])', '. ', text)
    text = re.sub(r'\.{2,}', '.', text)
    text = re.sub(r'\s{2,}', ' ', text)
    return text.strip()


def split_activity_clauses(text: str):
    """
    Break normalized text into atomic activity clauses so numbers stay tied to
    the correct entity.
    """
    fragments = [frag.strip(" .") for frag in nltk.tokenize.sent_tokenize(text) if frag.strip(" .")]
    clauses = []
    verb_pattern = '|'.join(re.escape(v) for v in ACTION_VERBS)

    for fragment in fragments:
        parts = re.split(
            r'\s*(?:,| and | or )\s*(?=(?:i\s+)?(?:' + verb_pattern + r')\b)',
            fragment,
            flags=re.IGNORECASE,
        )
        for part in parts:
            infinitive_parts = re.split(
                r'\s+to\s+(?=(?:' + verb_pattern + r')\b)',
                part,
                flags=re.IGNORECASE,
            )
            for infinitive_part in infinitive_parts:
                subparts = re.split(
                    r'\s+(?:and|or)\s+(?=(?:\d+(?:\.\d+)?|\.\d+|a|an|one|two|three|four|five|six|seven|eight|nine|ten)\b)',
                    infinitive_part,
                    flags=re.IGNORECASE,
                )
                for subpart in subparts:
                    clean = subpart.strip(" .")
                    if len(clean) > 2:
                        clauses.append(clean)

    return clauses


# ─────────────────────────────────────────────────────────────────────────────
#  CORE PROCESSING ENGINE
# ─────────────────────────────────────────────────────────────────────────────
def process_text_to_carbon(input_text: str, user_obj, clarifications=None):
    username = user_obj.username
    normalized_text = normalize_input_text(input_text)
    sentences = split_activity_clauses(normalized_text)
    logger.info("Processing %d activity clause(s) for user '%s'", len(sentences), username)

    clarifications = clarifications or {}
    pending_activities = []
    failed_sentences = []
    global_warnings = []
    total_co2 = 0.0
    batch_id = f"batch_{int(time.time())}"

    for index, sentence in enumerate(sentences):
        clean_text = sentence.strip()
        logger.debug("Processing: '%s'", clean_text)

        activity_type = 'Unknown'
        key = None
        quantity = 0.0
        unit = None
        qty_inferred = False
        analysis_results = None

        try:
            ai_resp = requests.post(
                AI_SERVICE_URL,
                json={"username": username, "input_text": clean_text},
                timeout=5,
            )
            if ai_resp.status_code == 200:
                extracted = ai_resp.json().get("extracted", [])
                if isinstance(extracted, list) and extracted:
                    analysis_results = extracted[0]
                elif isinstance(extracted, dict):
                    analysis_results = extracted
        except Exception as e:
            logger.debug("AI service unavailable: %s", e)

        if analysis_results and "error" not in analysis_results:
            ai_key = analysis_results.get('key')
            ai_type = analysis_results.get('activity_type', 'Unknown')
            key, activity_type, nat_unit = remap_ai_key(ai_key, ai_type)

            raw_qty = analysis_results.get('quantity')
            try:
                parsed_qty = float(raw_qty) if raw_qty is not None else 0
            except (ValueError, TypeError):
                parsed_qty = 0

            quantity, qty_inferred = (parsed_qty, False) if parsed_qty > 0 else extract_quantity(clean_text)
            detected = detect_unit_from_text(clean_text)
            unit = detected or normalize_unit(analysis_results.get('unit', '')) or nat_unit
            logger.debug("AI: type=%s key=%s qty=%s unit=%s", activity_type, key, quantity, unit)

        if activity_type == 'Unknown' or not key:
            logger.debug("Falling back to local classifier")
            activity_type, key, quantity, unit, qty_inferred = fallback_classify(clean_text)
            logger.debug("Fallback: type=%s key=%s qty=%s unit=%s", activity_type, key, quantity, unit)

        if activity_type == 'Unknown' or not key:
            logger.info("Unrecognized, skipping: '%s'", clean_text)
            failed_sentences.append(f"{clean_text} (Not Recognized)")
            continue

        clarification_key = clarifications.get(clean_text) or clarifications.get(str(index))
        key, ambiguity = resolve_ambiguous_factor(
            clean_text,
            activity_type,
            key,
            clarification_key=clarification_key,
        )
        if ambiguity:
            ambiguity["index"] = index
            return Response({
                "status": "needs_clarification",
                "transcript": input_text,
                "message": "Multiple emission factors matched. Please choose the correct option and submit again.",
                "clarifications": [ambiguity],
                "failed_sentences": failed_sentences,
                "warnings": global_warnings,
            }, status=status.HTTP_409_CONFLICT)

        if not quantity or quantity <= 0:
            quantity, qty_inferred = extract_quantity(clean_text)
        if not quantity or quantity <= 0:
            quantity, qty_inferred = 1.0, True

        quantity, unit = apply_piece_to_kg(key, quantity, unit)
        quantity, unit = normalize_to_base_unit(quantity, unit)

        activity_warnings = []
        if qty_inferred:
            msg = f"Quantity assumed as 1 for '{clean_text}' ? please specify for accuracy"
            activity_warnings.append(msg)
            global_warnings.append(msg)
            logger.warning(msg)

        co2e, is_verified = calculate_co2e(key, quantity, unit, request_user=user_obj)
        activity_ts = int(time.time() * 1000) + len(pending_activities)
        pending_activities.append({
            "username": username,
            "input_text": clean_text,
            "activity_type": activity_type,
            "key": key,
            "quantity": quantity,
            "unit": unit,
            "co2e": co2e,
            "is_verified": is_verified,
            "timestamp": activity_ts,
            "date_readable": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(activity_ts / 1000)),
            "source_group_id": batch_id,
            "confidence": {
                "source": "db_verified" if is_verified else ("db" if co2e > 0 else "defaults"),
                "qty_inferred": qty_inferred,
                "warnings": activity_warnings,
            },
        })

    logged_activities = []
    for cloudant_doc in pending_activities:
        try:
            save_activity_log(cloudant_doc)
            total_co2 += cloudant_doc["co2e"]
            cloudant_doc['id'] = f"temp_{cloudant_doc['timestamp']}_{len(logged_activities)}"
            logged_activities.append(cloudant_doc)
            logger.info("Saved: %s -> %.4f kg CO2e (verified=%s)", cloudant_doc["key"], cloudant_doc["co2e"], cloudant_doc["is_verified"])
        except Exception as e:
            logger.error("Cloudant save failed for '%s': %s", cloudant_doc["key"], e)
            failed_sentences.append(f"{cloudant_doc['input_text']} (Save Failed)")

    return Response({
        "status": "success",
        "transcript": input_text,
        "logs_count": len(logged_activities),
        "total_co2e_kg": round(total_co2, 4),
        "activities": logged_activities,
        "failed_sentences": failed_sentences,
        "warnings": global_warnings,
        "message": (
            f"Processed {len(logged_activities)} "
            f"activit{'y' if len(logged_activities) == 1 else 'ies'}"
            + (f", {len(failed_sentences)} skipped." if failed_sentences else ".")
        ),
    }, status=status.HTTP_201_CREATED)


# ─────────────────────────────────────────────────────────────────────────────
#  API VIEWS
# ─────────────────────────────────────────────────────────────────────────────

@api_view(['POST'])
@permission_classes([IsAuthenticatedOrOptions])
def log_activity_api(request):
    input_text = request.data.get('input_text', '').strip()
    if not input_text:
        return Response({"message": "Missing input_text"}, status=status.HTTP_400_BAD_REQUEST)
    clarifications = request.data.get('clarifications') or {}
    if not isinstance(clarifications, dict):
        clarifications = {}
    return process_text_to_carbon(input_text, request.user, clarifications=clarifications)


@api_view(['POST'])
@permission_classes([IsAuthenticatedOrOptions])   # FIXED: was AllowAny
def log_activity_audio_api(request):
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response({"message": "Missing audio file"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        stt = get_stt_service()
        result = stt.recognize(
            audio=audio_file, content_type='audio/webm', model='en-US_Multimedia',
        ).get_result()
        transcript = " ".join(
            r['alternatives'][0]['transcript'] for r in result.get('results', [])
        ).strip()
        if not transcript:
            return Response({"message": "No speech detected."}, status=status.HTTP_400_BAD_REQUEST)
        logger.info("STT transcript for '%s': '%s'", request.user.username, transcript)
        return process_text_to_carbon(transcript, request.user)
    except Exception as e:
        logger.error("STT error: %s", traceback.format_exc())
        return Response({"message": f"Transcription Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAuthenticatedOrOptions])
def get_user_activities_api(request):
    username = request.user.username
    try:
        docs = get_user_logs_cloudant(username)
        docs.sort(key=lambda x: float(x.get('timestamp', 0)), reverse=True)
        return Response({"status": "success", "count": len(docs), "activities": docs})
    except Exception as e:
        return Response({"message": f"History retrieval failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_leaderboard_api(request):
    try:
        from .cloudant_db import get_cloudant_client
        client = get_cloudant_client()
        if not client:
            return Response({"message": "Cloudant connection failed"}, status=500)
        result = client.post_all_docs(db="activity-logs", include_docs=True).get_result()
        totals = {}
        for row in result.get('rows', []):
            doc = row.get('doc')
            if doc and 'username' in doc and 'co2e' in doc:
                totals[doc['username']] = totals.get(doc['username'], 0) + float(doc['co2e'])
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        board  = [
            {"rank": i+1, "name": n, "contribution": f"{round(t,2)} kg CO₂",
             "medal": medals[i] if i < len(medals) else str(i+1)}
            for i, (n, t) in enumerate(sorted(totals.items(), key=lambda x: x[1], reverse=True)[:5])
        ]
        return Response({"status": "success", "leaderboard": board})
    except Exception as e:
        return Response({"message": str(e)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def speech_to_text_api(request):
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response({"message": "No audio provided"}, status=status.HTTP_400_BAD_REQUEST)
    try:
        stt    = get_stt_service()
        result = stt.recognize(
            audio=audio_file, content_type='audio/webm', model='en-US_Multimedia',
        ).get_result()
        transcript = " ".join(
            r['alternatives'][0]['transcript'] for r in result.get('results', [])
        ).strip()
        return Response({"status": "success", "transcript": transcript})
    except Exception as e:
        return Response({"message": f"Transcription failed: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticatedOrOptions])
def add_custom_factor(request):
    serializer = EmissionFactorSerializer(data=request.data)
    if serializer.is_valid():
        serializer.save(status='pending', added_by=request.user)
        global _DB_KEY_CACHE
        _DB_KEY_CACHE = None   # invalidate cache so new factor is found immediately
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
