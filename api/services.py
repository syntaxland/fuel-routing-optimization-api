import math
import requests
import polyline
from .models import FuelStation

def geocode_location(location_name):
    """Geocodes a string like 'New York, NY' into (lat, lon)."""
    url = f"https://nominatim.openstreetmap.org/search?q={location_name}&format=json&limit=1"
    headers = {'User-Agent': 'FuelOptimizerAPI/1.0'}
    response = requests.get(url, headers=headers).json()
    if not response:
        raise ValueError(f"Could not geocode location: {location_name}") 
    return float(response[0]['lat']), float(response[0]['lon'])

def get_route_data(start_coords, end_coords):
    """Fetches the route from OSRM, returning distance and decoded polyline coords."""
    url = f"http://router.project-osrm.org/route/v1/driving/{start_coords[1]},{start_coords[0]};{end_coords[1]},{end_coords[0]}?overview=full&geometries=polyline"
    response = requests.get(url).json()
    
    if response['code'] != 'Ok':
        raise ValueError("Routing API failed to find a valid route.")
        
    route = response['routes'][0]
    distance_miles = route['distance'] * 0.000621371
    geometry = route['geometry']
    route_coords = polyline.decode(geometry) # list of (lat, lon)
    
    return distance_miles, route_coords, geometry

def haversine(lat1, lon1, lat2, lon2):
    """Calculates the great-circle distance between two points on Earth in miles."""
    R = 3958.8 # Earth radius in miles
    dLat, dLon = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(dLat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dLon/2)**2
    return R * 2 * math.asin(math.sqrt(a))

def get_stations_along_route(route_coords, total_distance_miles):
    """Finds stations near the route polyline and calculates their distance from the start."""
    # Only fetch stations that successfully geocoded
    stations = FuelStation.objects.exclude(latitude__isnull=True).exclude(longitude__isnull=True)
    valid_stations = []
    
    # Sample the polyline to reduce computation (check every ~1% of the route)
    step_size = max(1, len(route_coords) // 100)
    sampled_coords = route_coords[::step_size]
    miles_per_step = total_distance_miles / len(sampled_coords)
    
    seen_ids = set()
    for i, (lat, lon) in enumerate(sampled_coords):
        current_dist_from_start = i * miles_per_step
        
        for station in stations:
            if station.id in seen_ids:
                continue
                
            # If station is within 15 miles of the route segment
            if haversine(lat, lon, station.latitude, station.longitude) <= 15:
                valid_stations.append({
                    'station': station,
                    'distance_from_start': current_dist_from_start,
                    'price': station.price
                })
                seen_ids.add(station.id)
                
    # Sort stations strictly by how far along the route they appear
    valid_stations.sort(key=lambda x: x['distance_from_start'])
    return valid_stations

def optimize_fuel_stops(stations, total_distance, max_range=500.0, mpg=10.0):
    """
    Greedy optimization algorithm. Assumes vehicle starts full. 
    It finds the cheapest station within range and fills up.
    """
    stops = []
    total_cost = 0.0
    current_pos = 0.0
    
    # Iterate until we are close enough to reach the finish line
    while current_pos + max_range < total_distance:
        # Find reachable stations in the upcoming 500 mile window
        reachable = [s for s in stations if current_pos < s['distance_from_start'] <= current_pos + max_range]
        
        if not reachable:
            raise ValueError(f"Route impossible: No stations found within 500 miles of mile-marker {round(current_pos)}.")
            
        # Greedy Choice: Select the cheapest station available in range
        cheapest_station = min(reachable, key=lambda x: x['price'])
        
        # Calculate fuel needed to cover distance since last fill-up
        distance_driven = cheapest_station['distance_from_start'] - current_pos
        gallons_needed = distance_driven / mpg
        
        cost_at_stop = gallons_needed * cheapest_station['price']
        total_cost += cost_at_stop
        
        stops.append({
            "station_name": cheapest_station['station'].name,
            "location": f"{cheapest_station['station'].city}, {cheapest_station['station'].state}",
            "gallons_purchased": round(gallons_needed, 2),
            "price_per_gallon": cheapest_station['price'],
            "cost_at_stop": round(cost_at_stop, 2),
            "mile_marker": round(cheapest_station['distance_from_start'], 2)
        })
        
        # Vehicle is now full at this new position
        current_pos = cheapest_station['distance_from_start']
        
    return stops, total_cost
