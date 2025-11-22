from django.db import models
import uuid
import json

class Trip(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    current_location = models.CharField(max_length=200)
    pickup_location = models.CharField(max_length=200)
    dropoff_location = models.CharField(max_length=200)
    cycle_used_hours = models.DecimalField(max_digits=5, decimal_places=2)

    
    total_distance_miles = models.DecimalField(max_digits=8, decimal_places=1, null=True, blank=True)
    total_driving_hours = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    route_raw = models.JSONField(null=True, blank=True) 
    route_summary = models.JSONField(null=True, blank=True) 

    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default="pending")

    def __str__(self):
        return f"Trip {self.id} - {self.pickup_location} → {self.dropoff_location}"