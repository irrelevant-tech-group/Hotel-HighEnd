#!/usr/bin/env python
"""
Script para enriquecer el archivo local_recommendations.json 
con datos de Google Places API (place_id, imágenes, reseñas)
"""

import json
import os
import requests
import time
import logging
from dotenv import load_dotenv

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# Cargar variables de entorno (para la API key)
load_dotenv()

# Configuración
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
INPUT_FILE = "data/local_recommendations.json"
OUTPUT_FILE = "data/local_recommendations_enriched.json"
# Límites para no exceder cuotas de API
MAX_PHOTOS_PER_PLACE = 5
RATE_LIMIT_DELAY = 0.5  # segundos entre llamadas a la API

def load_recommendations():
    """Cargar recomendaciones desde el archivo JSON"""
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error cargando archivo: {str(e)}")
        return []

def save_recommendations(recommendations):
    """Guardar recomendaciones enriquecidas en un nuevo archivo JSON"""
    try:
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(recommendations, f, ensure_ascii=False, indent=2)
        logger.info(f"Archivo guardado exitosamente: {OUTPUT_FILE}")
    except Exception as e:
        logger.error(f"Error guardando archivo: {str(e)}")

def get_place_id(name, address):
    """Obtener place_id de Google Places API usando búsqueda por texto"""
    if not GOOGLE_MAPS_API_KEY:
        logger.error("Google Maps API key no disponible")
        return None
        
    try:
        # Construir la consulta con nombre y dirección para mayor precisión
        input_text = f"{name}, {address}"
        
        url = "https://maps.googleapis.com/maps/api/place/findplacefromtext/json"
        params = {
            'input': input_text,
            'inputtype': 'textquery',
            'fields': 'place_id,formatted_address,geometry,name',
            'key': GOOGLE_MAPS_API_KEY
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] == 'OK' and len(data['candidates']) > 0:
            place_id = data['candidates'][0]['place_id']
            logger.info(f"Place ID encontrado para '{name}': {place_id}")
            return place_id
        else:
            logger.warning(f"No se encontró place_id para '{name}': {data['status']}")
            return None
            
    except Exception as e:
        logger.error(f"Error obteniendo place_id para '{name}': {str(e)}")
        return None

def get_place_details(place_id):
    """Obtener detalles completos de un lugar usando su place_id"""
    if not GOOGLE_MAPS_API_KEY or not place_id:
        return {}
        
    try:
        url = "https://maps.googleapis.com/maps/api/place/details/json"
        params = {
            'place_id': place_id,
            'fields': 'name,rating,review,photo,formatted_phone_number,website,price_level,opening_hours',
            'key': GOOGLE_MAPS_API_KEY,
            'language': 'es'  # Para obtener reseñas en español cuando sea posible
        }
        
        response = requests.get(url, params=params)
        data = response.json()
        
        if data['status'] == 'OK':
            return data['result']
        else:
            logger.warning(f"Error obteniendo detalles para place_id {place_id}: {data['status']}")
            return {}
            
    except Exception as e:
        logger.error(f"Error en solicitud para place_id {place_id}: {str(e)}")
        return {}

def format_photos(photos_data, place_id):
    """Formatear datos de fotos para nuestro formato JSON"""
    if not photos_data:
        return []
        
    formatted_photos = []
    
    for i, photo in enumerate(photos_data[:MAX_PHOTOS_PER_PLACE]):
        if 'photo_reference' in photo:
            photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&maxheight=600&photoreference={photo['photo_reference']}&key={GOOGLE_MAPS_API_KEY}"
            formatted_photos.append({
                'url': photo_url,
                'width': photo.get('width', 800),
                'height': photo.get('height', 600),
                'is_featured': i == 0,  # Primera foto como destacada
                'attribution': photo.get('html_attributions', [])
            })
    
    return formatted_photos

def format_reviews(reviews_data):
    """Formatear datos de reseñas para nuestro formato JSON"""
    if not reviews_data:
        return []
        
    formatted_reviews = []
    
    for review in reviews_data[:3]:  # Limitar a 3 reseñas
        formatted_reviews.append({
            'author': review.get('author_name', 'Cliente'),
            'text': review.get('text', ''),
            'rating': review.get('rating', 5),
            'time': review.get('relative_time_description', '')
        })
    
    return formatted_reviews

def generate_concierge_tips(place):
    """Generar tips de concierge basados en la categoría y tags del lugar"""
    tips = []
    category = place.get('category', '').lower()
    tags = place.get('tags', [])
    
    # Tips para restaurantes
    if 'restaurant' in category:
        if 'fine dining' in tags or 'upscale' in tags:
            tips.append("Reserve con al menos 3 días de antelación para asegurar una experiencia óptima")
            tips.append("Recomendamos el menú degustación para apreciar toda la creatividad del chef")
        elif 'traditional' in tags or 'local' in tags:
            tips.append("Pregunte por el plato tradicional del día, que no siempre está en el menú")
            tips.append("Los martes y jueves suelen ser menos concurridos para una experiencia más tranquila")
    
    # Tips para bares
    elif 'bar' in category:
        if 'cocktails' in tags:
            tips.append("Solicite que le preparen un cóctel personalizado basado en sus gustos")
            tips.append("Entre 6-8pm disfrutan de una atmósfera más relajada, ideal para conversación")
        else:
            tips.append("Este lugar es conocido por su selección de licores artesanales locales")
    
    # Tips para museos y atracciones
    elif 'museum' in category or 'attraction' in category:
        tips.append("Podemos organizar una visita guiada privada con antelación")
        tips.append("Las primeras horas de la mañana ofrecen una experiencia más tranquila")
    
    # Tips generales si no tenemos específicos
    if not tips:
        tips = [
            "Podemos organizar transporte privado de ida y vuelta para su comodidad",
            "Nuestro hotel mantiene relaciones especiales con este establecimiento para atención VIP"
        ]
    
    return tips

def enrich_recommendations():
    """Proceso principal para enriquecer las recomendaciones"""
    recommendations = load_recommendations()
    if not recommendations:
        logger.error("No se pudieron cargar las recomendaciones")
        return
    
    total_places = len(recommendations)
    logger.info(f"Comenzando a enriquecer {total_places} lugares...")
    
    enriched_count = 0
    for i, place in enumerate(recommendations):
        logger.info(f"Procesando {i+1}/{total_places}: {place['name']}")
        
        # 1. Obtener place_id si no existe
        if not place.get('place_id'):
            place['place_id'] = get_place_id(place['name'], place['address'])
            time.sleep(RATE_LIMIT_DELAY)  # Evitar límites de tasa de la API
        
        # 2. Si tenemos place_id, obtener detalles completos
        if place.get('place_id'):
            place_details = get_place_details(place['place_id'])
            time.sleep(RATE_LIMIT_DELAY)
            
            # 3. Añadir fotos
            if 'photos' in place_details:
                place['images'] = format_photos(place_details['photos'], place['place_id'])
            else:
                place['images'] = []
            
            # 4. Añadir reseñas
            if 'reviews' in place_details:
                place['reviews'] = format_reviews(place_details['reviews'])
            else:
                place['reviews'] = []
            
            # 5. Actualizar horarios si están disponibles
            if 'opening_hours' in place_details and 'weekday_text' in place_details['opening_hours']:
                # Mapear días de semana en inglés a las claves que ya usamos
                day_mapping = {
                    'Monday': 'monday',
                    'Tuesday': 'tuesday',
                    'Wednesday': 'wednesday',
                    'Thursday': 'thursday',
                    'Friday': 'friday',
                    'Saturday': 'saturday',
                    'Sunday': 'sunday'
                }
                
                updated_hours = {}
                for day_text in place_details['opening_hours']['weekday_text']:
                    day, hours = day_text.split(':', 1)
                    day_key = day_mapping.get(day.strip(), day.strip().lower())
                    updated_hours[day_key] = hours.strip()
                
                place['hours'] = updated_hours
            
            # 6. Actualizar otros campos si es necesario
            if 'rating' in place_details:
                place['google_rating'] = place_details['rating']
                
            if 'formatted_phone_number' in place_details and not place.get('phone'):
                place['phone'] = place_details['formatted_phone_number']
                
            if 'website' in place_details and not place.get('website'):
                place['website'] = place_details['website']
                
            if 'price_level' in place_details and not place.get('price_level'):
                place['price_level'] = place_details['price_level']
            
            # 7. Añadir tips del concierge
            place['concierge_tips'] = generate_concierge_tips(place)
            
            enriched_count += 1
        
        # Mostrar progreso
        if (i + 1) % 5 == 0 or i == total_places - 1:
            logger.info(f"Progreso: {i+1}/{total_places} lugares procesados")
    
    logger.info(f"Enriquecimiento completado: {enriched_count}/{total_places} lugares actualizados")
    save_recommendations(recommendations)

if __name__ == "__main__":
    if not GOOGLE_MAPS_API_KEY:
        logger.error("La API key de Google Maps no está configurada. Establezca la variable de entorno GOOGLE_MAPS_API_KEY.")
        exit(1)
        
    logger.info("Iniciando proceso de enriquecimiento de recomendaciones...")
    enrich_recommendations()
    logger.info("Proceso completado.")