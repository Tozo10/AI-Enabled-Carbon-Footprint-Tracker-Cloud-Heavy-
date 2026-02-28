from django.core.management.base import BaseCommand
from users.models import EmissionFactor

class Command(BaseCommand):
    help = 'Seeds top Indian emission factors (Electricity, Transport, Food)'

    def handle(self, *args, **options):
        # Data sourced from CEA (2024), MoRTH, and India-specific LCA studies
        india_data = [
            # --- UTILITIES ---
            {'key': 'Electricity_India_Grid', 'at': 'Utilities', 'val': 0.71, 'unit': 'kWh', 'src': 'CEA 2024'},
            {'key': 'LPG_Cooking_India', 'at': 'Utilities', 'val': 2.98, 'unit': 'kg', 'src': 'BEE'},
            
            # --- TRANSPORT (India Specific) ---
            {'key': 'Auto_Rickshaw_CNG', 'at': 'Transport', 'val': 0.08, 'unit': 'km', 'src': 'BEE'},
            {'key': 'Two_Wheeler_Petrol_100cc', 'at': 'Transport', 'val': 0.045, 'unit': 'km', 'src': 'MoRTH'},
            {'key': 'Bus_City_NonAC_India', 'at': 'Transport', 'val': 0.05, 'unit': 'km', 'src': 'DTC/BEST'},
            {'key': 'Indian_Railways_Sleeper', 'at': 'Public Transport', 'val': 0.02, 'unit': 'km', 'src': 'IR'},
            
            # --- FOOD (Indian Diet Staples) ---
            {'key': 'Rice_White_India', 'at': 'Food', 'val': 3.55, 'unit': 'kg', 'src': 'LCA India'},
            {'key': 'Wheat_Atta_India', 'at': 'Food', 'val': 1.15, 'unit': 'kg', 'src': 'LCA India'},
            {'key': 'Paneer_Indian', 'at': 'Food', 'val': 8.2, 'unit': 'kg', 'src': 'Dairy India'},
            {'key': 'Buffalo_Milk_Packet', 'at': 'Food', 'val': 1.7, 'unit': 'litre', 'src': 'Amul/MotherDairy'},
        ]

        count = 0
        for item in india_data:
            # We set status='verified' because these are your 'Gold Standard' seeds
            EmissionFactor.objects.update_or_create(
                key=item['key'],
                defaults={
                    'activity_type': item['at'],
                    'co2e_per_unit': item['val'],
                    'unit': item['unit'],
                    'status': 'verified',
                    'source_reference': item['src']
                }
            )
            count += 1
            
        self.stdout.write(self.style.SUCCESS(f'Successfully seeded {count} Indian factors.'))