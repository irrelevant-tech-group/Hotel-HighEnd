import logging
import json
import os
from difflib import SequenceMatcher
from config import FACILITIES

logger = logging.getLogger(__name__)

# Preguntas frecuentes predefinidas
DEFAULT_FAQS = {
    "breakfast": {
        "questions": [
            "¿A qué hora es el desayuno?",
            "¿Dónde puedo desayunar?",
            "¿Está incluido el desayuno?",
            "¿Tienen opciones vegetarianas para el desayuno?"
        ],
        "answer": f"El desayuno se sirve de {FACILITIES['breakfast']['hours']} en {FACILITIES['breakfast']['location']}. {FACILITIES['breakfast']['details']}"
    },
    "checkout": {
        "questions": [
            "¿A qué hora es el check-out?",
            "¿Puedo hacer late check-out?",
            "¿Cuándo debo dejar la habitación?",
            "¿Cómo funciona el checkout?"
        ],
        "answer": f"El check-out es a las {FACILITIES['checkout']['time']}. {FACILITIES['checkout']['late_checkout']}"
    },
    "wifi": {
        "questions": [
            "¿Hay WiFi en el hotel?",
            "¿Cuál es la contraseña del WiFi?",
            "¿Cómo me conecto al internet?",
            "¿El WiFi es gratis?"
        ],
        "answer": f"Sí, ofrecemos WiFi gratuito en todo el hotel. El nombre de la red es {FACILITIES['wifi']['name']}. {FACILITIES['wifi']['details']}"
    },
    "pool": {
        "questions": [
            "¿El hotel tiene piscina?",
            "¿Cuál es el horario de la piscina?",
            "¿Dónde está ubicada la piscina?",
            "¿Hay que pagar para usar la piscina?"
        ],
        "answer": f"Sí, tenemos una piscina disponible de {FACILITIES['pool']['hours']} en {FACILITIES['pool']['location']}. {FACILITIES['pool']['details']}"
    },
    "spa": {
        "questions": [
            "¿Tienen spa?",
            "¿Cómo reservo un tratamiento en el spa?",
            "¿Cuál es el horario del spa?",
            "¿Qué servicios ofrece el spa?"
        ],
        "answer": f"Nuestro spa está abierto de {FACILITIES['spa']['hours']} en {FACILITIES['spa']['location']}. {FACILITIES['spa']['details']}"
    },
    "gym": {
        "questions": [
            "¿Tienen gimnasio?",
            "¿Cuál es el horario del gimnasio?",
            "¿Dónde está el gimnasio?",
            "¿El gimnasio tiene instructor?"
        ],
        "answer": f"Sí, nuestro gimnasio está disponible {FACILITIES['gym']['hours']} en {FACILITIES['gym']['location']}. {FACILITIES['gym']['details']}"
    },
    "room_service": {
        "questions": [
            "¿Tienen servicio a la habitación?",
            "¿Cómo pido servicio a la habitación?",
            "¿Hasta qué hora puedo pedir comida a la habitación?",
            "¿Cuánto tarda el servicio a la habitación?"
        ],
        "answer": f"Ofrecemos servicio a la habitación {FACILITIES['room_service']['hours']}. {FACILITIES['room_service']['details']} Puede solicitarlo a través de Lina o marcando el 1 desde el teléfono de su habitación."
    },
    "restaurants": {
        "questions": [
            "¿Qué restaurantes tiene el hotel?",
            "¿Dónde puedo cenar en el hotel?",
            "¿Tienen restaurante para cenar?",
            "¿Cuál es el horario del restaurante?"
        ],
        "answer": "El Hotel Aramé cuenta con dos restaurantes: Aramé Gourmet (cocina internacional, abierto para desayuno, almuerzo y cena de 6:30 AM a 11:00 PM) y Azafrán (especialidad en cocina mediterránea, abierto para cena de 6:00 PM a 11:00 PM). Se recomienda reservación para cenas en Azafrán."
    },
    "parking": {
        "questions": [
            "¿Tienen estacionamiento?",
            "¿El estacionamiento es gratis?",
            "¿Dónde puedo estacionar mi auto?",
            "¿Tienen servicio de valet parking?"
        ],
        "answer": f"{FACILITIES['parking']['details']}"
    },
    "business_center": {
        "questions": [
            "¿Tienen centro de negocios?",
            "¿Dónde puedo imprimir documentos?",
            "¿Tienen salas de reuniones?",
            "¿Puedo usar alguna computadora del hotel?"
        ],
        "answer": f"Nuestro centro de negocios está disponible {FACILITIES['business_center']['hours']} en {FACILITIES['business_center']['location']}. {FACILITIES['business_center']['details']}"
    }
}

def load_faq_data():
    """Load FAQ data from file or configure default FAQs"""
    try:
        faq_file = os.path.join('data', 'faq.json')
        if os.path.exists(faq_file):
            with open(faq_file, 'r', encoding='utf-8') as file:
                return json.load(file)
        else:
            logger.info("FAQ file not found, using default FAQs")
            return DEFAULT_FAQS
    except Exception as e:
        logger.error(f"Error loading FAQ data: {str(e)}")
        return DEFAULT_FAQS

def calculate_similarity(query, reference):
    """Calculate string similarity between query and reference"""
    return SequenceMatcher(None, query.lower(), reference.lower()).ratio()

def get_faq_response(question):
    """
    Get response for a FAQ question
    
    Args:
        question (str): The question from the guest
        
    Returns:
        str: The answer to the question
    """
    try:
        # Load FAQ data
        faq_data = load_faq_data()
        
        best_match = None
        best_similarity = 0
        
        # Find the best match for the question
        for category, data in faq_data.items():
            for ref_question in data["questions"]:
                similarity = calculate_similarity(question, ref_question)
                
                if similarity > best_similarity and similarity > 0.6:
                    best_similarity = similarity
                    best_match = category
        
        # Return the answer if a good match is found
        if best_match and best_match in faq_data:
            return faq_data[best_match]["answer"]
        
        # If no good match, try to extract key terms and find related info
        lower_question = question.lower()
        for key_term in ["desayuno", "breakfast", "wifi", "internet", "piscina", "pool", 
                         "spa", "gimnasio", "gym", "checkout", "salida", "estacionamiento", 
                         "parking", "restaurante", "restaurant", "servicio a la habitación", 
                         "room service", "negocio", "business"]:
            if key_term in lower_question:
                for category, data in faq_data.items():
                    if key_term in category.lower() or any(key_term in q.lower() for q in data["questions"]):
                        return data["answer"]
        
        # Default response if no match found
        return "Lo siento, no tengo información específica sobre esa pregunta. Por favor, contacte a la recepción marcando 0 desde el teléfono de su habitación o consulte a Lina sobre otros temas como servicios del hotel, recomendaciones locales o reservas."
        
    except Exception as e:
        logger.error(f"Error getting FAQ response: {str(e)}")
        return "Lo siento, no pude procesar su pregunta en este momento. Por favor, intente de nuevo o contacte a la recepción."