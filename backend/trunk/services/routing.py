import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def geocode_location(location_str):
    url = "https://api.openrouteservice.org/geocode/search"
    params = {
        "api_key": settings.OPENROUTESERVICE_API_KEY,
        "text": location_str,
        "size": 1
    }
    try:
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if data['features']:
            coords = data['features'][0]['geometry']['coordinates']
            return [coords[0], coords[1]]  # [lon, lat]
    except Exception as e:
        logger.error(f"Geocoding failed for {location_str}: {e}")
    return None

def get_truck_route(coordinates):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"
    headers = {'Authorization': settings.OPENROUTESERVICE_API_KEY}
    body = {
        "coordinates": coordinates,
        "instructions": False,
        "preference": "recommended",
        "units": "mi",
        "geometry": False,
        "options": {
            "avoid_features": ["highways"]  # Optional: remove if you want highways
        }
    }
    
    try:
        resp = requests.post(url, json=body, headers=headers, timeout=20)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.error(f"Route calculation failed: {e}")
        return None