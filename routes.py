from flask import render_template, request, jsonify, session, redirect, url_for
from models import Guest, Conversation, RoomServiceOrder, TransportationRequest
from services.conversation_service import process_message
from services.recommendation_service import get_personalized_recommendations
from services.room_service import get_menu, place_order
from services.transportation_service import schedule_transportation
from services.faq_service import get_faq_response
import json
import uuid
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Import app and db after all other imports
from app import app, db

@app.route('/')
def index():
    """Landing page with a simple interface to simulate check-in"""
    return render_template('index.html')

@app.route('/onboarding/<guest_id>')
def onboarding(guest_id):
    """Onboarding screen to collect user preferences before chat"""
    guest = Guest.query.get(guest_id)
    if not guest:
        return redirect(url_for('index'))
    
    return render_template('onboarding.html', guest=guest)

@app.route('/api/save-preferences', methods=['POST'])
def save_preferences():
    """API endpoint to save guest preferences from onboarding"""
    data = request.json
    guest_id = data.get('guest_id')
    
    if not guest_id:
        return jsonify({'success': False, 'error': 'ID de huésped es requerido'}), 400
    
    guest = Guest.query.get(guest_id)
    if not guest:
        return jsonify({'success': False, 'error': 'Huésped no encontrado'}), 404
    
    # Save preferences
    preferences = {
        'trip_type': data.get('trip_type', ''),
        'interests': data.get('interests', []),
        'diet': data.get('diet', ''),
        'transport': data.get('transport', 'taxi')
    }
    
    # Update the guest record
    guest.preferences = json.dumps(preferences)
    db.session.commit()
    
    return jsonify({
        'success': True,
        'chat_url': url_for('chat', guest_id=guest_id)
    })

@app.route('/chat/<guest_id>')
def chat(guest_id):
    """Chat interface for a specific guest"""
    guest = Guest.query.get(guest_id)
    if not guest:
        return redirect(url_for('index'))
    
    # Create a unique session ID if it doesn't exist
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
    
    # Check if there's an existing conversation or create a new one
    conversation = Conversation.query.filter_by(
        guest_id=guest_id, 
        session_id=session['session_id']
    ).first()
    
    if not conversation:
        conversation = Conversation(
            guest_id=guest_id,
            session_id=session['session_id'],
            conversation_history=json.dumps([]),
            context=json.dumps({})
        )
        db.session.add(conversation)
        db.session.commit()
    
    return render_template('chat_simple.html', guest=guest)

@app.route('/api/check-in', methods=['POST'])
def check_in():
    """API endpoint to simulate guest check-in"""
    logger.info("Received check-in request")
    data = request.json
    logger.debug(f"Check-in data received: {json.dumps(data, indent=2)}")
    
    # Basic validation
    if not data.get('name') or not data.get('room_number'):
        error_msg = "Missing required fields: name and room_number are required"
        logger.error(error_msg)
        return jsonify({'success': False, 'error': error_msg}), 400
    
    try:
        # Check if guest already exists in this room
        existing_guest = Guest.query.filter_by(
            room_number=data['room_number'], 
            is_active=True
        ).first()
        
        if existing_guest:
            logger.info(f"Updating existing guest in room {data['room_number']}")
            # Update existing guest
            existing_guest.name = data['name']
            existing_guest.phone_number = data.get('phone_number')
            existing_guest.email = data.get('email')
            existing_guest.preferences = json.dumps(data.get('preferences', {}))
            db.session.commit()
            guest_id = existing_guest.id
            logger.info(f"Successfully updated guest with ID: {guest_id}")
        else:
            logger.info(f"Creating new guest for room {data['room_number']}")
            # Create new guest
            new_guest = Guest(
                name=data['name'],
                room_number=data['room_number'],
                phone_number=data.get('phone_number'),
                email=data.get('email'),
                preferences=json.dumps(data.get('preferences', {})),
                check_in_date=datetime.utcnow()
            )
            db.session.add(new_guest)
            try:
                db.session.commit()
                guest_id = new_guest.id
                logger.info(f"Successfully created new guest with ID: {guest_id}")
            except Exception as db_error:
                logger.error(f"Database error during guest creation: {str(db_error)}")
                db.session.rollback()
                raise
        
        response_data = {
            'success': True, 
            'guest_id': guest_id, 
            'message': 'Check-in completado correctamente',
            'onboarding_url': url_for('onboarding', guest_id=guest_id)
        }
        logger.info(f"Check-in successful. Response: {json.dumps(response_data, indent=2)}")
        return jsonify(response_data)
        
    except Exception as e:
        error_msg = f"Error during check-in process: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return jsonify({
            'success': False, 
            'error': error_msg,
            'details': str(e)
        }), 500

@app.route('/api/send-message', methods=['POST'])
def send_message():
    """API endpoint to process incoming messages from the guest"""
    data = request.json
    guest_id = data.get('guest_id')
    user_message = data.get('message')
    
    if not guest_id or not user_message:
        return jsonify({'success': False, 'error': 'ID de huésped y mensaje son requeridos'}), 400
    
    # Get the guest
    guest = Guest.query.get(guest_id)
    if not guest:
        return jsonify({'success': False, 'error': 'Huésped no encontrado'}), 404
    
    # Get or create conversation
    if 'session_id' not in session:
        session['session_id'] = str(uuid.uuid4())
        
    conversation = Conversation.query.filter_by(
        guest_id=guest_id, 
        session_id=session['session_id']
    ).first()
    
    if not conversation:
        conversation = Conversation(
            guest_id=guest_id,
            session_id=session['session_id'],
            conversation_history=json.dumps([]),
            context=json.dumps({})
        )
        db.session.add(conversation)
        db.session.commit()
    
    # Process the message
    try:
        response, updated_context = process_message(
            user_message, 
            guest, 
            json.loads(conversation.conversation_history) if conversation.conversation_history else [],
            json.loads(conversation.context) if conversation.context else {}
        )
        
        # Update conversation history
        history = json.loads(conversation.conversation_history) if conversation.conversation_history else []
        history.append({
            'role': 'user',
            'content': user_message,
            'timestamp': datetime.utcnow().isoformat()
        })
        history.append({
            'role': 'assistant',
            'content': response,
            'timestamp': datetime.utcnow().isoformat()
        })
        
        # Update conversation in database
        conversation.conversation_history = json.dumps(history)
        conversation.context = json.dumps(updated_context)
        conversation.last_activity = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'response': response
        })
    
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error al procesar el mensaje',
            'details': str(e)
        }), 500

@app.route('/api/room-service/menu', methods=['GET'])
def room_service_menu():
    """API endpoint to get the room service menu"""
    menu = get_menu()
    return jsonify({'success': True, 'menu': menu})

@app.route('/api/room-service/order', methods=['POST'])
def room_service_order():
    """API endpoint to place a room service order"""
    data = request.json
    guest_id = data.get('guest_id')
    items = data.get('items', [])
    special_instructions = data.get('special_instructions', '')
    
    if not guest_id or not items:
        return jsonify({'success': False, 'error': 'ID de huésped e ítems son requeridos'}), 400
    
    try:
        order_id = place_order(guest_id, items, special_instructions)
        return jsonify({
            'success': True,
            'order_id': order_id,
            'message': 'Pedido recibido correctamente'
        })
    except Exception as e:
        logger.error(f"Error placing order: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error al procesar el pedido',
            'details': str(e)
        }), 500

@app.route('/api/transportation/schedule', methods=['POST'])
def transportation_schedule():
    """API endpoint to schedule transportation"""
    data = request.json
    guest_id = data.get('guest_id')
    pickup_time = data.get('pickup_time')
    destination = data.get('destination')
    num_passengers = data.get('num_passengers', 1)
    vehicle_type = data.get('vehicle_type', 'taxi')
    special_notes = data.get('special_notes', '')
    
    if not guest_id or not pickup_time or not destination:
        return jsonify({
            'success': False, 
            'error': 'ID de huésped, hora de recogida y destino son requeridos'
        }), 400
    
    try:
        request_id = schedule_transportation(
            guest_id, 
            pickup_time, 
            destination, 
            num_passengers, 
            vehicle_type, 
            special_notes
        )
        return jsonify({
            'success': True,
            'request_id': request_id,
            'message': 'Transporte programado correctamente'
        })
    except Exception as e:
        logger.error(f"Error scheduling transportation: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error al programar el transporte',
            'details': str(e)
        }), 500

@app.route('/api/recommendations', methods=['GET'])
def get_recommendations():
    """API endpoint to get personalized recommendations"""
    guest_id = request.args.get('guest_id')
    category = request.args.get('category')  # restaurant, bar, activity, etc.
    
    if not guest_id:
        return jsonify({'success': False, 'error': 'ID de huésped es requerido'}), 400
    
    try:
        recommendations = get_personalized_recommendations(guest_id, category)
        return jsonify({
            'success': True,
            'recommendations': recommendations
        })
    except Exception as e:
        logger.error(f"Error getting recommendations: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error al obtener recomendaciones',
            'details': str(e)
        }), 500

@app.route('/api/faq', methods=['GET'])
def get_faq():
    """API endpoint to get FAQ response"""
    question = request.args.get('question')
    
    if not question:
        return jsonify({'success': False, 'error': 'Pregunta es requerida'}), 400
    
    try:
        response = get_faq_response(question)
        return jsonify({
            'success': True,
            'response': response
        })
    except Exception as e:
        logger.error(f"Error getting FAQ response: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Error al obtener respuesta',
            'details': str(e)
        }), 500
