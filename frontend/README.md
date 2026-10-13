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
- Add to Cart / Buy Now routes to Consumer Login
- Farmer sidebar opens Dashboard, My Products, Add Product, Orders, Deliveries, AI Assistant, Crop/Fertility, Previous Year Data, Transport, Matching, Earnings and Profile views
- Farmer logout returns to the starting interface
