from django.test import TestCase
from rest_framework.test import APITestCase
from rest_framework import status
from .services import haversine

class RoutingServicesTest(TestCase):
    def test_haversine_distance(self):
        """
        Test that the Haversine formula correctly calculates the 
        great-circle distance between two points in miles.
        """
        # Coordinates for New York, NY
        ny_lat, ny_lon = 40.7128, -74.0060
        # Coordinates for Los Angeles, CA
        la_lat, la_lon = 34.0522, -118.2437
        
        distance = haversine(ny_lat, ny_lon, la_lat, la_lon)
        
        # The actual flight distance is roughly 2,445 miles.
        # We check if our math falls within an acceptable 50-mile margin of error.
        self.assertTrue(2400 < distance < 2500, f"Calculated distance {distance} is wildly inaccurate.")

class OptimalRouteAPITest(APITestCase):
    def test_route_endpoint_missing_parameters(self):
        """
        Test that the API correctly rejects requests that are missing 
        the required 'start' or 'finish' query parameters.
        """
        # Test missing 'finish'
        response_no_finish = self.client.get('/api/route/?start=New+York,NY')
        self.assertEqual(response_no_finish.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response_no_finish.data)
        
        # Test missing 'start'
        response_no_start = self.client.get('/api/route/?finish=Los+Angeles,CA')
        self.assertEqual(response_no_start.status_code, status.HTTP_400_BAD_REQUEST)
        
        # Test missing both
        response_empty = self.client.get('/api/route/')
        self.assertEqual(response_empty.status_code, status.HTTP_400_BAD_REQUEST)