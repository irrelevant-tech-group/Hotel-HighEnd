import logging
import json
import os
import time
from datetime import datetime, timedelta
from config import OPENWEATHER_API_KEY, WEATHER_UPDATE_INTERVAL, HOTEL_COORDINATES

logger = logging.getLogger(__name__)

# Caché para almacenar datos de clima
weather_cache = {
    "last_update": 0,
    "current": None,
    "forecast": None
}

def get_current_weather():
    """
    Get current weather for the hotel location
    
    Returns:
        dict: Weather information including temperature, condition, humidity, etc.
    """
    try:
        # Verificar si necesitamos actualizar el caché
        current_time = time.time()
        if (current_time - weather_cache["last_update"] > WEATHER_UPDATE_INTERVAL or 
            weather_cache["current"] is None):
            
            # Para este ejemplo, proporcionamos datos de prueba
            # En una implementación real, haríamos una llamada a la API de OpenWeather
            
            # Datos de prueba para demostración
            weather_data = {
                "temperature": 27,
                "feels_like": 29,
                "condition": "Soleado",
                "icon": "sun",
                "humidity": 40,
                "wind_speed": 8,
                "pressure": 1010,
                "visibility": 10000,
                "sunrise": "06:05",
                "sunset": "18:20",
                "uv_index": 5,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            # Actualizar el caché
            weather_cache["current"] = weather_data
            weather_cache["last_update"] = current_time
            
            # Guardar los datos en un archivo para referencia
            _save_weather_data(weather_data)
            
        return weather_cache["current"]
        
    except Exception as e:
        logger.error(f"Error getting current weather: {str(e)}")
        # Devolver datos por defecto en caso de error
        return {
            "temperature": 25,
            "feels_like": 27,
            "condition": "Información no disponible",
            "icon": "cloud",
            "humidity": 50,
            "wind_speed": 5,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

def get_weather_forecast(days=3):
    """
    Get weather forecast for next few days
    
    Args:
        days (int): Number of days for forecast
        
    Returns:
        list: Daily forecast data
    """
    try:
        # Verificar si necesitamos actualizar el caché
        current_time = time.time()
        if (current_time - weather_cache["last_update"] > WEATHER_UPDATE_INTERVAL or 
            weather_cache["forecast"] is None):
            
            # Datos de prueba para demostración
            forecast_data = []
            
            # Generar datos para los próximos días
            for i in range(days):
                day = datetime.now() + timedelta(days=i+1)
                day_forecast = {
                    "date": day.strftime("%Y-%m-%d"),
                    "day_name": day.strftime("%A"),
                    "temperature_max": 28 + (i % 3) - 1,
                    "temperature_min": 20 + (i % 2),
                    "condition": _get_random_condition(i),
                    "icon": _get_icon_for_condition(_get_random_condition(i)),
                    "humidity": 45 + (i * 5) % 15,
                    "wind_speed": 5 + (i * 2) % 8,
                    "chance_of_rain": (i * 10) % 40
                }
                forecast_data.append(day_forecast)
            
            # Actualizar el caché
            weather_cache["forecast"] = forecast_data
            
        return weather_cache["forecast"]
        
    except Exception as e:
        logger.error(f"Error getting weather forecast: {str(e)}")
        # Devolver datos por defecto en caso de error
        return [
            {
                "date": (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d"),
                "day_name": (datetime.now() + timedelta(days=1)).strftime("%A"),
                "temperature_max": 26,
                "temperature_min": 19,
                "condition": "Información no disponible",
                "icon": "cloud",
                "humidity": 50,
                "wind_speed": 5
            }
        ]

def _save_weather_data(data):
    """Save weather data to file for reference"""
    try:
        data_dir = os.path.join('data')
        os.makedirs(data_dir, exist_ok=True)
        
        with open(os.path.join(data_dir, 'weather.json'), 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving weather data: {str(e)}")

def _get_random_condition(day_index):
    """Get a random weather condition for demo purposes"""
    conditions = [
        "Soleado", 
        "Parcialmente nublado", 
        "Nublado", 
        "Lluvioso", 
        "Tormenta eléctrica"
    ]
    return conditions[day_index % len(conditions)]

def _get_icon_for_condition(condition):
    """Map condition to icon name"""
    icon_mapping = {
        "Soleado": "sun",
        "Parcialmente nublado": "cloud-sun",
        "Nublado": "cloud",
        "Lluvioso": "cloud-rain",
        "Tormenta eléctrica": "cloud-lightning"
    }
    return icon_mapping.get(condition, "cloud")