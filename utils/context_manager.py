from datetime import datetime

def update_context(context, intent, entities):
    """
    Update conversation context based on current intent and entities
    """
    if not context:
        context = []
        
    # Create new context entry
    current_entry = {
        'intent': intent,
        'timestamp': datetime.now().isoformat()
    }
    
    # Track last mentioned destination
    if 'destination' in entities:
        is_valid, cleaned_dest = validate_destination(entities['destination'])
        if is_valid:
            current_entry['destination'] = cleaned_dest
            
    # Track last mentioned restaurant if present
    if 'restaurant' in entities:
        current_entry['restaurant'] = entities['restaurant']
        
    # Track place type if present
    if 'place_type' in entities:
        current_entry['place_type'] = entities['place_type']
        
    # Track time-related information
    if 'time' in entities:
        current_entry['time'] = entities['time']
    if 'date' in entities:
        current_entry['date'] = entities['date']
        
    # Add new entry to context
    context.append(current_entry)
    
    # Limit context size while preserving critical information
    if len(context) > 10:
        # Keep only the most recent entries that contain important keys
        important_keys = ['destination', 'restaurant', 'place_type', 'time', 'date']
        preserved_entries = []
        
        # Preserve entries with important information
        for entry in reversed(context):
            if any(key in entry for key in important_keys):
                preserved_entries.append(entry)
                if len(preserved_entries) >= 5:  # Keep at most 5 important entries
                    break
                    
        # Keep the 5 most recent entries regardless of content
        recent_entries = context[-5:]
        
        # Combine preserved and recent entries, remove duplicates
        new_context = list({entry['timestamp']: entry for entry in preserved_entries + recent_entries}.values())
        new_context.sort(key=lambda x: x['timestamp'])  # Sort by timestamp
        context = new_context[-10:]  # Keep at most 10 entries
    
    return context

def validate_destination(destination):
    """
    Validate and clean destination data
    Returns: (is_valid, cleaned_destination)
    """
    if not destination:
        return False, None
        
    # List of ambiguous terms that shouldn't be treated as valid destinations
    ambiguous_terms = ['ahi', 'alla', 'aca', 'aqui', 'there', 'here']
    
    # Common prefixes to remove
    prefixes_to_remove = [
        'quiero ir a', 'quiero ir al', 'quiero ir a la', 
        'ir a', 'ir al', 'ir a la',
        'voy a', 'voy al', 'voy a la',
        'para', 'hacia', 'hasta'
    ]
    
    # Clean the destination string
    cleaned_dest = destination.lower().strip()
    
    # Remove common prefixes
    for prefix in prefixes_to_remove:
        if cleaned_dest.startswith(prefix):
            cleaned_dest = cleaned_dest[len(prefix):].strip()
            
    # Remove leading articles if they exist
    articles = ['el ', 'la ', 'los ', 'las ']
    for article in articles:
        if cleaned_dest.startswith(article):
            cleaned_dest = cleaned_dest[len(article):].strip()
    
    # Check if the destination is just an ambiguous term
    if cleaned_dest in ambiguous_terms:
        return False, None
        
    # Additional validation could be added here (e.g., minimum length, format checking)
    if len(cleaned_dest) < 2:
        return False, None
        
    return True, cleaned_dest 