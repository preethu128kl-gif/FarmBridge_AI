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
- Fertility: GET `/api/crops/fertility`
- AI farming assistant: POST `/api/ai/farming-assistant`
- Transport partners: GET `/api/transport/partners`
- AI-style transport matching: POST `/api/transport/match`
- Assign transport: POST `/api/orders/<id>/transport`
- Share order: POST `/api/orders/<id>/share`
- Shared orders: GET `/api/orders/shared`

## Frontend integration

The React frontend uses this Flask API for authentication, products, cart,
wishlist, checkout, orders, farmer tools, and the farming assistant. Product
images uploaded by farmers are compressed in the browser and persisted in the
existing PostgreSQL `products.image` text column. Product categories are inferred
from recognized English/Kannada names; ambiguous names require a correction.

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
never be added to frontend environment variables. Without it, the existing
local farming guidance remains available.

Google sign-in is not implemented or simulated. The frontend option remains
disabled until a backend OAuth flow is configured. Create a Google OAuth 2.0
Web client and register `http://localhost:5000/api/auth/google/callback` as its
authorized redirect URI. Configure `GOOGLE_CLIENT_ID` and
`GOOGLE_CLIENT_SECRET` in the backend environment, implement and test that
callback, and only then enable the frontend option. Use the deployment's HTTPS
callback URL outside local development. Never expose the client secret to the
browser.

This project also does not connect a real payment gateway, map service, or
SMS/OTP provider; demo payments remain simulations.

## Production note

For deployment, use environment variables, HTTPS, a managed PostgreSQL database,
a production WSGI server such as Gunicorn, and a proper secret. Do not commit `.env`.
