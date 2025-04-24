import os
import logging
import requests
import json
import math
from config import HOTEL_COORDINATES
from services.maps_service import calculate_distance

logger = logging.getLogger(__name__)

# Google Maps API configuration
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
MAPS_BASE_URL = "https://www.google.com/maps/embed/v1/"

def get_nearby_places(place_type, radius=1500, language="es"):
    """
    Get nearby places using Google Places API
    
    Args:
        place_type (str): Type of place (restaurant, bar, museum, etc.)
        radius (int): Search radius in meters
        language (str): Response language
        
    Returns:
        list: List of nearby places
    """
    try:
        if not GOOGLE_MAPS_API_KEY:
            logger.warning("Google Maps API key not available")
            return []
            
        url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
        
        # Prepare params
        params = {
            'location': f"{HOTEL_COORDINATES['latitude']},{HOTEL_COORDINATES['longitude']}",
            'radius': radius,
            'type': place_type,
            'language': language,
            'key': GOOGLE_MAPS_API_KEY
        }
        
        # Make request
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] != 'OK':
            logger.error(f"Google Places API error: {data['status']}")
            return []
            
        # Process and format results
        places = []
        for place in data['results'][:10]:  # Limit to top 10 results
            place_details = {
                'name': place['name'],
                'address': place.get('vicinity', 'Dirección no disponible'),
                'rating': place.get('rating', 'No disponible'),
                'user_ratings_total': place.get('user_ratings_total', 0),
                'place_id': place['place_id'],
                'location': place['geometry']['location'],
                'types': place.get('types', []),
                'price_level': place.get('price_level', 0)
            }
            
            # Add photos if available
            if 'photos' in place:
                photo_reference = place['photos'][0]['photo_reference']
                place_details['photo_url'] = (
                    f"https://maps.googleapis.com/maps/api/place/photo?"
                    f"maxwidth=400&photoreference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"
                )
            
            # Calculate distance from hotel
            place_details['distance'] = calculate_distance(
                HOTEL_COORDINATES['latitude'],
                HOTEL_COORDINATES['longitude'],
                place['geometry']['location']['lat'],
                place['geometry']['location']['lng']
            )
            
            places.append(place_details)
        
        # Sort by rating and distance
        places.sort(key=lambda x: (-x.get('rating', 0), x.get('distance', 999)))
        
        return places
        
    except Exception as e:
        logger.error(f"Error getting nearby places: {str(e)}")
        return []

def get_place_details(place_id, language="es"):
    """
    Get detailed information about a specific place
    
    Args:
        place_id (str): Google Place ID
        language (str): Response language
        
    Returns:
        dict: Place details
    """
    try:
        if not GOOGLE_MAPS_API_KEY:
            logger.warning("Google Maps API key not available")
            return {}
            
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        
        # Prepare params
        params = {
            'place_id': place_id,
            'language': language,
            'fields': 'name,formatted_address,formatted_phone_number,opening_hours,website,price_level,rating,review,url',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        # Make request
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] != 'OK':
            logger.error(f"Google Place Details API error: {data['status']}")
            return {}
            
        # Extract and format details
        place = data['result']
        details = {
            'name': place.get('name', 'No disponible'),
            'address': place.get('formatted_address', 'Dirección no disponible'),
            'phone': place.get('formatted_phone_number', 'No disponible'),
            'website': place.get('website', ''),
            'price_level': place.get('price_level', 0),
            'rating': place.get('rating', 'No disponible'),
            'maps_url': place.get('url', ''),
            'reviews': []
        }
        
        # Format opening hours if available
        if 'opening_hours' in place and 'weekday_text' in place['opening_hours']:
            details['hours'] = place['opening_hours']['weekday_text']
        
        # Get a few reviews if available
        if 'reviews' in place:
            for review in place['reviews'][:3]:  # Limit to 3 reviews
                details['reviews'].append({
                    'rating': review.get('rating', 0),
                    'text': review.get('text', ''),
                    'author': review.get('author_name', 'Anónimo'),
                    'time': review.get('relative_time_description', '')
                })
        
        return details
        
    except Exception as e:
        logger.error(f"Error getting place details: {str(e)}")
        return {}

def generate_maps_embed_url(place_id=None, origin=None, destination=None, mode="place"):
    """
    Generate Google Maps embed URL for displaying maps
    
    Args:
        place_id (str, optional): Place ID for place mode
        origin (str, optional): Origin for directions mode
        destination (str, optional): Destination for directions mode
        mode (str): Map mode: 'place', 'directions', 'streetview', 'search'
        
    Returns:
        str: Google Maps embed URL
    """
    try:
        if not GOOGLE_MAPS_API_KEY:
            return ""
            
        base_url = f"{MAPS_BASE_URL}{mode}"
        query_params = []
        
        # Add mode-specific parameters
        if mode == "place" and place_id:
            query_params.append(f"q=place_id:{place_id}")
        elif mode == "directions" and origin and destination:
            query_params.append(f"origin={origin}")
            query_params.append(f"destination={destination}")
            query_params.append("avoid=tolls|highways")
        elif mode == "search":
            location = f"{HOTEL_COORDINATES['latitude']},{HOTEL_COORDINATES['longitude']}"
            query_params.append(f"q={place_id or 'atracciones+cerca'}")
            query_params.append(f"center={location}")
        
        # Common parameters
        query_params.append(f"key={GOOGLE_MAPS_API_KEY}")
        query_params.append("zoom=15")
        query_params.append("language=es")
        
        # Build the URL
        url = f"{base_url}?{'&'.join(query_params)}"
        return url
        
    except Exception as e:
        logger.error(f"Error generating Maps embed URL: {str(e)}")
        return ""

def format_walking_directions(origin, destination):
    """
    Format walking directions between two points in a user-friendly way
    
    Args:
        origin (str): Origin description
        destination (str): Destination description
        
    Returns:
        dict: Formatted directions information
    """
    try:
        if not GOOGLE_MAPS_API_KEY:
            return {
                "status": "API_KEY_MISSING",
                "message": "Se requiere la clave de Google Maps API para las indicaciones"
            }
        
        # Convert origin and destination to coordinates if they're not already
        origin_coords = origin
        if "," not in origin:
            origin_coords = f"{HOTEL_COORDINATES['latitude']},{HOTEL_COORDINATES['longitude']}"
            
        # Get directions from the API
        url = "https://maps.googleapis.com/maps/api/directions/json"
        params = {
            'origin': origin_coords,
            'destination': destination,
            'mode': 'walking',
            'alternatives': 'true',
            'language': 'es',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if data['status'] != 'OK':
            return {
                "status": data['status'],
                "message": "No se pudieron obtener indicaciones para esta ruta"
            }
            
        # Process the first route
        route = data['routes'][0]
        leg = route['legs'][0]
        
        # Format the walking directions
        directions = {
            "status": "OK",
            "origin": leg['start_address'],
            "destination": leg['end_address'],
            "distance": leg['distance']['text'],
            "duration": leg['duration']['text'],
            "steps": []
        }
        
        # Process each step in the route
        for i, step in enumerate(leg['steps'], 1):
            # Clean HTML tags from instructions
            instructions = step['html_instructions']
            instructions = instructions.replace('<b>', '').replace('</b>', '')
            instructions = instructions.replace(
                '<div style="font-size:0.9em">', '. ').replace('</div>', '')
            
            directions["steps"].append({
                "number": i,
                "instructions": instructions,
                "distance": step['distance']['text'],
                "duration": step['duration']['text']
            })
            
        return directions
        
    except Exception as e:
        logger.error(f"Error formatting walking directions: {str(e)}")
        return {
            "status": "ERROR",
            "message": "Error al obtener las indicaciones"
        }

# Añadido: función para obtener fotos de un lugar
def get_place_photos(place_id, max_height=500, max_width=800, max_photos=5):
    """
    Get photos for a specific place from Google Places API
    
    Args:
        place_id (str): Google Place ID
        max_height (int): Maximum height of photos
        max_width (int): Maximum width of photos
        max_photos (int): Maximum number of photos to return
        
    Returns:
        list: List of photo URLs
    """
    try:
        if not GOOGLE_MAPS_API_KEY:
            logger.warning("Google Maps API key not available")
            return []
            
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        
        # Prepare params
        params = {
            'place_id': place_id,
            'fields': 'photos',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        # Make request
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        if (data['status'] != 'OK' or
            'result' not in data or
            'photos' not in data['result']):
            logger.warning(f"No photos found for place_id: {place_id}")
            return []
            
        # Process photos
        photos = []
        for photo in data['result']['photos'][:max_photos]:
            if 'photo_reference' in photo:
                photo_url = (
                    f"https://maps.googleapis.com/maps/api/place/photo?"
                    f"maxwidth={max_width}&maxheight={max_height}&"
                    f"photoreference={photo['photo_reference']}&key={GOOGLE_MAPS_API_KEY}"
                )
                photos.append({
                    'url': photo_url,
                    'width': photo.get('width', max_width),
                    'height': photo.get('height', max_height),
                    'attribution': photo.get('html_attributions', []),
                    'is_featured': len(photos) == 0  # First photo is featured
                })
        
        return photos
        
    except Exception as e:
        logger.error(f"Error getting place photos: {str(e)}")
        return []
