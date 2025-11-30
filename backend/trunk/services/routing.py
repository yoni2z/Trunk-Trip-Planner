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
        if data.get('features'):
            coords = data['features'][0]['geometry']['coordinates']
            return [coords[0], coords[1]]
        return None
    except Exception as e:
        logger.error(f"Geocode failed: {e}")
        return None

def get_truck_route(coordinates):
    url = "https://api.openrouteservice.org/v2/directions/driving-car"

    headers = {
        'Authorization': settings.OPENROUTESERVICE_API_KEY,
        'Content-Type': 'application/json'
    }

    payload = {
        "coordinates": coordinates,
        "instructions": False,
        "preference": "recommended",
        "units": "mi",
        "geometry": True
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()

        # ✅ SAFE LOGGING (NO CRASHES EVER)
        if 'routes' in data:
            logger.info(
                f"Route success: {data['routes'][0]['summary']['distance']} miles"
            )
        elif 'features' in data:
            logger.info(
                f"Route success: {data['features'][0]['properties']['summary']['distance']} miles"
            )
        else:
            logger.warning(f"Unknown ORS response format: {data}")

        return data

    except requests.exceptions.HTTPError as e:
        logger.error(f"ORS HTTP Error: {e.response.status_code} - {e.response.text}")
        return None

    except Exception as e:
        logger.exception("Route failed with full traceback")
        return None
