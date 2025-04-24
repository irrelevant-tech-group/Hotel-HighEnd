from datetime import datetime
from app import db

class Guest(db.Model):
    """Model for hotel guests"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    room_number = db.Column(db.String(10), nullable=False)
    check_in_date = db.Column(db.DateTime, default=datetime.utcnow)
    check_out_date = db.Column(db.DateTime, nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    preferences = db.Column(db.Text, nullable=True)  # Stored as JSON
    is_active = db.Column(db.Boolean, default=True)
    language = db.Column(db.String(10), default='es')  # Default to Spanish

    # Relationships
    room_service_orders = db.relationship('RoomServiceOrder', backref='guest', lazy=True)
    transportation_requests = db.relationship('TransportationRequest', backref='guest', lazy=True)
    conversations = db.relationship('Conversation', backref='guest', lazy=True)

    def __repr__(self):
        return f'<Guest {self.name}, Room {self.room_number}>'


class RoomServiceOrder(db.Model):
    """Model for room service orders"""
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guest.id'), nullable=False)
    room_number = db.Column(db.String(10), nullable=False)
    order_items = db.Column(db.Text, nullable=False)  # Stored as JSON
    special_instructions = db.Column(db.Text, nullable=True)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')  # pending, in-progress, delivered, cancelled
    total_price = db.Column(db.Float, nullable=True)

    def __repr__(self):
        return f'<RoomServiceOrder {self.id} for Room {self.room_number}>'


class TransportationRequest(db.Model):
    """Model for transportation requests"""
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guest.id'), nullable=False)
    pickup_time = db.Column(db.DateTime, nullable=False)
    destination = db.Column(db.String(255), nullable=False)
    num_passengers = db.Column(db.Integer, default=1)
    vehicle_type = db.Column(db.String(50), default='taxi')  # taxi, private car, etc.
    special_notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')  # pending, confirmed, completed, cancelled
    request_date = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<TransportationRequest {self.id} to {self.destination}>'


class Conversation(db.Model):
    """Model for tracking conversation history"""
    id = db.Column(db.Integer, primary_key=True)
    guest_id = db.Column(db.Integer, db.ForeignKey('guest.id'), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    conversation_history = db.Column(db.Text, nullable=True)  # Stored as JSON
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    context = db.Column(db.Text, nullable=True)  # Stored as JSON, contains conversation context

    def __repr__(self):
        return f'<Conversation {self.id} for Guest {self.guest_id}>'


class Recommendation(db.Model):
    """Model for storing recommendation data"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    category = db.Column(db.String(50), nullable=False)  # restaurant, bar, activity, attraction
    description = db.Column(db.Text, nullable=False)
    images = db.Column(db.Text, nullable=True)  # Para guardar URLs de imágenes en JSON
    place_id = db.Column(db.String(100), nullable=True)  # Para Google Maps
    reviews = db.Column(db.Text, nullable=True)  # Reseñas en formato JSON
    google_rating = db.Column(db.Float, nullable=True)  # Rating de Google
    concierge_tips = db.Column(db.Text, nullable=True)
    address = db.Column(db.String(255), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    website = db.Column(db.String(255), nullable=True)
    price_level = db.Column(db.Integer, nullable=True)  # 1-4 for price range
    hours = db.Column(db.Text, nullable=True)  # Stored as JSON
    best_for = db.Column(db.String(100), nullable=True)  # morning, afternoon, evening, rainy, sunny
    tags = db.Column(db.String(255), nullable=True)  # comma-separated tags

    def __repr__(self):
        return f'<Recommendation {self.name} ({self.category})>'


class HotelInfo(db.Model):
    """Model for storing hotel-specific information (FAQ, amenities, etc.)"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True)
    value = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), nullable=False)  # faq, amenity, policy, contact
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<HotelInfo {self.key}>'
