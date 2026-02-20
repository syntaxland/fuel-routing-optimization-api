from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .services import geocode_location, get_route_data, get_stations_along_route, optimize_fuel_stops

class OptimalRouteView(APIView):
    def get(self, request):
        start = request.query_params.get('start')
        finish = request.query_params.get('finish')

        if not start or not finish:
            return Response(
                {"error": "Both 'start' and 'finish' parameters are required."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # 1. Geocode
            start_coords = geocode_location(start)
            end_coords = geocode_location(finish)
            
            # 2. Get Route
            dist_miles, coords, polyline_str = get_route_data(start_coords, end_coords)
            
            # 3. Spatial Math to find stations
            stations_on_route = get_stations_along_route(coords, dist_miles)
            
            # 4. Greedy Optimization
            stops, cost = optimize_fuel_stops(stations_on_route, dist_miles)

            return Response({
                "route_map": polyline_str,
                "total_distance_miles": round(dist_miles, 2),
                "total_cost": f"${round(cost, 2)}",
                "fuel_stops": stops
            }, status=status.HTTP_200_OK)

        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"error": "An internal error occurred. " + str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        