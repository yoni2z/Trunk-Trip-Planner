from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Trip
from .serializers import TripSerializer
from .services.routing import geocode_location, get_truck_route
from .services.hos_planner import plan_hos_compliant_trip
from datetime import datetime
from decimal import Decimal
import json

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all().order_by('-created_at')
    serializer_class = TripSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response({
                "message": "Invalid data",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        # Geocode locations
        locations = [
            request.data['current_location'],
            request.data['pickup_location'],
            request.data['dropoff_location']
        ]
        coords = []
        for loc in locations:
            coord = geocode_location(loc)
            if not coord:
                return Response({"message": f"Could not find location: {loc}"}, 
                              status=status.HTTP_400_BAD_REQUEST)
            coords.append(coord)

        # Get route
        route_data = get_truck_route(coords)
        if not route_data or 'routes' not in route_data:
            return Response({"message": "Route calculation failed"}, 
                          status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        route = route_data['routes'][0]
        summary = route['summary']
        total_miles = Decimal(summary['distance'])
        total_hours = Decimal(summary['duration']) / 3600

        # CRITICAL FIX: Convert Decimal → float before JSON
        total_miles_float = float(total_miles)
        total_hours_float = round(float(total_hours), 2)

        # Build clean summary with only JSON-serializable types
        route_summary_clean = {
            "total_distance_miles": total_miles_float,
            "total_driving_hours": total_hours_float,
            "segments": [
                {
                    "from": locations[0],
                    "to": locations[1],
                    "miles": total_miles_float * 0.4,  # placeholder split
                    "hours": total_hours_float * 0.4
                },
                {
                    "from": locations[1],
                    "to": locations[2],
                    "miles": total_miles_float * 0.6,
                    "hours": total_hours_float * 0.6
                }
            ]
        }

        # Save trip — now safe for JSONField
        trip = serializer.save(
            total_distance_miles=total_miles,
            total_driving_hours=total_hours,
            route_raw=route_data,
            route_summary=route_summary_clean,   # ← Now 100% JSON-safe
            status="route_calculated"
        )

        total_driving_seconds = route['summary']['duration']  # this is in seconds

        # Run HOS planner
        hos_result = plan_hos_compliant_trip(
            total_driving_seconds=int(total_driving_seconds),
            cycle_used_hours=Decimal(str(request.data['cycle_used_hours']))
        )

        # Save HOS plan
        trip.hos_plan = hos_result
        trip.hos_computed_at = datetime.now()
        trip.status = "hos_compliant"
        trip.save()

        return Response({
            "trip_id": str(trip.id)[:8].upper(),
            "message": "Route calculated successfully!",
            "route": route_summary_clean,
            "hos": hos_result
        }, status=status.HTTP_201_CREATED)