# FarmBridge AI — Complete PostgreSQL Backend

This backend is mapped to the current FarmBridge AI React frontend features.

## Technology

- Python
- Flask
- PostgreSQL
- SQLAlchemy
- JWT authentication
- Flask-CORS

## Frontend features mapped to backend

### Landing / roles
The landing screen itself is frontend UI. Authentication and role-specific data are handled by:
- POST `/api/auth/register`
- POST `/api/auth/login`
- GET `/api/auth/me`

### Consumer
- Product search: GET `/api/products?search=tomato`
- Category filtering: GET `/api/products?category=vegetables`
- Product details: GET `/api/products/<id>`
- Farmer list: GET `/api/farmers`
- Categories: GET `/api/categories`
- Cart: GET/POST/PATCH/DELETE `/api/cart...`
- Wishlist/heart: GET/POST/DELETE `/api/wishlist...`
- Orders: POST/GET `/api/orders`
- Track order: GET `/api/orders/track/ORD00001`
- Notifications: GET `/api/notifications`

### Farmer
- Dashboard: GET `/api/farmer/dashboard`
- My Products: GET `/api/farmer/products`
- Add Product: POST `/api/products`
- Update Product: PUT `/api/products/<id>`
- Remove Product: DELETE `/api/products/<id>`
- Orders: GET `/api/orders`
- Update order: PATCH `/api/orders/<id>/status`
- Deliveries: GET `/api/farmer/deliveries`
- Earnings: GET `/api/farmer/earnings`
- Profile: GET/PUT `/api/profile`
- Previous-year data: GET/POST `/api/crops/previous-year`
- Crop summary: GET `/api/crops/summary`
- AI farming assistant: POST `/api/ai/farming-assistant`
- Transport partners: GET `/api/transport/partners`
- AI-style transport matching: POST `/api/transport/match`
- Delivery requests are created automatically at checkout and accepted by the partner from `POST /api/partner/requests/<id>/accept`.
- Retry matching: POST `/api/orders/<id>/transport/retry`
- Share order: POST `/api/orders/<id>/share`
- Shared orders: GET `/api/orders/shared`

Previous Year Market Prices are not implemented. Adding them later will require
a verified market-price data source and its access/licensing configuration.

## Frontend integration

The React frontend uses this Flask API for authentication, products, cart,
wishlist, checkout, orders, farmer tools, and the farming assistant. Product
images uploaded by farmers are compressed in the browser and persisted in the
existing PostgreSQL `products.image` text column. Product categories are inferred
from recognized English and Kannada names; ambiguous names require a correction
instead of being silently misclassified. Product names and descriptions accept
Kannada and English text.

## PostgreSQL setup

Install PostgreSQL and pgAdmin.

Create a database named:

    farmbridge_ai

In pgAdmin Query Tool:

    CREATE DATABASE farmbridge_ai;

Then create `.env` from `.env.example`.

Example:

    PORT=5000
    DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/farmbridge_ai
    JWT_SECRET_KEY=put-a-long-secret-here
    CLIENT_URL=http://localhost:5173

If your password contains special URL characters, URL-encode them in the connection URL.

## Windows commands

Open this backend folder in VS Code Terminal:

    py -3.13 -m venv venv

Activate:

    .\venv\Scripts\activate

Install:

    python -m pip install -r requirements.txt

Run:

    python app.py

Test:

    http://localhost:5000/api/health

Expected:

    {"database":"connected","ok":true,"service":"FarmBridge AI API"}

Tables are created automatically by the backend.

## Demo accounts

After the first successful startup, demo data is inserted:

Consumer:
    consumer@farmbridge.local
    demo123

Farmer:
    farmer@farmbridge.local
    demo123

These are development/demo accounts only.

## Authentication header

For protected requests send:

    Authorization: Bearer YOUR_JWT_TOKEN

The React frontend stores the returned token and attaches it to protected API
requests. Passwords are stored as Werkzeug password hashes. Registration accepts
name, email, mobile number, password, and role; login accepts email or mobile
number plus password.

## Recommended React connection structure

Create:

    src/api.js

and centralize the backend URL:

    export const API_URL = "http://localhost:5000/api";

Then use:

    fetch(`${API_URL}/products`)

For protected requests:

    fetch(`${API_URL}/cart`, {
      headers: {
        Authorization: `Bearer ${localStorage.getItem("farmbridge_token")}`
      }
    })

## AI assistant and Google sign-in

Set `GROQ_API_KEY` in `backend/.env` to enable Groq-backed farming answers for
both signed-in consumers and farmers. The key is read only by Flask and must
never be added to frontend environment variables. Without it, the assistant
returns a clear configuration error and does not present canned answers as AI output.

Google sign-in uses Google Identity Services in the frontend and server-side
ID-token validation. Set the same OAuth Web client ID in `backend/.env` as
`GOOGLE_CLIENT_ID` and `frontend/.env` as `VITE_GOOGLE_CLIENT_ID`; configure
authorized JavaScript origins for your frontend host. Flask verifies the token
signature, audience, issuer and verified email. This flow does not use a
redirect callback or client secret. Existing email/mobile-password login
remains available.

Delivery partner accounts and farmer sales records are stored in additive
PostgreSQL tables. Partner document status remains `unverified`; no
document-review process is configured. Matching requires pickup and service
locality text plus sufficient vehicle capacity. When a service radius is set,
partners must provide service coordinates and farmers must enter pickup
coordinates in Profile. Matching uses their straight-line distance. Per-kilometre
fares use that distance as an estimate and remain unavailable if distance or
rate data is missing. Participants can retry matching; requests expire after
24 hours. Partner password reset requires SMTP configuration.

This project does not connect a real payment gateway; demo payments remain simulations. No map/geocoding service or SMS/OTP provider is configured.

## Production note

For deployment, use environment variables, HTTPS, a managed PostgreSQL database,
a production WSGI server such as Gunicorn, and a proper secret. Do not commit `.env`.
Demo records are not inserted on startup. Set `SEED_DEMO_DATA=true` only for an
empty development database where demo fixtures are wanted.
