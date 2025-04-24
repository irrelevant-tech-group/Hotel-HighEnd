import os
import logging
import requests
import math
from config import GOOGLE_MAPS_API_KEY

logger = logging.getLogger(__name__)

def calculate_distance(lat1, lon1, lat2, lon2):
    """
    Calculate distance between two coordinates using the Haversine formula
    
    Args:
        lat1 (float): Latitude of first point
        lon1 (float): Longitude of first point
        lat2 (float): Latitude of second point
        lon2 (float): Longitude of second point
        
    Returns:
        float: Distance in kilometers
    """
    # If we have Google Maps API key, use the Distance Matrix API
    if GOOGLE_MAPS_API_KEY:
        try:
            return get_distance_from_api(lat1, lon1, lat2, lon2)
        except Exception as e:
            logger.error(f"Error getting distance from Google Maps API: {str(e)}")
            # Fall back to Haversine formula if API fails
    
    # Earth radius in kilometers
    R = 6371.0
    
    # Convert latitude and longitude from degrees to radians
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    # Differences in coordinates
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    # Haversine formula
    a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    
    return distance


def get_distance_from_api(lat1, lon1, lat2, lon2):
    """
    Get distance between two coordinates using Google Maps Distance Matrix API
    
    Args:
        lat1 (float): Latitude of origin
        lon1 (float): Longitude of origin
        lat2 (float): Latitude of destination
        lon2 (float): Longitude of destination
        
    Returns:
        float: Distance in kilometers
    """
    try:
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            'origins': f"{lat1},{lon1}",
            'destinations': f"{lat2},{lon2}",
            'mode': 'walking',  # Assuming guests will likely walk to nearby places
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if data['status'] == 'OK':
            # Extract distance in meters
            distance_m = data['rows'][0]['elements'][0]['distance']['value']
            # Convert to kilometers
            distance_km = distance_m / 1000.0
            return distance_km
        else:
            logger.warning(f"Google Maps API returned non-OK status: {data['status']}")
            return None
            
    except Exception as e:
        logger.error(f"Error getting distance from Google Maps API: {str(e)}")
        return None


def get_directions(origin_lat, origin_lon, dest_lat, dest_lon, mode='walking'):
    """
    Get directions between two points
    
    Args:
        origin_lat (float): Origin latitude
        origin_lon (float): Origin longitude
        dest_lat (float): Destination latitude
        dest_lon (float): Destination longitude
        mode (str): Travel mode (walking, driving, transit)
        
    Returns:
        dict: Directions information
    """
    if not GOOGLE_MAPS_API_KEY:
        return {
            'status': 'API_KEY_MISSING',
            'message': 'Google Maps API key is required for directions'
        }
    
    try:
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            'origin': f"{origin_lat},{origin_lon}",
            'destination': f"{dest_lat},{dest_lon}",
            'mode': mode,
            'language': 'es',  # Spanish instructions
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        if data['status'] == 'OK':
            # Simplify the response to get just what we need
            route = data['routes'][0]
            leg = route['legs'][0]
            
            steps = []
            for step in leg['steps']:
                # Remove HTML tags from instructions
                instructions = step['html_instructions']
                instructions = instructions.replace('<b>', '').replace('</b>', '')
                instructions = instructions.replace('<div style="font-size:0.9em">', '. ').replace('</div>', '')
                
                steps.append({
                    'instructions': instructions,
                    'distance': step['distance']['text'],
                    'duration': step['duration']['text']
                })
            
            directions = {
                'status': 'OK',
                'origin': leg['start_address'],
                'destination': leg['end_address'],
                'distance': leg['distance']['text'],
                'duration': leg['duration']['text'],
                'steps': steps
            }
            
            return directions
        else:
            logger.warning(f"Google Directions API returned non-OK status: {data['status']}")
            return {
                'status': data['status'],
                'message': data.get('error_message', 'Error getting directions')
            }
            
    except Exception as e:
        logger.error(f"Error getting directions: {str(e)}")
        return {
            'status': 'ERROR',
            'message': 'Failed to retrieve directions information'
        }
    

    
