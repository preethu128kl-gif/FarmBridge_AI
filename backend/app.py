import os
import json
import uuid
import base64
import re
import unicodedata
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
from werkzeug.security import generate_password_hash, check_password_hash

load_dotenv()

app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})
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
app.config["JWT_SECRET_KEY"] = os.getenv(
    "JWT_SECRET_KEY", "CHANGE_THIS_SECRET_IN_ENV"
)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=7)

db = SQLAlchemy(app)
jwt = JWTManager(app)


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
    transport_partner_name = db.Column(db.String(160))
    from_location = db.Column(db.String(255))
    to_location = db.Column(db.String(255))
    total_weight = db.Column(db.Float, default=0)
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
    return {
        "id": p.id,
        "name": p.name,
        "category": p.category,
        "description": p.description,
        "price": p.price,
        "unit": p.unit,
        "stock": p.stock,
        "image": p.image,
        "location": p.location,
        "farmerId": p.farmer_id,
        "farmerName": p.farmer.name if p.farmer else None,
        "farmerVerified": bool(p.farmer.verified) if p.farmer else False,
        "isActive": bool(p.is_active),
        "createdAt": p.created_at.isoformat() if p.created_at else None,
    }


def order_dict(o):
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
        "transportPartnerId": o.transport_partner_id,
        "transportPartner": o.transport_partner_name,
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
    return db.session.get(User, int(identity))


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
        return None

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

@app.post("/api/products")
@role_required("farmer")
def create_product():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name") or "").strip()
    supplied_category = str(data.get("category") or "").strip().casefold()
    category = (
        supplied_category
        if supplied_category in PRODUCT_CATEGORIES
        else infer_product_category(name)
    )

    if not name or data.get("price") is None:
        return jsonify({"error": "name and price are required"}), 400
    if not category:
        return jsonify({
            "error": "Could not confidently categorize this product. Please choose its consumer category.",
            "categoryRequired": True,
        }), 400
    image_error = validate_product_image(data.get("image"))
    if image_error:
        return jsonify({"error": image_error}), 400

    p = Product(
        name=name,
        category=category,
        description=data.get("description", ""),
        price=float(data["price"]),
        unit=data.get("unit", "kg"),
        stock=float(data.get("stock", 0)),
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
            )
            db.session.add(order)
            db.session.flush()

            total = 0
            weight = 0

            for ci in items:
                if not ci.product or not ci.product.is_active:
                    raise ValueError("A product in your cart is no longer available.")
                if ci.quantity > ci.product.stock:
                    raise ValueError(f"Not enough stock for {ci.product.name}")

                line = ci.quantity * ci.product.price
                total += line
                weight += ci.quantity
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
            order.total_weight = weight
            add_tracking(order, "placed", "Order placed successfully.")
            add_notification(
                farmer_id,
                "New customer order",
                f"Order ORD{order.id:05d} has been placed."
            )
            created.append(order)

        db.session.commit()
    except Exception as exc:
        db.session.rollback()
        return jsonify({"error": str(exc)}), 400

    return jsonify({
        "message": "Order placed successfully",
        "orders": [order_dict(o) for o in created]
    }), 201


@app.get("/api/orders")
@jwt_required()
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


@app.get("/api/orders/track/<string:order_code>")
def track_order(order_code):
    code = order_code.upper().replace("#", "").replace("ORD", "")
    if not code.isdigit():
        return jsonify({"error": "Invalid order ID"}), 400

    o = db.session.get(Order, int(code))
    if not o:
        return jsonify({"error": "Order not found"}), 404

    return jsonify({"order": order_dict(o)})


@app.patch("/api/orders/<int:order_id>/status")
@role_required("farmer")
def update_order_status(order_id):
    o = db.session.get(Order, order_id)
    if not o or o.farmer_id != current_user().id:
        return jsonify({"error": "Order not found"}), 404

    data = request.get_json(silent=True) or {}
    status = data.get("status")

    allowed = {
        "placed", "confirmed", "transport_assigned",
        "out_for_delivery", "delivered", "cancelled"
    }
    if status not in allowed:
        return jsonify({"error": "Invalid order status"}), 400

    o.status = status
    add_tracking(o, status, data.get("note", ""))

    add_notification(
        o.consumer_id,
        "Order updated",
        f"Order ORD{o.id:05d}: {STATUS_LABELS.get(status, status)}"
    )
    db.session.commit()

    return jsonify({"message": "Order status updated", "order": order_dict(o)})


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

    prompt = [
        {
            "role": "system",
            "content": (
                "You are FarmBridge AI, a practical farming assistant. " + language_instruction + " "
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

    provider = "groq" if os.getenv("GROQ_API_KEY", "").strip() else "local"
    if provider == "groq":
        try:
            answer, language = groq_completion(prompt)
        except RuntimeError as exc:
            return jsonify({"error": str(exc)}), 502
        if language_hint != "Auto-detected":
            language = language_hint
        topic = "farming"
    else:
        q = message.lower()

        if any(x in q for x in ["fertility", "soil", "fertilizer", "ಗೊಬ್ಬರ", "ಮಣ್ಣು"]):
            answer = (
                "For soil fertility, start with a soil test for pH and nutrients. "
                "Add suitable organic matter and use fertilizer according to the crop "
                "and soil-test recommendation instead of guessing a dose."
            )
            topic = "soil_fertility"
        elif any(x in q for x in ["water", "irrigation", "ನೀರು"]):
            answer = (
                "Irrigation depends on crop, soil and weather. Check soil moisture, "
                "avoid waterlogging and use efficient irrigation where practical."
            )
            topic = "irrigation"
        elif any(x in q for x in ["pest", "insect", "disease", "ಕೀಟ", "ರೋಗ"]):
            answer = (
                "Identify the pest or disease first. Prefer integrated pest management "
                "and use only approved crop-protection products at the recommended dose."
            )
            topic = "pest_disease"
        elif any(x in q for x in ["tomato", "ಟೊಮ್ಯಾಟೊ"]):
            answer = (
                "For tomatoes, focus on balanced nutrition, good drainage, regular "
                "monitoring for leaf diseases and timely irrigation. Fertilizer quantity "
                "should be based on crop stage and soil-test results."
            )
            topic = "tomato"
        elif any(x in q for x in ["chilli", "ಚಿಲ್ಲಿ", "ಮೆಣಸಿನ"]):
            answer = (
                "For chilli, monitor leaf spots, sucking pests and moisture stress. "
                "Remove severely affected material and use locally approved management "
                "recommendations when needed."
            )
            topic = "chilli"
        elif any(x in q for x in ["maize", "ಮೆಕ್ಕೆಜೋಳ"]):
            answer = (
                "Maize sowing time depends on your local season and rainfall. Choose "
                "a locally recommended variety and ensure adequate soil moisture at sowing."
            )
            topic = "maize"
        else:
            answer = (
                "I can help with crops, soil fertility, irrigation, pests, diseases, "
                "fertilizer basics and previous-year crop data. Tell me the crop and "
                "the problem you are seeing."
            )
            topic = "general"
        language = "English"

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

    return jsonify({
        "partners": [
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
    })


@app.post("/api/transport/match")
@role_required("farmer")
def transport_match():
    data = request.get_json(silent=True) or {}

    from_location = (data.get("from") or data.get("location") or "").lower()
    weight = float(data.get("totalWeight", 0) or 0)

    rows = TransportPartner.query.filter_by(available=True).all()

    # Simple deterministic matching: local first, then enough capacity, then price.
    scored = []
    for p in rows:
        score = 0
        if from_location and from_location in (p.location or "").lower():
            score += 100
        if p.capacity_kg >= weight:
            score += 50
        else:
            score -= 50
        score -= p.price / 10000
        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)

    return jsonify({
        "matches": [
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
    o = db.session.get(Order, order_id)
    if not o or o.farmer_id != current_user().id:
        return jsonify({"error": "Order not found"}), 404

    data = request.get_json(silent=True) or {}
    partner = db.session.get(TransportPartner, data.get("transportPartnerId"))

    if not partner or not partner.available:
        return jsonify({"error": "Transport partner not available"}), 400
    if o.total_weight > partner.capacity_kg:
        return jsonify({"error": "Transport capacity is too small"}), 400

    o.transport_partner_id = partner.id
    o.transport_partner_name = partner.name
    o.status = "transport_assigned"

    add_tracking(
        o, "transport_assigned",
        f"Transport assigned: {partner.name}"
    )
    add_notification(
        o.consumer_id,
        "Transport assigned",
        f"{partner.name} has been assigned to order ORD{o.id:05d}."
    )

    db.session.commit()
    return jsonify({"message": "Transport assigned", "order": order_dict(o)})


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


with app.app_context():
    db.create_all()
    ensure_order_payment_columns()
    seed_demo()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print("==============================================")
    print(" FarmBridge AI - PostgreSQL Backend")
    print(" API: http://localhost:%s" % port)
    print(" Health: http://localhost:%s/api/health" % port)
    print("==============================================")
    app.run(host="0.0.0.0", port=port, debug=False)
