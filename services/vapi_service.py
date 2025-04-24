import requests
import os
from datetime import datetime
from models import Guest, TransportationRequest
from app import db
import logging

logger = logging.getLogger(__name__)

# Vapi API Configuration
VAPI_TOKEN = os.environ.get("VAPI_TOKEN")
VAPI_BASE_URL = "https://api.vapi.ai/call/phone"
PHONE_NUMBER_ID = os.environ.get("VAPI_PHONE_NUMBER_ID") 
USER_PHONE_NUMBER = os.environ.get("USER_PHONE_NUMBER") 


def make_transportation_confirmation_call(request_id):
    """
    Make a confirmation call for a transportation request using Vapi
    
    Args:
        request_id (int): ID of the transportation request
    
    Returns:
        dict: Call details including call_id
    """
    try:
        # Get the transportation request
        request = TransportationRequest.query.get(request_id)
        if not request:
            raise ValueError(f"Transportation request with ID {request_id} not found")
        
        # Get the guest
        guest = Guest.query.get(request.guest_id)
        if not guest:
            raise ValueError(f"Guest with ID {request.guest_id} not found")
        
        '''if not guest.phone_number:
            raise ValueError(f"No phone number found for guest {guest.name}")'''
        
        # Format pickup time
        pickup_time = request.pickup_time.strftime("%I:%M %p")
        
        # Create headers
        headers = {
            'Authorization': f'Bearer {VAPI_TOKEN}',
            'Content-Type': 'application/json',
        }
        
        # Create the data payload
        data = {
            'assistant': {
                "firstMessage": "Hello, this is the hotel transportation service.",
                "model": {
                    "provider": "openai",
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"""
                            Eres un asistente del servicio de transporte del hotel llamando para confirmar una solicitud de transporte.
                            
                            Detalles del huésped:
                            - Nombre: {guest.name}
                            - Habitación: {guest.room_number}
                            
                            Detalles del transporte:
                            - Hora de recogida: {pickup_time}
                            - Destino: {request.destination}
                            - Tipo de vehículo: {request.vehicle_type}
                            - Número de pasajeros: {request.num_passengers}
                            
                            Por favor:
                            1. Preséntate como el servicio de transporte del hotel
                            2. Confirma los detalles del transporte con el huésped
                            3. Pregunta si tienen algún requisito especial
                            4. Agradéceles y confirma que el servicio está programado
                            
                            Habla de manera natural y profesional. Si necesitan modificar algo, anótalo e infórmales que el conserje se pondrá en contacto con ellos.
                            """
                        }
                    ]
                },
                "voice": "jennifer-playht"
            },
            'phoneNumberId': PHONE_NUMBER_ID,
            'customer': {
                #'number': guest.phone_number,
                'number': USER_PHONE_NUMBER,
            },
        }
        
        # Make the API request
        response = requests.post(VAPI_BASE_URL, headers=headers, json=data)
        
        if response.status_code == 201:
            call_data = response.json()
            logger.info(f"Initiated confirmation call for transportation request {request_id}, call ID: {call_data.get('id')}")
            
            return {
                "success": True,
                "call_id": call_data.get('id'),
                "status": call_data.get('status')
            }
        else:
            error_msg = f"Failed to create call: {response.text}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        
    except Exception as e:
        logger.error(f"Error making confirmation call: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def make_transportation_arrival_call(request_id):
    """
    Make a call to notify the guest that their transportation has arrived
    
    Args:
        request_id (int): ID of the transportation request
    
    Returns:
        dict: Call details including call_id
    """
    try:
        # Get the transportation request
        request = TransportationRequest.query.get(request_id)
        if not request:
            raise ValueError(f"Transportation request with ID {request_id} not found")
        
        # Get the guest
        guest = Guest.query.get(request.guest_id)
        if not guest:
            raise ValueError(f"Guest with ID {request.guest_id} not found")
        
        '''if not guest.phone_number:
            raise ValueError(f"No phone number found for guest {guest.name}")'''
        
        # Create headers
        headers = {
            'Authorization': f'Bearer {VAPI_TOKEN}',
            'Content-Type': 'application/json',
        }
        
        # Create the data payload
        data = {
            'assistant': {
                "firstMessage": "Hello, this is the hotel transportation service.",
                "model": {
                    "provider": "openai",
                    "model": "gpt-4",
                    "messages": [
                        {
                            "role": "system",
                            "content": f"""
                            Eres un asistente del servicio de transporte del hotel llamando para notificar a un huésped que su transporte ha llegado.
                            
                            Detalles del huésped:
                            - Nombre: {guest.name}
                            - Habitación: {guest.room_number}
                            
                            Detalles del transporte:
                            - Tipo de vehículo: {request.vehicle_type}
                            - Destino: {request.destination}
                            
                            Por favor:
                            1. Preséntate como el servicio de transporte del hotel
                            2. Informa al huésped que su {request.vehicle_type} ha llegado
                            3. Indícales que pueden proceder al lobby/punto de recogida
                            4. Deséales un buen viaje
                            
                            Habla de manera natural y profesional. Si tienen alguna pregunta, bríndales asistencia.
                            """
                        }
                    ]
                },
                "voice": "alloy"
            },
            'phoneNumberId': PHONE_NUMBER_ID,
            'customer': {
                #'number': guest.phone_number,
                'number': USER_PHONE_NUMBER,
            },
        }
        
        # Make the API request
        response = requests.post(VAPI_BASE_URL, headers=headers, json=data)
        
        if response.status_code == 201:
            call_data = response.json()
            logger.info(f"Initiated arrival notification call for transportation request {request_id}, call ID: {call_data.get('id')}")
            
            return {
                "success": True,
                "call_id": call_data.get('id'),
                "status": call_data.get('status')
            }
        else:
            error_msg = f"Failed to create call: {response.text}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg
            }
        
    except Exception as e:
        logger.error(f"Error making arrival notification call: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

def handle_call_webhook(webhook_data):
    """
    Handle webhooks from Vapi for call status updates
    
    Args:
        webhook_data (dict): Webhook payload from Vapi
    
    Returns:
        bool: Success status
    """
    try:
        call_id = webhook_data.get("call_id")
        status = webhook_data.get("status")
        
        # Log webhook receipt
        logger.info(f"Received call webhook for call {call_id} with status {status}")
        
        # Handle different call statuses
        if status == "completed":
            # Call was successful
            logger.info(f"Call {call_id} completed successfully")
        elif status == "failed":
            # Call failed
            logger.error(f"Call {call_id} failed: {webhook_data.get('error')}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error handling call webhook: {str(e)}")
        return False 