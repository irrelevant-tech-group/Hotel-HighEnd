import logging
from datetime import datetime, timedelta
import dateutil.parser
from app import db
from models import Guest, TransportationRequest

logger = logging.getLogger(__name__)

def schedule_transportation(guest_id, pickup_time, destination, num_passengers=1, vehicle_type='taxi', special_notes=''):
    """
    Schedule transportation for a guest
    
    Args:
        guest_id (int): ID of the guest
        pickup_time (str): Time for pickup (can be datetime string or natural language)
        destination (str): Destination address
        num_passengers (int): Number of passengers
        vehicle_type (str): Type of vehicle (taxi, private car, etc.)
        special_notes (str): Additional notes
        
    Returns:
        int: Transportation request ID
    """
    try:
        # Get the guest
        guest = Guest.query.get(guest_id)
        if not guest:
            raise ValueError(f"Guest with ID {guest_id} not found")
        
        # Parse pickup time
        parsed_time = parse_pickup_time(pickup_time)
        
        # Create transportation request
        new_request = TransportationRequest(
            guest_id=guest_id,
            pickup_time=parsed_time,
            destination=destination,
            num_passengers=num_passengers,
            vehicle_type=vehicle_type,
            special_notes=special_notes
        )
        
        db.session.add(new_request)
        db.session.commit()
        
        return new_request.id
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error scheduling transportation: {str(e)}")
        raise


def parse_pickup_time(pickup_time):
    """
    Parse pickup time from various formats
    
    Args:
        pickup_time (str): Time string in various formats
        
    Returns:
        datetime: Parsed datetime object
    """
    try:
        # Try to parse as ISO format first
        return dateutil.parser.parse(pickup_time)
    except:
        # Handle relative time expressions
        now = datetime.now()
        lower_time = pickup_time.lower()
        
        if "minuto" in lower_time or "minutos" in lower_time:
            # e.g., "en 30 minutos"
            try:
                minutes = int(''.join(c for c in lower_time if c.isdigit()))
                return now.replace(microsecond=0) + timedelta(minutes=minutes)
            except:
                pass
                
        elif "hora" in lower_time or "horas" in lower_time:
            # e.g., "en 2 horas"
            try:
                hours = int(''.join(c for c in lower_time if c.isdigit()))
                return now.replace(microsecond=0) + timedelta(hours=hours)
            except:
                pass
                
        elif "mañana" in lower_time:
            # e.g., "mañana a las 10" or "mañana a las 10:30"
            try:
                # Extract time part
                if "a las" in lower_time:
                    time_part = lower_time.split("a las")[1].strip()
                    hours = int(time_part.split(":")[0])
                    minutes = int(time_part.split(":")[1]) if ":" in time_part else 0
                    
                    tomorrow = now + timedelta(days=1)
                    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, hours, minutes)
                else:
                    # Default to 9:00 AM tomorrow if no specific time
                    tomorrow = now + timedelta(days=1)
                    return datetime(tomorrow.year, tomorrow.month, tomorrow.day, 9, 0)
            except:
                pass
        
        # Try common time formats (for today)
        try:
            # Try parsing as time only (e.g., "14:30" or "2:30 pm")
            time_formats = ["%H:%M", "%I:%M %p", "%I:%M%p", "%I %p", "%I%p"]
            
            for fmt in time_formats:
                try:
                    parsed_time = datetime.strptime(pickup_time, fmt)
                    return datetime(now.year, now.month, now.day, 
                                  parsed_time.hour, parsed_time.minute)
                except:
                    continue
        except:
            pass
            
        # If all parsing attempts fail, default to 30 minutes from now
        logger.warning(f"Could not parse pickup time: {pickup_time}. Defaulting to 30 minutes from now.")
        return now.replace(microsecond=0) + timedelta(minutes=30)


def get_transportation_request(request_id):
    """
    Get details of a transportation request
    
    Args:
        request_id (int): ID of the transportation request
        
    Returns:
        dict: Transportation request details
    """
    try:
        request = TransportationRequest.query.get(request_id)
        if not request:
            raise ValueError(f"Transportation request with ID {request_id} not found")
        
        return {
            'id': request.id,
            'guest_id': request.guest_id,
            'pickup_time': request.pickup_time.isoformat(),
            'destination': request.destination,
            'num_passengers': request.num_passengers,
            'vehicle_type': request.vehicle_type,
            'special_notes': request.special_notes,
            'status': request.status,
            'request_date': request.request_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error getting transportation request: {str(e)}")
        return None


def update_transportation_status(request_id, new_status):
    """
    Update the status of a transportation request
    
    Args:
        request_id (int): ID of the transportation request
        new_status (str): New status value
        
    Returns:
        bool: Success or failure
    """
    try:
        request = TransportationRequest.query.get(request_id)
        if not request:
            raise ValueError(f"Transportation request with ID {request_id} not found")
        
        valid_statuses = ['pending', 'confirmed', 'completed', 'cancelled']
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")
        
        request.status = new_status
        db.session.commit()
        
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating transportation status: {str(e)}")
        return False


def get_upcoming_transportation_for_guest(guest_id):
    """
    Get upcoming transportation requests for a guest
    
    Args:
        guest_id (int): ID of the guest
        
    Returns:
        list: List of upcoming transportation requests
    """
    try:
        now = datetime.utcnow()
        
        # Get future requests that are pending or confirmed
        requests = TransportationRequest.query.filter(
            TransportationRequest.guest_id == guest_id,
            TransportationRequest.pickup_time > now,
            TransportationRequest.status.in_(['pending', 'confirmed'])
        ).order_by(TransportationRequest.pickup_time).all()
        
        return [{
            'id': req.id,
            'pickup_time': req.pickup_time.isoformat(),
            'destination': req.destination,
            'vehicle_type': req.vehicle_type,
            'status': req.status
        } for req in requests]
        
    except Exception as e:
        logger.error(f"Error getting upcoming transportation: {str(e)}")
        return []
