import os
import logging

# Prevent duplicate logging
for handler in logging.root.handlers[:]:
    logging.root.removeHandler(handler)

# Configure logging with a single handler
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s | %(levelname)s:%(name)s:%(message)s',
    handlers=[logging.StreamHandler()]
)

# Configuración del hotel
HOTEL_NAME = "Hotel Aramé"
HOTEL_ADDRESS = "Calle 10 #40-45, El Poblado, Medellín, Colombia"
HOTEL_CONTACT = {
    "phone": "+57 (601) 987-6543",
    "email": "info@hotelarame.com",
    "website": "www.hotelarame.com"
}
HOTEL_COORDINATES = {
    "latitude": 6.2087,  # Coordenadas aproximadas para El Poblado, Medellín
    "longitude": -75.5698
}

# Configuración del asistente
ASSISTANT_NAME = "Lina"
ASSISTANT_DESCRIPTION = "Concierge Digital del Hotel Aramé"
WELCOME_MESSAGE = "Bienvenido al Hotel Aramé. Soy Lina, su concierge digital personal. Estoy aquí para ayudarle con cualquier necesidad durante su estadía. Puedo asistirle con recomendaciones locales, servicio a la habitación, transporte, información del hotel y mucho más. ¿En qué puedo ayudarle hoy?"

# Límites y configuración de conversación
MAX_CONVERSATION_HISTORY = 20
DEFAULT_LANGUAGE = "es"

# Integración con OpenAI
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
OPENAI_MODEL = "gpt-4o"  # El modelo más reciente de OpenAI

# Integración con Google Maps
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY")
MAPS_SEARCH_RADIUS = 2000  # Radio de búsqueda en metros

# Integración con OpenWeather para clima
OPENWEATHER_API_KEY = os.environ.get("OPENWEATHER_API_KEY", "sample_key")  # Utiliza una clave de muestra para pruebas
WEATHER_UPDATE_INTERVAL = 30 * 60  # Actualizar cada 30 minutos

# Categorías de recomendaciones
RECOMMENDATION_CATEGORIES = {
    "restaurant": "Restaurantes",
    "bar": "Bares y vida nocturna",
    "cafe": "Cafés",
    "attraction": "Atracciones turísticas",
    "museum": "Museos y cultura",
    "shopping": "Compras",
    "entertainment": "Entretenimiento",
    "nature": "Naturaleza y aire libre",
    "spa": "Bienestar y spa"
}

# Configuración de servicio a la habitación
ROOM_SERVICE_HOURS = "24/7"
ROOM_SERVICE_DELIVERY_TIME = 30  # Tiempo estimado de entrega en minutos

# Configuración de transporte
TRANSPORTATION_OPTIONS = {
    "taxi": "Taxi estándar",
    "private_car": "Vehículo privado",
    "luxury_car": "Automóvil de lujo",
    "suv": "SUV",
    "van": "Van (hasta 8 pasajeros)"
}
AIRPORT_TRANSFER_NOTICE = 3  # Horas de anticipación recomendadas para reservar traslado al aeropuerto

# URLs para imágenes del hotel y el asistente
HOTEL_IMAGES = {
    "logo": "/static/img/hotel-logo.png",
    "lobby": "/static/img/lobby.jpg",
    "restaurant": "/static/img/restaurant.jpg",
    "pool": "/static/img/pool.jpg"
}
ASSISTANT_AVATAR = "/static/img/lina-avatar.jpg"

# Opciones de personalización
DIETARY_PREFERENCES = [
    "Sin restricciones",
    "Vegetariano",
    "Vegano",
    "Sin gluten",
    "Sin lactosa",
    "Halal",
    "Kosher"
]

INTEREST_CATEGORIES = [
    "gastronomia",
    "cultura",
    "aventura",
    "naturaleza",
    "compras",
    "nightlife"
]

# Información del hotel para FAQs y servicios
FACILITIES = {
    "breakfast": {
        "hours": "6:30 AM - 10:30 AM",
        "location": "Restaurante principal, primer piso",
        "details": "Desayuno buffet completo incluido en su tarifa. Opciones vegetarianas y veganas disponibles."
    },
    "wifi": {
        "name": "Arame_Guest",
        "details": "Disponible en todas las áreas del hotel sin costo adicional. La contraseña se encuentra en su tarjeta de bienvenida."
    },
    "pool": {
        "hours": "6:00 AM - 10:00 PM",
        "location": "Terraza, piso 10",
        "details": "Piscina climatizada con vistas a la ciudad. Toallas disponibles en el área de la piscina."
    },
    "spa": {
        "hours": "9:00 AM - 9:00 PM",
        "location": "Piso 9",
        "details": "Reserve su tratamiento con 2 horas de anticipación. Amplia variedad de masajes y tratamientos disponibles."
    },
    "gym": {
        "hours": "24 horas",
        "location": "Piso 8",
        "details": "Equipamiento completo de cardio y pesas. Instructor disponible de 7:00 AM a 8:00 PM."
    },
    "business_center": {
        "hours": "24 horas",
        "location": "Lobby, primer piso",
        "details": "Computadoras, impresora y sala de reuniones disponibles. Reserve la sala de reuniones con anticipación."
    },
    "checkout": {
        "time": "12:00 PM",
        "late_checkout": "Disponible hasta las 4:00 PM con cargo adicional del 50% de la tarifa por noche, sujeto a disponibilidad."
    },
    "parking": {
        "details": "Servicio de valet parking disponible sin costo adicional para huéspedes."
    },
    "room_service": {
        "hours": "24 horas",
        "details": "Menú completo disponible las 24 horas. Tiempo estimado de entrega: 30 minutos."
    }
}