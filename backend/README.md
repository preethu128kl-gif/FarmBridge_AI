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

## Important: this backend is not yet connected to the React frontend

The current React `main.jsx` contains demo/static product, order, farmer and dashboard values.
This backend makes those features persistent. The next step is to replace those demo values
with `fetch()`/Axios API calls from React.

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

The React frontend should store the returned token after login and attach it to
protected API requests.

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

## What this backend does not pretend to implement

The current frontend does not contain a real payment gateway, real map service,
real external AI model, SMS/OTP verification, or image-upload storage.
Therefore this backend does not invent those integrations.

The farming assistant endpoint is a safe rule-based starter. A real AI provider
can be connected later.

## Production note

For deployment, use environment variables, HTTPS, a managed PostgreSQL database,
a production WSGI server such as Gunicorn, and a proper secret. Do not commit `.env`.
