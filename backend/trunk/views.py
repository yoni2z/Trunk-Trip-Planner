from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Trip
from .serializers import TripSerializer

class TripViewSet(viewsets.ModelViewSet):
    queryset = Trip.objects.all().order_by('-created_at')
    serializer_class = TripSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            trip = serializer.save()
            headers = self.get_success_headers(serializer.data)
            return Response({
                "trip_id": str(trip.id)[:8].upper(),
                "message": "Trip received! Planning route and ELD logs...",
                "status": "success"
            }, status=status.HTTP_201_CREATED, headers=headers)
        
        return Response({
            "message": "Invalid data",
            "errors": serializer.errors
        }, status=status.HTTP_400_BAD_REQUEST)