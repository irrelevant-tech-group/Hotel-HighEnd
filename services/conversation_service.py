import logging
import json
import requests
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
        # Add the raw message text to entities for further processing
        entities['text'] = message
        logger.debug(f"Extracted entities: {entities}")
        
        # Detect intent for specialized handling and analytics
        intent, confidence = classify_intent(message)
        logger.debug(f"\n\n---------------------------------\n\n")
        logger.debug(f"Detected intent: {intent} with confidence: {confidence}")
        logger.debug(f"\n\n---------------------------------\n\n")
        
        # Store previous intent before updating
        if 'current_intent' in updated_context:
            updated_context['previous_intent'] = updated_context['current_intent']
        updated_context['current_intent'] = intent

        logger.debug(f"\n\n---------------------------------\n\n")
        logger.debug(f"current_intent: {updated_context['current_intent']}")
        logger.debug(f"\n\n---------------------------------\n\n")

        # Check if this is a follow-up question about a specific place
        if 'text' in entities:
            # Look for place names in the question
            place_matches = extract_place_references(entities['text'])
            if place_matches:
                # Store the most recently discussed place
                updated_context['last_mentioned_destination'] = place_matches[0]
                # If this is a question about a place, treat it as a recommendation follow-up
                if intent == "question":
                    updated_context['previous_intent'] = "recommendation"
            
            # Check for references to previous context
            ambiguous_terms = ['alla', 'ahi', 'ahí', 'alli', 'allí', 'para alla', 'el lugar']
            if any(term in message.lower() for term in ambiguous_terms):
                # Keep the previous context active
                if 'previous_intent' in updated_context:
                    intent = updated_context['previous_intent']
                    updated_context['current_intent'] = intent
        
        # Special handling for transportation requests following any restaurant/place discussion
        if intent == "transportation":
            # Update context with new entities while preserving relevant previous context
            for key, value in entities.items():
                if key not in ['destination', 'vehicle_type'] or value is not None:
                    updated_context[key] = value

            # First check for explicit destination in request
            if 'destination' not in entities and 'destination' in updated_context:
                entities['destination'] = updated_context['destination']
            elif 'destination' not in entities:
                # Then check context in order of precedence:
                # 1. Last explicitly mentioned destination
                if 'last_mentioned_destination' in updated_context:
                    entities['destination'] = updated_context['last_mentioned_destination']
                # 2. Current recommendation being discussed
                elif 'current_recommendation' in updated_context:
                    entities['destination'] = updated_context['current_recommendation'].get('name')
                # 3. Most recent recommendation from history
                elif 'all_recommendations' in updated_context and updated_context['all_recommendations']:
                    entities['destination'] = updated_context['all_recommendations'][0].get('name')

            # Check for vehicle type in context
            if 'vehicle_type' not in entities and 'vehicle_type' in updated_context:
                entities['vehicle_type'] = updated_context['vehicle_type']

            # Synchronize time and pickup_time
            if 'time' in entities and 'pickup_time' not in entities:
                entities['pickup_time'] = entities['time']
                updated_context['pickup_time'] = entities['time']
            elif 'pickup_time' in entities and 'time' not in entities:
                entities['time'] = entities['pickup_time']
                updated_context['time'] = entities['pickup_time']
            elif 'time' not in entities and 'pickup_time' not in entities:
                if 'time' in updated_context:
                    entities['time'] = updated_context['time']
                    entities['pickup_time'] = updated_context['time']
                elif 'pickup_time' in updated_context:
                    entities['time'] = updated_context['pickup_time']
                    entities['pickup_time'] = updated_context['pickup_time']
            
            # Define required fields for transportation
            required_fields = ['destination', 'vehicle_type', 'pickup_time']
            missing_fields = [field for field in required_fields if field not in entities]
            
            logger.debug(f"\n\n---------------------------------\n\n")
            logger.debug("Transportation Intent Detected - Status:")
            logger.debug("\nCampos presentes:")
            for key, value in entities.items():
                logger.debug(f"✓ {key}: {value}")
                # Update context with any new information
                updated_context[key] = value
            
            logger.debug("\nCampos faltantes:")
            for field in required_fields:
                if field not in entities:
                    logger.debug(f"✗ {field}: No especificado")
            
            logger.debug(f"\nContexto actual:")
            logger.debug(f"{updated_context}")
            logger.debug(f"\n---------------------------------\n\n")
            
            if missing_fields:
                # Create a more natural message asking for missing information
                if 'destination' in missing_fields:
                    return "¿A qué lugar te gustaría ir?", updated_context
                elif 'vehicle_type' in missing_fields:
                    return "¿Prefieres que sea taxi, Uber o carro privado?", updated_context
                elif 'pickup_time' in missing_fields:
                    return "¿A qué hora te gustaría salir?", updated_context
            
            # If we have all required fields, proceed with transportation request
            response = handle_transportation(guest, entities, updated_context)
            return response, updated_context
        
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
            
            # Get the recommendations and store the current one in context
            recommendations = get_personalized_recommendations(guest.id, entities['category'])
            if recommendations:
                updated_context['current_recommendation'] = recommendations[0]
                updated_context['all_recommendations'] = recommendations
        
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
    try:
        logger.debug("\n" + "="*50)
        logger.debug("ENTERING handle_transportation")
        logger.debug(f"Guest: {guest}")
        logger.debug(f"Entities: {entities}")
        logger.debug(f"Context: {context}")
        
        # First check for ambiguous references to previously mentioned places
        if 'destination' in entities:
            ambiguous_terms = ['alla', 'ahi', 'ahí', 'alli', 'allí', 'para alla', 'el lugar']
            if any(term in entities['destination'].lower() for term in ambiguous_terms):
                if 'last_mentioned_destination' in context:
                    entities['destination'] = context['last_mentioned_destination']
                    logger.debug(f"Using last mentioned destination: {entities['destination']}")
                elif 'current_recommendation' in context:
                    entities['destination'] = context['current_recommendation'].get('name')
                    logger.debug(f"Using current recommendation as destination: {entities['destination']}")
                else:
                    return "¿A dónde te gustaría ir? Necesito saber el destino específico para programar tu transporte."

        # If no destination found, check context
        if 'destination' not in entities:
            logger.debug("No destination found in entities")
            if 'last_mentioned_destination' in context:
                entities['destination'] = context['last_mentioned_destination']
            elif 'current_recommendation' in context:
                entities['destination'] = context['current_recommendation'].get('name')
            else:
                return "¿A dónde te gustaría ir? Necesito saber el destino para programar tu transporte."

        destination = entities['destination']
        logger.debug(f"Destination found: {destination}")
        
        # Store the destination in context for future reference
        context['last_mentioned_destination'] = destination

        # Get or set default values for other transportation details
        # If time is specified in the request (e.g., "en 10 minutos"), use that
        if 'time' in entities:
            pickup_time = entities['time']
        else:
            pickup_time = datetime.now().isoformat()
        logger.debug(f"Pickup time: {pickup_time}")
            
        # Use guest's preferred transport type if available, or maintain the one from context
        vehicle_type = entities.get('vehicle_type')
        if not vehicle_type:
            vehicle_type = context.get('vehicle_type') or context.get('preferred_transport')
            if not vehicle_type and guest.preferences:
                try:
                    vehicle_type = json.loads(guest.preferences).get('transport', 'taxi')
                except:
                    vehicle_type = 'taxi'
        
        # Store vehicle type in context for future use
        context['vehicle_type'] = vehicle_type
        logger.debug(f"Vehicle type: {vehicle_type}")
        
        num_passengers = entities.get('num_passengers', 1)
        logger.debug(f"Number of passengers: {num_passengers}")

        # Schedule the transportation
        try:
            logger.debug("Attempting to schedule transportation")
            request_id = schedule_transportation(
                guest_id=guest.id,
                pickup_time=pickup_time,
                destination=destination,
                num_passengers=num_passengers,
                vehicle_type=vehicle_type
            )
            logger.debug(f"Transportation scheduled, request_id: {request_id}")
            
            if request_id:
                # Format response based on context
                response = f"He programado tu {vehicle_type} para ir a {destination}. "
                response += f"Tu número de confirmación es {request_id}. "
                response += "Recibirás una llamada de confirmación en breve. Te avisaré cuando el vehículo esté llegando."
                logger.debug(f"Returning success response: {response}")
                return response
            else:
                logger.debug("No request_id received, returning error message")
                return "Lo siento, hubo un problema al programar el transporte. ¿Podrías intentarlo de nuevo?"
                
        except Exception as e:
            logger.error(f"Error scheduling transportation: {str(e)}", exc_info=True)
            return "Lo siento, hubo un problema al programar el transporte. ¿Podrías intentarlo de nuevo?"

    except Exception as e:
        logger.error(f"Error handling transportation request: {str(e)}", exc_info=True)
        return "Lo siento, tuve un problema al procesar tu solicitud de transporte. ¿Puedes intentarlo de nuevo?"


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


def extract_place_references(text):
    """Extract potential place names from text using NLP"""
    # This is a simplified version - in practice, you'd want to use a proper NLP library
    # and maintain a list of known places
    known_places = [
        "Mondongos", "Carmen", "El Cielo", "OCI.Mde",
        # Add other known restaurant/place names
    ]
    
    found_places = []
    for place in known_places:
        if place.lower() in text.lower():
            found_places.append(place)
    
    return found_places
