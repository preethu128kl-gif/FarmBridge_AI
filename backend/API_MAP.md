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
read by Flask; without it, the endpoint returns a configuration error instead
of presenting canned text as an AI response. Pass `uiLanguage` as `en` or `kn`
to follow the active site language when a message's language is otherwise ambiguous.

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

Transport Requests
→ created automatically in PostgreSQL during consumer checkout
→ eligible delivery partners poll `GET /api/partner/requests`
→ assigned partner accepts through `POST /api/partner/requests/<id>/accept`
→ a participant may retry matching with `POST /api/orders/<id>/transport/retry`
→ partner request expires after 24 hours if not accepted

Pickup radius and per-kilometre pricing use farmer and partner coordinates.
Farmers enter pickup coordinates in Profile; partners enter service base
coordinates during registration. When coordinates or distance are unavailable,
radius-bound partners are not matched and the fare is left unavailable.

Shared Orders
→ POST `/api/orders/<id>/share`
→ GET `/api/orders/shared`

Profile
→ GET/PUT `/api/profile`

Logout
→ frontend removes JWT token and returns to landing.

## Google sign-in

Google Identity Services sends an ID token to `POST /api/auth/google`. Flask
verifies its signature using Google's published keys and checks the audience,
issuer and verified email before creating a FarmBridge session. Set the same
Google OAuth Web client ID as `GOOGLE_CLIENT_ID` in `backend/.env` and
`VITE_GOOGLE_CLIENT_ID` in `frontend/.env`; add the frontend host to the OAuth
client's authorized JavaScript origins. This flow does not use a redirect
callback or require a client secret. Keep the backend `JWT_SECRET_KEY` private.
