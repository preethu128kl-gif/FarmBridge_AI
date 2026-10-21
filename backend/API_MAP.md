# FarmBridge AI Frontend → Backend Map

This document is the implementation checklist for connecting the current React UI.

## Consumer

Landing role buttons
→ route to login/register
→ POST `/api/auth/login` or `/api/auth/register`

Consumer AI assistant
→ POST `/api/ai/farming-assistant` using the signed-in user's JWT
→ reuses the Groq configuration shared with the farmer assistant

Consumer search box
→ GET `/api/products?search=<query>`

Consumer category buttons
→ GET `/api/products?category=<category>`

Product card Add to Cart
→ POST `/api/cart`
body:
{
  "productId": 1,
  "quantity": 1
}

Product Buy
→ login first
→ add to cart
→ POST `/api/orders`
body: `{ "deliveryAddress": "...", "paymentMethod": "COD", "checkoutId": "..." }`
`paymentMethod` and `checkoutId` are optional for older clients; omitted payment method defaults to COD.
→ accepted methods: `COD`, `GOOGLE_PAY_DEMO`, `PHONEPE_DEMO`, `PAYTM_DEMO`, `CARD_DEMO`
→ COD is stored as `PENDING`; successful UPI/card simulations are stored as `PAID_DEMO`
→ `checkoutId` makes retries idempotent; demo methods never call a payment gateway

Heart
→ POST/DELETE `/api/wishlist`

Cart count
→ GET `/api/cart`

My Orders
→ GET `/api/orders`

Track Order
→ GET `/api/orders/track/ORD00001`

Bell
→ GET `/api/notifications`

## Farmer

Farmer login
→ POST `/api/auth/login` with `"role":"farmer"`

Dashboard
→ GET `/api/farmer/dashboard`

My Products
→ GET `/api/farmer/products`

Add Product form
→ POST `/api/products`
→ category is inferred from supported English/Kannada product names; an uncertain
  product requires an explicit category correction
→ optional compressed JPEG/PNG/WebP image is stored in PostgreSQL's existing
  `products.image` text column and returned as both `image` and `image_url`

Edit Product
→ PUT `/api/products/<id>`

Remove Product
→ DELETE `/api/products/<id>`

Orders
→ GET `/api/orders`

Order status buttons
→ PATCH `/api/orders/<id>/status`

Deliveries
→ GET `/api/farmer/deliveries`

AI Assistant
→ POST `/api/ai/farming-assistant`
body:
{
  "message": "How can I improve soil fertility?",
  "conversationId": 1
}
→ GET `/api/ai/conversations` for the signed-in user's history
→ GET `/api/ai/conversations/<id>` to load a conversation
→ DELETE `/api/ai/conversations/<id>` to remove a conversation

Set `GROQ_API_KEY` in `backend/.env` to enable Groq responses. The key is only
read by Flask; without it, the existing local farming guidance remains available.

Previous Year Data
→ GET `/api/crops/previous-year`

Save crop record
→ POST `/api/crops/previous-year`

Crop report
→ GET `/api/crops/summary`

Transport Partners
→ GET `/api/transport/partners`

Transport Matching
→ POST `/api/transport/match`

Assign Transport
→ POST `/api/orders/<id>/transport`

Shared Orders
→ POST `/api/orders/<id>/share`
→ GET `/api/orders/shared`

Profile
→ GET/PUT `/api/profile`

Logout
→ frontend removes JWT token and returns to landing.

## Google sign-in

Google OAuth is intentionally not enabled or simulated. The frontend displays a
disabled, clearly labelled integration point. To enable it, configure a Google
OAuth 2.0 Web client with the authorized redirect URI
`http://localhost:5000/api/auth/google/callback`, provide its client ID and
secret to the backend as `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, and
implement/enable the backend callback before making the frontend option active.
For deployment, use the HTTPS callback registered for that deployment. Never
put the client secret in frontend environment variables.
