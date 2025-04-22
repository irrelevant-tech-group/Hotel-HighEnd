import logging
import json
import os
import random
from datetime import datetime
from config import RECOMMENDATION_CATEGORIES, HOTEL_COORDINATES
from models import Recommendation
from app import db
from services.weather_service import get_current_weather

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
                        tags=','.join(rec.get('tags', []))
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
                tags=','.join(rec.get('tags', []))
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
    Get personalized recommendations based on guest preferences, time, and weather
    
    Args:
        guest_id (int): The guest ID
        category (str, optional): Type of recommendation (restaurant, bar, activity, etc.)
        weather_condition (str, optional): Current weather condition
        time_of_day (str, optional): Time of day (morning, afternoon, evening)
        limit (int, optional): Maximum number of recommendations to return
        
    Returns:
        list: List of recommendation dictionaries
    """
    try:
        # Cargar todas las recomendaciones
        all_recommendations = load_recommendations()
        recommendations = []
        
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
        filtered_recommendations = []
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
                        'tags': rec.tags.split(',') if rec.tags else []
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
                        'tags': rec.tags.split(',') if rec.tags else []
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
        
        # Calcular distancia aproximada desde el hotel
        for rec in recommendations:
            # Si no hay coordenadas, asignar una distancia por defecto
            if not rec.get('latitude') or not rec.get('longitude'):
                rec['distance'] = "Distancia no disponible"
                continue
                
            # Calcular distancia utilizando la fórmula de Haversine
            from math import sin, cos, sqrt, atan2, radians
            
            R = 6371  # Radio de la Tierra en km
            
            lat1 = radians(HOTEL_COORDINATES['latitude'])
            lon1 = radians(HOTEL_COORDINATES['longitude'])
            lat2 = radians(rec['latitude'])
            lon2 = radians(rec['longitude'])
            
            dlon = lon2 - lon1
            dlat = lat2 - lat1
            
            a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
            c = 2 * atan2(sqrt(a), sqrt(1 - a))
            distance = R * c
            
            # Formatear la distancia
            if distance < 1:
                rec['distance'] = f"{int(distance * 1000)} metros"
            else:
                rec['distance'] = f"{distance:.1f} km"
        
        # Agregar un consejo personalizado basado en el clima y la hora
        for rec in recommendations:
            weather_context = ""
            if 'lluv' in weather_condition:
                if 'indoor' in rec.get('tags', []):
                    weather_context = "Perfecto para un día lluvioso como hoy."
                else:
                    weather_context = "No olvide llevar paraguas ya que hoy está lloviendo."
            elif 'solea' in weather_condition:
                if 'outdoor' in rec.get('tags', []):
                    weather_context = "Ideal para disfrutar del buen clima de hoy."
                else:
                    weather_context = "Una buena opción para escapar del calor de hoy."
            
            time_context = ""
            if time_of_day == "morning":
                time_context = "Excelente para comenzar el día con energía."
            elif time_of_day == "afternoon":
                time_context = "Perfecto para su tarde en Medellín."
            else:
                time_context = "Una gran opción para disfrutar de la noche en la ciudad."
            
            if weather_context and time_context:
                rec['tip'] = f"{weather_context} {time_context}"
        
        return recommendations
        
    except Exception as e:
        logger.error(f"Error getting personalized recommendations: {str(e)}")
        return []

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