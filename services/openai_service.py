import os
import json
import logging
from openai import OpenAI
from datetime import datetime

logger = logging.getLogger(__name__)

# Initialize OpenAI client with API key
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
client = OpenAI(api_key=OPENAI_API_KEY)

def generate_response(prompt, conversation_history=None, guest_info=None, context=None, max_tokens=500):
    """
    Generate a response using OpenAI's GPT model with RAG capabilities
    
    Args:
        prompt (str): The prompt/question to answer
        conversation_history (list, optional): Previous conversation messages 
        guest_info (dict, optional): Information about the guest
        context (dict, optional): Additional context information
        max_tokens (int, optional): Maximum tokens for response
        
    Returns:
        str: Generated response text
    """
    try:
        # Get current time in Medellín
        current_time = datetime.now().strftime("%A, %d de %B de %Y, %H:%M")
        
        # Prepare conversation history in the format OpenAI expects
        messages = []
        
        # STEP 1: Create a detailed system prompt with RAG components
        system_prompt = create_rag_system_prompt(guest_info, context, current_time)
        messages.append({"role": "system", "content": system_prompt})
        
        # STEP 2: Add relevant conversation history with summaries if needed
        if conversation_history:
            # If conversation history is too long, summarize older parts
            if len(conversation_history) > 10:
                # Extract the most recent 5 messages
                recent_messages = conversation_history[-5:]
                
                # Summarize older messages
                older_messages = conversation_history[:-5]
                summary = summarize_conversation(older_messages)
                messages.append({
                    "role": "system", 
                    "content": f"Resumen de la conversación anterior: {summary}"
                })
                
                # Add the recent messages directly
                for message in recent_messages:
                    messages.append({
                        "role": message.get("role", "user"),
                        "content": message.get("content", "")
                    })
            else:
                # Add all conversation history if it's not too long
                for message in conversation_history:
                    messages.append({
                        "role": message.get("role", "user"),
                        "content": message.get("content", "")
                    })
        
        # STEP 3: Add the current prompt with enhanced context awareness
        # If we have context, check if the prompt is related to any specific service
        enhanced_prompt = prompt
        if context:
            # Analyze if prompt is related to specific hotel services
            service_context = get_service_specific_context(prompt, context)
            if service_context:
                enhanced_prompt = f"{prompt}\n\nInformación relevante: {service_context}"
        
        messages.append({"role": "user", "content": enhanced_prompt})
        
        # STEP 4: Call OpenAI API with the enhanced context
        response = client.chat.completions.create(
            model="gpt-4o",  # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.7
        )
        
        # STEP 5: Extract and post-process the response
        response_text = response.choices[0].message.content
        
        # Make responses less formal and more conversational if needed
        response_text = make_response_conversational(response_text)
        
        return response_text
        
    except Exception as e:
        logger.error(f"Error generating OpenAI response: {str(e)}")
        return "Lo siento, tuve un problema al procesar tu solicitud. ¿Puedes intentarlo de nuevo?"

def create_rag_system_prompt(guest_info, context, current_time):
    """
    Create a comprehensive system prompt with RAG components
    """
    # Base persona definition
    base_prompt = (
        "Eres Lina, la concierge digital del Hotel Aramé en Medellín, Colombia. "
        "Eres servicial, cercana y conocedora de la ciudad. "
        "Responde en español con un tono cálido y cercano, como si fueras una amiga que conoce muy bien la ciudad. "
        "Evita ser excesivamente formal o usar lenguaje corporativo. "
        "Usa un lenguaje sencillo, directo y ocasionalmente expresiones locales de Medellín. "
        "No termines tus mensajes con 'Saludos cordiales' ni firmes como 'Lina, Concierge Digital'. "
        "Tu objetivo es hacer que la estancia del huésped sea memorable."
    )
    
    # Add current time context
    time_context = f"Hoy es {current_time} en Medellín, Colombia."
    
    # Add guest-specific information if available
    guest_context = ""
    if guest_info:
        name = guest_info.get('name', '')
        room = guest_info.get('room_number', '')
        interests = guest_info.get('interests', [])
        interests_str = ", ".join(interests) if interests else "desconocidos"
        diet = guest_info.get('diet', '')
        trip_type = guest_info.get('trip_type', '')
        
        guest_context = (
            f"Estás hablando con {name} que se hospeda en la habitación {room}. "
            f"Sus intereses incluyen: {interests_str}. "
        )
        
        if diet:
            guest_context += f"Tiene preferencias alimentarias: {diet}. "
        
        if trip_type:
            guest_context += f"Está viajando por: {trip_type}. "
    
    # Add hotel-specific information and local knowledge
    hotel_info = (
        "El Hotel Aramé es un hotel boutique de lujo en El Poblado, Medellín. "
        "Ofrece servicio a la habitación 24/7, spa, piscina, restaurante 'Sabor Aramé' y bar en la terraza. "
        "El desayuno se sirve de 6:30am a 10:30am. El check-out es a las 12:00pm. "
        "Lugares cercanos populares incluyen Parque Lleras (10 min caminando), Centro Comercial El Tesoro (10 min en taxi), "
        "y Plaza Botero (20 min en taxi). "
    )
    
    # Add any additional context from the conversation
    additional_context = ""
    if context:
        for key, value in context.items():
            if key == "recommendations" and value:
                additional_context += "Recomendaciones previas: " + ", ".join(value) + ". "
            elif key == "previous_requests" and value:
                additional_context += "Solicitudes previas: " + ", ".join(value) + ". "
    
    # Combine all contexts
    full_system_prompt = f"{base_prompt}\n\n{time_context}\n\n{guest_context}\n\n{hotel_info}\n\n{additional_context}"
    
    # Add instructions for response style
    response_instructions = (
        "Sé conversacional y natural en tus respuestas. "
        "Si no sabes algo específico, sé honesta pero siempre ofrece ayudar a conseguir la información. "
        "Cuando menciones lugares específicos, incluye detalles útiles como la distancia aproximada desde el hotel. "
        "Personaliza tus respuestas basándote en los intereses y preferencias conocidas del huésped."
    )
    
    return f"{full_system_prompt}\n\n{response_instructions}"

def summarize_conversation(messages):
    """
    Summarize a list of conversation messages
    """
    try:
        # Prepare conversation text
        conversation_text = ""
        for message in messages:
            role = message.get("role", "user")
            content = message.get("content", "")
            conversation_text += f"{role}: {content}\n"
        
        # Create a prompt for summarization
        prompt = f"""
        Resumir brevemente los puntos clave de esta conversación, enfocándote en:
        1. Las solicitudes o preguntas principales del huésped
        2. Información personal compartida
        3. Preferencias expresadas
        4. Cualquier compromiso o promesa hecha por el concierge
        
        Conversación:
        {conversation_text}
        """
        
        response = client.chat.completions.create(
            model="gpt-4o", # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            messages=[{"role": "user", "content": prompt}],
            max_tokens=250,
            temperature=0.5
        )
        
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error summarizing conversation: {str(e)}")
        return "Conversación previa sobre servicios del hotel y recomendaciones locales."

def get_service_specific_context(prompt, context):
    """
    Get relevant context for specific services mentioned in the prompt
    """
    # Check for room service related queries
    if any(term in prompt.lower() for term in ["comida", "comer", "hambre", "room service", "menú", "desayuno", "almuerzo", "cena"]):
        return (
            "El servicio a la habitación está disponible 24/7. El menú incluye opciones internacionales y locales. "
            "Los platos más populares son el Filete de Pescado Caribeño, Bandeja Paisa y Risotto de Setas. "
            "Para desayuno: continental (desde $25.000 COP), americano (desde $35.000 COP), típico antioqueño (desde $45.000 COP). "
            "Tiempo estimado de entrega: 30-45 minutos."
        )
    
    # Check for transportation related queries
    elif any(term in prompt.lower() for term in ["taxi", "uber", "transporte", "ir a", "visitar", "llegar"]):
        return (
            "El hotel ofrece servicio de transporte privado con reserva previa (mínimo 2 horas). "
            "También podemos llamar un taxi de confianza. Uber y DiDi funcionan bien en la ciudad. "
            "El tiempo al aeropuerto José María Córdova es aproximadamente 45-60 minutos dependiendo del tráfico. "
            "Al centro de la ciudad son aproximadamente 25 minutos en taxi."
        )
    
    # Check for local recommendations
    elif any(term in prompt.lower() for term in ["recomendar", "visitar", "conocer", "turismo", "actividad"]):
        if "restaurante" in prompt.lower() or "comer" in prompt.lower():
            return (
                "Restaurantes recomendados cerca del hotel: "
                "El Cielo (alta cocina colombiana, 5 min en taxi), "
                "Carmen (fusión contemporánea, 10 min caminando), "
                "Mondongo's (comida típica antioqueña, 15 min en taxi), "
                "Pergamino Café (mejor café de especialidad, 7 min caminando)."
            )
        else:
            return (
                "Atracciones populares en Medellín: Parque Arví (teleférico + naturaleza), "
                "Plaza Botero y Museo de Antioquia (arte), Comuna 13 (graffiti tours), "
                "Jardín Botánico (naturaleza urbana), Pueblito Paisa (vistas panorámicas). "
                "Para tours personalizados, podemos organizarlo con nuestros guías de confianza."
            )
    
    # No specific context needed
    return None

def make_response_conversational(text):
    """
    Make responses less formal and more conversational
    """
    # Remove formal closings
    text = text.replace("Saludos cordiales,", "")
    text = text.replace("Atentamente,", "")
    text = text.replace("Cordialmente,", "")
    
    # Remove signatures
    text = text.replace("Lina", "")
    text = text.replace("Concierge Digital", "")
    text = text.replace("Hotel Aramé", "")
    
    # Simplify honorifics
    text = text.replace("Estimado/a señor/a", "Hola")
    text = text.replace("Estimado huésped", "Hola")
    text = text.replace("Distinguido huésped", "Hola")
    
    # Clean up extra spaces and line breaks
    text = text.replace("  ", " ").strip()
    
    return text

def analyze_preferences(guest_info, conversation_history):
    """
    Analyze guest preferences based on their information and conversation history
    
    Args:
        guest_info (dict): Guest information
        conversation_history (list): Previous conversation messages
        
    Returns:
        dict: Guest preferences and insights
    """
    try:
        # Create a prompt for preference analysis
        conversation_text = ""
        for message in conversation_history:
            role = message.get("role", "user")
            content = message.get("content", "")
            conversation_text += f"{role}: {content}\n"
        
        interests = guest_info.get("interests", [])
        interests_text = ", ".join(interests) if interests else "No especificado"
        
        prompt = f"""
        Analiza las preferencias del huésped basado en la siguiente información:
        
        Información del huésped:
        - Nombre: {guest_info.get('name', 'No especificado')}
        - Intereses declarados: {interests_text}
        
        Historial de conversación:
        {conversation_text}
        
        Identifica y devuelve en formato JSON:
        1. Posibles intereses no declarados explícitamente
        2. Tipo de viaje (negocios, vacaciones, etc.)
        3. Preferencias de comida y bebida
        4. Actividades que podrían interesarle
        5. Nivel de formalidad preferido en la comunicación
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        # Parse JSON response
        result = json.loads(response.choices[0].message.content)
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing preferences: {str(e)}")
        return {
            "error": "No se pudieron analizar las preferencias en este momento",
            "interests": [],
            "trip_type": "No determinado",
            "food_preferences": [],
            "activities": [],
            "communication_style": "neutral"
        }

def enhance_recommendations(places, guest_preferences, current_context):
    """
    Enhance place recommendations based on guest preferences and current context
    
    Args:
        places (list): Basic place recommendations
        guest_preferences (dict): Guest preference data
        current_context (dict): Current context (weather, time, etc.)
        
    Returns:
        list: Enhanced recommendations with personalized descriptions
    """
    try:
        # Convert places to JSON string
        places_json = json.dumps(places, ensure_ascii=False)
        preferences_json = json.dumps(guest_preferences, ensure_ascii=False)
        context_json = json.dumps(current_context, ensure_ascii=False)
        
        prompt = f"""
        Mejora las siguientes recomendaciones de lugares basándote en las preferencias del huésped y el contexto actual.
        
        Lugares básicos:
        {places_json}
        
        Preferencias del huésped:
        {preferences_json}
        
        Contexto actual:
        {context_json}
        
        Para cada lugar, añade:
        1. Una descripción personalizada basada en las preferencias del huésped
        2. Por qué este lugar específicamente sería de interés para el huésped
        3. Recomendaciones específicas sobre qué hacer, ver o pedir en ese lugar
        
        Devuelve los resultados en formato JSON manteniendo todos los campos originales más los nuevos campos.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        # Parse and return enhanced recommendations
        result = json.loads(response.choices[0].message.content)
        return result.get("places", places)
        
    except Exception as e:
        logger.error(f"Error enhancing recommendations: {str(e)}")
        return places

def generate_questionnaire(guest_info):
    """
    Generate a personalized questionnaire to learn more about the guest
    
    Args:
        guest_info (dict): Current guest information
        
    Returns:
        list: List of questions objects with question text and possible answers
    """
    try:
        prompt = f"""
        Genera un cuestionario corto (5 preguntas máximo) para aprender más sobre un huésped de hotel y poder ofrecerle recomendaciones más personalizadas.
        
        Información actual del huésped:
        - Nombre: {guest_info.get('name', 'No especificado')}
        - Intereses conocidos: {', '.join(guest_info.get('interests', ['No especificado']))}
        
        Cada pregunta debe:
        1. Ser corta y específica
        2. Tener entre 3-5 posibles respuestas predefinidas
        3. Servir para personalizar recomendaciones
        4. Estar en español
        
        Devuelve el resultado como un array JSON con objetos que tengan:
        - question: El texto de la pregunta
        - answers: Array de posibles respuestas
        - preference_category: La categoría de preferencia que se está consultando (ej. "food", "activities", etc.)
        """
        
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        # Parse and return questionnaire
        result = json.loads(response.choices[0].message.content)
        return result.get("questions", [])
        
    except Exception as e:
        logger.error(f"Error generating questionnaire: {str(e)}")
        return [
            {
                "question": "¿Cuál es el propósito principal de tu viaje?",
                "answers": ["Negocios", "Vacaciones", "Evento especial", "Otro"],
                "preference_category": "trip_purpose"
            },
            {
                "question": "¿Qué tipo de gastronomía prefieres?",
                "answers": ["Local/Colombiana", "Internacional", "Vegetariana/Vegana", "Fusión"],
                "preference_category": "food"
            }
        ]