# FarmBridge AI Frontend → Backend Map

This document is the implementation checklist for connecting the current React UI.

## Consumer

Landing role buttons
→ route to login/register
→ POST `/api/auth/login` or `/api/auth/register`

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
  "message": "How can I improve soil fertility?"
}

Previous Year Data
→ GET `/api/crops/previous-year`

Save crop record
→ POST `/api/crops/previous-year`

Crop report
→ GET `/api/crops/summary`

Fertility
→ GET `/api/crops/fertility?soilType=Loamy&ph=6.5`

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
