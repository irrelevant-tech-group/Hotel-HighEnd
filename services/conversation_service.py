import logging
import json
from datetime import datetime
from services.faq_service import get_faq_response
from services.recommendation_service import get_personalized_recommendations
from services.room_service import get_menu, place_order
from services.transportation_service import schedule_transportation
from services.weather_service import get_current_weather
from services.openai_service import generate_response, analyze_preferences, enhance_recommendations
from services.maps_enhanced_service import get_nearby_places, format_walking_directions, generate_maps_embed_url
from utils.nlp_utils import classify_intent, extract_entities
from config import MAX_CONVERSATION_HISTORY, WELCOME_MESSAGE

logger = logging.getLogger(__name__)

def process_message(message, guest, conversation_history, context):
    """
    Process an incoming message from a guest and generate a response
    
    Args:
        message (str): The message from the guest
        guest (Guest): The guest model object
        conversation_history (list): Previous messages in the conversation
        context (dict): The current conversation context
        
    Returns:
        tuple: (response, updated_context)
    """
    try:
        # Always update context with the latest timestamp
        updated_context = context.copy()
        updated_context['last_updated'] = datetime.utcnow().isoformat()
        
        # Extract any entities from the message for context enhancement
        entities = extract_entities(message)
        # Add the raw message text to entities for follow-up handling
        entities['text'] = message
        logger.debug(f"Extracted entities: {entities}")
        
        # Add extracted entities to context
        for key, value in entities.items():
            if value:  # Only add non-empty values
                updated_context[key] = value
                # Keep track of entities we've collected
                if 'known_entities' not in updated_context:
                    updated_context['known_entities'] = []
                if key not in updated_context['known_entities']:
                    updated_context['known_entities'].append(key)
        
        # Detect intent for specialized handling and analytics
        intent, confidence = classify_intent(message)
        logger.debug(f"Detected intent: {intent} with confidence: {confidence}")
        updated_context['current_intent'] = intent
        
        # Track intents for personalization
        if 'intent_history' not in updated_context:
            updated_context['intent_history'] = []
        updated_context['intent_history'].append(intent)
        
        # Create guest info dictionary for RAG
        guest_info = {
            'name': guest.name,
            'room_number': guest.room_number,
            'check_in_date': guest.check_in_date.isoformat() if guest.check_in_date else None,
            'check_out_date': guest.check_out_date.isoformat() if guest.check_out_date else None,
            'email': guest.email,
            'phone_number': guest.phone_number
        }
        
        # Add preferences if they exist
        if guest.preferences:
            try:
                preferences = json.loads(guest.preferences)
                guest_info.update(preferences)
            except:
                # If JSON parsing fails, just continue
                pass
                
        # Convert conversation history to the format OpenAI expects
        formatted_history = []
        for msg in conversation_history:
            formatted_history.append({
                "role": msg.get("role", "user"),
                "content": msg.get("content", "")
            })
        
        # Use the enhanced RAG-based response generation
        response = generate_response(
            message,  # Use the original message directly
            conversation_history=formatted_history,
            guest_info=guest_info,
            context=updated_context,
            max_tokens=500
        )
        
        # Update context with latest timestamp
        updated_context['last_response'] = datetime.utcnow().isoformat()
        
        # Special handling for certain detected intents
        # This helps maintain structured data for future service requests
        if intent == "room_service" and 'order_items' in entities and entities['order_items']:
            # Log food preference for future personalization
            if 'food_preferences' not in updated_context:
                updated_context['food_preferences'] = []
            for item in entities['order_items']:
                if item not in updated_context['food_preferences']:
                    updated_context['food_preferences'].append(item)
        
        elif intent == "recommendation" and 'category' in entities:
            # Track recommendation categories requested
            if 'recommendation_interests' not in updated_context:
                updated_context['recommendation_interests'] = []
            if entities['category'] not in updated_context['recommendation_interests']:
                updated_context['recommendation_interests'].append(entities['category'])
        
        elif intent == "transportation":
            # Handle transportation request
            response = handle_transportation(guest, entities, updated_context)
            return response, updated_context
        
        # Keep conversation history within limits
        while len(conversation_history) > MAX_CONVERSATION_HISTORY:
            conversation_history.pop(0)
        
        return response, updated_context
            
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return "Lo siento, tuve un problema al procesar tu mensaje. ¿Puedes intentarlo de nuevo?", context


def update_context(context, intent, entities):
    """Update the conversation context with new information"""
    updated_context = context.copy()
    
    # Add or update the current intent
    updated_context['current_intent'] = intent
    
    # Add timestamp
    updated_context['last_updated'] = datetime.utcnow().isoformat()
    
    # Update context based on intent and entities
    if intent == "recommendation":
        if 'category' in entities:
            updated_context['recommendation_category'] = entities['category']
        if 'time_period' in entities:
            updated_context['time_period'] = entities['time_period']
            
    elif intent == "room_service":
        if 'order_items' in entities:
            updated_context['order_items'] = entities.get('order_items', [])
        if 'special_instructions' in entities:
            updated_context['special_instructions'] = entities['special_instructions']
            
    elif intent == "transportation":
        if 'destination' in entities:
            updated_context['destination'] = entities['destination']
        if 'pickup_time' in entities:
            updated_context['pickup_time'] = entities['pickup_time']
        if 'vehicle_type' in entities:
            updated_context['vehicle_type'] = entities['vehicle_type']
        if 'num_passengers' in entities:
            updated_context['num_passengers'] = entities['num_passengers']
    
    return updated_context


def handle_greeting(guest, context):
    """Handle greeting intent"""
    hour = datetime.now().hour
    
    if 'greeted' not in context or not context['greeted']:
        # First greeting in the conversation
        if hour < 12:
            time_greeting = "Buenos días"
        elif hour < 18:
            time_greeting = "Buenas tardes"
        else:
            time_greeting = "Buenas noches"
            
        return f"{time_greeting}, {guest.name}. {WELCOME_MESSAGE}"
    else:
        # Subsequent greeting
        return f"Hola de nuevo, {guest.name}. ¿En qué puedo ayudarte ahora?"


def handle_farewell(guest):
    """Handle farewell intent"""
    return f"Ha sido un placer ayudarte, {guest.name}. Si necesitas cualquier cosa más, no dudes en contactarme. ¡Que disfrutes tu estadía en Hotel Aramé!"


def handle_recommendation_request(guest, entities, context):
    """Handle recommendation request intent"""
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
        
        # Format response
        response = f"Aquí tienes algunas recomendaciones de {category} para ti:\n\n"
        
        for i, rec in enumerate(recommendations[:3], 1):
            response += f"{i}. {rec['name']} - {rec['description']}\n"
            response += f"   📍 {rec['address']}\n"
            if 'distance' in rec:
                response += f"   🚶 A {rec['distance']} del hotel\n"
            if 'hours' in rec and rec['hours']:
                response += f"   🕒 {rec['hours']}\n"
            response += "\n"
            
        response += "¿Te gustaría más información sobre alguno de estos lugares?"
        
        return response
        
    except Exception as e:
        logger.error(f"Error handling recommendation: {str(e)}")
        return "Lo siento, tuve un problema al buscar recomendaciones. ¿Puedes intentarlo de nuevo?"


def handle_room_service(guest, entities, context):
    """Handle room service intent"""
    # Check if we have items to order or need to present the menu
    if 'order_items' in entities and entities['order_items']:
        try:
            # Place order with extracted items
            order_id = place_order(
                guest.id, 
                entities['order_items'], 
                entities.get('special_instructions', '')
            )
            
            return (f"He registrado tu pedido para la habitación {guest.room_number}. "
                    f"Tu número de orden es {order_id} y llegará en aproximadamente 30 minutos. "
                    f"¿Necesitas algo más?")
            
        except Exception as e:
            logger.error(f"Error placing room service order: {str(e)}")
            return "Lo siento, tuve un problema al procesar tu pedido. ¿Puedes intentarlo de nuevo?"
    
    # If we don't have order items, present the menu
    try:
        menu = get_menu()
        
        response = "Aquí tienes nuestro menú de servicio a la habitación:\n\n"
        
        # Group by category
        for category, items in menu.items():
            response += f"**{category}**\n"
            for item in items:
                response += f"• {item['name']} - ${item['price']}\n"
            response += "\n"
            
        response += ("Para ordenar, puedes decirme algo como 'Quiero ordenar una hamburguesa y una limonada' "
                     "o 'Por favor tráeme un sandwich de pollo a la habitación'.")
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting room service menu: {str(e)}")
        return "Lo siento, tuve un problema al obtener el menú. ¿Puedes intentarlo de nuevo más tarde?"


def handle_transportation(guest, entities, context):
    """Handle transportation request intent"""
    # If this is a follow-up message in a transportation conversation
    if context.get('current_intent') == 'transportation':
        # If we're waiting for destination and we have text in entities
        if context.get('awaiting') == 'destination' and entities.get('text'):
            destination = entities.get('text')
            entities['destination'] = destination
            context['destination'] = destination
            context['awaiting'] = 'pickup_time'
        # If we're waiting for pickup time and we have text in entities
        elif context.get('awaiting') == 'pickup_time' and entities.get('text'):
            pickup_time = entities.get('text')
            entities['pickup_time'] = pickup_time
            context['pickup_time'] = pickup_time
            context['awaiting'] = None
    
    # Check if we have all the necessary information
    destination = entities.get('destination', context.get('destination'))
    pickup_time = entities.get('pickup_time', context.get('pickup_time'))
    
    if not destination:
        context['awaiting'] = 'destination'
        context['current_intent'] = 'transportation'
        return "¿A dónde te gustaría ir? Necesito saber el destino para programar tu transporte."
    
    if not pickup_time:
        context['awaiting'] = 'pickup_time'
        context['current_intent'] = 'transportation'
        return f"¿A qué hora necesitas el transporte para ir a {destination}? Por ejemplo, '9:30 am' o 'en 2 horas'."
    
    # Optional information
    vehicle_type = entities.get('vehicle_type', context.get('vehicle_type', 'taxi'))
    num_passengers = entities.get('num_passengers', context.get('num_passengers', 1))
    special_notes = entities.get('special_notes', context.get('special_notes', ''))
    
    try:
        # Schedule transportation
        request_id = schedule_transportation(
            guest.id,
            pickup_time,
            destination,
            num_passengers,
            vehicle_type,
            special_notes
        )
        
        # Clear the transportation context since request is complete
        context['awaiting'] = None
        context['current_intent'] = None
        context['destination'] = None
        context['pickup_time'] = None
        
        return (f"He programado tu {vehicle_type} para {pickup_time} con destino a {destination}. "
                f"Tu solicitud ha sido registrada con el número {request_id}. "
                f"Te avisaremos en tu habitación cuando el vehículo llegue. "
                f"¿Necesitas algo más?")
                
    except Exception as e:
        logger.error(f"Error scheduling transportation: {str(e)}")
        return "Lo siento, tuve un problema al programar tu transporte. ¿Puedes intentarlo de nuevo?"


def handle_faq(message, entities):
    """Handle FAQ intent"""
    try:
        # Get response from FAQ service
        response = get_faq_response(message)
        return response
    except Exception as e:
        logger.error(f"Error handling FAQ: {str(e)}")
        return "Lo siento, no pude encontrar una respuesta a tu pregunta. ¿Puedes ser más específico o preguntar de otra manera?"


def handle_weather_request(guest):
    """Handle weather request intent"""
    try:
        weather = get_current_weather()
        
        if not weather:
            return "Lo siento, no pude obtener la información del clima en este momento."
        
        temp = weather.get('temperature', {}).get('current')
        condition = weather.get('condition', 'desconocido')
        humidity = weather.get('humidity')
        
        response = f"El clima actual en Medellín es: {condition}. "
        
        if temp:
            response += f"La temperatura es de {temp}°C. "
            
        if humidity:
            response += f"La humedad es del {humidity}%. "
        
        # Add recommendation based on weather
        if 'rain' in condition.lower():
            response += "\nTe recomendaría llevar un paraguas si vas a salir. "
            response += "Quizás sea buen momento para visitar uno de nuestros museos o centros comerciales."
        elif 'sol' in condition.lower() or 'clear' in condition.lower():
            response += "\nEs un gran día para explorar la ciudad o visitar uno de los parques cercanos."
            
        return response
        
    except Exception as e:
        logger.error(f"Error getting weather: {str(e)}")
        return "Lo siento, tuve un problema al obtener la información del clima. ¿Puedo ayudarte con otra cosa?"


def handle_help_request():
    """Handle help request intent"""
    return """Puedo ayudarte con varias cosas durante tu estadía:

1. **Recomendaciones** - Puedo sugerirte restaurantes, bares, atracciones turísticas y actividades en Medellín.
2. **Servicio a la habitación** - Puedes pedir comida y bebida a tu habitación.
3. **Transporte** - Te ayudo a programar taxis u otros servicios de transporte.
4. **Información del hotel** - Pregúntame sobre horarios, ubicaciones o servicios del hotel.
5. **Clima** - Te puedo informar sobre el clima actual y pronóstico.

Simplemente háblame como lo harías normalmente. Por ejemplo:
- "¿Me recomiendas un buen restaurante cerca?"
- "Quiero ordenar algo de comer a mi habitación"
- "Necesito un taxi para ir al aeropuerto mañana a las 10 am"
- "¿Cuál es la clave del WiFi?"
- "¿Cómo está el clima hoy?"

¿En qué puedo ayudarte ahora?"""


def handle_thanks():
    """Handle thanks intent"""
    responses = [
        "De nada, es un placer ayudarte.",
        "Para eso estoy aquí. ¿Hay algo más en lo que pueda asistirte?",
        "No hay de qué. Estoy aquí para hacer tu estadía más cómoda.",
        "Es mi placer. Si necesitas cualquier otra cosa, solo pregunta."
    ]
    return responses[datetime.now().second % len(responses)]
