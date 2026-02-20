import csv
import time
from django.core.management.base import BaseCommand
from api.models import FuelStation
from geopy.geocoders import Nominatim

class Command(BaseCommand):
    help = 'Loads and geocodes fuel stations from CSV'

    def handle(self, *args, **kwargs):
        geolocator = Nominatim(user_agent="fuel_routing_api_jb")
        
        self.stdout.write("Parsing CSV and geocoding stations. This may take a few minutes...")
        
        with open('fuel-prices-for-be-assessment.csv', 'r') as file:
            reader = csv.DictReader(file)
            for i, row in enumerate(reader):
                # Skip if already exists
                if FuelStation.objects.filter(opis_id=row['OPIS Truckstop ID']).exists():
                    continue
                
                # Using just City/State is faster and more reliable for Nominatim than full addresses
                address_query = f"{row['City']}, {row['State']}, USA"
                
                lat, lon = None, None
                try:
                    location = geolocator.geocode(address_query, timeout=5)
                    if location:
                        lat, lon = location.latitude, location.longitude
                    
                    # Nominatim requires 1 request per second max
                    time.sleep(1) 
                except Exception:
                    pass # Silent fail for missing coords, will be excluded in spatial filter

                FuelStation.objects.create(
                    opis_id=row['OPIS Truckstop ID'],
                    name=row['Truckstop Name'],
                    address=row['Address'],
                    city=row['City'],
                    state=row['State'],
                    price=float(row['Retail Price']),
                    latitude=lat,
                    longitude=lon
                )
                
                if i > 0 and i % 25 == 0:
                    self.stdout.write(f"Processed {i} stations...")

        self.stdout.write(self.style.SUCCESS('Successfully completed loading and geocoding stations.'))
        