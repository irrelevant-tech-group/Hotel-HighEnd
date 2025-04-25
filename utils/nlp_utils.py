import logging
import re
import json
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

# Since we don't have direct access to spaCy in this implementation,
# we'll create simplified NLP functions for the MVP

def classify_intent(message, context=None):
    """
    Classify the intent of a user message, taking into account conversation context
    
    Args:
        message (str): The user message
        context (dict, optional): The current conversation context
        
    Returns:
        tuple: (intent, confidence)
    """
    logger.debug("\n" + "="*50)
    logger.debug("ENTERING classify_intent")
    logger.debug(f"Message: {message}")
    logger.debug(f"Context: {context}")
    
    # Normalize message
    message = message.lower().strip()
    logger.debug(f"Normalized message: {message}")
    
    # If we have context and are in the middle of a transportation request,
    # bias towards keeping the transportation intent
    if context and context.get('current_intent') == 'transportation':
        # If we're missing destination or pickup_time, this is likely still part of the transportation flow
        if not context.get('destination') or not context.get('pickup_time'):
            logger.debug("Continuing transportation intent from context")
            return 'transportation', 0.8
            
    # Define intent patterns
    intents = {
        'greeting': [
            r'\bhola\b', r'\bbuenos dias\b', r'\bbuenas tardes\b', r'\bbuenas noches\b',
            r'^hi\b', r'^hey\b', r'\bsaludos\b', r'^holi\b', r'\bvolver\b'
        ],
        'farewell': [
            r'\badios\b', r'\bchao\b', r'\bnos vemos\b', r'\bhasta luego\b',
            r'\bhasta pronto\b', r'\badiós\b'
        ],
        'thanks': [
            r'\bgracias\b', r'\bte agradezco\b', r'\bmuchas gracias\b', r'\bgenial\b.*\bgracias\b',
            r'\bperfecto\b.*\bgracias\b', r'\bexcelente\b.*\bgracias\b'
        ],
        'help': [
            r'\bayuda\b', r'\bayúdame\b', r'\bqué puedes hacer\b', r'\bcómo funciona\b',
            r'\bqué haces\b', r'\bcómo te uso\b', r'\bpuedes ayudarme\b'
        ],
        'recommendation': [
            r'\brecomienda\b', r'\bdónde\b.*\bcomer\b', r'\bdónde\b.*\bvisitar\b',
            r'\bqué\b.*\brecomiendas\b', r'\bsugieres\b', r'\balgo para\b.*\bvisitar\b',
            r'\brestaurante\b', r'\bbar\b', r'\bcafé\b', r'\bmuseo\b', r'\bturismo\b',
            r'\bparque\b', r'\batracci[óo]n\b', r'\bactividad\b', r'\bconocer\b'
        ],
        'room_service': [
            r'\bservicio a la habitaci[óo]n\b', r'\broom service\b', r'\bordenar\b.*\bcomida\b',
            r'\bmen[úu]\b', r'\bcomer\b.*\bhabitaci[óo]n\b', r'\bpedir\b.*\bcomer\b',
            r'\bquiero\b.*\bordenar\b', r'\bhambre\b', r'\btraer\b.*\bcomida\b',
            r'\bdesayuno\b.*\bhabitaci[óo]n\b'
        ],
        'transportation': [
            r'\btaxi\b', r'\btransporte\b', r'\buber\b', r'\bcarro\b', r'\bveh[íi]culo\b',
            r'\bir\b.*\baeropuerto\b', r'\bir\b.*\bciudad\b', 
            r'\bir (?:al?|hacia|para)\b', r'\bme gustar[íi]a ir\b',  # Catch "ir a/al/hacia" and "me gustaría ir"
            r'\bviaje\b', r'\btraslado\b', r'\bcomo llegar\b', r'\bmovilizarme\b',
            r'\ba las\b', r'\bpara las\b', r'\ben\b.*\bhoras?\b', r'\bma[ñn]ana\b',
            r'\b al \b', r'\b hacia \b'
        ],
        'weather': [
            r'\bclima\b', r'\btiempo\b.*\bhoy\b', r'\bllover\b', r'\blluvia\b',
            r'\btemperatura\b', r'\bcalor\b', r'\bfr[íi]o\b', r'\bnublado\b',
            r'\bcómo está\b.*\btiempo\b', r'\bpron[óo]stico\b'
        ],
        'faq': [
            r'\bclave\b.*\bwifi\b', r'\bcontraseña\b.*\bwifi\b', r'\binternet\b',
            r'\bdónde\b.*\bpiscina\b', r'\bdónde\b.*\bspa\b', r'\bdónde\b.*\bgym\b',
            r'\bhorario\b.*\bdesayuno\b', r'\bhora\b.*\bcheck.?out\b', r'\bhora\b.*\bsalida\b',
            r'\bqué\b.*\bincluye\b', r'\bservicio\b.*\bincluido\b', r'\bpagar\b.*\bextra\b'
        ]
    }
    
    # Check each intent pattern
    scores = {}
    for intent, patterns in intents.items():
        score = 0
        matches = []
        for pattern in patterns:
            if re.search(pattern, message):
                score += 1
                matches.append(pattern)
        
        if score > 0:
            # Boost confidence for the current ongoing intent from context
            if context and context.get('current_intent') == intent:
                score += 1
            
            confidence = min(0.5 + (score * 0.1), 0.95)  # Scale confidence
            scores[intent] = confidence
            logger.debug(f"Intent {intent} matched patterns: {matches}, score: {score}, confidence: {confidence}")
    
    # If no matches but we have context, maintain the current intent with lower confidence
    if not scores and context and context.get('current_intent'):
        logger.debug(f"No matches found, maintaining context intent: {context.get('current_intent')}")
        return context['current_intent'], 0.4
    
    # If still no matches, default to FAQ with low confidence
    if not scores:
        logger.debug("No matches found, defaulting to FAQ")
        return 'faq', 0.3
        
    # Get the intent with highest confidence
    max_intent = max(scores.items(), key=lambda x: x[1])
    logger.debug(f"Selected intent: {max_intent[0]} with confidence: {max_intent[1]}")
    return max_intent[0], max_intent[1]


def extract_time(text):
    # Pattern for time with optional "a las" prefix and am/pm
    time_pattern = r'\b(?:a las\s+)?(\d{1,2})(?:\s*(?:am|pm|AM|PM))?\b'
    match = re.search(time_pattern, text)
    if match:
        hour = int(match.group(1))
        # Check if "am" or "pm" is in the text
        if 'pm' in text.lower() and hour < 12:
            hour += 12
        elif 'am' in text.lower() and hour == 12:
            hour = 0
        return f"{hour:02d}:00"
    return None

def extract_entities(message):
    """
    Extract entities from a user message
    
    Args:
        message (str): The user message
        
    Returns:
        dict: Extracted entities
    """
    entities = {}
    
    # Normalize message
    message = message.lower().strip()
    
    # Extract time first
    time = extract_time(message)
    if time:
        entities['time'] = time
        entities['pickup_time'] = time
    
    # Extract recommendation categories
    if re.search(r'\brestaurante\b|\bcomer\b|\bcomida\b|\bgastronom[íi]a\b', message):
        entities['category'] = 'restaurant'
    elif re.search(r'\bbar\b|\bbeber\b|\btrago\b|\bcoctel\b|\bcerveza\b|\bcervecería\b', message):
        entities['category'] = 'bar'
    elif re.search(r'\bcafé\b|\bcafeter[íi]a\b', message):
        entities['category'] = 'cafe'
    elif re.search(r'\bmuseo\b|\barte\b|\bcultura\b|\bexhibici[óo]n\b', message):
        entities['category'] = 'museum'
    elif re.search(r'\bparque\b|\bplaza\b|\bjard[íi]n\b|\b[áa]rea verde\b', message):
        entities['category'] = 'park'
    elif re.search(r'\bturismo\b|\batracci[óo]n\b|\blugar\b.*\btur[íi]stico\b|\bvisitar\b', message):
        entities['category'] = 'attraction'
    elif re.search(r'\bactividad\b|\bexperiencia\b|\btour\b|\bexcursi[óo]n\b', message):
        entities['category'] = 'activity'
    elif re.search(r'\btienda\b|\bcomprar\b|\bshopping\b|\bcentro comercial\b|\bmercado\b', message):
        entities['category'] = 'shopping'
    
    # Extract time periods
    if re.search(r'\bma[ñn]ana\b|\bdesayuno\b|\btemprano\b', message):
        entities['time_period'] = 'morning'
    elif re.search(r'\btarde\b|\balmuerzo\b|\bmediod[íi]a\b', message):
        entities['time_period'] = 'afternoon'
    elif re.search(r'\bnoche\b|\bcena\b|\btarde\b.*\bnoche\b', message):
        entities['time_period'] = 'evening'
    
    # Extract room service items (simplified)
    if 'room_service' in message or 'servicio a la habitación' in message or 'ordenar' in message:
        items = []
        # Simple food item detection
        food_items = [
            'hamburguesa', 'sandwich', 'sándwich', 'ensalada', 'pasta', 'risotto', 
            'sopa', 'pescado', 'carne', 'pollo', 'filete', 'arroz', 'desayuno',
            'americano', 'continental', 'huevos', 'fruta', 'postre', 'tiramisú',
            'cheesecake', 'torta', 'helado'
        ]
        
        # Simple drink item detection
        drink_items = [
            'agua', 'jugo', 'refresco', 'soda', 'café', 'té', 'cerveza', 'vino',
            'cóctel', 'limonada', 'naranja', 'piña', 'gaseosa'
        ]
        
        # Check for food items
        for item in food_items:
            if item in message:
                items.append(item)
        
        # Check for drink items
        for item in drink_items:
            if item in message:
                items.append(item)
        
        if items:
            entities['order_items'] = items
        
        # Extract special instructions
        special_instr_match = re.search(r'(?:con|sin|extra)\s+([a-zá-úñ\s,]+)', message)
        if special_instr_match:
            entities['special_instructions'] = special_instr_match.group(0)
    
    # Extract transportation details
    if 'taxi' in message or 'transporte' in message or 'uber' in message or 'carro' in message or re.search(r'\bir\b', message):
        # First check for common destinations that should override other patterns
        common_destinations = {
            'aeropuerto': r'\baeropuerto\b',
            'centro comercial': r'\bcentro\s+comercial\b',
            'parque lleras': r'\bparque\s+lleras\b',
            'estadio': r'\bestadio\b',
            'terminal': r'\bterminal\b',
            'plaza botero': r'\bplaza\s+botero\b',
            'museo': r'\bmuseo\b',
            'universidad': r'\buniversidad\b',
            'hospital': r'\bhospital\b',
            'metro': r'\bmetro\b'
        }
        
        destination = None
        for dest, pattern in common_destinations.items():
            if re.search(pattern, message):
                destination = dest
                break
                
        if not destination:
            # Extract destination using various patterns
            dest_patterns = [
                # Pattern for "al/a/hacia/para [destination]"
                r'(?:ir|voy|vamos|llegar|quiero ir)\s+(?:a|al|hacia|para)\s+(?:el|la|los|las)?\s+([a-zá-úñ][a-zá-úñ\s]+?)(?:\s+(?:en|con|a las|para|por|mañana|hoy)|$)',
                # Pattern for destinations in taxi/transport requests
                r'(?:pides?|solicitas?|necesitas?|quieres?)?\s+(?:un)?\s+(?:taxi|uber|carro)\s+(?:a|al|hacia|para)\s+(?:el|la|los|las)?\s+([a-zá-úñ][a-zá-úñ\s]+?)(?:\s+(?:para|a)\s+las|$)',
                # Basic destination pattern
                r'(?:a|al|hacia|para)\s+(?:el|la|los|las)?\s+([a-zá-úñ][a-zá-úñ\s]+?)(?:\s+(?:en|con|a las|para|por|mañana|hoy)|$)'
            ]
            
            for pattern in dest_patterns:
                dest_match = re.search(pattern, message)
                if dest_match:
                    # Clean up destination
                    destination = dest_match.group(1).strip()
                    # Remove common verbs and prepositions
                    destination = re.sub(r'^(?:ir|voy|vamos|quiero|para|hacia)\s+(?:a|al|el|la|los|las)?\s*', '', destination)
                    destination = re.sub(r'\s+(?:en|con|por)\s+(?:taxi|uber|carro).*$', '', destination)
                    break
        
        if destination and len(destination) > 2:  # Avoid single letters/articles
            entities['destination'] = destination
        
        # Extract vehicle type
        if 'uber' in message:
            entities['vehicle_type'] = 'uber'
        elif 'taxi' in message:
            entities['vehicle_type'] = 'taxi'
        elif re.search(r'carro\s+privado|vehículo\s+privado', message):
            entities['vehicle_type'] = 'private_car'
        
        # Extract number of passengers
        passengers_match = re.search(r'para\s+(\d+)\s+personas', message)
        if passengers_match:
            try:
                entities['num_passengers'] = int(passengers_match.group(1))
            except:
                pass
    
    return entities
