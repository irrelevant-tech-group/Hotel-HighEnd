import logging
import re
import json
from datetime import datetime, timedelta
import random

logger = logging.getLogger(__name__)

# Since we don't have direct access to spaCy in this implementation,
# we'll create simplified NLP functions for the MVP

def classify_intent(message):
    """
    Classify the intent of a user message
    
    Args:
        message (str): The user message
        
    Returns:
        tuple: (intent, confidence)
    """
    # Normalize message
    message = message.lower().strip()
    
    # Simple rule-based intent classification
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
            r'\bir\b.*\baeropuerto\b', r'\bir\b.*\bciudad\b', r'\bir\b.*\a\b',
            r'\bviaje\b', r'\btraslado\b', r'\bcomo llegar\b', r'\bmovilizarme\b'
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
        for pattern in patterns:
            if re.search(pattern, message):
                score += 1
        
        if score > 0:
            confidence = min(0.5 + (score * 0.1), 0.95)  # Scale confidence
            scores[intent] = confidence
    
    # If no matches, default to FAQ with low confidence
    if not scores:
        return 'faq', 0.3
    
    # Get highest scoring intent
    best_intent = max(scores.items(), key=lambda x: x[1])
    return best_intent[0], best_intent[1]


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
    if 'taxi' in message or 'transporte' in message or 'uber' in message or 'carro' in message:
        # Extract destination
        dest_patterns = [
            r'(?:a|al|hacia|para)\s+(?:el|la|los|las)?\s+([a-zá-úñ\s]+?)(?:\s+a las|\s+para|\s+por|\s+mañana|\s+hoy|\.|$)',
            r'(?:ir)\s+(?:a|al)\s+([a-zá-úñ\s]+?)(?:\s+a las|\s+para|\s+por|\s+mañana|\s+hoy|\.|$)'
        ]
        
        for pattern in dest_patterns:
            dest_match = re.search(pattern, message)
            if dest_match:
                # Clean up destination
                destination = dest_match.group(1).strip()
                if destination:
                    entities['destination'] = destination
                break
        
        # Extract time
        time_patterns = [
            r'a las\s+(\d{1,2}(?::\d{2})?(?:\s*[ap]\.?m\.?)?)',
            r'para las\s+(\d{1,2}(?::\d{2})?(?:\s*[ap]\.?m\.?)?)',
            r'(\d{1,2}(?::\d{2})?(?:\s*[ap]\.?m\.?))',
            r'en\s+(\d+)\s+(?:hora|horas)',
            r'mañana a las\s+(\d{1,2}(?::\d{2})?(?:\s*[ap]\.?m\.?)?)'
        ]
        
        for pattern in time_patterns:
            time_match = re.search(pattern, message)
            if time_match:
                pickup_time = time_match.group(1).strip()
                if pickup_time:
                    # Add 'mañana' prefix if context implies
                    if 'mañana' in message and 'mañana' not in pickup_time:
                        pickup_time = 'mañana ' + pickup_time
                    entities['pickup_time'] = pickup_time
                break
        
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
