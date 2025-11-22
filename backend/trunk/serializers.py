from rest_framework import serializers
from .models import Trip

class TripSerializer(serializers.ModelSerializer):
    class Meta:
        model = Trip
        fields = ['current_location', 'pickup_location', 'dropoff_location', 'cycle_used_hours']
        extra_kwargs = {
            'cycle_used_hours': {'min_value': 0, 'max_value': 70}
        }

    def validate(self, data):
        # Extra safety
        if data['cycle_used_hours'] > 70:
            raise serializers.ValidationError("Cycle used cannot exceed 70 hours")
        return data