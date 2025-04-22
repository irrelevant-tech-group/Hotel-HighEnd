import json
import os
import logging
from datetime import datetime
from app import db
from models import Guest, RoomServiceOrder

logger = logging.getLogger(__name__)

# Cache for menu data
_menu_cache = None

def get_menu():
    """
    Get the room service menu
    
    Returns:
        dict: Menu items organized by category
    """
    global _menu_cache
    
    # Return cached menu if available
    if _menu_cache:
        return _menu_cache
    
    try:
        # Load menu from file
        file_path = os.path.join('data', 'menu.json')
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                menu = json.load(f)
                _menu_cache = menu
                return menu
        
        # If file doesn't exist, provide a default menu
        default_menu = {
            "Desayunos": [
                {"name": "Desayuno Americano", "price": 25000, "description": "Huevos, bacon, tostadas, jugo y café"},
                {"name": "Desayuno Continental", "price": 20000, "description": "Croissant, frutas, yogurt y café"},
                {"name": "Huevos Benedictinos", "price": 28000, "description": "Huevos pochados sobre muffin inglés con salsa holandesa"}
            ],
            "Platos Principales": [
                {"name": "Risotto de Champiñones", "price": 35000, "description": "Risotto cremoso con variedad de hongos y queso parmesano"},
                {"name": "Salmón a la Parrilla", "price": 48000, "description": "Filete de salmón con vegetales salteados y salsa de limón"},
                {"name": "Filete Mignon", "price": 55000, "description": "Corte de res premium con puré de papas y espárragos"}
            ],
            "Sándwiches": [
                {"name": "Club Sándwich", "price": 32000, "description": "Pollo, bacon, lechuga, tomate y mayonesa"},
                {"name": "Hamburguesa Aramé", "price": 38000, "description": "Carne Angus, queso, bacon, cebolla caramelizada y papas"},
                {"name": "Sándwich Vegetariano", "price": 28000, "description": "Vegetales asados, queso de cabra y pesto en pan integral"}
            ],
            "Sopas y Ensaladas": [
                {"name": "Sopa del Día", "price": 22000, "description": "Preparación fresca del chef"},
                {"name": "Ensalada César", "price": 26000, "description": "Lechuga romana, pollo, crutones, parmesano y aderezo César"},
                {"name": "Ensalada de Quinoa", "price": 28000, "description": "Quinoa, aguacate, tomate, pepino y vinagreta de cítricos"}
            ],
            "Postres": [
                {"name": "Tiramisú", "price": 18000, "description": "Tradicional postre italiano con café y mascarpone"},
                {"name": "Cheesecake", "price": 20000, "description": "Con salsa de frutos rojos"},
                {"name": "Selección de Frutas", "price": 15000, "description": "Variedad de frutas frescas de temporada"}
            ],
            "Bebidas": [
                {"name": "Selección de Jugos Naturales", "price": 12000, "description": "Naranja, mandarina, piña o frutos rojos"},
                {"name": "Café Especial Colombiano", "price": 8000, "description": "Servido en prensa francesa"},
                {"name": "Limonada de Coco", "price": 14000, "description": "Refrescante limonada con crema de coco"},
                {"name": "Cerveza Local", "price": 15000, "description": "Selección de cervezas artesanales de Medellín"}
            ]
        }
        
        _menu_cache = default_menu
        return default_menu
        
    except Exception as e:
        logger.error(f"Error loading menu: {str(e)}")
        return {}


def place_order(guest_id, items, special_instructions=''):
    """
    Place a room service order
    
    Args:
        guest_id (int): ID of the guest
        items (list): List of items to order
        special_instructions (str): Any special instructions for the order
        
    Returns:
        int: Order ID
    """
    try:
        # Get the guest
        guest = Guest.query.get(guest_id)
        if not guest:
            raise ValueError(f"Guest with ID {guest_id} not found")
        
        # Validate items against the menu
        menu = get_menu()
        all_menu_items = []
        
        for category in menu.values():
            all_menu_items.extend(category)
        
        # Convert menu items to a dict by name for easy lookup
        menu_lookup = {item['name'].lower(): item for item in all_menu_items}
        
        # Normalize and validate order items
        order_items = []
        total_price = 0
        
        for item_name in items:
            # Standardize name for lookup
            item_name_lower = item_name.lower()
            
            # Look for closest match if exact match not found
            matching_item = None
            if item_name_lower in menu_lookup:
                matching_item = menu_lookup[item_name_lower]
            else:
                # Try partial matching
                for menu_item_name, menu_item in menu_lookup.items():
                    if item_name_lower in menu_item_name or menu_item_name in item_name_lower:
                        matching_item = menu_item
                        break
            
            if matching_item:
                order_items.append({
                    'name': matching_item['name'],
                    'price': matching_item['price'],
                    'quantity': 1  # Default quantity
                })
                total_price += matching_item['price']
            else:
                # Log unrecognized item but still include it
                logger.warning(f"Unrecognized menu item: {item_name}")
                order_items.append({
                    'name': item_name,
                    'price': 0,  # Price unknown
                    'quantity': 1
                })
        
        # Create the order
        new_order = RoomServiceOrder(
            guest_id=guest_id,
            room_number=guest.room_number,
            order_items=json.dumps(order_items),
            special_instructions=special_instructions,
            total_price=total_price
        )
        
        db.session.add(new_order)
        db.session.commit()
        
        return new_order.id
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error placing room service order: {str(e)}")
        raise


def get_order_status(order_id):
    """
    Get the status of a room service order
    
    Args:
        order_id (int): ID of the order
        
    Returns:
        dict: Order status information
    """
    try:
        order = RoomServiceOrder.query.get(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")
        
        # Parse order items from JSON
        items = json.loads(order.order_items) if order.order_items else []
        
        return {
            'id': order.id,
            'status': order.status,
            'room_number': order.room_number,
            'order_date': order.order_date.isoformat(),
            'items': items,
            'special_instructions': order.special_instructions,
            'total_price': order.total_price
        }
        
    except Exception as e:
        logger.error(f"Error getting order status: {str(e)}")
        return None


def update_order_status(order_id, new_status):
    """
    Update the status of a room service order
    
    Args:
        order_id (int): ID of the order
        new_status (str): New status value
        
    Returns:
        bool: Success or failure
    """
    try:
        order = RoomServiceOrder.query.get(order_id)
        if not order:
            raise ValueError(f"Order with ID {order_id} not found")
        
        valid_statuses = ['pending', 'in-progress', 'delivered', 'cancelled']
        if new_status not in valid_statuses:
            raise ValueError(f"Invalid status: {new_status}. Must be one of {valid_statuses}")
        
        order.status = new_status
        db.session.commit()
        
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating order status: {str(e)}")
        return False
