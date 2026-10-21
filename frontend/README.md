# FarmBridge AI – Clean Reference-Based React Frontend

This frontend uses React + Vite + Lucide icons. The reference screenshots are recreated with JSX/CSS; the supplied photos are used only in the requested hero/banner areas.

## Image mapping
- `landing-farm.jpg` → starting role-selection background
- `consumer-hero.jpg` → consumer dashboard hero/banner only
- `farmer-hero.jpg` → farmer dashboard hero/banner only
- `consumer-login-hero.jpg` → consumer login hero/banner only
- `farmer-login-hero.jpg` → farmer login hero/banner only

## Run
```bash
npm install
npm run dev
```

Default language is Kannada. Use the language button to switch Kannada → English.

## Main interactions
- Consumer/Farmer role selection
- Login/Register screens with back navigation
- Consumer search filters products
- Consumer category navigation opens category-specific product views
- Product names and descriptions preserve English or Kannada text; categories are inferred safely from known product names
- Farmer product images are compressed, validated, and stored by the PostgreSQL backend
- About, Features, How It Works, and Contact navigation pages
- Add to Cart / Buy Now routes to Consumer Login
- Consumer and Farmer AI assistants reuse the secured backend Groq integration
- Farmer sidebar opens Dashboard, My Products, Add Product, Orders, Deliveries, AI Assistant, Previous Year Data, Transport, Matching, Earnings and Profile views
- Farmer logout returns to the starting interface
- Google sign-in is clearly marked unavailable until backend OAuth credentials and callback are configured; see `../backend/README.md`
