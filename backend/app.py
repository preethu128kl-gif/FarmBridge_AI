import os
import json
import uuid
import base64
import math
import re
import unicodedata
import secrets
import hashlib
import smtplib
from email.message import EmailMessage
import jwt as pyjwt
from jwt import PyJWKClient
from difflib import SequenceMatcher
from datetime import datetime, timedelta
from functools import wraps

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, get_jwt_identity, jwt_required
from flask_sqlalchemy import SQLAlchemy
from groq import Groq
from sqlalchemy import inspect, or_, func
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
allowed_origins = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CLIENT_URL", "http://localhost:5173").split(",")
    if origin.strip()
]
CORS(app, resources={r"/api/*": {"origins": allowed_origins}})
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is missing. Create .env from .env.example first."
    )
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_pre_ping": True,
    "pool_recycle": 280,
}
jwt_secret = os.getenv("JWT_SECRET_KEY", "").strip()
if not jwt_secret or jwt_secret == "CHANGE_THIS_TO_A_LONG_RANDOM_SECRET":
    raise RuntimeError("JWT_SECRET_KEY is missing or still uses its example value. Configure a long random secret in backend/.env.")
app.config["JWT_SECRET_KEY"] = jwt_secret
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)

db = SQLAlchemy(app)
jwt = JWTManager(app)
google_jwks = PyJWKClient("https://www.googleapis.com/oauth2/v3/certs", cache_keys=True)


# ============================================================
# DATABASE MODELS
# ============================================================

class User(db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(180), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(30))
    role = db.Column(db.String(20), nullable=False, default="consumer")
    location = db.Column(db.String(255))
    latitude = db.Column(db.Float)
    longitude = db.Column(db.Float)
    farm_name = db.Column(db.String(160))
    experience_years = db.Column(db.Integer)
    verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    products = db.relationship("Product", backref="farmer", lazy=True)
    orders_as_consumer = db.relationship(
        "Order", foreign_keys="Order.consumer_id", backref="consumer", lazy=True
    )
    orders_as_farmer = db.relationship(
        "Order", foreign_keys="Order.farmer_id", backref="farmer_user", lazy=True
    )


class AIConversation(db.Model):
    __tablename__ = "ai_conversations"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    title = db.Column(db.String(160), nullable=False, default="New conversation")
    language = db.Column(db.String(60), nullable=False, default="Auto-detected")
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    messages = db.relationship(
        "AIMessage", backref="conversation", cascade="all, delete-orphan",
        order_by="AIMessage.created_at", lazy=True
    )


class AIMessage(db.Model):
    __tablename__ = "ai_messages"

    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(
        db.Integer, db.ForeignKey("ai_conversations.id"), nullable=False, index=True
    )
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)


class Product(db.Model):
    __tablename__ = "products"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False, index=True)
    category = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text, default="")
    price = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(30), default="kg")
    stock = db.Column(db.Float, nullable=False, default=0)
    image = db.Column(db.Text)
    location = db.Column(db.String(255))
    is_active = db.Column(db.Boolean, default=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CartItem(db.Model):
    __tablename__ = "cart_items"

    id = db.Column(db.Integer, primary_key=True)
    consumer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    quantity = db.Column(db.Float, nullable=False, default=1)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")


class WishlistItem(db.Model):
    __tablename__ = "wishlist_items"

    id = db.Column(db.Integer, primary_key=True)
    consumer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    product = db.relationship("Product")


class Notification(db.Model):
    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    title = db.Column(db.String(180), nullable=False)
    message = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Order(db.Model):
    __tablename__ = "orders"

    id = db.Column(db.Integer, primary_key=True)
    consumer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    total_amount = db.Column(db.Float, nullable=False, default=0)
    delivery_address = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(40), nullable=False, default="placed")
    payment_method = db.Column(db.String(40), nullable=True)
    payment_status = db.Column(db.String(30), nullable=True)
    checkout_id = db.Column(db.String(80), nullable=True, index=True)
    transport_partner_id = db.Column(
        db.Integer, db.ForeignKey("transport_partners.id"), nullable=True
    )
    delivery_partner_id = db.Column(
        db.Integer, db.ForeignKey("delivery_partners.id"), nullable=True, index=True
    )
    transport_partner_name = db.Column(db.String(160))
    from_location = db.Column(db.String(255))
    to_location = db.Column(db.String(255))
    total_weight = db.Column(db.Float, default=0)
    pickup_latitude = db.Column(db.Float)
    pickup_longitude = db.Column(db.Float)
    delivery_date = db.Column(db.Date)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    items = db.relationship(
        "OrderItem", backref="order", cascade="all, delete-orphan", lazy=True
    )
    tracking = db.relationship(
        "OrderTracking", backref="order", cascade="all, delete-orphan",
        order_by="OrderTracking.created_at", lazy=True
    )


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey("products.id"), nullable=False)
    product_name = db.Column(db.String(160), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)


class OrderTracking(db.Model):
    __tablename__ = "order_tracking"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    status = db.Column(db.String(40), nullable=False)
    note = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class CropRecord(db.Model):
    __tablename__ = "crop_records"

    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    crop_name = db.Column(db.String(120), nullable=False)
    category = db.Column(db.String(100))
    season = db.Column(db.String(80))
    year = db.Column(db.Integer, nullable=False)
    area_acres = db.Column(db.Float)
    yield_amount = db.Column(db.Float)
    average_price = db.Column(db.Float)
    total_income = db.Column(db.Float)
    soil_type = db.Column(db.String(100))
    soil_ph = db.Column(db.Float)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class TransportPartner(db.Model):
    __tablename__ = "transport_partners"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(160), nullable=False)
    phone = db.Column(db.String(30))
    vehicle_type = db.Column(db.String(80))
    capacity_kg = db.Column(db.Float, default=500)
    location = db.Column(db.String(255))
    price = db.Column(db.Float, default=1500)
    available = db.Column(db.Boolean, default=True)


class DeliveryPartner(db.Model):
    __tablename__ = "delivery_partners"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    mobile = db.Column(db.String(30), nullable=True, unique=True)
    email = db.Column(db.String(180), nullable=True, unique=True, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    address = db.Column(db.Text, nullable=True)
    city = db.Column(db.String(120), nullable=True)
    pincode = db.Column(db.String(12), nullable=True)
    vehicle_type = db.Column(db.String(80), nullable=True)
    vehicle_registration = db.Column(db.String(40), nullable=True, unique=True)
    capacity_kg = db.Column(db.Float, nullable=True)
    vehicle_photo = db.Column(db.Text)
    license_number = db.Column(db.String(80), nullable=True)
    documents = db.Column(db.Text)
    pricing_method = db.Column(db.String(12), nullable=True)
    per_km_rate = db.Column(db.Float)
    per_kg_rate = db.Column(db.Float)
    service_radius_km = db.Column(db.Float, nullable=True)
    service_location = db.Column(db.String(180), nullable=True)
    service_latitude = db.Column(db.Float)
    service_longitude = db.Column(db.Float)
    availability = db.Column(db.String(12), nullable=False, default="available")
    verification_status = db.Column(db.String(20), nullable=False, default="unverified")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class PartnerTransportRequest(db.Model):
    __tablename__ = "partner_transport_requests"
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False, index=True)
    partner_id = db.Column(db.Integer, db.ForeignKey("delivery_partners.id"), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="pending")
    distance_km = db.Column(db.Float)
    estimated_charge = db.Column(db.Float)
    pricing_method = db.Column(db.String(12))
    order = db.relationship("Order")
    partner = db.relationship("DeliveryPartner")
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime)
    __table_args__ = (db.UniqueConstraint("order_id", "partner_id", name="uq_partner_order"),)


class FarmerSaleRecord(db.Model):
    __tablename__ = "farmer_sale_records"
    id = db.Column(db.Integer, primary_key=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    product_name = db.Column(db.String(160), nullable=False)
    selling_date = db.Column(db.Date, nullable=False, index=True)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(12), nullable=False)
    selling_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)


class PartnerPasswordReset(db.Model):
    __tablename__ = "partner_password_resets"
    id = db.Column(db.Integer, primary_key=True)
    partner_id = db.Column(db.Integer, db.ForeignKey("delivery_partners.id"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    expires_at = db.Column(db.DateTime, nullable=False)
    used_at = db.Column(db.DateTime)


class SharedOrder(db.Model):
    __tablename__ = "shared_orders"

    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey("orders.id"), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    shared_with_farmer_id = db.Column(db.Integer, db.ForeignKey("users.id"))
    status = db.Column(db.String(30), default="available")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============================================================
# HELPERS
# ============================================================

STATUS_LABELS = {
    "placed": "Order Placed",
    "confirmed": "Confirmed",
    "transport_assigned": "Transport Assigned",
    "out_for_delivery": "Out for Delivery",
    "delivered": "Delivered",
    "cancelled": "Cancelled",
}


def user_dict(u):
    return {
        "id": u.id,
        "name": u.name,
        "email": u.email,
        "phone": u.phone,
        "role": u.role,
        "location": u.location,
        "latitude": u.latitude,
        "longitude": u.longitude,
        "farmName": u.farm_name,
        "experienceYears": u.experience_years,
        "verified": bool(u.verified),
    }


PRODUCT_CATEGORY_TERMS = {
    "fruits": (
        "apple", "orange", "grape", "banana", "mango", "papaya", "watermelon",
        "pineapple", "lemon", "lime", "coconut", "dates", "guava", "jackfruit",
        "pear", "peach", "plum", "pomegranate", "ಸೇಬು", "ಕಿತ್ತಳೆ", "ದ್ರಾಕ್ಷಿ",
        "ಬಾಳೆಹಣ್ಣು", "ಬಾಳೆ", "ಮಾವು", "ಪಪ್ಪಾಯಿ", "ಕಲ್ಲಂಗಡಿ", "ಅನಾನಸ್",
        "ನಿಂಬೆ", "ತೆಂಗಿನಕಾಯಿ", "ಪೇರಳೆ", "ಸೀತಾಫಲ",
    ),
    "vegetables": (
        "tomato", "potato", "onion", "carrot", "cabbage", "cauliflower", "brinjal",
        "eggplant", "aubergine", "okra", "ladyfinger", "bhindi", "cucumber", "beans",
        "beetroot", "radish", "pumpkin", "spinach", "lettuce", "capsicum", "bell pepper",
        "bottle gourd", "bitter gourd", "ridge gourd", "drumstick", "peas", "mushroom",
        "ಟೊಮೇಟೊ", "ಟೊಮ್ಯಾಟೊ", "ಟೊಮೆಟೊ", "ಆಲೂಗಡ್ಡೆ", "ಈರುಳ್ಳಿ", "ಕ್ಯಾರೆಟ್",
        "ಎಲೆಕೋಸು", "ಹೂಕೋಸು", "ಬದನೆಕಾಯಿ", "ಬೆಂಡೆಕಾಯಿ", "ಸೌತೆಕಾಯಿ", "ಬೀಟ್ರೂಟ್",
        "ಮೂಲಂಗಿ", "ಕುಂಬಳಕಾಯಿ", "ಪಾಲಕ್", "ಅವರೆಕಾಯಿ", "ಬಟಾಣಿ", "ಸೊರೆಕಾಯಿ",
    ),
    "grains": (
        "rice", "wheat", "maize", "corn", "millet", "bajra", "jowar", "sorghum",
        "ragi", "finger millet", "barley", "oats", "quinoa", "lentil", "dal",
        "chickpea", "gram", "beans", "peanut", "groundnut", "soybean", "cowpea",
        "ಅಕ್ಕಿ", "ಗೋಧಿ", "ಮೆಕ್ಕೆಜೋಳ", "ಜೋಳ", "ರಾಗಿ", "ಸಜ್ಜೆ", "ಬಾರ್ಲಿ", "ಅವರೆ",
        "ಕಡಲೆ", "ಹೆಸರುಕಾಳು", "ತೊಗರಿ", "ಉದ್ದು", "ಕಡಲೆಕಾಯಿ",
    ),
    "spices": (
        "chilli", "chili", "pepper", "turmeric", "ginger", "garlic", "cumin",
        "coriander", "cardamom", "cinnamon", "clove", "mustard", "fennel",
        "fenugreek", "nutmeg", "saffron", "ajwain", "tamarind", "ಮೆಣಸಿನಕಾಯಿ",
        "ಅರಿಶಿನ", "ಶುಂಠಿ", "ಬೆಳ್ಳುಳ್ಳಿ", "ಜೀರಿಗೆ", "ಕೊತ್ತಂಬರಿ", "ಏಲಕ್ಕಿ",
        "ದಾಲ್ಚಿನ್ನಿ", "ಲವಂಗ", "ಸಾಸಿವೆ", "ಮೆಂತ್ಯ", "ಹುಣಸೆ",
    ),
    "dairy": (
        "milk", "egg", "eggs", "cheese", "butter", "yogurt", "curd", "paneer",
        "ghee", "ಹಾಲು", "ಮೊಟ್ಟೆ", "ಬೆಣ್ಣೆ", "ಮೊಸರು", "ತುಪ್ಪ",
    ),
    "oils": (
        "oil", "sunflower oil", "coconut oil", "groundnut oil", "sesame oil",
        "ಎಣ್ಣೆ", "ತೆಂಗಿನ ಎಣ್ಣೆ",
    ),
    "flowers": (
        "flower", "rose", "jasmine", "marigold", "hibiscus", "lotus", "ಚೆಂಡುಹೂವು",
        "ಮಲ್ಲಿಗೆ", "ಗುಲಾಬಿ", "ದಾಸವಾಳ", "ಕಮಲ",
    ),
    "herbal": (
        "herb", "aloe vera", "neem", "mint", "basil", "lemongrass", "curry leaves",
        "ಔಷಧಿ", "ಅಲೋವೆರಾ", "ಬೇವಿನ", "ಪುದೀನ", "ತುಳಸಿ", "ಕರಿಬೇವು",
    ),
}
PRODUCT_CATEGORIES = frozenset((*PRODUCT_CATEGORY_TERMS, "organic"))
PRODUCT_CATEGORY_ALIASES = {
    category: {normalize for normalize in terms}
    for category, terms in PRODUCT_CATEGORY_TERMS.items()
}
PRODUCT_CATEGORY_ALIASES["organic"] = {"organic", "ಸಾವಯವ"}


def normalize_product_text(value):
    value = unicodedata.normalize("NFKC", str(value or "")).casefold()
    value = re.sub(r"[_-]+", " ", value)
    value = "".join(
        char if char.isalnum() or unicodedata.category(char).startswith("M") or char.isspace() else " "
        for char in value
    )
    return " ".join(value.split())


PRODUCT_CATEGORY_ALIASES = {
    category: {normalize_product_text(term) for term in terms}
    for category, terms in PRODUCT_CATEGORY_ALIASES.items()
}


def singular_product_word(word):
    if re.search(r"[a-z]", word):
        if word.endswith("ies") and len(word) > 4:
            return word[:-3] + "y"
        if word.endswith("oes") and len(word) > 4:
            return word[:-2]
        if word.endswith("s") and not word.endswith(("ss", "us")) and len(word) > 3:
            return word[:-1]
    return word


def infer_product_category(name):
    normalized = normalize_product_text(name)
    if not normalized:
        return None

    full_categories = {
        category
        for category, terms in PRODUCT_CATEGORY_ALIASES.items()
        if normalized in terms
    }
    if len(full_categories) == 1:
        return next(iter(full_categories))

    candidates = [normalized]
    for word in normalized.split():
        candidates.extend((word, singular_product_word(word)))
    exact_categories = {
        category
        for category, terms in PRODUCT_CATEGORY_ALIASES.items()
        if any(candidate in terms for candidate in candidates)
    }
    if "organic" in exact_categories and len(exact_categories) > 1:
        return "organic"
    exact_categories.discard("organic")
    if len(exact_categories) == 1:
        return next(iter(exact_categories))
    if exact_categories:
        return None

    fuzzy_inputs = [candidate for candidate in candidates if len(candidate) >= 4]
    best_by_category = {
        category: max(
            (
                SequenceMatcher(None, candidate, term).ratio()
                for candidate in fuzzy_inputs
                for term in terms
                if len(term) >= 4
            ),
            default=0,
        )
        for category, terms in PRODUCT_CATEGORY_ALIASES.items()
    }
    ranked = sorted(best_by_category.items(), key=lambda item: item[1], reverse=True)
    if not ranked or ranked[0][1] < 0.82:
        return None
    if len(ranked) > 1 and ranked[0][1] - ranked[1][1] < 0.04:
        return None
    return ranked[0][0]


def validate_product_image(image):
    if image is None or image == "":
        return None
    if not isinstance(image, str) or len(image) > 3_500_000:
        return "Product images must be no larger than 2.5 MB after compression."
    if not image.startswith("data:"):
        return None

    match = re.fullmatch(
        r"data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/]+={0,2})",
        image,
        re.IGNORECASE,
    )
    if not match:
        return "Upload a valid JPEG, PNG, or WebP image."
    try:
        content = base64.b64decode(match.group(2), validate=True)
    except ValueError:
        return "Upload a valid JPEG, PNG, or WebP image."
    image_type = match.group(1).lower()
    signatures = {
        "jpeg": content.startswith(b"\xff\xd8\xff"),
        "png": content.startswith(b"\x89PNG\r\n\x1a\n"),
        "webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP",
    }
    if not signatures[image_type]:
        return "Upload a valid JPEG, PNG, or WebP image."
    if len(content) > 2_500_000:
        return "Product images must be no larger than 2.5 MB after compression."
    return None


def product_dict(p):
    unit = str(p.unit or "kg").strip()
    if re.fullmatch(r"(?:\d+(?:\.\d+)?\s*)?kg(?:\s*\d+(?:\.\d+)?)?", unit, re.IGNORECASE):
        unit = "kg"
    elif re.fullmatch(r"(?:\d+(?:\.\d+)?\s*)?units?(?:\s*\d+(?:\.\d+)?)?", unit, re.IGNORECASE):
        unit = "Units"
    quantity = float(p.stock or 0)
    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "description": p.description,
        "price": p.price,
        "unit": unit,
        "quantity": quantity,
        "stock": quantity,
        "image": p.image,
        "location": p.location,
        "farmerId": p.farmer_id,
        "farmerName": p.farmer.name if p.farmer else None,
        "farmerVerified": bool(p.farmer.verified) if p.farmer else False,
        "isActive": bool(p.is_active),
        "createdAt": p.created_at.isoformat() if p.created_at else None,
    }


def order_dict(o):
    partner_requests = PartnerTransportRequest.query.filter_by(order_id=o.id).all()
    assigned_request = next((x for x in partner_requests if x.status in ("accepted", "picked_up", "in_transit", "delivered")), None)
    assigned_partner = db.session.get(DeliveryPartner, o.delivery_partner_id) if o.delivery_partner_id else None
    if o.status == "cancelled":
        transport_status = "Cancelled"
    elif assigned_request:
        transport_status = "Transport Assigned" if assigned_request.status == "accepted" else assigned_request.status.replace("_", " ").title()
    elif any(x.status == "pending" for x in partner_requests):
        transport_status = "Request sent"
    elif partner_requests:
        transport_status = "No partner accepted"
    elif o.status not in ("cancelled", "delivered"):
        transport_status = "Searching for Transport"
    elif o.transport_partner_name:
        transport_status = "Assigned"
    elif o.status == "confirmed":
        transport_status = "No eligible partner found"
    else:
        transport_status = "Not requested"
    return {
        "id": o.id,
        "orderId": f"ORD{o.id:05d}",
        "consumerId": o.consumer_id,
        "consumerName": o.consumer.name if o.consumer else None,
        "farmerId": o.farmer_id,
        "farmerName": o.farmer_user.name if o.farmer_user else None,
        "totalAmount": round(o.total_amount, 2),
        "deliveryAddress": o.delivery_address,
        "status": o.status,
        "statusLabel": STATUS_LABELS.get(o.status, o.status),
        "paymentMethod": o.payment_method,
        "paymentStatus": o.payment_status,
        "isDemoPayment": bool(o.payment_method and o.payment_method.endswith("_DEMO")),
        "transportPartnerId": o.delivery_partner_id or o.transport_partner_id,
        "transportPartner": assigned_partner.name if assigned_partner else o.transport_partner_name,
        "transportVehicleType": assigned_partner.vehicle_type if assigned_partner else None,
        "transportVehicleRegistration": assigned_partner.vehicle_registration if assigned_partner else None,
        "transportStatus": transport_status,
        "from": o.from_location,
        "to": o.to_location,
        "totalWeight": o.total_weight,
        "deliveryDate": o.delivery_date.isoformat() if o.delivery_date else None,
        "createdAt": o.created_at.isoformat() if o.created_at else None,
        "items": [
            {
                "id": i.id,
                "productId": i.product_id,
                "productName": i.product_name,
                "quantity": i.quantity,
                "unitPrice": i.unit_price,
                "subtotal": round(i.quantity * i.unit_price, 2),
            }
            for i in o.items
        ],
        "tracking": [
            {
                "status": t.status,
                "statusLabel": STATUS_LABELS.get(t.status, t.status),
                "note": t.note,
                "createdAt": t.created_at.isoformat() if t.created_at else None,
            }
            for t in o.tracking
        ],
    }


def current_user():
    identity = get_jwt_identity()
    try:
        return db.session.get(User, int(identity))
    except (TypeError, ValueError):
        return None


def partner_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        identity = str(get_jwt_identity() or "")
        if not identity.startswith("partner:"):
            return jsonify({"error": "Delivery partner access required"}), 403
        try:
            partner = db.session.get(DeliveryPartner, int(identity.split(":", 1)[1]))
        except (TypeError, ValueError):
            partner = None
        if not partner:
            return jsonify({"error": "Delivery partner account not found"}), 403
        request.delivery_partner = partner
        return fn(*args, **kwargs)
    return wrapper


def ai_message_dict(message):
    return {
        "id": message.id,
        "role": message.role,
        "content": message.content,
        "createdAt": message.created_at.isoformat() if message.created_at else None,
    }


def ai_conversation_dict(conversation, include_messages=False):
    result = {
        "id": conversation.id,
        "title": conversation.title,
        "language": conversation.language,
        "createdAt": conversation.created_at.isoformat(),
        "updatedAt": conversation.updated_at.isoformat(),
    }
    if include_messages:
        result["messages"] = [ai_message_dict(message) for message in conversation.messages]
    return result


def detect_message_language(message):
    scripts = {
        "Kannada": (0x0C80, 0x0CFF),
        "Hindi": (0x0900, 0x097F),
        "Telugu": (0x0C00, 0x0C7F),
        "Tamil": (0x0B80, 0x0BFF),
    }
    counts = {
        language: sum(start <= ord(char) <= end for char in message)
        for language, (start, end) in scripts.items()
    }
    has_english = any(char.isascii() and char.isalpha() for char in message)
    if counts["Kannada"] and has_english:
        return "Kannada-English"
    for language, count in counts.items():
        if count:
            return language
    return "Auto-detected"


def groq_completion(messages):
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("AI assistant is not configured. Set GROQ_API_KEY in the backend environment and restart the server.")

    try:
        result = Groq(api_key=api_key, timeout=45.0, max_retries=1).chat.completions.create(
            model=os.getenv("GROQ_MODEL", "openai/gpt-oss-120b"),
            messages=messages,
            temperature=0.4,
            max_tokens=1200,
            response_format={"type": "json_object"},
        )
    except Exception as exc:
        raise RuntimeError("Groq could not complete the request. Check the backend API configuration and try again.") from exc

    content = result.choices[0].message.content or ""
    try:
        parsed = json.loads(content)
        answer = str(parsed.get("answer", "")).strip()
        language = str(parsed.get("language", "Auto-detected")).strip()
    except (TypeError, ValueError):
        answer = str(content).strip()
        language = "Auto-detected"
    if not answer:
        raise RuntimeError("Groq returned an empty response. Please try again.")
    return answer, language or "Auto-detected"


def role_required(*roles):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user = current_user()
            if not user or user.role not in roles:
                return jsonify({"error": "Access denied"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def add_notification(user_id, title, message):
    db.session.add(Notification(
        user_id=user_id, title=title, message=message
    ))


def add_tracking(order, status, note=""):
    db.session.add(OrderTracking(
        order_id=order.id, status=status, note=note
    ))


def seed_transport():
    if TransportPartner.query.count():
        return
    db.session.add_all([
        TransportPartner(
            name="Ramesh Transport", phone="9000000001",
            vehicle_type="Tata Ace", capacity_kg=750,
            location="Mysore", price=1500
        ),
        TransportPartner(
            name="Kaveri Logistics", phone="9000000002",
            vehicle_type="Pickup", capacity_kg=1200,
            location="Mysore", price=2200
        ),
        TransportPartner(
            name="Shree Goods Carrier", phone="9000000003",
            vehicle_type="Pickup", capacity_kg=1000,
            location="Bengaluru", price=2000
        ),
        TransportPartner(
            name="Wilson Mini Truck", phone="9000000004",
            vehicle_type="Mini Truck", capacity_kg=750,
            location="Mysore", price=1800
        ),
    ])
    db.session.commit()


# ============================================================
# HEALTH
# ============================================================

@app.get("/")
def root():
    return jsonify({
        "service": "FarmBridge AI Backend",
        "database": "PostgreSQL",
        "status": "running",
        "health": "/api/health"
    })


@app.get("/api/health")
def health():
    try:
        db.session.execute(db.text("SELECT 1"))
        return jsonify({
            "ok": True,
            "database": "connected",
            "service": "FarmBridge AI API"
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({"ok": False, "database": "disconnected", "error": str(e)}), 500


# ============================================================
# AUTHENTICATION
# ============================================================

@app.post("/api/auth/register")
def register():
    data = request.get_json(silent=True) or {}

    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    phone = re.sub(r"[\s()-]", "", str(data.get("phone") or ""))
    role = (data.get("role") or "consumer").lower()

    if not name or not email or not password:
        return jsonify({"error": "name, email and password are required"}), 400
    if len(name) > 120 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
        return jsonify({"error": "Enter a valid name and email address"}), 400
    if phone and not re.fullmatch(r"\+?[0-9]{7,15}", phone):
        return jsonify({"error": "Enter a valid mobile number"}), 400
    if role not in ("consumer", "farmer"):
        return jsonify({"error": "role must be consumer or farmer"}), 400
    if len(password) < 6:
        return jsonify({"error": "password must contain at least 6 characters"}), 400
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "email already registered"}), 409
    if phone and User.query.filter_by(phone=phone).first():
        return jsonify({"error": "mobile number already registered"}), 409

    user = User(
        name=name,
        email=email,
        password_hash=generate_password_hash(password),
        phone=phone or None,
        role=role,
        location=data.get("location"),
        farm_name=data.get("farmName"),
        experience_years=data.get("experienceYears"),
        verified=False,
    )
    db.session.add(user)
    db.session.commit()

    add_notification(
        user.id,
        "Welcome to FarmBridge AI",
        "Your account has been created successfully."
    )
    db.session.commit()

    token = create_access_token(identity=str(user.id))
    return jsonify({
        "message": "Registration successful",
        "token": token,
        "user": user_dict(user)
    }), 201


@app.post("/api/auth/login")
def login():
    data = request.get_json(silent=True) or {}
    identifier = (data.get("email") or data.get("identifier") or "").strip()
    password = data.get("password") or ""
    requested_role = (data.get("role") or "").lower()

    user = User.query.filter_by(email=identifier.lower()).first()
    if not user:
        phone = re.sub(r"[\s()-]", "", identifier)
        user = User.query.filter_by(phone=phone).first()
        if not user and phone != identifier:
            user = User.query.filter_by(phone=identifier).first()
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401
    if requested_role and requested_role != user.role:
        return jsonify({"error": f"This account is registered as {user.role}"}), 403

    token = create_access_token(identity=str(user.id))
    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": user_dict(user)
    })


@app.get("/api/auth/me")
@jwt_required()
def me():
    return jsonify({"user": user_dict(current_user())})


# ============================================================
# PROFILE + NOTIFICATIONS
# ============================================================

@app.get("/api/profile")
@jwt_required()
def get_profile():
    return jsonify({"user": user_dict(current_user())})


@app.put("/api/profile")
@jwt_required()
def update_profile():
    u = current_user()
    data = request.get_json(silent=True) or {}

    for field in ["name", "phone", "location", "farmName"]:
        if field in data:
            setattr(u, {
                "farmName": "farm_name"
            }.get(field, field), data[field])

    for field, low, high in (("latitude", -90, 90), ("longitude", -180, 180)):
        if field in data:
            raw = data[field]
            if raw in (None, ""):
                setattr(u, field, None)
                continue
            try:
                value = float(raw)
            except (TypeError, ValueError):
                return jsonify({"error": f"{field} must be a valid coordinate"}), 400
            if not math.isfinite(value) or not low <= value <= high:
                return jsonify({"error": f"{field} is outside the valid range"}), 400
            setattr(u, field, value)
    if (u.latitude is None) != (u.longitude is None):
        return jsonify({"error": "Enter both latitude and longitude, or leave both empty"}), 400

    if "experienceYears" in data:
        u.experience_years = int(data["experienceYears"]) if data["experienceYears"] else None

    db.session.commit()
    return jsonify({"message": "Profile updated", "user": user_dict(u)})


@app.get("/api/notifications")
@jwt_required()
def notifications():
    rows = Notification.query.filter_by(
        user_id=current_user().id
    ).order_by(Notification.created_at.desc()).limit(50).all()

    return jsonify({
        "notifications": [
            {
                "id": n.id,
                "title": n.title,
                "message": n.message,
                "isRead": bool(n.is_read),
                "createdAt": n.created_at.isoformat()
            }
            for n in rows
        ]
    })


@app.patch("/api/notifications/<int:notification_id>/read")
@jwt_required()
def notification_read(notification_id):
    n = db.session.get(Notification, notification_id)
    if not n or n.user_id != current_user().id:
        return jsonify({"error": "Notification not found"}), 404
    n.is_read = True
    db.session.commit()
    return jsonify({"message": "Notification marked as read"})


# ============================================================
# PUBLIC MARKETPLACE: PRODUCTS / CATEGORIES / FARMERS
# ============================================================

@app.get("/api/categories")
def categories():
    rows = db.session.query(
        Product.category, func.count(Product.id)
    ).filter(Product.is_active.is_(True)).group_by(Product.category).all()

    return jsonify({
        "categories": [
            {"key": key, "productCount": count}
            for key, count in rows
        ]
    })


@app.get("/api/products")
def products():
    q = (request.args.get("search") or "").strip()
    category = (request.args.get("category") or "").strip()
    farmer_id = request.args.get("farmerId")

    query = Product.query.filter_by(is_active=True)

    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Product.name.ilike(like),
            Product.category.ilike(like),
            Product.description.ilike(like),
            Product.location.ilike(like)
        ))

    if category:
        query = query.filter(Product.category.ilike(category))

    if farmer_id:
        query = query.filter(Product.farmer_id == int(farmer_id))

    rows = query.order_by(Product.created_at.desc()).all()
    return jsonify({"products": [product_dict(p) for p in rows]})


@app.get("/api/products/<int:product_id>")
def get_product(product_id):
    p = db.session.get(Product, product_id)
    if not p or not p.is_active:
        return jsonify({"error": "Product not found"}), 404
    return jsonify({"product": product_dict(p)})


@app.get("/api/farmers")
def farmers():
    rows = User.query.filter_by(role="farmer").order_by(User.name.asc()).all()
    return jsonify({
        "farmers": [
            {
                **user_dict(u),
                "productCount": Product.query.filter_by(
                    farmer_id=u.id, is_active=True
                ).count()
            }
            for u in rows
        ]
    })


# ============================================================
# FARMER PRODUCT MANAGEMENT
# ============================================================

@app.get("/api/farmer/products")
@role_required("farmer")
def farmer_products():
   
     rows = Product.query.filter_by(
      farmer_id=current_user().id,
      is_active=True
).order_by(Product.created_at.desc()).all()

     return jsonify({"products": [product_dict(p) for p in rows]})

@app.get("/api/products/category")
@role_required("farmer")
def product_category():
    name = str(request.args.get("name") or "").strip()
    return jsonify({"category": infer_product_category(name)})


@app.post("/api/products")
@role_required("farmer")
def create_product():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    supplied_category = str(data.get("category") or "").strip().casefold()
    category = infer_product_category(name)

    try:
        price = float(data.get("price"))
    except (TypeError, ValueError):
        price = math.nan
    try:
        stock = float(data.get("quantity", data.get("stock")))
    except (TypeError, ValueError):
        stock = math.nan
    if not name:
        return jsonify({"error": "Product name is required"}), 400
    if len(name) > 160:
        return jsonify({"error": "Product name must be 160 characters or fewer"}), 400
    if not math.isfinite(price) or price < 0:
        return jsonify({"error": "Price must be a valid non-negative number"}), 400
    if not math.isfinite(stock) or stock <= 0:
        return jsonify({"error": "Quantity must be a valid number greater than zero"}), 400
    unit = str(data.get("unit") or "kg").strip()
    if unit.casefold() not in {"kg", "unit", "units"}:
        return jsonify({"error": "Unit must be kg or Units"}), 400
    unit = "kg" if unit.casefold() == "kg" else "Units"
    if not category:
        return jsonify({
            "error": "Could not confidently categorize this product. Enter a recognized Kannada or English product name.",
            "categoryRequired": True,
        }), 400
    if supplied_category and supplied_category != category:
        return jsonify({"error": "The supplied category does not match the inferred product category."}), 400
    image_error = validate_product_image(data.get("image"))
    if image_error:
        return jsonify({"error": image_error}), 400

    p = Product(
        name=name,
        category=category,
        description=data.get("description", ""),
        price=price,
        unit=unit,
        stock=stock,
        image=data.get("image"),
        location=data.get("location") or current_user().location,
        farmer_id=current_user().id,
        is_active=True,
    )
    db.session.add(p)
    db.session.commit()

    return jsonify({
        "message": "Product added successfully",
        "product": product_dict(p)
    }), 201


@app.put("/api/products/<int:product_id>")
@role_required("farmer")
def update_product(product_id):
    p = db.session.get(Product, product_id)
    if not p or p.farmer_id != current_user().id:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json(silent=True) or {}
    if "image" in data:
        image_error = validate_product_image(data["image"])
        if image_error:
            return jsonify({"error": image_error}), 400

    text_fields = ["name", "category", "description", "unit", "image", "location"]
    for field in text_fields:
        if field in data:
            setattr(p, field, data[field])

    if "price" in data:
        p.price = float(data["price"])
    if "stock" in data:
        p.stock = float(data["stock"])
    if "isActive" in data:
        p.is_active = bool(data["isActive"])

    db.session.commit()
    return jsonify({"message": "Product updated", "product": product_dict(p)})


@app.delete("/api/products/<int:product_id>")
@role_required("farmer")
def delete_product(product_id):
    p = db.session.get(Product, product_id)
    if not p or p.farmer_id != current_user().id:
        return jsonify({"error": "Product not found"}), 404

    p.is_active = False
    db.session.commit()
    return jsonify({"message": "Product removed"})


# ============================================================
# CART + WISHLIST
# ============================================================

@app.get("/api/cart")
@role_required("consumer")
def get_cart():
    rows = CartItem.query.filter_by(
        consumer_id=current_user().id
    ).order_by(CartItem.created_at.desc()).all()

    total = sum(
        i.quantity * i.product.price for i in rows if i.product and i.product.is_active
    )

    return jsonify({
        "items": [
            {
                "id": i.id,
                "product": product_dict(i.product),
                "quantity": i.quantity,
                "subtotal": round(i.quantity * i.product.price, 2)
            }
            for i in rows if i.product
        ],
        "total": round(total, 2)
    })


@app.post("/api/cart")
@role_required("consumer")
def add_cart():
    data = request.get_json(silent=True) or {}
    product_id = data.get("productId")
    quantity = float(data.get("quantity", 1))

    p = db.session.get(Product, product_id)
    if not p or not p.is_active:
        return jsonify({"error": "Product not found"}), 404
    if quantity <= 0:
        return jsonify({"error": "Quantity must be greater than 0"}), 400

    item = CartItem.query.filter_by(
        consumer_id=current_user().id, product_id=p.id
    ).first()

    new_quantity = quantity + (item.quantity if item else 0)
    if new_quantity > p.stock:
        return jsonify({"error": "Not enough stock"}), 400

    if item:
        item.quantity = new_quantity
    else:
        db.session.add(CartItem(
            consumer_id=current_user().id,
            product_id=p.id,
            quantity=quantity
        ))

    db.session.commit()
    return jsonify({"message": "Added to cart"})


@app.patch("/api/cart/<int:item_id>")
@role_required("consumer")
def update_cart(item_id):
    item = db.session.get(CartItem, item_id)
    if not item or item.consumer_id != current_user().id:
        return jsonify({"error": "Cart item not found"}), 404

    data = request.get_json(silent=True) or {}
    quantity = float(data.get("quantity", 0))
    if quantity <= 0:
        db.session.delete(item)
    else:
        if quantity > item.product.stock:
            return jsonify({"error": "Not enough stock"}), 400
        item.quantity = quantity

    db.session.commit()
    return jsonify({"message": "Cart updated"})


@app.delete("/api/cart/<int:item_id>")
@role_required("consumer")
def remove_cart(item_id):
    item = db.session.get(CartItem, item_id)
    if not item or item.consumer_id != current_user().id:
        return jsonify({"error": "Cart item not found"}), 404
    db.session.delete(item)
    db.session.commit()
    return jsonify({"message": "Removed from cart"})


@app.get("/api/wishlist")
@role_required("consumer")
def get_wishlist():
    rows = WishlistItem.query.filter_by(
        consumer_id=current_user().id
    ).order_by(WishlistItem.created_at.desc()).all()
    return jsonify({"items": [
        {"id": x.id, "product": product_dict(x.product)}
        for x in rows if x.product
    ]})


@app.post("/api/wishlist")
@role_required("consumer")
def add_wishlist():
    data = request.get_json(silent=True) or {}
    p = db.session.get(Product, data.get("productId"))
    if not p:
        return jsonify({"error": "Product not found"}), 404

    exists = WishlistItem.query.filter_by(
        consumer_id=current_user().id, product_id=p.id
    ).first()
    if not exists:
        db.session.add(WishlistItem(
            consumer_id=current_user().id, product_id=p.id
        ))
        db.session.commit()

    return jsonify({"message": "Added to wishlist"})


@app.delete("/api/wishlist/<int:product_id>")
@role_required("consumer")
def remove_wishlist(product_id):
    row = WishlistItem.query.filter_by(
        consumer_id=current_user().id, product_id=product_id
    ).first()
    if not row:
        return jsonify({"error": "Wishlist item not found"}), 404
    db.session.delete(row)
    db.session.commit()
    return jsonify({"message": "Removed from wishlist"})


# ============================================================
# ORDERS + TRACKING
# ============================================================

@app.post("/api/orders")
@role_required("consumer")
def create_order():
    data = request.get_json(silent=True) or {}
    address = (data.get("deliveryAddress") or "").strip()
    raw_payment_method = data.get("paymentMethod") or "COD"
    if not isinstance(raw_payment_method, str):
        return jsonify({"error": "Invalid payment method"}), 400
    payment_method = raw_payment_method.strip().upper()
    raw_checkout_id = data.get("checkoutId") or request.headers.get("Idempotency-Key")
    checkout_id = str(raw_checkout_id).strip() if raw_checkout_id else uuid.uuid4().hex

    if not address:
        return jsonify({"error": "deliveryAddress is required"}), 400
    allowed_payment_methods = {
        "COD", "GOOGLE_PAY_DEMO", "PHONEPE_DEMO", "PAYTM_DEMO", "CARD_DEMO"
    }
    if payment_method not in allowed_payment_methods:
        return jsonify({"error": "Invalid payment method"}), 400
    if len(checkout_id) > 80:
        return jsonify({"error": "checkoutId must be 80 characters or fewer"}), 400

    user_id = current_user().id
    existing_orders = Order.query.filter_by(
        consumer_id=user_id, checkout_id=checkout_id
    ).order_by(Order.id.asc()).all()
    if existing_orders:
        return jsonify({
            "message": "This checkout was already processed",
            "orders": [order_dict(order) for order in existing_orders],
            "idempotentReplay": True,
        }), 200

    cart_items = CartItem.query.filter_by(
        consumer_id=user_id
    ).with_for_update().all()
    if not cart_items:
        existing_orders = Order.query.filter_by(
            consumer_id=user_id, checkout_id=checkout_id
        ).order_by(Order.id.asc()).all()
        if existing_orders:
            return jsonify({
                "message": "This checkout was already processed",
                "orders": [order_dict(order) for order in existing_orders],
                "idempotentReplay": True,
            }), 200
        return jsonify({"error": "Cart is empty"}), 400

    # One order is created per farmer so farmer dashboards remain clean.
    groups = {}
    for ci in cart_items:
        groups.setdefault(ci.product.farmer_id, []).append(ci)

    created = []

    try:
        for farmer_id, items in groups.items():
            farmer = db.session.get(User, farmer_id)
            order = Order(
                consumer_id=user_id,
                farmer_id=farmer_id,
                total_amount=0,
                delivery_address=address,
                status="placed",
                payment_method=payment_method,
                payment_status="PENDING" if payment_method == "COD" else "PAID_DEMO",
                checkout_id=checkout_id,
                from_location=farmer.location if farmer else None,
                to_location=current_user().location,
                pickup_latitude=farmer.latitude if farmer else None,
                pickup_longitude=farmer.longitude if farmer else None,
            )
            db.session.add(order)
            db.session.flush()

            total = 0
            weight = 0
            weight_known = True

            for ci in items:
                if not ci.product or not ci.product.is_active:
                    raise ValueError("A product in your cart is no longer available.")
                if ci.quantity > ci.product.stock:
                    raise ValueError(f"Not enough stock for {ci.product.name}")

                line = ci.quantity * ci.product.price
                total += line
                if (ci.product.unit or "").strip().casefold() in ("kg", "kilogram", "kilograms"):
                    weight += ci.quantity
                else:
                    weight_known = False
                ci.product.stock -= ci.quantity

                db.session.add(OrderItem(
                    order_id=order.id,
                    product_id=ci.product.id,
                    product_name=ci.product.name,
                    quantity=ci.quantity,
                    unit_price=ci.product.price
                ))
                db.session.delete(ci)

            order.total_amount = round(total, 2)
            order.total_weight = weight if weight_known else 0
            add_tracking(order, "placed", "Order placed successfully.")
            add_notification(
                farmer_id,
                "New customer order",
                f"Order ORD{order.id:05d} has been placed."
            )
            created.append(order)

        for order in created:
            create_partner_requests(order)

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "message": "Order placed successfully",
        "orders": [order_dict(o) for o in created]
    }), 201


@app.get("/api/orders")
@role_required("consumer", "farmer")
def get_orders():
    u = current_user()

    if u.role == "consumer":
        rows = Order.query.filter_by(
            consumer_id=u.id
        ).order_by(Order.created_at.desc()).all()
    else:
        rows = Order.query.filter_by(
            farmer_id=u.id
        ).order_by(Order.created_at.desc()).all()

    return jsonify({"orders": [order_dict(o) for o in rows]})


@app.get("/api/orders/<int:order_id>")
@jwt_required()
def get_order(order_id):
    o = db.session.get(Order, order_id)
    if not o:
        return jsonify({"error": "Order not found"}), 404

    u = current_user()
    if u.id not in (o.consumer_id, o.farmer_id):
        return jsonify({"error": "Access denied"}), 403

    return jsonify({"order": order_dict(o)})


@app.post("/api/orders/<int:order_id>/transport/retry")
@jwt_required()
def retry_transport_matching(order_id):
    order = Order.query.filter_by(id=order_id).with_for_update().first()
    user = current_user()
    if not order or not user or user.id not in (order.consumer_id, order.farmer_id):
        return jsonify({"error": "Order not found"}), 404
    if order.status in ("cancelled", "delivered") or order.delivery_partner_id or order.transport_partner_id:
        return jsonify({"error": "Transport matching is no longer available for this order"}), 409
    farmer = db.session.get(User, order.farmer_id)
    if farmer:
        if order.pickup_latitude is None: order.pickup_latitude = farmer.latitude
        if order.pickup_longitude is None: order.pickup_longitude = farmer.longitude
    created = create_partner_requests(order)
    db.session.commit()
    refreshed = order_dict(order)
    return jsonify({"message": "Matching retried", "requestsCreated": created, "order": refreshed})


@app.get("/api/orders/track/<string:order_code>")
@jwt_required()
def track_order(order_code):
    code = order_code.upper().replace("#", "").replace("ORD", "")
    if not code.isdigit():
        return jsonify({"error": "Invalid order ID"}), 400

    o = db.session.get(Order, int(code))
    if not o:
        return jsonify({"error": "Order not found"}), 404

    user = current_user()
    if not user or user.id not in (o.consumer_id, o.farmer_id):
        return jsonify({"error": "Order not found"}), 404

    return jsonify({"order": order_dict(o)})


@app.patch("/api/orders/<int:order_id>/status")
@role_required("farmer")
def update_order_status(order_id):
    o = Order.query.filter_by(id=order_id).with_for_update().first()
    if not o or o.farmer_id != current_user().id:
        return jsonify({"error": "Order not found"}), 404

    data = request.get_json(silent=True) or {}
    status = data.get("status")

    allowed = {"placed", "confirmed", "cancelled"}
    if status not in allowed:
        return jsonify({"error": "Invalid order status"}), 400
    if o.status not in ("placed", "confirmed") and status != "cancelled":
        return jsonify({"error": "Transport status is managed by the assigned delivery partner"}), 409

    request_count = 0
    if status == "confirmed" and o.status != "confirmed":
        request_count = create_partner_requests(o)
    if status == "cancelled":
        PartnerTransportRequest.query.filter_by(order_id=o.id, status="pending").update(
            {"status": "cancelled", "updated_at": datetime.utcnow()},
            synchronize_session=False,
        )

    o.status = status
    add_tracking(o, status, data.get("note", ""))

    add_notification(
        o.consumer_id,
        "Order updated",
        f"Order ORD{o.id:05d}: {STATUS_LABELS.get(status, status)}"
    )
    db.session.commit()

    has_pending_requests = PartnerTransportRequest.query.filter_by(order_id=o.id, status="pending").count() > 0
    return jsonify({"message": "Order status updated", "partnerRequestsCreated": request_count,
                    "transportMessage": "Eligible delivery partners were notified." if has_pending_requests else "No eligible delivery partners matched the available location and weight data.",
                    "order": order_dict(o)})


def create_partner_requests(order):
    """Persist one broadcast request per eligible partner using real coordinates when radius applies."""
    pickup = (order.from_location or "").casefold().strip()
    if not pickup or not order.total_weight or order.total_weight <= 0:
        return 0
    count = 0
    for partner in DeliveryPartner.query.filter_by(availability="available").all():
        service = (partner.service_location or "").casefold().strip()
        if not service or (service not in pickup and pickup not in service):
            continue
        if partner.capacity_kg is None or order.total_weight > partner.capacity_kg:
            continue
        distance = transport_distance_km(
            order.pickup_latitude, order.pickup_longitude,
            partner.service_latitude, partner.service_longitude,
        )
        if partner.service_radius_km is not None:
            if distance is None or distance > partner.service_radius_km:
                continue
        existing = PartnerTransportRequest.query.filter_by(order_id=order.id, partner_id=partner.id).first()
        if existing:
            continue
        estimate = transport_estimate(partner, order.total_weight, distance)
        db.session.add(PartnerTransportRequest(order_id=order.id, partner_id=partner.id,
            status="pending", distance_km=distance, estimated_charge=estimate, pricing_method=partner.pricing_method,
            expires_at=datetime.utcnow() + timedelta(hours=24)))
        count += 1
    return count


def transport_distance_km(lat1, lon1, lat2, lon2):
    values = (lat1, lon1, lat2, lon2)
    if any(value is None or not math.isfinite(value) for value in values):
        return None
    if not (-90 <= lat1 <= 90 and -90 <= lat2 <= 90 and -180 <= lon1 <= 180 and -180 <= lon2 <= 180):
        return None
    earth_radius_km = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi, d_lambda = math.radians(lat2 - lat1), math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    a = min(1.0, max(0.0, a))
    return round(earth_radius_km * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a)), 2)


def transport_estimate(partner, weight, distance):
    if not math.isfinite(weight) or weight <= 0:
        return None
    if partner.pricing_method == "per_kg" and partner.per_kg_rate is not None and math.isfinite(partner.per_kg_rate) and partner.per_kg_rate >= 0:
        return round(partner.per_kg_rate * weight, 2)
    if partner.pricing_method == "per_km" and partner.per_km_rate is not None and math.isfinite(partner.per_km_rate) and partner.per_km_rate >= 0 and distance is not None:
        return round(partner.per_km_rate * distance, 2)
    return None


def sale_dict(row):
    return {"id": row.id, "productName": row.product_name, "sellingDate": row.selling_date.isoformat(),
            "month": row.selling_date.month, "year": row.selling_date.year, "quantity": row.quantity,
            "unit": row.unit, "sellingPrice": row.selling_price,
            "total": round(row.quantity * row.selling_price, 2)}


@app.get("/api/farmer/sales")
@role_required("farmer")
def farmer_sales():
    query = FarmerSaleRecord.query.filter_by(farmer_id=current_user().id)
    try:
        year = int(request.args["year"]) if request.args.get("year") else None
        month = int(request.args["month"]) if request.args.get("month") else None
    except ValueError:
        return jsonify({"error": "Month and year must be numeric"}), 400
    if year is not None and not 2000 <= year <= 2100:
        return jsonify({"error": "Year must be between 2000 and 2100"}), 400
    if month is not None and not 1 <= month <= 12:
        return jsonify({"error": "Month must be between 1 and 12"}), 400
    if year is not None: query = query.filter(db.extract("year", FarmerSaleRecord.selling_date) == year)
    if month is not None: query = query.filter(db.extract("month", FarmerSaleRecord.selling_date) == month)
    rows = query.order_by(FarmerSaleRecord.selling_date.desc(), FarmerSaleRecord.id.desc()).all()
    return jsonify({"records": [sale_dict(x) for x in rows],
        "totalQuantity": round(sum(x.quantity for x in rows), 3),
        "totalSales": round(sum(x.quantity * x.selling_price for x in rows), 2)})


@app.post("/api/farmer/sales")
@role_required("farmer")
def add_farmer_sale():
    data = request.get_json(silent=True) or {}
    name = str(data.get("productName", "")).strip()
    unit = data.get("unit")
    try:
        date = datetime.strptime(str(data.get("sellingDate", "")), "%Y-%m-%d").date()
        quantity, price = float(data.get("quantity")), float(data.get("sellingPrice"))
    except (TypeError, ValueError):
        return jsonify({"error": "Enter a valid date, quantity and selling price"}), 400
    if not name or len(name) > 160 or unit not in ("kg", "Units") or quantity <= 0 or price < 0 or date > datetime.utcnow().date() or not math.isfinite(quantity + price):
        return jsonify({"error": "Product, positive quantity, kg/Units and non-negative price are required"}), 400
    row = FarmerSaleRecord(farmer_id=current_user().id, product_name=name, selling_date=date, quantity=quantity, unit=unit, selling_price=price)
    db.session.add(row); db.session.commit()
    return jsonify({"record": sale_dict(row)}), 201


@app.post("/api/auth/google")
def google_login():
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    credential = (request.get_json(silent=True) or {}).get("credential", "")
    role = (request.get_json(silent=True) or {}).get("role", "consumer")
    if not client_id:
        return jsonify({"error": "Google sign-in is not configured. Set GOOGLE_CLIENT_ID and VITE_GOOGLE_CLIENT_ID."}), 503
    if role not in ("consumer", "farmer") or not credential:
        return jsonify({"error": "A Google credential and valid account role are required"}), 400
    if not isinstance(credential, str) or len(credential) > 10000:
        return jsonify({"error": "Google credential is invalid"}), 401
    try:
        signing_key = google_jwks.get_signing_key_from_jwt(credential)
        claims = pyjwt.decode(credential, signing_key.key, algorithms=["RS256"], audience=client_id,
                              issuer=["https://accounts.google.com", "accounts.google.com"])
    except Exception:
        return jsonify({"error": "Google credential could not be verified"}), 401
    if claims.get("email_verified") not in (True, "true"):
        return jsonify({"error": "Google credential validation failed"}), 401
    email = str(claims.get("email", "")).strip().lower()
    name = str(claims.get("name", "")).strip()[:120]
    if not email or not name: return jsonify({"error": "Google account is missing a verified email or name"}), 401
    user = User.query.filter_by(email=email).first()
    if user and user.role != role: return jsonify({"error": f"This account is registered as {user.role}"}), 403
    if not user:
        user = User(name=name, email=email, password_hash=generate_password_hash(secrets.token_urlsafe(32)), role=role, verified=True)
        db.session.add(user); db.session.commit()
    return jsonify({"token": create_access_token(identity=str(user.id)), "user": user_dict(user)})


def partner_public(p):
    return {"id": p.id, "name": p.name, "mobile": p.mobile, "email": p.email, "address": p.address,
        "city": p.city, "pincode": p.pincode, "vehicleType": p.vehicle_type, "vehicleRegistration": p.vehicle_registration,
        "capacityKg": p.capacity_kg, "vehiclePhoto": p.vehicle_photo, "licenseNumber": p.license_number,
        "documents": p.documents, "pricingMethod": p.pricing_method, "perKmRate": p.per_km_rate,
        "perKgRate": p.per_kg_rate, "serviceRadiusKm": p.service_radius_km, "serviceLocation": p.service_location,
        "serviceLatitude": p.service_latitude, "serviceLongitude": p.service_longitude,
        "availability": p.availability, "verificationStatus": p.verification_status}


def partner_request_dict(row, include_private=False):
    o = row.order
    result = {"id": row.id, "orderId": f"ORD{o.id:05d}", "orderDbId": o.id, "status": row.status,
        "product": ", ".join(f"{i.product_name} × {i.quantity:g}" for i in o.items), "quantity": o.total_weight,
        "pickup": o.from_location or o.farmer_user.location or "Unavailable", "delivery": o.to_location or o.delivery_address,
        "distanceKm": row.distance_km, "estimatedCharge": row.estimated_charge, "pricingMethod": row.pricing_method,
        "createdAt": row.created_at.isoformat(), "consumerName": o.consumer.name if o.consumer else None,
        "farmerName": o.farmer_user.name if o.farmer_user else None}
    if include_private and row.status in ("accepted", "picked_up", "in_transit"):
        result.update({"consumerPhone": o.consumer.phone if o.consumer else None, "farmerPhone": o.farmer_user.phone if o.farmer_user else None})
    return result


@app.post("/api/partner/register")
def partner_register():
    d = request.form if request.form else (request.get_json(silent=True) or {})
    # Targeted diagnostics omit submitted values, credentials and file contents.
    app.logger.info("Partner registration request: content_type=%s fields=%s files=%s",
                    request.mimetype, sorted(d.keys()), sorted(request.files.keys()))
    required = {"name": "Full name is required.", "password": "Password is required."}
    errors = {key: message for key, message in required.items() if not str(d.get(key, "")).strip()}
    email_value = str(d.get("email", "")).strip().lower()
    mobile_value = str(d.get("mobile", "")).strip()
    email = email_value or None
    mobile = mobile_value or None
    if not email and not mobile:
        errors["email"] = "Enter an email address or mobile number."
        errors["mobile"] = "Enter an email address or mobile number."
    if email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email): errors["email"] = "Enter a valid email address."
    if mobile and not re.fullmatch(r"\+?[0-9 ()-]{7,20}", mobile): errors["mobile"] = "Enter a valid mobile number."
    if not isinstance(d.get("password"), str) or len(d["password"]) < 8: errors["password"] = "Use at least 8 characters."

    def optional_number(field, label, positive=False):
        raw = str(d.get(field, "")).strip()
        if not raw: return None
        try: value = float(raw)
        except (TypeError, ValueError):
            errors[field] = f"Enter a valid {label}."
            return None
        if not math.isfinite(value) or (positive and value <= 0) or (not positive and value < 0):
            errors[field] = f"{label.capitalize()} must be {'greater than zero' if positive else 'zero or greater'}."
            return None
        return value

    capacity = optional_number("capacityKg", "vehicle capacity", positive=True)
    radius = optional_number("serviceRadiusKm", "service radius", positive=True)
    perkg = optional_number("perKgRate", "rate per kg")
    perkm = optional_number("perKmRate", "rate per km")
    service_latitude = optional_number("serviceLatitude", "service latitude")
    service_longitude = optional_number("serviceLongitude", "service longitude")
    if service_latitude is not None and not -90 <= service_latitude <= 90:
        errors["serviceLatitude"] = "Latitude must be between -90 and 90."
    if service_longitude is not None and not -180 <= service_longitude <= 180:
        errors["serviceLongitude"] = "Longitude must be between -180 and 180."
    if (service_latitude is None) != (service_longitude is None):
        errors["serviceLatitude"] = "Enter both service coordinates, or leave both empty."
    if radius is not None and service_latitude is None:
        errors["serviceLatitude"] = "Service latitude and longitude are required when a service radius is set."
    pricing_method = str(d.get("pricingMethod", "")).strip() or None
    if pricing_method and pricing_method not in ("per_kg", "per_km"):
        errors["pricingMethod"] = "Choose per kilogram or per kilometre."
    availability = str(d.get("availability", "available")).strip() or "available"
    if availability not in ("available", "busy", "offline"):
        errors["availability"] = "Choose a valid availability status."
    reg_value = str(d.get("vehicleRegistration", "")).strip().upper()
    reg = reg_value or None

    def read_upload(field, allowed_types, label):
        uploaded = request.files.get(field)
        if not uploaded or not uploaded.filename:
            return ""
        if uploaded.mimetype not in allowed_types:
            errors[field] = f"{label} must use an accepted file type."
            return ""
        content = uploaded.read(900001)
        if len(content) > 900000:
            errors[field] = f"{label} must be under 900 KB."
            return ""
        if not content:
            errors[field] = f"{label} cannot be empty."
            return ""
        signatures = {
            "image/jpeg": content.startswith(b"\xff\xd8\xff"),
            "image/png": content.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/webp": content.startswith(b"RIFF") and content[8:12] == b"WEBP",
            "application/pdf": content.startswith(b"%PDF-"),
        }
        if not signatures.get(uploaded.mimetype, False):
            errors[field] = f"{label} contents do not match the selected file type."
            return ""
        import base64
        return f"data:{uploaded.mimetype};base64," + base64.b64encode(content).decode("ascii")

    vehicle_photo = read_upload("vehiclePhoto", {"image/jpeg", "image/png", "image/webp"}, "Vehicle photo")
    documents = read_upload("documents", {"application/pdf", "image/jpeg", "image/png", "image/webp"}, "Supporting document")
    if errors:
        app.logger.warning("Partner registration validation rejected: fields=%s", sorted(errors.keys()))
        return jsonify({"error": "Review the highlighted fields and try again.", "errors": errors}), 400
    duplicate_filters = []
    if email: duplicate_filters.append(DeliveryPartner.email == email)
    if mobile: duplicate_filters.append(DeliveryPartner.mobile == mobile)
    if reg: duplicate_filters.append(DeliveryPartner.vehicle_registration == reg)
    if duplicate_filters and DeliveryPartner.query.filter(or_(*duplicate_filters)).first():
        duplicates = {}
        if email and DeliveryPartner.query.filter_by(email=email).first(): duplicates["email"] = "This email is already registered."
        if mobile and DeliveryPartner.query.filter_by(mobile=mobile).first(): duplicates["mobile"] = "This mobile number is already registered."
        if reg and DeliveryPartner.query.filter_by(vehicle_registration=reg).first(): duplicates["vehicleRegistration"] = "This vehicle registration is already registered."
        app.logger.warning("Partner registration duplicate rejected: fields=%s", sorted(duplicates.keys()))
        return jsonify({"error": "An account already uses one or more of these details.", "errors": duplicates}), 409

    def optional_text(field):
        return str(d.get(field, "")).strip() or None

    p = DeliveryPartner(name=str(d["name"]).strip(), mobile=mobile, email=email,
        password_hash=generate_password_hash(d["password"]), address=optional_text("address"),
        city=optional_text("city"), pincode=optional_text("pincode"),
        vehicle_type=optional_text("vehicleType"), vehicle_registration=reg, capacity_kg=capacity,
        vehicle_photo=vehicle_photo or None, license_number=optional_text("licenseNumber"),
        documents=documents or None, pricing_method=pricing_method, per_km_rate=perkm,
        per_kg_rate=perkg, service_radius_km=radius,
        service_location=optional_text("serviceLocation"),
        service_latitude=service_latitude, service_longitude=service_longitude,
        availability=availability, verification_status="unverified")
    try:
        db.session.add(p)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        app.logger.warning("Partner registration database uniqueness conflict")
        return jsonify({"error": "Email, mobile or vehicle registration is already registered.", "errors": {
            "email": "Check whether this email is already registered.",
            "mobile": "Check whether this mobile number is already registered.",
            "vehicleRegistration": "Check whether this vehicle registration is already registered.",
        }}), 409
    except Exception:
        db.session.rollback()
        app.logger.exception("Partner registration could not be saved")
        return jsonify({"error": "Registration could not be saved. Check the entered details and try again."}), 500
    app.logger.info("Partner registration saved: partner_id=%s", p.id)
    return jsonify({"message": "Registration received; documents are unverified pending review", "token": create_access_token(identity=f"partner:{p.id}"), "partner": {k:v for k,v in partner_public(p).items() if k not in ("documents", "vehiclePhoto")}}), 201


@app.post("/api/partner/login")
def partner_login():
    d = request.get_json(silent=True) or {}
    identifier = str(d.get("identifier", d.get("email", ""))).strip()
    p = DeliveryPartner.query.filter(or_(DeliveryPartner.email == identifier.lower(), DeliveryPartner.mobile == identifier)).first()
    if not p or not check_password_hash(p.password_hash, d.get("password", "")): return jsonify({"error": "Invalid partner mobile/email or password"}), 401
    return jsonify({"token": create_access_token(identity=f"partner:{p.id}"), "partner": partner_public(p)})


@app.post("/api/partner/forgot-password")
def partner_forgot_password():
    host=os.getenv("SMTP_HOST","").strip(); user=os.getenv("SMTP_USER","").strip(); password=os.getenv("SMTP_PASSWORD",""); sender=os.getenv("SMTP_FROM",user).strip()
    if not all((host,user,password,sender)):
        return jsonify({"error": "Password reset is unavailable until SMTP_HOST, SMTP_USER, SMTP_PASSWORD and SMTP_FROM are configured."}), 503
    email=str((request.get_json(silent=True) or {}).get("email","")).strip().lower()
    partner=DeliveryPartner.query.filter_by(email=email).first()
    if partner:
        raw=secrets.token_urlsafe(32); reset=PartnerPasswordReset(partner_id=partner.id,token_hash=hashlib.sha256(raw.encode()).hexdigest(),expires_at=datetime.utcnow()+timedelta(minutes=30))
        db.session.add(reset); db.session.commit()
        message=EmailMessage(); message["Subject"]="FarmBridge delivery partner password reset"; message["From"]=sender; message["To"]=email
        message.set_content(f"Use this one-time password reset token within 30 minutes:\n\n{raw}\n\nIf you did not request this, ignore this message.")
        try:
            port=int(os.getenv("SMTP_PORT","587")); client=smtplib.SMTP_SSL if port==465 else smtplib.SMTP
            with client(host,port,timeout=10) as smtp:
                if port!=465: smtp.starttls()
                smtp.login(user,password); smtp.send_message(message)
        except Exception:
            db.session.delete(reset); db.session.commit()
            return jsonify({"error": "Password reset email could not be sent. Check SMTP configuration."}), 503
    return jsonify({"message": "If the partner account exists, a one-time reset token has been sent."})


@app.post("/api/partner/reset-password")
def partner_reset_password():
    data=request.get_json(silent=True) or {}; raw=str(data.get("token", "")); password=data.get("password", "")
    if not isinstance(password,str) or len(password)<8: return jsonify({"error": "New password must contain at least 8 characters"}),400
    token_hash=hashlib.sha256(raw.encode()).hexdigest()
    reset=PartnerPasswordReset.query.filter_by(token_hash=token_hash,used_at=None).first()
    if not reset or reset.expires_at<datetime.utcnow(): return jsonify({"error": "Reset token is invalid or expired"}),400
    partner=db.session.get(DeliveryPartner,reset.partner_id)
    if not partner: return jsonify({"error": "Partner account not found"}),404
    partner.password_hash=generate_password_hash(password); reset.used_at=datetime.utcnow(); db.session.commit()
    return jsonify({"message": "Password reset successful. Sign in with the new password."})


@app.get("/api/partner/me")
@partner_required
def partner_me(): return jsonify({"partner": partner_public(request.delivery_partner)})


@app.get("/api/partner/requests")
@partner_required
def partner_requests():
    p = request.delivery_partner
    now = datetime.utcnow()
    PartnerTransportRequest.query.filter_by(partner_id=p.id, status="pending").filter(
        or_(PartnerTransportRequest.expires_at <= now,
            PartnerTransportRequest.expires_at.is_(None) & (PartnerTransportRequest.created_at <= now - timedelta(hours=24)))
    ).update({"status": "expired", "updated_at": now}, synchronize_session=False)
    db.session.commit()
    rows = PartnerTransportRequest.query.filter_by(partner_id=p.id).order_by(PartnerTransportRequest.created_at.desc()).all()
    return jsonify({"requests": [partner_request_dict(x, True) for x in rows], "pendingCount": sum(x.status == "pending" for x in rows)})


@app.post("/api/partner/requests/<int:request_id>/reject")
@partner_required
def partner_reject(request_id):
    row = PartnerTransportRequest.query.filter_by(id=request_id, partner_id=request.delivery_partner.id, status="pending").with_for_update().first()
    if not row: return jsonify({"error": "Request is no longer pending"}), 409
    row.status="rejected"; row.updated_at=datetime.utcnow(); db.session.commit()
    return jsonify({"message": "Request rejected"})


@app.post("/api/partner/requests/<int:request_id>/accept")
@partner_required
def partner_accept(request_id):
    try:
        # The order row lock serializes competing partner acceptance transactions on PostgreSQL.
        row = PartnerTransportRequest.query.filter_by(id=request_id, partner_id=request.delivery_partner.id).with_for_update().first()
        if not row: return jsonify({"error": "Request is no longer pending"}), 409
        if row.status != "pending":
            assigned_order = db.session.get(Order, row.order_id)
            if assigned_order and (assigned_order.delivery_partner_id or assigned_order.transport_partner_id):
                return jsonify({"error": "Another partner has already accepted this order"}), 409
            return jsonify({"error": "Request is no longer pending"}), 409
        now = datetime.utcnow()
        expires_at = row.expires_at or (row.created_at + timedelta(hours=24))
        if expires_at <= now:
            row.status="expired"; row.updated_at=now; db.session.commit()
            return jsonify({"error": "This transport request has expired"}), 409
        order = Order.query.filter_by(id=row.order_id).with_for_update().first()
        if not order or order.status not in ("placed", "confirmed"):
            row.status="cancelled"; row.updated_at=datetime.utcnow(); db.session.commit()
            return jsonify({"error": "This order is no longer available for transport"}), 409
        if request.delivery_partner.availability != "available":
            return jsonify({"error": "Your partner account is not currently available for bookings"}), 409
        if order.delivery_partner_id or order.transport_partner_id or PartnerTransportRequest.query.filter_by(order_id=row.order_id, status="accepted").first():
            return jsonify({"error": "Another partner has already accepted this order"}), 409
        row.status="accepted"; row.updated_at=datetime.utcnow(); order.status="transport_assigned"; order.delivery_partner_id=request.delivery_partner.id; order.transport_partner_name=request.delivery_partner.name; request.delivery_partner.availability="busy"
        PartnerTransportRequest.query.filter(
            PartnerTransportRequest.order_id == row.order_id,
            PartnerTransportRequest.id != row.id,
            PartnerTransportRequest.status == "pending",
        ).update({"status": "cancelled", "updated_at": datetime.utcnow()}, synchronize_session=False)
        add_tracking(order, "transport_assigned", f"Delivery partner {request.delivery_partner.name} accepted the booking")
        for user_id in (order.consumer_id, order.farmer_id): add_notification(user_id, "Delivery partner assigned", f"{request.delivery_partner.name} accepted order ORD{order.id:05d}.")
        db.session.commit(); return jsonify({"message": "Booking accepted", "booking": partner_request_dict(row, True)})
    except Exception:
        db.session.rollback(); raise


@app.patch("/api/partner/availability")
@partner_required
def partner_availability():
    value=(request.get_json(silent=True) or {}).get("availability")
    if value not in ("available", "busy", "offline"): return jsonify({"error": "Availability must be available, busy or offline"}),400
    if value == "available" and PartnerTransportRequest.query.filter_by(partner_id=request.delivery_partner.id).filter(
        PartnerTransportRequest.status.in_(("accepted", "picked_up", "in_transit"))
    ).count():
        return jsonify({"error": "Complete active bookings before becoming available"}), 409
    request.delivery_partner.availability=value; db.session.commit(); return jsonify({"partner": partner_public(request.delivery_partner)})


@app.get("/api/partner/earnings")
@partner_required
def partner_earnings():
    rows=PartnerTransportRequest.query.filter_by(partner_id=request.delivery_partner.id).filter(PartnerTransportRequest.status.in_(("delivered",))).all()
    return jsonify({"completed":len(rows),"earnings":round(sum(x.estimated_charge or 0 for x in rows),2),"bookings":[partner_request_dict(x,True) for x in rows]})


@app.patch("/api/partner/bookings/<int:request_id>/status")
@partner_required
def partner_booking_status(request_id):
    row=PartnerTransportRequest.query.filter_by(id=request_id,partner_id=request.delivery_partner.id).first(); value=(request.get_json(silent=True) or {}).get("status")
    mapping={"picked_up":"out_for_delivery","in_transit":"out_for_delivery","delivered":"delivered"}
    allowed_next={"accepted":"picked_up","picked_up":"in_transit","in_transit":"delivered"}
    if not row or row.order.status == "cancelled" or allowed_next.get(row.status) != value: return jsonify({"error":"Invalid booking status"}),400
    row.status=value; row.updated_at=datetime.utcnow(); row.order.status=mapping[value]; add_tracking(row.order,mapping[value],f"Delivery partner updated booking to {value}")
    if value == "delivered" and PartnerTransportRequest.query.filter_by(partner_id=row.partner_id).filter(
        PartnerTransportRequest.status.in_(("accepted", "picked_up", "in_transit"))
    ).count() == 0:
        row.partner.availability = "available"
    for user_id in (row.order.consumer_id,row.order.farmer_id): add_notification(user_id,"Delivery update",f"Order ORD{row.order_id:05d}: {value.replace('_',' ')}")
    db.session.commit(); return jsonify({"booking":partner_request_dict(row,True)})


# ============================================================
# FARMER DASHBOARD / EARNINGS / DELIVERIES
# ============================================================

@app.get("/api/farmer/dashboard")
@role_required("farmer")
def farmer_dashboard():
    u = current_user()
    all_orders = Order.query.filter_by(farmer_id=u.id).all()

    delivered = [o for o in all_orders if o.status == "delivered"]
    pending = [
        o for o in all_orders
        if o.status not in ("delivered", "cancelled")
    ]

    earnings = sum(o.total_amount for o in delivered)

    return jsonify({
        "farmer": user_dict(u),
        "stats": {
            "products": Product.query.filter_by(
                farmer_id=u.id, is_active=True
            ).count(),
            "orders": len(all_orders),
            "pendingOrders": len(pending),
            "deliveries": len(delivered),
            "earnings": round(earnings, 2)
        }
    })


@app.get("/api/farmer/earnings")
@role_required("farmer")
def farmer_earnings():
    rows = Order.query.filter_by(
        farmer_id=current_user().id
    ).order_by(Order.created_at.desc()).all()

    delivered = [o for o in rows if o.status == "delivered"]
    pending = [o for o in rows if o.status not in ("delivered", "cancelled")]

    return jsonify({
        "summary": {
            "totalIncome": round(sum(o.total_amount for o in delivered), 2),
            "deliveredOrders": len(delivered),
            "pendingOrders": len(pending),
            "totalOrders": len(rows)
        },
        "orders": [order_dict(o) for o in rows]
    })


@app.get("/api/farmer/deliveries")
@role_required("farmer")
def farmer_deliveries():
    rows = Order.query.filter(
        Order.farmer_id == current_user().id,
        Order.status.in_((
            "transport_assigned", "out_for_delivery", "delivered"
        ))
    ).order_by(Order.created_at.desc()).all()

    return jsonify({"deliveries": [order_dict(o) for o in rows]})


# ============================================================
# PREVIOUS YEAR CROP DATA + FERTILITY
# ============================================================

@app.get("/api/crops/previous-year")
@role_required("farmer")
def previous_year_crops():
    year = request.args.get("year")
    crop = request.args.get("crop")

    query = CropRecord.query.filter_by(farmer_id=current_user().id)

    if year:
        query = query.filter_by(year=int(year))
    if crop:
        query = query.filter(CropRecord.crop_name.ilike(f"%{crop}%"))

    rows = query.order_by(CropRecord.year.desc()).all()

    return jsonify({
        "records": [
            {
                "id": r.id,
                "cropName": r.crop_name,
                "category": r.category,
                "season": r.season,
                "year": r.year,
                "areaAcres": r.area_acres,
                "yieldAmount": r.yield_amount,
                "averagePrice": r.average_price,
                "totalIncome": r.total_income,
                "soilType": r.soil_type,
                "soilPh": r.soil_ph,
                "notes": r.notes,
            }
            for r in rows
        ]
    })


@app.post("/api/crops/previous-year")
@role_required("farmer")
def add_crop_record():
    data = request.get_json(silent=True) or {}

    if not data.get("cropName") or not data.get("year"):
        return jsonify({"error": "cropName and year are required"}), 400

    r = CropRecord(
        farmer_id=current_user().id,
        crop_name=data["cropName"],
        category=data.get("category"),
        season=data.get("season"),
        year=int(data["year"]),
        area_acres=float(data["areaAcres"]) if data.get("areaAcres") is not None else None,
        yield_amount=float(data["yieldAmount"]) if data.get("yieldAmount") is not None else None,
        average_price=float(data["averagePrice"]) if data.get("averagePrice") is not None else None,
        total_income=float(data["totalIncome"]) if data.get("totalIncome") is not None else None,
        soil_type=data.get("soilType"),
        soil_ph=float(data["soilPh"]) if data.get("soilPh") is not None else None,
        notes=data.get("notes"),
    )
    db.session.add(r)
    db.session.commit()

    return jsonify({"message": "Previous-year crop record saved", "id": r.id}), 201


@app.get("/api/crops/summary")
@role_required("farmer")
def crop_summary():
    rows = CropRecord.query.filter_by(farmer_id=current_user().id).all()

    if not rows:
        return jsonify({
            "summary": {
                "averageYield": 0,
                "averagePrice": 0,
                "totalProduction": 0,
                "totalIncome": 0
            }
        })

    valid_yields = [r.yield_amount for r in rows if r.yield_amount is not None]
    valid_prices = [r.average_price for r in rows if r.average_price is not None]
    production = sum(r.yield_amount or 0 for r in rows)
    income = sum(r.total_income or 0 for r in rows)

    return jsonify({
        "summary": {
            "averageYield": round(sum(valid_yields) / len(valid_yields), 2) if valid_yields else 0,
            "averagePrice": round(sum(valid_prices) / len(valid_prices), 2) if valid_prices else 0,
            "totalProduction": round(production, 2),
            "totalIncome": round(income, 2)
        }
    })


# ============================================================
# FARMING AI ASSISTANT
# ============================================================

@app.get("/api/ai/conversations")
@jwt_required()
def ai_conversations():
    user = current_user()
    if not user:
        return jsonify({"error": "User not found"}), 401
    conversations = AIConversation.query.filter_by(user_id=user.id).order_by(
        AIConversation.updated_at.desc()
    ).all()
    return jsonify({"conversations": [ai_conversation_dict(item) for item in conversations]})


@app.get("/api/ai/conversations/<int:conversation_id>")
@jwt_required()
def get_ai_conversation(conversation_id):
    user = current_user()
    conversation = db.session.get(AIConversation, conversation_id)
    if not user or not conversation or conversation.user_id != user.id:
        return jsonify({"error": "Conversation not found"}), 404
    return jsonify({"conversation": ai_conversation_dict(conversation, include_messages=True)})


@app.delete("/api/ai/conversations/<int:conversation_id>")
@jwt_required()
def delete_ai_conversation(conversation_id):
    user = current_user()
    conversation = db.session.get(AIConversation, conversation_id)
    if not user or not conversation or conversation.user_id != user.id:
        return jsonify({"error": "Conversation not found"}), 404
    db.session.delete(conversation)
    db.session.commit()
    return jsonify({"message": "Conversation deleted"})


@app.post("/api/ai/farming-assistant")
@jwt_required()
def farming_assistant():
    data = request.get_json(silent=True) or {}
    message = (data.get("message") or "").strip()

    if not message:
        return jsonify({"error": "message is required"}), 400
    if len(message) > 5000:
        return jsonify({"error": "message must be 5000 characters or fewer"}), 400

    user = current_user()
    if not user:
        return jsonify({"error": "User not found"}), 401

    conversation_id = data.get("conversationId")
    conversation = None
    if conversation_id is not None:
        try:
            conversation_id = int(conversation_id)
        except (TypeError, ValueError):
            return jsonify({"error": "conversationId must be an integer"}), 400
        conversation = db.session.get(AIConversation, conversation_id)
        if not conversation or conversation.user_id != user.id:
            return jsonify({"error": "Conversation not found"}), 404

    language_hint = detect_message_language(message)
    requested_language = data.get("uiLanguage")
    if requested_language not in (None, "en", "kn"):
        return jsonify({"error": "uiLanguage must be 'en' or 'kn'"}), 400
    if requested_language in ("en", "kn") and language_hint != "Kannada-English":
        language_hint = "Kannada" if requested_language == "kn" else "English"
    if language_hint == "Kannada-English":
        language_instruction = (
            "This message is mixed Kannada-English. Answer in a natural Kannada-English mix, using Kannada script "
            "for Kannada phrases and English for the English terms. Do not answer in English only. Set the language "
            "field to 'Kannada-English'."
        )
    elif language_hint != "Auto-detected":
        language_instruction = (
            f"The latest message is written in {language_hint}. Reply fully in {language_hint}, and set the language "
            f"field to '{language_hint}'."
        )
    else:
        language_instruction = (
            "Identify whether the latest message is in Kannada, English, Hindi, Telugu, or Tamil, and reply in that "
            "same language. If it is Kannada-English code-mixed, preserve that natural mix."
        )

    if user.role == "consumer":
        role_context = (
            "The authenticated user is a CONSUMER. Use the actual Consumer dashboard labels: Home/category navigation and "
            "the search field browse farmer listings; open a product for its details; use Add to Cart or Buy Now, then "
            "Cart and Checkout; use Wishlist for saved products; use My Orders to review purchases and order tracking; "
            "Profile and Notifications are also available. At checkout an order can "
            "create a transport request; eligible available delivery partners receive it, and the first valid acceptance "
            "assigns transport. Explain only these existing workflows."
        )
    elif user.role == "farmer":
        role_context = (
            "The authenticated user is a FARMER. Use the actual Farmer dashboard labels: Add Product and My Products manage "
            "listings; Orders and Deliveries show order and delivery progress; Previous Year Crop Details and sales records "
            "show farm history; Transport Matching shows matching information; Earnings and Profile are available. "
            "Consumer checkout creates a transport request automatically; eligible delivery partners receive it and the "
            "first valid acceptance assigns it. Farmers do not manually assign a partner. Explain only these workflows."
        )
    else:
        return jsonify({"error": "This account cannot use the farming assistant"}), 403

    prompt = [
        {
            "role": "system",
            "content": (
                "You are FarmBridge AI, a practical farming and FarmBridge website assistant. " + role_context + " "
                "For website questions give concise numbered steps that match the authenticated user's role and the "
                "features described here. Do not claim to see or change account, order, sales or product data; do not "
                "claim to perform actions. Never reveal private data. If a feature is not described, say you cannot "
                "confirm it instead of inventing a page, button or API. " + language_instruction + " "
                "Use prior messages to understand follow-ups, but match the language of the latest question. "
                "Return only a JSON object with string keys 'language' and 'answer'. "
                "Give clear, cautious agricultural guidance; do not invent local conditions or prescribe chemical doses. "
                "Recommend a local agronomist or soil test when a reliable recommendation depends on them."
            ),
        }
    ]
    if conversation:
        previous_messages = AIMessage.query.filter_by(
            conversation_id=conversation.id
        ).order_by(AIMessage.created_at.desc()).limit(16).all()
        prompt.extend(
            {"role": item.role, "content": item.content}
            for item in reversed(previous_messages)
        )
    prompt.append({"role": "user", "content": message})

    provider = "groq"
    try:
        answer, language = groq_completion(prompt)
    except RuntimeError as exc:
        message_text = str(exc)
        return jsonify({"error": message_text}), (503 if "not configured" in message_text else 502)
    if language_hint != "Auto-detected":
        language = language_hint
    topic = "farming_and_farmbridge"
    if not conversation:
        conversation = AIConversation(
            user_id=user.id,
            title=message[:160],
            language=language,
        )
        db.session.add(conversation)
    else:
        conversation.language = language
        conversation.updated_at = datetime.utcnow()
    db.session.add_all([
        AIMessage(conversation=conversation, role="user", content=message),
        AIMessage(conversation=conversation, role="assistant", content=answer),
    ])
    db.session.commit()

    return jsonify({
        "answer": answer,
        "topic": topic,
        "language": language,
        "provider": provider,
        "conversation": ai_conversation_dict(conversation),
        "disclaimer": "This is general agricultural guidance, not a substitute for local soil-test or agronomist advice."
    })


# ============================================================
# TRANSPORT PARTNERS + MATCHING
# ============================================================

@app.get("/api/transport/partners")
@jwt_required()
def transport_partners():
    location = (request.args.get("location") or "").lower()

    query = TransportPartner.query.filter_by(available=True)
    rows = query.order_by(TransportPartner.price.asc()).all()

    if location:
        local = [x for x in rows if location in (x.location or "").lower()]
        if local:
            rows = local

    result = [
            {
                "id": p.id,
                "name": p.name,
                "phone": p.phone,
                "vehicleType": p.vehicle_type,
                "capacityKg": p.capacity_kg,
                "location": p.location,
                "price": p.price,
                "available": bool(p.available)
            }
            for p in rows
        ]
    for partner in DeliveryPartner.query.filter_by(availability="available").all():
        if location and location not in (partner.service_location or "").casefold():
            continue
        result.append({"id": f"dp:{partner.id}", "partnerType": "delivery_portal", "name": partner.name,
            "phone": None, "vehicleType": partner.vehicle_type, "capacityKg": partner.capacity_kg,
            "location": partner.service_location, "price": partner.per_kg_rate if partner.pricing_method == "per_kg" else None,
            "pricingMethod": partner.pricing_method, "available": True})
    return jsonify({"partners": result})


@app.post("/api/transport/match")
@role_required("farmer")
def transport_match():
    data = request.get_json(silent=True) or {}

    from_location = (data.get("from") or data.get("location") or "").casefold().strip()
    try: weight = float(data.get("totalWeight", 0) or 0)
    except (TypeError, ValueError): return jsonify({"error": "Weight must be a valid number in kilograms"}), 400
    if not math.isfinite(weight) or weight <= 0: return jsonify({"error": "Weight must be greater than zero kilograms"}), 400

    rows = TransportPartner.query.filter_by(available=True).all()

    # Simple deterministic matching: local first, then enough capacity, then price.
    scored = []
    for p in rows:
        score = 0
        locality = (p.location or "").casefold().strip()
        if not from_location or not locality or (from_location not in locality and locality not in from_location):
            continue
        if p.capacity_kg is None or p.capacity_kg < weight:
            continue
        score += 100
        score += 50
        score -= float(p.price or 0) / 10000
        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)

    portal_matches = []
    farmer = current_user()
    for partner in DeliveryPartner.query.filter_by(availability="available").all():
        locality = (partner.service_location or "").casefold().strip()
        if not from_location or not locality or partner.capacity_kg is None or (locality not in from_location and from_location not in locality) or weight <= 0 or weight > partner.capacity_kg:
            continue
        distance = transport_distance_km(farmer.latitude, farmer.longitude,
                                         partner.service_latitude, partner.service_longitude)
        if partner.service_radius_km is not None and (distance is None or distance > partner.service_radius_km):
            continue
        portal_matches.append({"id": f"dp:{partner.id}", "partnerType": "delivery_portal", "name": partner.name,
            "vehicleType": partner.vehicle_type, "capacityKg": partner.capacity_kg, "location": partner.service_location,
            "price": transport_estimate(partner, weight, distance),
            "pricingMethod": partner.pricing_method, "distanceKm": distance, "available": True})

    return jsonify({
        "matches": portal_matches + [
            {
                "id": p.id,
                "name": p.name,
                "phone": p.phone,
                "vehicleType": p.vehicle_type,
                "capacityKg": p.capacity_kg,
                "location": p.location,
                "price": p.price,
                "available": bool(p.available)
            }
            for _, p in scored[:5]
        ]
    })


@app.post("/api/orders/<int:order_id>/transport")
@role_required("farmer")
def assign_transport(order_id):
    order = db.session.get(Order, order_id)
    if not order or order.farmer_id != current_user().id:
        return jsonify({"error": "Order not found"}), 404
    return jsonify({"error": "Transport matching and partner assignment are automatic. Eligible partners can accept from their dashboard."}), 409


# ============================================================
# SHARED ORDER / TRANSPORT SHARING
# ============================================================

@app.post("/api/orders/<int:order_id>/share")
@role_required("farmer")
def share_order(order_id):
    o = db.session.get(Order, order_id)
    if not o or o.farmer_id != current_user().id:
        return jsonify({"error": "Order not found"}), 404

    data = request.get_json(silent=True) or {}
    other_farmer_id = data.get("farmerId")

    if other_farmer_id:
        other = db.session.get(User, int(other_farmer_id))
        if not other or other.role != "farmer":
            return jsonify({"error": "Farmer not found"}), 404
    else:
        other = None

    row = SharedOrder(
        order_id=o.id,
        farmer_id=current_user().id,
        shared_with_farmer_id=other.id if other else None,
        status="shared"
    )
    db.session.add(row)

    if other:
        add_notification(
            other.id,
            "Shared transport order",
            f"Farmer {current_user().name} shared order ORD{o.id:05d} with you."
        )

    db.session.commit()
    return jsonify({"message": "Order shared", "sharedOrderId": row.id})


@app.get("/api/orders/shared")
@role_required("farmer")
def shared_orders():
    u = current_user()

    rows = SharedOrder.query.filter(
        or_(
            SharedOrder.farmer_id == u.id,
            SharedOrder.shared_with_farmer_id == u.id
        )
    ).order_by(SharedOrder.created_at.desc()).all()

    return jsonify({
        "sharedOrders": [
            {
                "id": r.id,
                "order": order_dict(db.session.get(Order, r.order_id)),
                "status": r.status,
                "createdAt": r.created_at.isoformat()
            }
            for r in rows
        ]
    })


# ============================================================
# SEED DEMO DATA
# ============================================================

def seed_demo():
    seed_transport()

    if User.query.count() == 0:
        consumer = User(
            name="Demo Consumer",
            email="consumer@farmbridge.local",
            password_hash=generate_password_hash("demo123"),
            role="consumer",
            phone="9000000010",
            location="Bangalore, Karnataka",
            verified=True
        )
        farmer = User(
            name="Ramesh H.",
            email="farmer@farmbridge.local",
            password_hash=generate_password_hash("demo123"),
            role="farmer",
            phone="9000000011",
            location="Mysore, Karnataka",
            farm_name="Green Valley Farm",
            experience_years=12,
            verified=True
        )
        db.session.add_all([consumer, farmer])
        db.session.commit()

    if Product.query.count() == 0:
        farmer = User.query.filter_by(email="farmer@farmbridge.local").first()
        products = [
            Product(
                name="Tomato", category="vegetables",
                description="Fresh farm tomatoes", price=30, unit="kg",
                stock=100, location="Mysore, Karnataka",
                farmer_id=farmer.id
            ),
            Product(
                name="Brinjal", category="vegetables",
                description="Fresh brinjal", price=25, unit="kg",
                stock=60, location="Mandya, Karnataka",
                farmer_id=farmer.id
            ),
            Product(
                name="Green Chilli", category="spices",
                description="Fresh green chilli", price=40, unit="kg",
                stock=50, location="Chikkaballapur",
                farmer_id=farmer.id
            ),
            Product(
                name="Carrot", category="vegetables",
                description="Fresh carrots", price=28, unit="kg",
                stock=80, location="Kolar, Karnataka",
                farmer_id=farmer.id
            ),
            Product(
                name="Potato", category="vegetables",
                description="Farm potatoes", price=26, unit="kg",
                stock=120, location="Haveri, Karnataka",
                farmer_id=farmer.id
            ),
            Product(
                name="Onion", category="vegetables",
                description="Fresh onions", price=22, unit="kg",
                stock=150, location="Belagavi, Karnataka",
                farmer_id=farmer.id
            ),
            Product(
                name="Organic Carrot", category="organic",
                description="Organic farm carrots", price=35, unit="kg",
                stock=40, location="Kolar, Karnataka",
                farmer_id=farmer.id
            ),
            Product(
                name="Mango", category="fruits",
                description="Seasonal farm mangoes", price=90, unit="kg",
                stock=70, location="Mysore, Karnataka",
                farmer_id=farmer.id
            ),
        ]
        db.session.add_all(products)
        db.session.commit()

    if CropRecord.query.count() == 0:
        farmer = User.query.filter_by(email="farmer@farmbridge.local").first()
        db.session.add_all([
            CropRecord(
                farmer_id=farmer.id, crop_name="Tomato",
                category="vegetables", season="Kharif", year=2025,
                area_acres=2.5, yield_amount=25.4,
                average_price=18.6, total_income=230000,
                soil_type="Loamy", soil_ph=6.5,
                notes="Good yield with drip irrigation."
            ),
            CropRecord(
                farmer_id=farmer.id, crop_name="Potato",
                category="vegetables", season="Rabi", year=2024,
                area_acres=2.0, yield_amount=19.2,
                average_price=22.0, total_income=185000,
                soil_type="Sandy Loam", soil_ph=6.2,
                notes="Good drainage produced better results."
            )
        ])
        db.session.commit()


# ============================================================
# ERROR HANDLERS + STARTUP
# ============================================================

@app.errorhandler(404)
def not_found(_):
    return jsonify({"error": "API route not found"}), 404


@app.errorhandler(413)
def request_too_large(_):
    return jsonify({"error": "Request is too large. Compress the product image and try again."}), 413


@app.errorhandler(500)
def server_error(_):
    db.session.rollback()
    return jsonify({"error": "Internal server error"}), 500


def ensure_order_payment_columns():
    columns = {column["name"] for column in inspect(db.engine).get_columns("orders")}
    additions = {
        "payment_method": "VARCHAR(40)",
        "payment_status": "VARCHAR(30)",
        "checkout_id": "VARCHAR(80)",
        "delivery_partner_id": "INTEGER REFERENCES delivery_partners(id)",
        "pickup_latitude": "FLOAT",
        "pickup_longitude": "FLOAT",
    }
    with db.engine.begin() as connection:
        for name, sql_type in additions.items():
            if name not in columns:
                connection.execute(db.text(
                    f"ALTER TABLE orders ADD COLUMN {name} {sql_type}"
                ))
        connection.execute(db.text(
            "CREATE INDEX IF NOT EXISTS ix_orders_checkout_id ON orders (checkout_id)"
        ))
        connection.execute(db.text(
            "CREATE INDEX IF NOT EXISTS ix_orders_delivery_partner_id ON orders (delivery_partner_id)"
        ))


def ensure_transport_coordinate_columns():
    additions = {
        "users": {"latitude": "FLOAT", "longitude": "FLOAT"},
        "delivery_partners": {"service_latitude": "FLOAT", "service_longitude": "FLOAT"},
    }
    with db.engine.begin() as connection:
        for table, table_additions in additions.items():
            columns = {column["name"] for column in inspect(db.engine).get_columns(table)}
            for name, sql_type in table_additions.items():
                if name not in columns:
                    connection.execute(db.text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))
        request_columns = {column["name"] for column in inspect(db.engine).get_columns("partner_transport_requests")}
        if "expires_at" not in request_columns:
            connection.execute(db.text("ALTER TABLE partner_transport_requests ADD COLUMN expires_at TIMESTAMP"))


def ensure_partner_optional_registration_columns():
    if db.engine.dialect.name != "postgresql":
        return
    columns = {column["name"]: column["nullable"] for column in inspect(db.engine).get_columns("delivery_partners")}
    optional_columns = (
        "mobile", "email", "address", "city", "pincode", "vehicle_type",
        "vehicle_registration", "capacity_kg", "license_number", "pricing_method",
        "service_radius_km", "service_location",
    )
    with db.engine.begin() as connection:
        for name in optional_columns:
            if name in columns and not columns[name]:
                connection.execute(db.text(
                    f"ALTER TABLE delivery_partners ALTER COLUMN {name} DROP NOT NULL"
                ))


with app.app_context():
    db.create_all()
    ensure_order_payment_columns()
    ensure_partner_optional_registration_columns()
    ensure_transport_coordinate_columns()
    if os.getenv("SEED_DEMO_DATA", "").strip().lower() == "true":
        seed_demo()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print("==============================================")
    print(" FarmBridge AI - PostgreSQL Backend")
    print(" API: http://localhost:%s" % port)
    print(" Health: http://localhost:%s/api/health" % port)
    print("==============================================")
    app.run(host="0.0.0.0", port=port, debug=False)
