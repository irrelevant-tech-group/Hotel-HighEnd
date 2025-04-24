import logging
import json
import os
import random
import re
from datetime import datetime
from config import RECOMMENDATION_CATEGORIES, HOTEL_COORDINATES
from models import Recommendation
from app import db
from services.weather_service import get_current_weather
from services.maps_service import calculate_distance, get_distance_from_api
from services.maps_enhanced_service import get_place_details, get_place_photos, generate_maps_embed_url

logger = logging.getLogger(__name__)

def load_recommendations():
    """Load recommendations from database or file"""
    try:
        # Intentar cargar desde la base de datos
        db_recommendations = Recommendation.query.all()
        
        if db_recommendations:
            logger.debug(f"Loaded {len(db_recommendations)} recommendations from database")
            return db_recommendations
        
        # Si no hay recomendaciones en la base de datos, cargar desde archivo
        recommendations_file = os.path.join('data', 'local_recommendations.json')
        
        if os.path.exists(recommendations_file):
            with open(recommendations_file, 'r', encoding='utf-8') as file:
                recommendations_data = json.load(file)
                
                # Guardar en la base de datos para futuras consultas
                for rec in recommendations_data:
                    db_rec = Recommendation(
                        name=rec.get('name', ''),
                        category=rec.get('category', ''),
                        description=rec.get('description', ''),
                        address=rec.get('address', ''),
                        latitude=rec.get('latitude'),
                        longitude=rec.get('longitude'),
                        phone=rec.get('phone', ''),
                        website=rec.get('website', ''),
                        price_level=rec.get('price_level', 0),
                        hours=json.dumps(rec.get('hours', {})),
                        best_for=rec.get('best_for', ''),
                        tags=','.join(rec.get('tags', [])),
                        place_id=rec.get('place_id', ''),
                        images=json.dumps(rec.get('images', [])),
                        reviews=json.dumps(rec.get('reviews', [])),
                        concierge_tips=json.dumps(rec.get('concierge_tips', []))
                    )
                    db.session.add(db_rec)
                
                db.session.commit()
                logger.info(f"Imported {len(recommendations_data)} recommendations into database")
                return Recommendation.query.all()
        
        # Si el archivo no existe, generar datos de ejemplo
        default_recommendations = _generate_default_recommendations()
        
        # Guardar los datos generados en un archivo para futuras ejecuciones
        with open(recommendations_file, 'w', encoding='utf-8') as file:
            json.dump(default_recommendations, file, ensure_ascii=False, indent=2)
        
        # Y también en la base de datos
        for rec in default_recommendations:
            db_rec = Recommendation(
                name=rec.get('name', ''),
                category=rec.get('category', ''),
                description=rec.get('description', ''),
                address=rec.get('address', ''),
                latitude=rec.get('latitude'),
                longitude=rec.get('longitude'),
                phone=rec.get('phone', ''),
                website=rec.get('website', ''),
                price_level=rec.get('price_level', 0),
                hours=json.dumps(rec.get('hours', {})),
                best_for=rec.get('best_for', ''),
                tags=','.join(rec.get('tags', [])),
                place_id=rec.get('place_id', ''),
                images=json.dumps(rec.get('images', [])),
                reviews=json.dumps(rec.get('reviews', [])),
                concierge_tips=json.dumps(rec.get('concierge_tips', []))
            )
            db.session.add(db_rec)
        
        db.session.commit()
        logger.info(f"Generated and saved {len(default_recommendations)} default recommendations")
        return Recommendation.query.all()
        
    except Exception as e:
        logger.error(f"Error loading recommendations: {str(e)}")
        # Si ocurre algún error, devolver recomendaciones por defecto sin guardarlas
        return _generate_default_recommendations()

def get_personalized_recommendations(guest_id, category=None, weather_condition=None, time_of_day=None, limit=5):
    """
    Get personalized recommendations with enhanced visual and informational content
    
    Args:
        guest_id (int): The guest ID
        category (str, optional): Type of recommendation (restaurant, bar, activity, etc.)
        weather_condition (str, optional): Current weather condition
        time_of_day (str, optional): Time of day (morning, afternoon, evening)
        limit (int, optional): Maximum number of recommendations to return
        
    Returns:
        list: List of enhanced recommendation dictionaries
    """
    try:
        # Cargar todas las recomendaciones
        all_recommendations = load_recommendations()
        filtered_recommendations = []
        
        # Determinar la hora del día si no se proporciona
        if not time_of_day:
            hour = datetime.now().hour
            if hour < 12:
                time_of_day = "morning"
            elif hour < 18:
                time_of_day = "afternoon"
            else:
                time_of_day = "evening"
        
        # Determinar el clima si no se proporciona
        if not weather_condition:
            weather = get_current_weather()
            weather_condition = weather.get("condition", "").lower()
        else:
            weather_condition = weather_condition.lower()
        
        # Filtrar por categoría si se proporciona
        if category:
            # Mapear categoría en español a inglés si es necesario
            category_map = {v.lower(): k for k, v in RECOMMENDATION_CATEGORIES.items()}
            category_key = category_map.get(category.lower(), category.lower())
            
            for rec in all_recommendations:
                # Si es un objeto de base de datos, convertir a diccionario
                if isinstance(rec, Recommendation):
                    rec_dict = {
                        'id': rec.id,
                        'name': rec.name,
                        'category': rec.category,
                        'description': rec.description,
                        'address': rec.address,
                        'latitude': rec.latitude,
                        'longitude': rec.longitude,
                        'phone': rec.phone,
                        'website': rec.website,
                        'price_level': rec.price_level,
                        'hours': json.loads(rec.hours) if rec.hours else {},
                        'best_for': rec.best_for,
                        'tags': rec.tags.split(',') if rec.tags else [],
                        'images': json.loads(rec.images) if hasattr(rec, 'images') and rec.images else [],
                        'reviews': json.loads(rec.reviews) if hasattr(rec, 'reviews') and rec.reviews else [],
                        'place_id': rec.place_id if hasattr(rec, 'place_id') else '',
                        'concierge_tips': json.loads(rec.concierge_tips) if hasattr(rec, 'concierge_tips') and rec.concierge_tips else []
                    }
                else:
                    rec_dict = rec
                
                if category_key in rec_dict['category'].lower():
                    filtered_recommendations.append(rec_dict)
        else:
            # Si no hay categoría, usar todas
            for rec in all_recommendations:
                # Si es un objeto de base de datos, convertir a diccionario
                if isinstance(rec, Recommendation):
                    rec_dict = {
                        'id': rec.id,
                        'name': rec.name,
                        'category': rec.category,
                        'description': rec.description,
                        'address': rec.address,
                        'latitude': rec.latitude,
                        'longitude': rec.longitude,
                        'phone': rec.phone,
                        'website': rec.website,
                        'price_level': rec.price_level,
                        'hours': json.loads(rec.hours) if rec.hours else {},
                        'best_for': rec.best_for,
                        'tags': rec.tags.split(',') if rec.tags else [],
                        'images': json.loads(rec.images) if hasattr(rec, 'images') and rec.images else [],
                        'reviews': json.loads(rec.reviews) if hasattr(rec, 'reviews') and rec.reviews else [],
                        'place_id': rec.place_id if hasattr(rec, 'place_id') else '',
                        'concierge_tips': json.loads(rec.concierge_tips) if hasattr(rec, 'concierge_tips') and rec.concierge_tips else []
                    }
                else:
                    rec_dict = rec
                
                filtered_recommendations.append(rec_dict)
                
        # Ordenar por relevancia (basado en clima, hora del día, etc.)
        for rec in filtered_recommendations:
            relevance_score = 0
            
            # Aumentar relevancia si es bueno para la hora del día actual
            if time_of_day in rec.get('best_for', '').lower():
                relevance_score += 3
            
            # Aumentar relevancia si es bueno para el clima actual
            if 'rainy' in rec.get('best_for', '').lower() and 'lluv' in weather_condition:
                relevance_score += 2
            if 'sunny' in rec.get('best_for', '').lower() and 'solea' in weather_condition:
                relevance_score += 2
            
            # Añadir algo de aleatoriedad para variedad
            relevance_score += random.random()
            
            rec['relevance'] = relevance_score
        
        # Ordenar por relevancia
        filtered_recommendations.sort(key=lambda x: x.get('relevance', 0), reverse=True)
        
        # Limitar el número de resultados
        recommendations = filtered_recommendations[:limit]
        
        # Enriquecer cada recomendación con contenido adicional
        for rec in recommendations:
            # 1. Añadir enlace directo a Google Maps
            if rec.get('latitude') and rec.get('longitude'):
                rec['maps_url'] = f"https://www.google.com/maps/search/?api=1&query={rec['latitude']},{rec['longitude']}"
                
                # Si tenemos un place_id, crear un enlace más preciso
                if rec.get('place_id'):
                    rec['maps_url'] = f"https://www.google.com/maps/search/?api=1&query={rec['name'].replace(' ', '+')}&query_place_id={rec['place_id']}"
                
                # Generar URL para iframe embed de Google Maps
                if rec.get('place_id'):
                    rec['maps_embed_url'] = generate_maps_embed_url(place_id=rec['place_id'])
                else:
                    rec['maps_embed_url'] = generate_maps_embed_url(mode="search", place_id=f"{rec['name']} {rec['address']}")
            
            # 2. Conseguir fotos si no tenemos o necesitamos más
            if rec.get('place_id') and (not rec.get('images') or len(rec.get('images', [])) < 2):
                try:
                    photos = get_place_photos(rec['place_id'])
                    if photos:
                        rec['images'] = photos
                except Exception as e:
                    logger.warning(f"Error obteniendo fotos para {rec['name']}: {str(e)}")
            
            # Asegurarnos de tener una foto destacada
            if rec.get('images') and len(rec['images']) > 0:
                rec['featured_image'] = next((img for img in rec['images'] 
                                           if img.get('is_featured')), rec['images'][0])
            
            # 3. Conseguir reseñas si no tenemos
            if rec.get('place_id') and not rec.get('reviews'):
                try:
                    place_details = get_place_details(rec['place_id'])
                    if place_details.get('reviews'):
                        rec['reviews'] = place_details['reviews']
                except Exception as e:
                    logger.warning(f"Error obteniendo reseñas para {rec['name']}: {str(e)}")
            
            # Calcular rating promedio y destacar mejor reseña
            if rec.get('reviews') and len(rec['reviews']) > 0:
                ratings = [r.get('rating', 0) for r in rec['reviews']]
                rec['avg_rating'] = sum(ratings) / len(ratings) if ratings else 0
                
                # Seleccionar la reseña más positiva (con mayor rating)
                positive_reviews = sorted(rec['reviews'], key=lambda x: x.get('rating', 0), reverse=True)
                if positive_reviews:
                    rec['highlighted_review'] = positive_reviews[0]
            
            # 4. Calcular distancia desde el hotel si tenemos coordenadas
            if rec.get('latitude') and rec.get('longitude'):
                try:
                    # Primero intenta con la API para rutas reales
                    distance = get_distance_from_api(
                        HOTEL_COORDINATES['latitude'],
                        HOTEL_COORDINATES['longitude'],
                        rec['latitude'],
                        rec['longitude']
                    )
                    
                    # Si falla, usa cálculo básico de Haversine
                    if not distance:
                        distance = calculate_distance(
                            HOTEL_COORDINATES['latitude'],
                            HOTEL_COORDINATES['longitude'],
                            rec['latitude'],
                            rec['longitude']
                        )
                    
                    # Formatear la distancia
                    if distance < 1:
                        rec['distance'] = f"{int(distance * 1000)} metros"
                        rec['walking_time'] = f"{int((distance * 1000) / 80)} minutos caminando" # Velocidad promedio 80m/min
                    else:
                        rec['distance'] = f"{distance:.1f} km"
                        rec['walking_time'] = f"{int(distance * 60 / 5)} minutos en auto" # Velocidad promedio urbana 5km/h
                        
                except Exception as e:
                    logger.warning(f"Error calculando distancia para {rec['name']}: {str(e)}")
            
            # 5. Añadir consejo personalizado basado en el clima y hora del día
            weather_tips = {
                "lluv": "Para días lluviosos como hoy, " if 'indoor' in rec.get('tags', []) 
                        else "No olvides llevar paraguas, ",
                "solea": "Ideal para disfrutar del buen clima actual, " if 'outdoor' in rec.get('tags', []) 
                         else "Una excelente opción para este día soleado, ",
                "nubla": "Perfecto para un día nublado como hoy, " if 'indoor' in rec.get('tags', []) 
                         else "Una buena alternativa para este clima variable, "
            }
            
            time_tips = {
                "morning": "excelente para iniciar el día con energía.",
                "afternoon": "perfecto para disfrutar tu tarde en Medellín.",
                "evening": "ideal para una experiencia nocturna memorable."
            }
            
            # Construir el consejo completo
            tip_weather = next((tip for weather, tip in weather_tips.items() 
                              if weather in weather_condition.lower()), "")
            tip_time = time_tips.get(time_of_day, "")
            
            rec['tip'] = tip_weather + tip_time
            
        return recommendations
        
    except Exception as e:
        logger.error(f"Error getting personalized recommendations: {str(e)}")
        return []

def handle_recommendation_request(guest, entities, context):
    """
    Handle recommendation request intent con presentación visual mejorada
    
    Args:
        guest (Guest): Guest object
        entities (dict): Extracted entities
        context (dict): Current conversation context
        
    Returns:
        str: Formatted response with rich recommendations
    """
    try:
        # Extract category from entities or context
        category = entities.get('category', context.get('recommendation_category'))
        
        if not category:
            return "¿Qué tipo de lugar te gustaría conocer? Puedo recomendarte restaurantes, bares, atracciones turísticas o actividades."
        
        # Get weather to provide context-aware recommendations
        weather = get_current_weather()
        
        # Get time of day
        hour = datetime.now().hour
        if hour < 12:
            time_of_day = "morning"
        elif hour < 18:
            time_of_day = "afternoon"
        else:
            time_of_day = "evening"
        
        # Get recommendations based on category, weather, and time
        recommendations = get_personalized_recommendations(
            guest.id, 
            category, 
            weather_condition=weather.get('condition', 'clear'),
            time_of_day=time_of_day
        )
        
        if not recommendations:
            return f"Lo siento, no tengo recomendaciones de {category} en este momento. ¿Puedo ayudarte con otra cosa?"
        
        # Format response with rich visual elements
        category_names = {
            "restaurant": "restaurantes",
            "bar": "bares y vida nocturna",
            "cafe": "cafés",
            "attraction": "atracciones turísticas",
            "museum": "museos",
            "park": "parques",
            "shopping": "lugares para compras"
        }
        
        display_category = category_names.get(category.lower(), category)
        response = f"# ✨ Recomendaciones de {display_category} para ti ✨\n\n"
        response += f"Basado en {weather.get('condition', 'el clima actual')} y la hora del día, te sugiero:\n\n"
        
        for i, rec in enumerate(recommendations[:3], 1):
            # Cabecera con nombre y categoría
            response += f"## {i}. {rec['name']}\n\n"
            
            # Imagen destacada si está disponible
            if rec.get('featured_image'):
                response += f"![{rec['name']}]({rec['featured_image']['url']})\n\n"
            
            # Descripción
            response += f"{rec['description']}\n\n"
            
            # Información clave
            response += "### Información clave\n\n"
            
            # Rating con estrellas si está disponible
            if rec.get('avg_rating'):
                stars = "★" * int(rec['avg_rating']) + "☆" * (5 - int(rec['avg_rating']))
                response += f"⭐ **Rating:** {rec['avg_rating']:.1f}/5 ({stars})\n"
            
            # Precio con símbolos de dinero
            if rec.get('price_level'):
                price_symbols = "💲" * int(rec['price_level'])
                response += f"💰 **Precio:** {price_symbols}\n"
            
            # Dirección y distancia
            response += f"📍 **Dirección:** {rec['address']}\n"
            if rec.get('distance'):
                response += f"🚶 **Distancia:** {rec['distance']} del hotel"
                if rec.get('walking_time'):
                    response += f" ({rec['walking_time']})\n"
                else:
                    response += "\n"
                
            # Horarios para hoy
            if rec.get('hours'):
                today = datetime.now().strftime('%A').lower()
                if today in rec.get('hours', {}):
                    response += f"🕒 **Horario hoy:** {rec['hours'][today]}\n"
            
            # Reseña destacada si está disponible
            if rec.get('highlighted_review'):
                review = rec['highlighted_review']
                response += f"\n### Lo que dicen los visitantes\n"
                response += f"💬 \"{review.get('text', '')[:150]}{'...' if len(review.get('text', '')) > 150 else ''}\"\n"
                response += f"   — {review.get('author', 'Cliente')} ({review.get('rating', '5')}/5)\n"
            
            # Tip personalizado
            if rec.get('tip'):
                response += f"\n✨ **Tip personal:** {rec['tip']}\n"
            
            # Enlaces útiles
            response += "\n### Enlaces útiles\n"
            if rec.get('maps_url'):
                response += f"🗺️ [Ver en Google Maps]({rec['maps_url']})\n"
            if rec.get('website'):
                response += f"🌐 [Sitio web oficial]({rec['website']})\n"
            if rec.get('phone'):
                response += f"📞 [Llamar ahora]({rec['phone']})\n"
            
            # Separador entre recomendaciones
            response += "\n---\n\n"
        
        # Llamada a la acción y opciones de seguimiento
        response += "¿Te gustaría más información sobre alguno de estos lugares? Puedes pedirme:\n"
        response += "- Más fotos de un lugar específico\n"
        response += "- Indicaciones para llegar\n"
        response += "- Reservar una mesa\n"
        response += "- Ver más recomendaciones similares\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error handling recommendation: {str(e)}")
        return "Lo siento, tuve un problema al buscar recomendaciones. ¿Puedes intentarlo de nuevo?"

def get_place_details_for_conversation(place_name, guest_id=None):
    """
    Get detailed information about a specific place with rich visual content
    
    Args:
        place_name (str): Name of the place
        guest_id (int, optional): Guest ID for personalization
        
    Returns:
        str: Formatted place details with visual elements
    """
    try:
        # Buscar el lugar en nuestras recomendaciones
        all_recommendations = load_recommendations()
        place = None
        
        # Buscar por nombre (case-insensitive partial match)
        for rec in all_recommendations:
            if isinstance(rec, Recommendation):
                if place_name.lower() in rec.name.lower():
                    # Convertir objeto de base de datos a diccionario
                    place = {
                        'id': rec.id,
                        'name': rec.name,
                        'category': rec.category,
                        'description': rec.description,
                        'address': rec.address,
                        'latitude': rec.latitude,
                        'longitude': rec.longitude,
                        'phone': rec.phone,
                        'website': rec.website,
                        'price_level': rec.price_level,
                        'hours': json.loads(rec.hours) if rec.hours else {},
                        'best_for': rec.best_for,
                        'tags': rec.tags.split(',') if rec.tags else [],
                        'images': json.loads(rec.images) if hasattr(rec, 'images') and rec.images else [],
                        'reviews': json.loads(rec.reviews) if hasattr(rec, 'reviews') and rec.reviews else [],
                        'place_id': rec.place_id if hasattr(rec, 'place_id') else '',
                        'concierge_tips': json.loads(rec.concierge_tips) if hasattr(rec, 'concierge_tips') and rec.concierge_tips else []
                    }
                    break
            else:
                if place_name.lower() in rec['name'].lower():
                    place = rec
                    break
        
        if not place:
            return f"Lo siento, no tengo información detallada sobre {place_name}. ¿Puedo recomendarte otro lugar similar?"
        
        # Enriquecer con datos adicionales si es necesario
        if place.get('place_id'):
            # Si no tenemos imágenes, conseguirlas
            if not place.get('images') or len(place.get('images', [])) < 3:
                try:
                    photos = get_place_photos(place['place_id'])
                    if photos:
                        place['images'] = photos
                except Exception as e:
                    logger.warning(f"Error getting photos: {str(e)}")
            
            # Si no tenemos reseñas, conseguirlas
            if not place.get('reviews'):
                try:
                    details = get_place_details(place['place_id'])
                    if details.get('reviews'):
                        place['reviews'] = details['reviews']
                except Exception as e:
                    logger.warning(f"Error getting reviews: {str(e)}")
        
        # Crear una respuesta visual rica
        response = f"# {place['name']}\n\n"
        
        # Mostrar imágenes principales en formato galería
        if place.get('images') and len(place.get('images', [])) > 0:
            # Mostrar las dos primeras imágenes una al lado de la otra si hay varias
            if len(place['images']) >= 2:
                response += "<div style='display:flex; gap:10px;'>\n"
                for img in place['images'][:2]:
                    response += f"<div style='flex:1;'><img src='{img['url']}' alt='{place['name']}' style='width:100%; border-radius:8px;'/></div>\n"
                response += "</div>\n\n"
            else:
                # Solo una imagen
                response += f"![{place['name']}]({place['images'][0]['url']})\n\n"
        
        # Descripción principal
        response += f"{place['description']}\n\n"
        
        # Información básica en estilo tarjeta
        response += "## 📌 Información General\n\n"
        
        # Crear tabla de información general
        response += "| | |\n"
        response += "|---|---|\n"
        response += f"| **Categoría** | {place['category'].capitalize()} |\n"
        response += f"| **Dirección** | {place['address']} |\n"
        
        if place.get('phone'):
            response += f"| **Teléfono** | {place['phone']} |\n"
        
        if place.get('website'):
            response += f"| **Sitio Web** | [{place['website'].split('://')[1].split('/')[0]}]({place['website']}) |\n"
        
        if place.get('price_level'):
            price_symbols = "💲" * place['price_level']
            response += f"| **Nivel de Precio** | {price_symbols} |\n"
        
        # Mostrar mapa si tenemos coordenadas
        if place.get('latitude') and place.get('longitude'):
            # Crear URL para mapa estático o embedding
            if place.get('maps_embed_url'):
                response += f"\n## 🗺️ Ubicación\n\n"
                response += f"<iframe width='100%' height='300' frameborder='0' style='border:0; border-radius:8px;' "
                response += f"src='{place['maps_embed_url']}' allowfullscreen></iframe>\n\n"
                
                # Añadir enlace para direcciones
                maps_url = f"https://www.google.com/maps/search/?api=1&query={place['latitude']},{place['longitude']}"
                if place.get('place_id'):
                    maps_url = f"https://www.google.com/maps/search/?api=1&query={place['name'].replace(' ', '+')}&query_place_id={place['place_id']}"
                
                response += f"[📍 Ver indicaciones para llegar desde el hotel]({maps_url})\n\n"
        
        # Horarios en un formato bonito
        if place.get('hours'):
            response += "## 🕒 Horarios\n\n"
            
            # Traductor de días
            days_es = {
                'monday': 'Lunes',
                'tuesday': 'Martes',
                'wednesday': 'Miércoles',
                'thursday': 'Jueves',
                'friday': 'Viernes',
                'saturday': 'Sábado',
                'sunday': 'Domingo'
            }
            
            # Destacar el día actual
            today = datetime.now().strftime('%A').lower()
            
            response += "| Día | Horario |\n"
            response += "|-----|--------|\n"
            
            for day, hours in place['hours'].items():
                day_es = days_es.get(day.lower(), day)
                
                if day.lower() == today:
                    response += f"| **{day_es} (HOY)** | **{hours}** |\n"
                else:
                    response += f"| {day_es} | {hours} |\n"
        
        # Reseñas en formato tarjeta
        if place.get('reviews') and len(place['reviews']) > 0:
            response += "\n## 💬 Lo que dicen los visitantes\n\n"
            
            # Calcular rating promedio
            ratings = [r.get('rating', 0) for r in place['reviews']]
            avg_rating = sum(ratings) / len(ratings) if ratings else 0
            stars = "★" * int(avg_rating) + "☆" * (5 - int(avg_rating))
            
            response += f"### Rating promedio: {avg_rating:.1f}/5 {stars}\n\n"
            
            # Mostrar las 3 mejores reseñas
            top_reviews = sorted(place['reviews'], key=lambda x: x.get('rating', 0), reverse=True)[:3]
            
            for review in top_reviews:
                rev_stars = "★" * int(review.get('rating', 5)) + "☆" * (5 - int(review.get('rating', 5)))
                response += f"**{review.get('author', 'Cliente')}** - {rev_stars}\n\n"
                response += f"_{review.get('text', '')}_ \n\n"
                response += "---\n\n"
        
        # Recomendaciones del concierge
        response += "## 💎 Recomendaciones del Concierge\n\n"
        
        # Usar consejos del concierge si están disponibles
        if place.get('concierge_tips') and len(place['concierge_tips']) > 0:
            for tip in place['concierge_tips']:
                response += f"- {tip}\n"
        else:
            # Generar consejos personalizados basados en la categoría y tags
            concierge_tips = []
            
            if 'restaurant' in place['category']:
                concierge_tips.append("**Plato destacado:** Pregunta por el plato de temporada, que utiliza ingredientes frescos locales.")
                concierge_tips.append("**Reserva:** Recomendamos reservar con al menos 2 días de antelación para cenas de fin de semana.")
            
            elif 'bar' in place['category']:
                concierge_tips.append("**Cóctel exclusivo:** No dejes de probar su creación insignia, premiada internacionalmente.")
                concierge_tips.append("**Mejor hora:** Para una experiencia más íntima, recomendamos visitarlo entre 6-8pm.")
            
            elif 'museum' in place['category']:
                concierge_tips.append("**Visita guiada:** Solicita un tour privado con antelación para una experiencia personalizada.")
                concierge_tips.append("**Exposiciones temporales:** Actualmente cuenta con una exhibición especial que no te puedes perder.")
            
            # Tips genéricos si no tenemos específicos
            if not concierge_tips:
                concierge_tips = [
                    "**Transporte personalizado:** Podemos coordinar un servicio privado de ida y vuelta para ti.",
                    "**Experiencia VIP:** Nuestro hotel tiene acuerdos especiales que te brindarán atención preferencial."
                ]
            
            # Añadir tips
            for tip in concierge_tips:
                response += f"- {tip}\n"
        
        # Llamada a la acción
        response += "\n## ¿Puedo ayudarte con algo más?\n\n"
        response += "- 📸 Ver más fotos de este lugar\n"
        response += "- 🗓️ Hacer una reservación\n"
        response += "- 🚗 Organizar transporte\n"
        response += "- 👜 Ver otros lugares similares\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting place details: {str(e)}")
        return f"Lo siento, tuve un problema al obtener información sobre {place_name}. ¿Puedo ayudarte con otro lugar?"

def show_place_images(place_name, guest_id=None):
    """
    Show a gallery of images for a specific place
    
    Args:
        place_name (str): Name of the place
        guest_id (int, optional): Guest ID for personalization
        
    Returns:
        str: Formatted response with image gallery
    """
    try:
        # Find the place in our recommendations
        all_recommendations = load_recommendations()
        place = None
        
        # Find by name (case-insensitive partial match)
        for rec in all_recommendations:
            if isinstance(rec, Recommendation):
                if place_name.lower() in rec.name.lower():
                    # Convert DB object to dictionary
                    place = {
                        'id': rec.id,
                        'name': rec.name,
                        'category': rec.category,
                        'place_id': rec.place_id if hasattr(rec, 'place_id') else '',
                        'images': json.loads(rec.images) if hasattr(rec, 'images') and rec.images else []
                    }
                    break
            else:
                if place_name.lower() in rec['name'].lower():
                    place = rec
                    break
        
        if not place:
            return f"Lo siento, no tengo fotos de {place_name}."
        
        # If we don't have images but have a place_id, try to get them from Google
        if (not place.get('images') or len(place.get('images', [])) < 3) and place.get('place_id'):
            try:
                new_photos = get_place_photos(place['place_id'], max_photos=8)
                if new_photos:
                    if place.get('images'):
                        # Add new photos to existing ones
                        existing_urls = [img.get('url') for img in place['images']]
                        for photo in new_photos:
                            if photo.get('url') not in existing_urls:
                                place['images'].append(photo)
                    else:
                        place['images'] = new_photos
            except Exception as e:
                logger.warning(f"Error obteniendo fotos desde Google: {str(e)}")
        
        if not place.get('images') or len(place.get('images', [])) == 0:
            return f"Lo siento, actualmente no tengo fotos disponibles de {place['name']}. Puedo mostrarte otras recomendaciones con imágenes disponibles."
        
        # Format a beautiful gallery response
        response = f"# 📸 Galería de imágenes: {place['name']}\n\n"
        
        # Small intro text
        category_text = {
            'restaurant': 'restaurante',
            'bar': 'bar',
            'cafe': 'café',
            'museum': 'museo',
            'attraction': 'atracción',
            'park': 'parque'
        }
        
        category_display = category_text.get(place.get('category', '').lower(), place.get('category', 'lugar'))
        
        response += f"Te muestro algunas imágenes de este {category_display} para que puedas visualizar mejor lo que te espera.\n\n"
        
        # Create a gallery layout with flexbox
        if len(place['images']) >= 4:
            # Grid layout for 4+ images
            response += "<div style='display:grid; grid-template-columns:1fr 1fr; gap:10px;'>\n"
            
            for i, image in enumerate(place['images'][:8]):
                img_alt = f"Imagen {i+1} de {place['name']}"
                response += f"<div><img src='{image['url']}' alt='{img_alt}' style='width:100%; border-radius:8px;'/></div>\n"
            
            response += "</div>\n\n"
        else:
            # Simple vertical layout for fewer images
            for i, image in enumerate(place['images']):
                img_alt = f"Imagen {i+1} de {place['name']}"
                response += f"### {img_alt}\n\n"
                response += f"![{img_alt}]({image['url']})\n\n"
        
        # Add attribution if available
        has_attribution = any(img.get('attribution') for img in place['images'] if img.get('attribution'))
        if has_attribution:
            response += "---\n\n"
            response += "*Atribuciones de imágenes: Algunas imágenes son cortesía de Google y sus contribuidores.*\n\n"
        
        # Call to action
        response += "## ¿Te gustaría visitar este lugar?\n\n"
        response += "Puedo ayudarte con:\n"
        response += "- 🗓️ Hacer una reservación\n"
        response += "- 🚗 Organizar transporte\n"
        response += "- 🗺️ Ver la ubicación en el mapa\n"
        response += "- 💬 Más información detallada\n"
        
        return response
        
    except Exception as e:
        logger.error(f"Error mostrando imágenes: {str(e)}")
        return f"Lo siento, tuve un problema al obtener las fotos de {place_name}. ¿Puedo ayudarte con otra cosa?"

def _generate_default_recommendations():
    """Generate default recommendations for demonstration"""
    
    # Estamos generando datos aleatorios con sentido para demostración
    # En un entorno de producción, estos datos vendrían de una base de datos real
    
    default_recommendations = [
        # Restaurantes
        {
            "name": "Restaurante El Cielo",
            "category": "restaurant",
            "description": "Restaurante de alta cocina con menú degustación que ofrece una experiencia gastronómica multisensorial innovadora.",
            "address": "Calle 7D #43C-130, El Poblado, Medellín",
            "latitude": 6.2098,
            "longitude": -75.5713,
            "phone": "+57 4 268 3002",
            "website": "https://elcielorestaurant.com/",
            "price_level": 4,
            "hours": {
                "Monday": "Cerrado",
                "Tuesday": "19:00 - 23:00",
                "Wednesday": "19:00 - 23:00",
                "Thursday": "19:00 - 23:00",
                "Friday": "19:00 - 23:00",
                "Saturday": "12:30 - 15:30, 19:00 - 23:00",
                "Sunday": "12:30 - 15:30"
            },
            "best_for": "evening dinner",
            "tags": ["fine dining", "molecular gastronomy", "indoor", "gourmet", "romantic"]
        },
        {
            "name": "Mondongo's El Poblado",
            "category": "restaurant",
            "description": "Restaurante tradicional paisa que sirve el auténtico mondongo y otras delicias colombianas en un ambiente casual.",
            "address": "Calle 10 #38-38, El Poblado, Medellín",
            "latitude": 6.2105,
            "longitude": -75.5689,
            "phone": "+57 4 312 2346",
            "website": "https://www.mondongos.com.co/",
            "price_level": 2,
            "hours": {
                "Monday": "11:00 - 22:00",
                "Tuesday": "11:00 - 22:00",
                "Wednesday": "11:00 - 22:00",
                "Thursday": "11:00 - 22:00",
                "Friday": "11:00 - 22:00",
                "Saturday": "11:00 - 22:00",
                "Sunday": "11:00 - 22:00"
            },
            "best_for": "lunch traditional",
            "tags": ["colombian", "traditional", "casual", "local cuisine", "family-friendly"]
        },
        {
            "name": "Carmen Restaurant",
            "category": "restaurant",
            "description": "Restaurante elegante que sirve cocina colombiana contemporánea con ingredientes locales y técnicas internacionales.",
            "address": "Carrera 36 #10A-27, El Poblado, Medellín",
            "latitude": 6.2102,
            "longitude": -75.5672,
            "phone": "+57 4 311 9625",
            "website": "https://www.carmen.com.co/",
            "price_level": 4,
            "hours": {
                "Monday": "12:00 - 15:00, 18:30 - 22:30",
                "Tuesday": "12:00 - 15:00, 18:30 - 22:30",
                "Wednesday": "12:00 - 15:00, 18:30 - 22:30",
                "Thursday": "12:00 - 15:00, 18:30 - 22:30",
                "Friday": "12:00 - 15:00, 18:30 - 22:30",
                "Saturday": "18:30 - 22:30",
                "Sunday": "Cerrado"
            },
            "best_for": "evening dinner",
            "tags": ["fine dining", "colombian fusion", "indoor", "romantic", "gourmet"]
        },
        
        # Cafés
        {
            "name": "Pergamino Café",
            "category": "cafe",
            "description": "Café de especialidad con granos de origen local que ofrece métodos de preparación artesanales y ambiente acogedor.",
            "address": "Carrera 37 #8A-37, El Poblado, Medellín",
            "latitude": 6.2118,
            "longitude": -75.5674,
            "phone": "+57 4 266 8581",
            "website": "https://pergamino.coffee/",
            "price_level": 2,
            "hours": {
                "Monday": "08:00 - 19:00",
                "Tuesday": "08:00 - 19:00",
                "Wednesday": "08:00 - 19:00",
                "Thursday": "08:00 - 19:00",
                "Friday": "08:00 - 19:00",
                "Saturday": "09:00 - 19:00",
                "Sunday": "09:00 - 18:00"
            },
            "best_for": "morning afternoon rainy",
            "tags": ["coffee", "specialty", "indoor", "cozy", "breakfast", "hipster"]
        },
        {
            "name": "Café Velvet",
            "category": "cafe",
            "description": "Café con ambiente europeo que sirve opciones de brunch y los mejores cafés de especialidad en un espacio elegante.",
            "address": "Carrera 37 #8A-21, El Poblado, Medellín",
            "latitude": 6.2119,
            "longitude": -75.5673,
            "phone": "+57 4 444 0441",
            "website": "https://cafevelvet.co/",
            "price_level": 2,
            "hours": {
                "Monday": "08:00 - 20:00",
                "Tuesday": "08:00 - 20:00",
                "Wednesday": "08:00 - 20:00",
                "Thursday": "08:00 - 20:00",
                "Friday": "08:00 - 20:00",
                "Saturday": "09:00 - 20:00",
                "Sunday": "09:00 - 18:00"
            },
            "best_for": "morning brunch rainy",
            "tags": ["coffee", "brunch", "indoor", "instagram", "breakfast", "hipster"]
        },
        
        # Atracciones
        {
            "name": "Plaza Botero",
            "category": "attraction",
            "description": "Plaza pública con 23 esculturas monumentales del reconocido artista colombiano Fernando Botero en el centro histórico.",
            "address": "Carrera 52 #52-01, La Candelaria, Medellín",
            "latitude": 6.2518,
            "longitude": -75.5693,
            "phone": "",
            "website": "",
            "price_level": 0,
            "hours": {
                "Monday": "00:00 - 23:59",
                "Tuesday": "00:00 - 23:59",
                "Wednesday": "00:00 - 23:59",
                "Thursday": "00:00 - 23:59",
                "Friday": "00:00 - 23:59",
                "Saturday": "00:00 - 23:59",
                "Sunday": "00:00 - 23:59"
            },
            "best_for": "morning afternoon sunny",
            "tags": ["art", "culture", "outdoor", "photography", "free", "historic"]
        },
        {
            "name": "Parque Arví",
            "category": "attraction",
            "description": "Extenso parque ecológico en las montañas con senderos, mercado campesino y actividades al aire libre. Accesible por metrocable.",
            "address": "Corregimiento Santa Elena, Medellín",
            "latitude": 6.2768,
            "longitude": -75.4985,
            "phone": "+57 4 444 2979",
            "website": "https://www.parquearvi.org/",
            "price_level": 1,
            "hours": {
                "Monday": "Cerrado",
                "Tuesday": "09:00 - 17:00",
                "Wednesday": "09:00 - 17:00",
                "Thursday": "09:00 - 17:00",
                "Friday": "09:00 - 17:00",
                "Saturday": "09:00 - 17:00",
                "Sunday": "09:00 - 17:00"
            },
            "best_for": "morning day sunny nature",
            "tags": ["nature", "hiking", "outdoor", "ecotourism", "metrocable", "market"]
        },
        {
            "name": "Museo de Antioquia",
            "category": "museum",
            "description": "Importante museo con colección de arte colombiano incluyendo obras de Fernando Botero y artistas regionales.",
            "address": "Calle 52 #52-43, La Candelaria, Medellín",
            "latitude": 6.2518,
            "longitude": -75.5692,
            "phone": "+57 4 251 3636",
            "website": "https://www.museodeantioquia.co/",
            "price_level": 1,
            "hours": {
                "Monday": "10:00 - 17:00",
                "Tuesday": "10:00 - 17:00",
                "Wednesday": "10:00 - 17:00",
                "Thursday": "10:00 - 17:00",
                "Friday": "10:00 - 17:00",
                "Saturday": "10:00 - 17:00",
                "Sunday": "10:00 - 17:00"
            },
            "best_for": "afternoon rainy",
            "tags": ["art", "culture", "museum", "indoor", "botero", "history"]
        },
        
        # Bares y vida nocturna
        {
            "name": "Envy Rooftop",
            "category": "bar",
            "description": "Bar con terraza en la azotea que ofrece cócteles artesanales y espectaculares vistas panorámicas de la ciudad.",
            "address": "Calle 10 #36-09, El Poblado, Medellín",
            "latitude": 6.2107,
            "longitude": -75.5673,
            "phone": "+57 300 438 8924",
            "website": "",
            "price_level": 3,
            "hours": {
                "Monday": "Cerrado",
                "Tuesday": "17:00 - 01:00",
                "Wednesday": "17:00 - 01:00",
                "Thursday": "17:00 - 01:00",
                "Friday": "17:00 - 02:00",
                "Saturday": "17:00 - 02:00",
                "Sunday": "17:00 - 00:00"
            },
            "best_for": "evening sunset",
            "tags": ["rooftop", "cocktails", "nightlife", "views", "outdoor", "trendy"]
        },
        {
            "name": "El Social Bar",
            "category": "bar",
            "description": "Bar con ambiente vintage que sirve cócteles clásicos y tiene una buena selección de cervezas artesanales locales.",
            "address": "Carrera 36 #10A-22, El Poblado, Medellín",
            "latitude": 6.2102,
            "longitude": -75.5669,
            "phone": "+57 311 764 1528",
            "website": "",
            "price_level": 2,
            "hours": {
                "Monday": "Cerrado",
                "Tuesday": "17:00 - 01:00",
                "Wednesday": "17:00 - 01:00",
                "Thursday": "17:00 - 01:00",
                "Friday": "17:00 - 02:00",
                "Saturday": "17:00 - 02:00",
                "Sunday": "Cerrado"
            },
            "best_for": "evening night",
            "tags": ["cocktails", "craft beer", "vintage", "indoor", "nightlife", "casual"]
        },
        
        # Compras
        {
            "name": "El Tesoro Parque Comercial",
            "category": "shopping",
            "description": "Centro comercial de lujo con diseño al aire libre, tiendas exclusivas, restaurantes y entretenimiento con vistas a la ciudad.",
            "address": "Carrera 25A #1A Sur-45, El Tesoro, Medellín",
            "latitude": 6.1981,
            "longitude": -75.5599,
            "phone": "+57 4 321 1010",
            "website": "https://eltesoro.com.co/",
            "price_level": 3,
            "hours": {
                "Monday": "10:00 - 21:00",
                "Tuesday": "10:00 - 21:00",
                "Wednesday": "10:00 - 21:00",
                "Thursday": "10:00 - 21:00",
                "Friday": "10:00 - 21:00",
                "Saturday": "10:00 - 21:00",
                "Sunday": "11:00 - 20:00"
            },
            "best_for": "afternoon shopping",
            "tags": ["shopping", "luxury", "outdoor mall", "restaurants", "entertainment", "views"]
        },
        {
            "name": "Mercado del Río",
            "category": "shopping",
            "description": "Mercado gastronómico con múltiples opciones culinarias, ambiente animado y estaciones de comida de todo el mundo.",
            "address": "Calle 24 #48-28, Ciudad del Río, Medellín",
            "latitude": 6.2279,
            "longitude": -75.5766,
            "phone": "+57 4 404 7374",
            "website": "https://www.mercadodelrio.com/",
            "price_level": 2,
            "hours": {
                "Monday": "12:00 - 22:00",
                "Tuesday": "12:00 - 22:00",
                "Wednesday": "12:00 - 22:00",
                "Thursday": "12:00 - 22:00",
                "Friday": "12:00 - 22:00",
                "Saturday": "12:00 - 22:00",
                "Sunday": "12:00 - 21:00"
            },
            "best_for": "lunch dinner rainy",
            "tags": ["food market", "indoor", "gastronomy", "variety", "foodie", "casual"]
        }
    ]
    
    return default_recommendations