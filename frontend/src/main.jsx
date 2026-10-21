import React, { useEffect, useMemo, useState } from "react";
import { apiRequest } from "./api";
import FarmingAssistant from "./FarmingAssistant";
import { createRoot } from "react-dom/client";
import {
  ArrowLeft, ArrowRight, Bell, Boxes, Check, ChevronDown, Globe2, Heart,
  Leaf, MapPin, Menu, MessageCircle, Search, ShoppingCart, ShieldCheck,
  Sparkles, Truck, UserRound, PackageCheck, BarChart3, Wheat, LogOut,
  Eye, EyeOff, Sprout, Plus, X, CircleDollarSign, ClipboardList, Package,
  BrainCircuit, History, Store, Apple, Carrot, Wheat as WheatIcon, Cookie,
  Milk, Droplets, Flower2, Stethoscope, RefreshCw
} from "lucide-react";
import "./styles.css";
import "./PaymentDemo.css";

import landingFarm from "./assets/landing-farm.jpg";
import consumerHero from "./assets/consumer-hero.jpg";
import tomato from "./assets/tomato.jpg";
import potato from "./assets/potato.jpg";
import onion from "./assets/onion.jpg";
import carrot from "./assets/carrot.jpg";
import cabbage from "./assets/cabbage.jpg";
import farmerHero from "./assets/farmer-hero.jpg";
import consumerLoginHero from "./assets/consumer-login-hero.jpg";
import farmerLoginHero from "./assets/farmer-login-hero.jpg";

const productImageFiles = import.meta.glob("../product-images/*.jpg", {
  eager: true,
  query: "?url",
  import: "default"
});
const productImageSources = Object.fromEntries(
  Object.entries(productImageFiles).map(([path, url]) => {
    const fileName = path.split("/").pop().replace(/\.jpg$/i, "");
    return [normalizeProductName(fileName), url];
  })
);
const productImages = Object.fromEntries(
  Object.entries(productImageSources).filter(([name]) => !/\s\(\d+\)$/.test(name))
);
productImages.turmeric = productImageSources["turmeric (2)"];
productImages.sunflower = productImageSources["sunflower (2)"];
const productImageAliases = {
  "bell pepper": "capsicum",
  eggplant: "brinjal",
  "green chili": "green chilli",
  tomatoes: "tomato"
};
const productImagePlaceholder = `data:image/svg+xml,${encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512"><rect width="512" height="512" fill="#f4f7f2"/><path d="M256 367c-39-63-38-137 4-211 42 74 43 148 4 211m-5-48c-42-44-91-58-147-43 38 57 87 74 147 56m10-13c40-42 88-56 143-41-37 55-84 71-143 54" fill="none" stroke="#82a779" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/></svg>'
)}`;

function normalizeProductName(name) {
  return String(name || "")
    .trim()
    .toLowerCase()
    .replace(/[_-]+/g, " ")
    .replace(/\s+/g, " ");
}

function productImage(product) {
  const savedImage =
    product && typeof product === "object"
      ? product.image_url || product.image
      : "";
  if (savedImage) return savedImage;

  const name = normalizeProductName(
    typeof product === "string" ? product : product?.name
  );
  return productImages[productImageAliases[name] || name] || productImagePlaceholder;
}

function ProductImage({ product, alt, className }) {
  const image = productImage(product);
  const localImage = productImage(
    typeof product === "string" ? product : { name: product?.name }
  );
  const [failedSource, setFailedSource] = useState("");
  useEffect(() => setFailedSource(""), [image, localImage]);
  const src = !failedSource
    ? image
    : failedSource === image && image !== localImage
      ? localImage
      : productImagePlaceholder;

  return (
    <img
      src={src}
      alt={alt}
      className={className}
      onError={() => setFailedSource(src)}
    />
  );
}

const T = {
  kn: {
    home:"ಮುಖಪುಟ", about:"ನಮ್ಮ ಬಗ್ಗೆ", features:"ವೈಶಿಷ್ಟ್ಯಗಳು", how:"ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ", contact:"ಸಂಪರ್ಕ",
    english:"English", kannada:"ಕನ್ನಡ", fresh:"ತಾಜಾ. ಸ್ಥಳೀಯ. ವಿಶ್ವಾಸಾರ್ಹ.", bringing:"ರೈತರನ್ನು ನಿಮ್ಮ", closer:"ಹತ್ತಿರಕ್ಕೆ ತರುತ್ತಿದ್ದೇವೆ",
    choose:"ನಮ್ಮೊಂದಿಗೆ ನಿಮ್ಮ ಪ್ರಯಾಣವನ್ನು ಆಯ್ಕೆ ಮಾಡಿ ಮತ್ತು ಉತ್ತಮ ಕೃಷಿ ಅನುಭವ ಪಡೆಯಿರಿ.", consumer:"ಗ್ರಾಹಕ", farmer:"ರೈತ",
    consumerDesc:"ರೈತರಿಂದ ನೇರವಾಗಿ ತಾಜಾ ಉತ್ಪನ್ನಗಳನ್ನು ಖರೀದಿಸಿ", farmerDesc:"ನಿಮ್ಮ ಫಾರ್ಮ್ ನಿರ್ವಹಿಸಿ, ಉತ್ಪನ್ನಗಳನ್ನು ಪಟ್ಟಿ ಮಾಡಿ ಮತ್ತು ವ್ಯವಹಾರ ಬೆಳೆಸಿ",
    continueConsumer:"ಗ್ರಾಹಕರಾಗಿ ಮುಂದುವರಿಯಿರಿ", continueFarmer:"ರೈತರಾಗಿ ಮುಂದುವರಿಯಿರಿ", freshHealthy:"ತಾಜಾ ಮತ್ತು ಆರೋಗ್ಯಕರ", natural:"100% ನೈಸರ್ಗಿಕ ಉತ್ಪನ್ನ",
    supportLocal:"ಸ್ಥಳೀಯ ರೈತರಿಗೆ ಬೆಂಬಲ", empower:"ರೈತರನ್ನು ಸಬಲಗೊಳಿಸಿ", safe:"ಸುರಕ್ಷಿತ ಮತ್ತು ವಿಶ್ವಾಸಾರ್ಹ", quality:"ನೀವು ನಂಬಬಹುದಾದ ಗುಣಮಟ್ಟ", aiPowered:"AI ಆಧಾರಿತ", smart:"ಸ್ಮಾರ್ಟ್ ಕೃಷಿ ಪರಿಹಾರಗಳು",
    search:"ಉತ್ಪನ್ನಗಳು, ರೈತರು, ವರ್ಗಗಳನ್ನು ಹುಡುಕಿ...", deliver:"ವಿತರಣೆ", location:"ಬೆಂಗಳೂರು, ಕರ್ನಾಟಕ", categories:"ಎಲ್ಲಾ ವರ್ಗಗಳು", shopCategory:"ವರ್ಗದ ಮೂಲಕ ಖರೀದಿ",
    vegetables:"ತಾಜಾ ತರಕಾರಿಗಳು", fruits:"ಹಣ್ಣುಗಳು", grains:"ಧಾನ್ಯಗಳು ಮತ್ತು ಬೇಳೆಕಾಳುಗಳು", spices:"ಮಸಾಲೆಗಳು", dairy:"ಹಾಲು ಮತ್ತು ಮೊಟ್ಟೆಗಳು", oils:"ಎಣ್ಣೆ ಮತ್ತು ತುಪ್ಪ", organic:"ಸಾವಯವ ಉತ್ಪನ್ನಗಳು", flowers:"ಹೂವು ಮತ್ತು ಎಲೆಗಳು", herbal:"ಔಷಧೀಯ ಮತ್ತು ನೈಸರ್ಗಿಕ",
    recommended:"ನಿಮಗಾಗಿ ಶಿಫಾರಸು", viewAll:"ಎಲ್ಲವನ್ನೂ ನೋಡಿ", orders:"ನನ್ನ ಆರ್ಡರ್‌ಗಳು", track:"ಆರ್ಡರ್ ಟ್ರ್ಯಾಕ್ ಮಾಡಿ", orderId:"ಆರ್ಡರ್ ID ನಮೂದಿಸಿ", trackBtn:"ಟ್ರ್ಯಾಕ್", assistant:"AI ಕೃಷಿ ಸಹಾಯಕ", ask:"ಕೃಷಿ, ಬೆಳೆಗಳು, ರಸಗೊಬ್ಬರಗಳು, ರೋಗಗಳು, ಮಣ್ಣು ಮತ್ತು ಇನ್ನಷ್ಟು ಬಗ್ಗೆ ಕೇಳಿ.",
    fertilizer:"ಟೊಮ್ಯಾಟೊಗೆ ಯಾವ ರಸಗೊಬ್ಬರ ಉತ್ತಮ?", leafSpot:"ಮೆಣಸಿನಕಾಯಿಯಲ್ಲಿ ಎಲೆ ಚುಕ್ಕೆ ನಿಯಂತ್ರಿಸುವುದು ಹೇಗೆ?", soil:"ಮಣ್ಣಿನ ಫಲವತ್ತತೆಯನ್ನು ಹೇಗೆ ಸುಧಾರಿಸುವುದು?", maize:"ಮೆಕ್ಕೆಜೋಳ ಬಿತ್ತಲು ಉತ್ತಮ ಸಮಯ?", question:"ನಿಮ್ಮ ಪ್ರಶ್ನೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ...",
    addCart:"ಕಾರ್ಟ್‌ಗೆ ಸೇರಿಸಿ", buy:"ಖರೀದಿಸಿ", shopNow:"ಈಗ ಖರೀದಿಸಿ", direct:"ರೈತರಿಂದ ನೇರವಾಗಿ", quality2:"ತಾಜಾ ಮತ್ತು ಗುಣಮಟ್ಟ", fast:"ವೇಗದ ವಿತರಣೆ", payment:"ಸುರಕ್ಷಿತ ಪಾವತಿ", returns:"ಸುಲಭ ರಿಟರ್ನ್", noMiddle:"ಮಧ್ಯವರ್ತಿಗಳಿಲ್ಲ", combo:"ಕಾಂಬೋ ಡೀಲ್", free:"ಉಚಿತ ವಿತರಣೆ", best:"ಅತ್ಯುತ್ತಮ ಬೆಲೆ",
    login:"ಲಾಗಿನ್", register:"ನೋಂದಣಿ", email:"ಇಮೇಲ್ / ಮೊಬೈಲ್", password:"ಪಾಸ್‌ವರ್ಡ್", name:"ಹೆಸರು", create:"ಖಾತೆ ರಚಿಸಿ", back:"ಹಿಂದಕ್ಕೆ", welcome:"ಮತ್ತೆ ಸ್ವಾಗತ", loginHint:"ನಿಮ್ಮ ಖಾತೆಗೆ ಮುಂದುವರಿಯಿರಿ", registerHint:"ಹೊಸ ಖಾತೆ ರಚಿಸಿ", noAccount:"ಖಾತೆ ಇಲ್ಲವೇ?", haveAccount:"ಈಗಾಗಲೇ ಖಾತೆ ಇದೆಯೇ?", demo:"ಡೆಮೊಗಾಗಿ ಯಾವುದೇ ವಿವರಗಳನ್ನು ಬಳಸಿ.",
    dashboard:"ಡ್ಯಾಶ್‌ಬೋರ್ಡ್", products:"ನನ್ನ ಉತ್ಪನ್ನಗಳು", addProduct:"ಆಡ್ ಪ್ರಾಡಕ್ಟ್", myOrders:"ಆರ್ಡರ್‌ಗಳು", deliveries:"ನನ್ನ ವಿತರಣೆಗಳು", cropInfo:"ಬೆಳೆ ಮತ್ತು ಫಲವತ್ತತೆ ಮಾಹಿತಿ", previous:"ಹಿಂದಿನ ವರ್ಷದ ಡೇಟಾ", transport:"ಸಾರಿಗೆ ಪಾಲುದಾರರು", matching:"ಸಾರಿಗೆ ಹೊಂದಾಣಿಕೆ", earnings:"ಆದಾಯ", profile:"ಪ್ರೊಫೈಲ್", logout:"ಲಾಗ್‌ಔಟ್", popular:"ಜನಪ್ರಿಯ ವರ್ಗಗಳು", available:"ಲಭ್ಯವಿರುವ ಉತ್ಪನ್ನಗಳು", cropData:"ಹಿಂದಿನ ವರ್ಷದ ಬೆಳೆ ಡೇಟಾ", selectCrop:"ಬೆಳೆ ಆಯ್ಕೆ ಮಾಡಿ", selectYear:"ವರ್ಷ ಆಯ್ಕೆ ಮಾಡಿ", report:"ವರದಿ ನೋಡಿ", avgYield:"ಸರಾಸರಿ ಇಳುವರಿ", avgPrice:"ಸರಾಸರಿ ಬೆಲೆ", production:"ಒಟ್ಟು ಉತ್ಪಾದನೆ", income:"ಒಟ್ಟು ಆದಾಯ", detailed:"ವಿವರವಾದ ವರದಿ", transportPartners:"ಸಾರಿಗೆ ಪಾಲುದಾರರು", transportMatch:"AI ಆಧಾರಿತ ಸಾರಿಗೆ ಹೊಂದಾಣಿಕೆ", assign:"ಸಾರಿಗೆ ನಿಯೋಜಿಸಿ", shared:"ಈ ಆರ್ಡರ್ ಅನ್ನು ಇನ್ನೊಬ್ಬ ರೈತನೊಂದಿಗೆ ಹಂಚಬಹುದು.", ordersTracking:"ನನ್ನ ಆರ್ಡರ್‌ಗಳು ಮತ್ತು ವಿತರಣೆ ಟ್ರ್ಯಾಕಿಂಗ್", placed:"ಆರ್ಡರ್ ಮಾಡಿದ", confirmed:"ದೃಢೀಕರಿಸಲಾಗಿದೆ", assigned:"ಸಾರಿಗೆ ನಿಯೋಜಿಸಲಾಗಿದೆ", out:"ವಿತರಣೆಗೆ ಹೊರಟಿದೆ", delivered:"ವಿತರಿಸಲಾಗಿದೆ", select:"ಆಯ್ಕೆ", availableYes:"ಲಭ್ಯವಿದೆ", from:"ಇಂದ", to:"ಗೆ", totalWeight:"ಒಟ್ಟು ತೂಕ", deliveryDate:"ವಿತರಣಾ ದಿನಾಂಕ", viewShared:"ಹಂಚಿದ ಆರ್ಡರ್‌ಗಳನ್ನು ನೋಡಿ"
  },
  en: {}
};
T.en = {
  home:"Home", about:"About Us", features:"Features", how:"How It Works", contact:"Contact", english:"English", kannada:"ಕನ್ನಡ", fresh:"Fresh. Local. Reliable.", bringing:"Bringing Farms", closer:"Closer to You", choose:"Choose your journey with us and experience the best of farming.", consumer:"Consumer", farmer:"Farmer", consumerDesc:"Shop fresh produce directly from farmers", farmerDesc:"Manage your farm, list products & grow your business", continueConsumer:"Continue as Consumer", continueFarmer:"Continue as Farmer", freshHealthy:"Fresh & Healthy", natural:"100% Natural Produce", supportLocal:"Support Local", empower:"Empowering Farmers", safe:"Safe & Reliable", quality:"Quality You Can Trust", aiPowered:"AI Powered", smart:"Smart Farming Solutions", search:"Search for products, farmers, categories...", deliver:"Deliver to", location:"Bangalore, Karnataka", categories:"All Categories", shopCategory:"Shop by Category", vegetables:"Fresh Vegetables", fruits:"Fruits", grains:"Grains & Pulses", spices:"Spices & Masalas", dairy:"Dairy & Eggs", oils:"Oils & Ghee", organic:"Organic Products", flowers:"Flower & Leaves", herbal:"Herbal & Natural", recommended:"Recommended for You", viewAll:"View All", orders:"My Orders", track:"Track Your Order", orderId:"Enter Order ID", trackBtn:"Track", assistant:"AI Farming Assistant", ask:"Ask me anything about farming, crops, fertilizers, diseases, soil, and more.", fertilizer:"Which fertilizer is best for tomatoes?", leafSpot:"How to control leaf spot in chili?", soil:"How to improve soil fertility?", maize:"Best time to sow maize?", question:"Type your question...", addCart:"Add to Cart", buy:"Buy Now", shopNow:"Shop Now", direct:"Direct from Farmers", quality2:"Fresh & Quality", fast:"Fast Delivery", payment:"Secure Payment", returns:"Easy Returns", noMiddle:"No Middlemen", combo:"Combo Deal", free:"Free Delivery", best:"Best Prices", login:"Login", register:"Register", email:"Email / Mobile", password:"Password", name:"Name", create:"Create Account", back:"Back", welcome:"Welcome Back", loginHint:"Continue to your account", registerHint:"Create your new account", noAccount:"Don't have an account?", haveAccount:"Already have an account?", demo:"Use any details for demo.", dashboard:"Dashboard", products:"My Products", addProduct:"Add Product", myOrders:"Orders", deliveries:"My Deliveries", cropInfo:"Crop & Fertility Info", previous:"Previous Year Data", transport:"Transport Partners", matching:"Transport Matching", earnings:"Earnings", profile:"Profile", logout:"Logout", popular:"Popular Categories", available:"Available Products", cropData:"Previous Year Crop Data", selectCrop:"Select Crop", selectYear:"Select Year", report:"View Report", avgYield:"Average Yield", avgPrice:"Average Price", production:"Total Production", income:"Total Income", detailed:"View Detailed Report", transportPartners:"Transport Partners", transportMatch:"Transport Matching (AI Powered)", assign:"Assign Transport", shared:"This order can be shared with 1 more farmer.", ordersTracking:"My Orders & Delivery Tracking", placed:"Order Placed", confirmed:"Confirmed", assigned:"Transport Assigned", out:"Out for Delivery", delivered:"Delivered", select:"Select", availableYes:"Available", from:"From", to:"To", totalWeight:"Total Weight", deliveryDate:"Delivery Date", viewShared:"View Shared Orders"
};

const productData = [
  [tomato,"Tomato","Ramesh Farmer","₹25 / kg","50 kg","vegetables"],
  [potato,"Potato","Suresh Farm","₹20 / kg","100 kg","vegetables"],
  [onion,"Onion","Mahesh Farm","₹18 / kg","80 kg","vegetables"],
  [carrot,"Carrot","Prakash Farmer","₹22 / kg","40 kg","vegetables"],
  [cabbage,"Cabbage","Lakshmi Farm","₹15 / kg","60 kg","vegetables"],
  [tomato,"Fresh Tomato","Ramesh Farmer","₹25 / kg","50 kg","fruits"],
  [potato,"Sweet Potato","Suresh Farm","₹30 / kg","70 kg","fruits"],
  [onion,"Red Onion","Mahesh Farm","₹22 / kg","80 kg","fruits"],
  [carrot,"Organic Carrot","Prakash Farmer","₹28 / kg","40 kg","organic"],
  [cabbage,"Organic Cabbage","Lakshmi Farm","₹20 / kg","60 kg","organic"]
];

const categories = [
  ["vegetables", VegetablesIcon, "120+ Products"], ["fruits", Apple, "80+ Products"], ["grains", WheatIcon, "45+ Products"],
  ["spices", Cookie, "25+ Products"], ["dairy", Milk, "40+ Products"], ["oils", Droplets, "30+ Products"],
  ["organic", Leaf, "35+ Products"], ["flowers", Flower2, "20+ Products"], ["herbal", Stethoscope, "18+ Products"]
];
function VegetablesIcon(){return <Carrot/>}
const labelKey = { vegetables:"vegetables", fruits:"fruits", grains:"grains", spices:"spices", dairy:"dairy", oils:"oils", organic:"organic", flowers:"flowers", herbal:"herbal" };

function Lang({lang,setLang}) { return <button className="lang" onClick={()=>setLang(lang === "kn" ? "en" : "kn")}><Globe2 size={17}/>{lang === "kn" ? "ಕನ್ನಡ" : "English"}<ChevronDown size={15}/></button> }
function Logo({dark=false}) { return <div className={`logo ${dark?"dark":""}`}><Leaf size={34}/><div><b>FarmBridge <span>AI</span></b><small>Bringing Farms Closer to You</small></div></div> }
function Top({lang,setLang,back}) { const t=T[lang]; return <header className="top">{back && <button className="back" onClick={back}><ArrowLeft size={18}/>{t.back}</button>}<Logo/><nav><a>{t.home}</a><a>{t.about}</a><a>{t.features}</a><a>{t.how}</a><a>{t.contact}</a></nav><Lang lang={lang} setLang={setLang}/></header> }

function Landing({lang,setLang,go}) { const t=T[lang]; return <div className="landing" style={{backgroundImage:`url(${landingFarm})`}}><Top lang={lang} setLang={setLang}/><div className="landing-main"><div className="landing-copy"><div className="eyebrow"><Leaf size={17}/>{t.fresh}</div><h1>{t.bringing}<br/><span>{t.closer}</span></h1><p>{t.choose}</p></div><div className="roles"><Role farmer={false} t={t} go={()=>go("consumer")}/><Role farmer t={t} go={()=>go("farmerLogin")}/></div></div><div className="features"><Feature i={<Leaf/>} a={t.freshHealthy} b={t.natural}/><Feature i={<UserRound/>} a={t.supportLocal} b={t.empower}/><Feature i={<ShieldCheck/>} a={t.safe} b={t.quality}/><Feature i={<Sparkles/>} a={t.aiPowered} b={t.smart}/></div><footer>© 2026 FarmBridge AI. All rights reserved.</footer></div> }
function Feature({i,a,b}) { return <div className="feature"><span>{i}</span><div><b>{a}</b><small>{b}</small></div></div> }
function Role({farmer,t,go}) { return <div className={`role ${farmer?"farmer":"consumer"}`}><div className="role-head"><div className="role-icon">{farmer?<Sprout size={42}/>:<ShoppingCart size={42}/>}</div><div><small>I'm a</small><h2>{farmer?t.farmer:t.consumer}</h2><p>{farmer?t.farmerDesc:t.consumerDesc}</p></div></div><div className="points">{(farmer?["Grow Your Business","Reach More Customers","Better Profits"]:[t.freshHealthy,t.direct,t.fast]).map(x=><div key={x}><Check size={17}/>{x}</div>)}</div><button onClick={go}>{farmer?t.continueFarmer:t.continueConsumer}<ArrowRight size={18}/></button></div> }

function Consumer({lang,setLang,go}) {
  const t = T[lang];
  const [query,setQuery] = useState("");
  const [category,setCategory] = useState(null);
  const [cart,setCart] = useState([]);
  const [products,setProducts] = useState([]);
  const [wishlist,setWishlist] = useState([]);
  const [view,setView] = useState("home");
  const [selectedProduct,setSelectedProduct] = useState(null);

  let sessionUser = {};
  try { sessionUser = JSON.parse(localStorage.getItem("farmbridge_user") || "{}"); }
  catch { sessionUser = {}; }
  const hasToken = !!localStorage.getItem("farmbridge_token");
  const loggedIn = hasToken && sessionUser.role === "consumer";
  const requireLogin = () => {
    if (hasToken && sessionUser.role && sessionUser.role !== "consumer") {
      alert("This session belongs to a farmer account. Sign in with a consumer account to access cart, wishlist, and consumer orders.");
    }
    go("consumerLogin");
  };

  const loadCart = async () => {
    if (!loggedIn) return;
    try { const data = await apiRequest("/cart"); setCart(data.items || []); }
    catch (e) { console.error(e); }
  };
  const loadWishlist = async () => {
    if (!loggedIn) return;
    try { const data = await apiRequest("/wishlist"); setWishlist(data.items || []); }
    catch (e) { console.error(e); }
  };
  const loadProducts = async () => {
    try { const data = await apiRequest("/products"); setProducts(data.products || []); }
    catch (e) { console.error(e); }
  };

  useEffect(() => { loadProducts(); loadCart(); loadWishlist(); }, []);

  const visible = useMemo(() => {
    let list = products;
    if (category) list = list.filter(p => (p.category || "").toLowerCase() === category.toLowerCase());
    if (query.trim()) {
      const q = query.toLowerCase().trim();
      list = list.filter(p => `${p.name||""} ${p.farmerName||""} ${p.category||""} ${p.description||""} ${p.location||""}`.toLowerCase().includes(q));
    }
    return list;
  }, [products,category,query]);

  async function addProductToCart(product, quantity=1, silent=false) {
    if (!loggedIn) { requireLogin(); return false; }
    try {
      await apiRequest("/cart", {method:"POST", body:JSON.stringify({productId:Number(product.id), quantity:Number(quantity)})});
      await loadCart();
      if (!silent) alert(`${product.name} added to cart successfully!`);
      return true;
    } catch (e) { alert(e.message); return false; }
  }

  async function addToCart(product) { await addProductToCart(product,1,false); }

  async function toggleWishlist(product) {
    if (!loggedIn) { requireLogin(); return; }
    const existing = wishlist.find(item => Number(item.product?.id ?? item.productId ?? item.product_id) === Number(product.id));
    try {
      if (existing) {
        const productId = existing.product?.id ?? existing.productId ?? existing.product_id;
        await apiRequest(`/wishlist/${productId}`, {method:"DELETE"});
      } else {
        await apiRequest("/wishlist", {method:"POST", body:JSON.stringify({productId:Number(product.id)})});
      }
      await loadWishlist();
    } catch (e) { alert(e.message); }
  }

  const isWishlisted = product => wishlist.some(item => Number(item.product?.id ?? item.productId ?? item.product_id) === Number(product.id));

  function openProduct(product) { setSelectedProduct(product); setView("details"); }
  async function buyNow(product, quantity=1) {
    const ok = await addProductToCart(product, quantity, true);
    if (ok) setView("checkout");
  }

  if (view === "cart") return <CartView cart={cart} setCart={setCart} go={()=>setView("home")} loadCart={loadCart} onCheckout={()=>setView("checkout")}/>;
  if (view === "wishlist") return <WishlistView wishlist={wishlist} products={products} go={()=>setView("home")} loadWishlist={loadWishlist} addToCart={addToCart} openProduct={openProduct}/>;
  if (view === "orders") return <OrdersPage go={()=>setView("home")}/>;
  if (view === "profile") {
  return (
    <ConsumerProfile
      go={() => setView("home")}
      onLogout={() => {
        localStorage.removeItem("farmbridge_token");
        localStorage.removeItem("farmbridge_user");
        setCart([]);
        setWishlist([]);
        setView("home");
        go("landing");
      }}
    />
  );
}
  if (view === "notifications") return <NotificationsPage go={()=>setView("home")}/>;
  if (view === "checkout") return <CheckoutView cart={cart} loadCart={loadCart} go={()=>setView("home")} onDone={()=>setView("orders")}/>;
  if (view === "details" && selectedProduct) return <ProductDetails product={selectedProduct} go={()=>setView("home")} addToCart={addToCart} buyNow={buyNow} liked={isWishlisted(selectedProduct)} onWishlist={()=>toggleWishlist(selectedProduct)}/>;

  return <div className="consumer-page">
    <Top lang={lang} setLang={setLang} back={()=>go("landing")}/>
    <div className="consumer-header">
      <button className="all-cat"><Menu size={17}/>{t.categories}</button>
      <div className="consumer-nav">
        {[["home",t.home],["vegetables",t.vegetables],["fruits",t.fruits],["grains",t.grains],["spices",t.spices],["dairy",t.dairy]].map(([key,label])=><button key={key} className={(key==="home"&&!category)||category===key?"active":""} onClick={()=>{setCategory(key==="home"?null:key);setView("home")}}>{label}</button>)}
        <button onClick={()=>loggedIn?setView("orders"):requireLogin()}>{t.orders}</button>
        <button onClick={()=>loggedIn?setView("wishlist"):requireLogin()}>Wishlist</button>
      </div>
      <div className="consumer-actions">
        <div className="consumer-search"><Search size={16}/><input value={query} onChange={e=>setQuery(e.target.value)} placeholder={t.search}/>{query&&<X size={15} onClick={()=>setQuery("")}/>}</div>
        <button className="icon-btn" onClick={()=>loggedIn?setView("wishlist"):requireLogin()}><Heart size={20}/>{wishlist.length>0&&<i>{wishlist.length}</i>}</button>
        <button className="icon-btn cart-btn" onClick={()=>loggedIn?setView("cart"):requireLogin()}><ShoppingCart size={20}/><i>{cart.length}</i></button>
        <button className="icon-btn" onClick={()=>loggedIn?setView("notifications"):requireLogin()}><Bell size={20}/></button>
        <button
  className="profile-btn"
  onClick={() => loggedIn ? setView("profile") : requireLogin()}
>
  <UserRound size={17} />
  {loggedIn
    ? (JSON.parse(localStorage.getItem("farmbridge_user") || "{}").name || "Account")
    : t.login}
</button>
      </div>
    </div>
    <div className="consumer-layout">
      <aside className="left"><h3>{t.shopCategory}</h3>{categories.map(([k,I])=><button className={`cat ${category===k?"selected":""}`} key={k} onClick={()=>setCategory(k)}><I size={15}/>{t[k]}</button>)}<button className={`cat ${!category?"selected":""}`} onClick={()=>setCategory(null)}><Store size={15}/>All Categories</button><div className="why"><Sparkles/><b>Why Choose FarmBridge AI?</b>{[t.direct,"Best Quality Products","Fair Prices","Safe & Secure Delivery","Transparent Process"].map(x=><small key={x}><Check size={13}/>{x}</small>)}</div></aside>
      <main className="consumer-main">
        <section className="hero" style={{backgroundImage:`url(${consumerHero})`}}><div><h1>{category?t[category]:<>Fresh From Farms<br/><span>Delivered to Your Home</span></>}</h1><p>{category?`${t.recommended} • ${t[category]}`:"Buy directly from farmers. Support local.\nEat healthy. Live better."}</p><button onClick={()=>setCategory(category||"vegetables")}>{t.shopNow}<ArrowRight size={16}/></button></div></section>
        <div className="benefits">{[[t.direct,t.noMiddle,UserRound],[t.quality2,t.natural,Leaf],[t.fast,"On-time Delivery",Truck],[t.payment,"Multiple Payment Options",ShieldCheck],[t.returns,"Hassle Free Returns",RefreshCw]].map(([a,b,I])=><div key={a}><I/><span><b>{a}</b><small>{b}</small></span></div>)}</div>
        <section className="box product-section"><div className="title"><h2>{category?`${t[category]} • ${t.recommended}`:t.recommended}</h2><a onClick={()=>setCategory(category||"vegetables")}>{t.viewAll}</a></div><div className="product-grid">{visible.slice(0,10).map(p=><Product key={p.id} p={p} t={t} onCart={()=>addToCart(p)} onBuy={()=>buyNow(p)} liked={isWishlisted(p)} onWishlist={()=>toggleWishlist(p)} onOpen={()=>openProduct(p)}/>)}</div>{!visible.length&&<div className="empty">No products found. Try another search.</div>}</section>
        <div className="promos"><Promo t={t.combo} s="Fresh Vegetables Combo"/><Promo t={t.free} s="On orders above ₹499"/><Promo t={t.best} s="Direct from Farmers"/></div>
      </main>
      <aside className="right"><Orders t={t} onLogin={()=>loggedIn?setView("orders"):requireLogin()}/><Assistant t={t}/></aside>
    </div>
    {cart.length>0&&<div className="toast">{cart.length} item(s) in cart <button onClick={()=>setView("cart")}>View Cart</button></div>}
  </div>;
}
function Product({p,t,onCart,onBuy,liked,onWishlist,onOpen}) {
  const name = p.name || "Product";
  const farmer = p.farmerName || p.farmer_name || "Farmer";
  const price = p.price ?? 0;
  const stock = p.stock ?? 0;

  return (
    <div className="product" onClick={onOpen}>
      <div className="pic">
        <ProductImage product={p} alt={name} />

        <button
          className={`wishlist-btn ${liked ? "liked" : ""}`}
          onClick={(e) => {
            e.stopPropagation();
            onWishlist();
          }}
        >
          <Heart size={18} fill={liked ? "currentColor" : "none"} />
        </button>
      </div>

      <b>{name}</b>
      <small>By {farmer} ✓</small>
      <strong>₹{price}</strong>
      <small>{stock} available</small>

      <div className="product-actions">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onCart();
          }}
        >
          <ShoppingCart size={13} />
          {t.addCart}
        </button>

        <button
          className="buy"
          onClick={(e) => {
            e.stopPropagation();
            onBuy();
          }}
        >
          {t.buy}
        </button>
      </div>
    </div>
  );
}


function Orders({t,onLogin}) {
  return (
    <div className="box orders">
      <div className="title">
        <h2>{t.orders}</h2>
        <a onClick={onLogin}>{t.viewAll}</a>
      </div>

      <div className="order">
        <PackageCheck size={25}/>
        <div>
          <b>Recent Orders</b>
          <small>View your order history and tracking</small>
        </div>
      </div>

      <div className="track">
        <b>{t.track}</b>
        <div>
          <input placeholder={t.orderId}/>
          <button onClick={onLogin}>{t.trackBtn}</button>
        </div>
      </div>
    </div>
  );
}


function Assistant({t}) {
  const [answer,setAnswer] = useState("");

  return (
    <div className="box assistant">
      <div className="assistant-head">
        <MessageCircle/>
        <div>
          <b>{t.assistant}</b>
          <small>{t.ask}</small>
        </div>
      </div>

      {[t.fertilizer,t.leafSpot,t.soil,t.maize].map(x => (
        <button
          key={x}
          onClick={() => setAnswer(x)}
        >
          {x}
        </button>
      ))}

      {answer && (
        <div className="ai-answer">
          AI tip: {answer.replace("?","")} — follow crop-specific recommendations.
        </div>
      )}

      <div className="ask">
        <input placeholder={t.question}/>
        <button>
          <ArrowRight size={15}/>
        </button>
      </div>
    </div>
  );
}


function Promo({t,s}) {
  return (
    <div className="promo">
      <small>{t}</small>
      <b>{s}</b>
      <span>Fresh • Local • Reliable</span>
      <a>{t.shopNow} →</a>
    </div>
  );
}
function ConsumerProfile({ go, onLogout }) {
  const user = JSON.parse(
    localStorage.getItem("farmbridge_user") || "{}"
  );

  return (
    <div className="cart-page consumer-profile-page">
      <button className="back" onClick={go}>
        <ArrowLeft size={18} />
        Back to Shopping
      </button>

      <div className="profile-card">
        <div className="profile-heading">
          <div className="profile-avatar">
            <UserRound size={36} />
          </div>

          <div>
            <h1>My Profile</h1>
            <p>Manage your account and personal details.</p>
          </div>
        </div>

        <div className="profile-information">
          <div className="profile-field">
            <span>Full Name</span>
            <strong>{user.name || "Not available"}</strong>
          </div>

          <div className="profile-field">
            <span>Email Address</span>
            <strong>{user.email || "Not available"}</strong>
          </div>

          <div className="profile-field">
            <span>Account Type</span>
            <strong>Consumer</strong>
          </div>
        </div>

        <div className="profile-settings">
          <h2>Account Settings</h2>
          <p>
            View your account details and manage your FarmBridge AI account.
          </p>
        </div>

        <div className="profile-footer">
          <button className="profile-back-btn" onClick={go}>
            Continue Shopping
          </button>

          <button className="profile-logout-btn" onClick={onLogout}>
            <LogOut size={18} />
            Logout
          </button>
        </div>
      </div>
    </div>
  );
}
function ProductDetails({product,go,addToCart,buyNow,liked,onWishlist}) {
  const [qty,setQty]=useState(1);
  const name=product.name||"Product"; const price=Number(product.price||0);
  return <div className="product-detail-page"><button className="back" onClick={go}><ArrowLeft size={18}/> Back</button><div className="detail-product-card"><div className="detail-product-image"><ProductImage product={product} alt={name}/></div><div className="detail-product-info"><div className="detail-breadcrumb">Home / {product.category || "Products"} / {name}</div><h1>{name}</h1><p className="detail-farmer">By {product.farmerName||product.farmer_name||"Farmer"} ✓</p><div className="detail-price">₹{price} <small>/ {product.unit||"kg"}</small></div><p>{product.description||"Fresh farm product supplied directly by a trusted farmer."}</p><div className="stock-badge">● {Number(product.stock||0)>0?"In Stock":"Out of Stock"}</div><div className="detail-qty"><b>Quantity</b><button onClick={()=>setQty(Math.max(1,qty-1))}>−</button><span>{qty}</span><button onClick={()=>setQty(qty+1)}>+</button></div><div className="detail-actions"><button onClick={()=>addToCart({...product},qty)}><ShoppingCart size={16}/> Add to Cart</button><button className="buy" onClick={()=>buyNow(product,qty)}>Buy Now</button><button className={`wishlist-detail ${liked?"liked":""}`} onClick={onWishlist}><Heart fill={liked?"currentColor":"none"}/></button></div><div className="detail-features"><span>✓ Direct from Farm</span><span>✓ Fresh & Natural</span><span>✓ Secure Delivery</span></div></div></div><div className="box detail-information"><h2>Product Information</h2><p>{product.description||"Farm fresh quality product. Carefully handled and supplied directly from the farmer."}</p></div></div>;
}

function CartView({cart,setCart,go,loadCart,onCheckout}) {
  const [loading,setLoading]=useState(false);
  async function changeQuantity(item,quantity){if(quantity<1)return;try{setLoading(true);await apiRequest(`/cart/${item.id}`,{method:"PATCH",body:JSON.stringify({quantity})});await loadCart();}catch(e){alert(e.message)}finally{setLoading(false)}}
  async function removeItem(id){try{await apiRequest(`/cart/${id}`,{method:"DELETE"});await loadCart()}catch(e){alert(e.message)}}
  const total=cart.reduce((sum,item)=>sum+Number(item.product?.price||item.price||0)*Number(item.quantity||1),0);
  return <div className="cart-page"><button className="back" onClick={go}><ArrowLeft size={18}/> Back to Shopping</button><div className="cart-header"><div><h1>My Cart</h1><p>{cart.length} item(s) in your cart</p></div></div>{!cart.length?<div className="cart-empty"><ShoppingCart size={58}/><h2>Your Cart is Empty</h2><p>Add fresh products directly from farmers.</p><button onClick={go}>Continue Shopping <ArrowRight size={17}/></button></div>:<div className="cart-layout"><div className="cart-items">{cart.map(item=>{const product=item.product||item;const name=product.name||"Product";const price=Number(product.price||item.price||0);return <div className="cart-item" key={item.id}><ProductImage product={product} alt={name}/><div className="cart-item-info"><h3>{name}</h3><small>By {product.farmerName||product.farmer_name||"Farmer"}</small><strong>₹{price}</strong><div className="quantity"><button disabled={loading} onClick={()=>changeQuantity(item,Number(item.quantity)-1)}>−</button><span>{item.quantity}</span><button disabled={loading} onClick={()=>changeQuantity(item,Number(item.quantity)+1)}>+</button></div></div><button className="remove-cart" onClick={()=>removeItem(item.id)}>Remove</button></div>})}</div><div className="cart-summary"><h2>Order Summary</h2><div><span>Subtotal</span><b>₹{total.toFixed(2)}</b></div><div><span>Delivery</span><b>FREE</b></div><hr/><div className="grand-total"><span>Total</span><strong>₹{total.toFixed(2)}</strong></div><button className="checkout" onClick={onCheckout}>Proceed to Checkout <ArrowRight size={17}/></button><button className="continue-shopping" onClick={go}>Continue Shopping</button></div></div>}</div>;
}

function WishlistView({wishlist,products,go,loadWishlist,addToCart,openProduct}) {
  async function removeItem(wish){try{const productId=wish.product?.id??wish.productId??wish.product_id;await apiRequest(`/wishlist/${productId}`,{method:"DELETE"});await loadWishlist()}catch(e){alert(e.message)}}
  return <div className="cart-page"><button className="back" onClick={go}><ArrowLeft size={18}/> Back to Shopping</button><div className="cart-header"><div><h1>My Wishlist</h1><p>{wishlist.length} saved item(s)</p></div></div>{!wishlist.length?<div className="cart-empty"><Heart size={58}/><h2>Your Wishlist is Empty</h2><p>Save products you want to buy later.</p><button onClick={go}>Continue Shopping <ArrowRight size={17}/></button></div>:<div className="wishlist-grid">{wishlist.map((wish,index)=>{const product=wish.product||products.find(p=>Number(p.id)===Number(wish.productId));const name=product?.name||"Product";const price=Number(product?.price||0);return <div className="wishlist-card" key={wish.id||index}><div className="wishlist-image"><ProductImage product={product} alt={name}/><Heart fill="currentColor"/></div><h3>{name}</h3><small>By {product?.farmerName||product?.farmer_name||"Farmer"}</small><strong>₹{price}</strong><div className="wishlist-actions"><button onClick={()=>openProduct(product)}><Eye size={14}/> View</button><button onClick={()=>addToCart(product)}><ShoppingCart size={14}/> Add to Cart</button><button onClick={()=>removeItem(wish)}><X size={14}/> Remove</button></div></div>})}</div>}</div>;
}

function OrdersPage({go}) {
  const [orders,setOrders]=useState([]); const [loading,setLoading]=useState(true); const [track,setTrack]=useState(""); const [tracked,setTracked]=useState(null);
  useEffect(()=>{(async()=>{try{const d=await apiRequest("/orders");setOrders(d.orders||[])}catch(e){alert(e.message)}finally{setLoading(false)}})()},[]);
  async function trackOrder(){if(!track.trim())return;try{const d=await apiRequest(`/orders/track/${track.trim()}`);setTracked(d.order)}catch(e){alert(e.message)}}
  return <div className="cart-page"><button className="back" onClick={go}><ArrowLeft size={18}/> Back</button><div className="cart-header"><h1>My Orders</h1><p>Order history and delivery tracking</p></div><div className="track-box"><input value={track} onChange={e=>setTrack(e.target.value)} placeholder="Enter Order ID e.g. ORD00001"/><button onClick={trackOrder}>Track</button></div>{tracked&&<OrderCard order={tracked}/>}<div className="order-history">{loading?<p>Loading orders...</p>:!orders.length?<div className="cart-empty"><Package size={50}/><h2>No orders yet</h2></div>:orders.map(o=><OrderCard key={o.id} order={o}/>)}</div></div>;
}

function orderPaymentLabel(method) {
  return ({
    COD: "Cash on Delivery",
    GOOGLE_PAY_DEMO: "Google Pay Demo",
    PHONEPE_DEMO: "PhonePe Demo",
    PAYTM_DEMO: "Paytm Demo",
    CARD_DEMO: "Card Demo",
  })[method] || method || "Not recorded";
}

function OrderCard({ order }) {
  const status = (order.status || "placed").toLowerCase();

  const steps = [
    { key: "placed", label: "Order Placed" },
    { key: "confirmed", label: "Order Confirmed" },
    { key: "assigned", label: "Transport Assigned" },
    { key: "out_for_delivery", label: "Out for Delivery" },
    { key: "delivered", label: "Delivered" }
  ];

  const statusIndex = steps.findIndex(
    step => step.key === status
  );

  return (
    <div className="order-history-card">
      <div>
        <b>ORD{String(order.id).padStart(5, "0")}</b>
        <small>
          {order.createdAt
            ? new Date(order.createdAt).toLocaleString()
            : ""}
        </small>
      </div>

      <strong>₹{Number(order.totalAmount || 0).toFixed(2)}</strong>

      <span className={`status ${status}`}>
        {status.replaceAll("_", " ")}
      </span>

      <small>
        <span>{order.deliveryAddress || "Delivery address not available"}</span>
        <span className="order-payment-detail">Payment: {orderPaymentLabel(order.paymentMethod)}</span>
        <span className="order-payment-detail">Payment status: {order.paymentStatus || "Not recorded"}{order.isDemoPayment ? " · DEMO ONLY" : ""}</span>
      </small>

      <div className="tracking-details">
        <h3>Order Tracking</h3>

        {steps.map((step, index) => (
          <div
            key={step.key}
            className={
              statusIndex >= index
                ? "tracking-step completed"
                : "tracking-step"
            }
          >
            <span>{statusIndex >= index ? "✓" : "○"}</span>
            {step.label}
          </div>
        ))}
      </div>
    </div>
  );
}

function CheckoutView({cart,loadCart,go,onDone}) {
  const [address,setAddress]=useState("");
  const [paymentMethod,setPaymentMethod]=useState("COD");
  const [screen,setScreen]=useState("checkout");
  const [placing,setPlacing]=useState(false);
  const [error,setError]=useState("");
  const [placedOrders,setPlacedOrders]=useState([]);
  const [checkoutId]=useState(()=>globalThis.crypto?.randomUUID?.()||`checkout-${Date.now()}-${Math.random().toString(36).slice(2)}`);
  const total=cart.reduce((sum,item)=>sum+Number(item.product?.price||0)*Number(item.quantity||1),0);
  const paymentChoices=[
    {method:"COD",title:"Cash on Delivery",detail:"Pay when your order arrives",group:"COD"},
    {method:"GOOGLE_PAY_DEMO",title:"Google Pay",detail:"UPI Demo Only",group:"UPI DEMO"},
    {method:"PHONEPE_DEMO",title:"PhonePe",detail:"UPI Demo Only",group:"UPI DEMO"},
    {method:"PAYTM_DEMO",title:"Paytm",detail:"UPI Demo Only",group:"UPI DEMO"},
    {method:"CARD_DEMO",title:"Card Payment",detail:"Demo only · no card details collected",group:"CARD DEMO"},
  ];
  const selectedPayment=paymentChoices.find(choice=>choice.method===paymentMethod)||paymentChoices[0];
  const demoTotal=placedOrders.reduce((sum,order)=>sum+Number(order.totalAmount||0),0);

  async function submitOrder(){
    if(placing)return;
    setPlacing(true);
    setError("");
    try{
      const result=await apiRequest("/orders",{
        method:"POST",
        body:JSON.stringify({deliveryAddress:address,paymentMethod,checkoutId}),
      });
      setPlacedOrders(result.orders||[]);
      setScreen("success");
      try{await loadCart()}catch(loadError){console.error(loadError)}
    }catch(requestError){
      setError(requestError.message);
    }finally{
      setPlacing(false);
    }
  }

  function continueCheckout(event){
    event.preventDefault();
    setError("");
    if(paymentMethod==="COD")submitOrder();
    else setScreen("demo-payment");
  }

  if(screen==="success"){
    const demoPaid=placedOrders.some(order=>order.paymentStatus==="PAID_DEMO");
    return <div className="cart-page"><div className="payment-result"><span className="payment-demo-tag">DEMO ONLY</span><h1>{demoPaid?"Demo Payment Successful — No Real Money Deducted":"Order Placed"}</h1><p>{demoPaid?"Your demo payment was recorded. No real transaction was made.":"Your order is confirmed. Payment is due on delivery."}</p><div className="payment-result-total"><span>Order total</span><strong>₹{demoTotal.toFixed(2)}</strong></div><div className="payment-result-meta"><span>{orderPaymentLabel(placedOrders[0]?.paymentMethod)}</span><span>{placedOrders[0]?.paymentStatus||"PENDING"}</span></div><button className="checkout" onClick={onDone}>View My Orders <ArrowRight size={17}/></button></div></div>;
  }

  if(screen==="demo-payment"){
    return <div className="cart-page"><button className="back" onClick={()=>{setError("");setScreen("checkout")}}><ArrowLeft size={18}/> Cancel and return</button><div className="cart-header"><div><span className="payment-demo-tag">DEMO ONLY · NO REAL PAYMENT</span><h1>Demo Payment</h1><p>This screen does not connect to a bank or payment gateway.</p></div></div><section className="payment-demo-panel"><div className="payment-demo-method"><small>SELECTED METHOD</small><strong>{selectedPayment.title}</strong><span>{selectedPayment.group}</span></div><div className="payment-demo-total"><small>AMOUNT TO CONFIRM</small><strong>₹{total.toFixed(2)}</strong></div><p className="payment-demo-disclaimer">Clicking Pay Now records a simulated success only. No card details, UPI PIN, or banking credentials are requested.</p>{error&&<div className="checkout-error" role="alert">{error}</div>}<div className="payment-demo-actions"><button className="continue-shopping" type="button" disabled={placing} onClick={()=>{setError("");setScreen("checkout")}}>Cancel</button><button className="checkout" type="button" disabled={placing} onClick={submitOrder}>{placing?"Processing demo...":"Pay Now · Demo"} <ArrowRight size={17}/></button></div></section></div>;
  }

  return <div className="cart-page"><button className="back" onClick={go}><ArrowLeft size={18}/> Back to Cart</button><div className="cart-header"><div><h1>Checkout</h1><p>Confirm your delivery details</p></div></div><form className="checkout-layout" onSubmit={continueCheckout}><div className="checkout-card"><h2>Delivery Address</h2><textarea value={address} onChange={event=>setAddress(event.target.value)} placeholder="House / Street / Area / City / Pincode" required/><h2>Payment Method</h2><div className="payment-method-list">{paymentChoices.map(choice=><label className={`payment-method-option ${paymentMethod===choice.method?"selected":""}`} key={choice.method}><input type="radio" name="paymentMethod" value={choice.method} checked={paymentMethod===choice.method} onChange={()=>setPaymentMethod(choice.method)}/><span className="payment-method-copy"><b>{choice.title}</b><small>{choice.detail}</small></span><span className={`payment-method-badge ${choice.group==="COD"?"cod":"demo"}`}>{choice.group}</span></label>)}</div><p className="payment-demo-disclaimer">UPI and card options are simulations for demonstration only. No real payment details are collected.</p>{error&&<div className="checkout-error" role="alert">{error}</div>}</div><div className="cart-summary"><h2>Order Summary</h2><div><span>Items</span><b>{cart.reduce((count,item)=>count+Number(item.quantity||1),0)}</b></div><div><span>Subtotal</span><b>₹{total.toFixed(2)}</b></div><div><span>Delivery</span><b>FREE</b></div><hr/><div className="grand-total"><span>Total</span><strong>₹{total.toFixed(2)}</strong></div><button className="checkout" disabled={placing||!cart.length}>{placing?"Placing Order...":paymentMethod==="COD"?"Place COD Order":"Continue to Demo Payment"} <ArrowRight size={17}/></button></div></form></div>;
}

function NotificationsPage({go}){const [items,setItems]=useState([]);useEffect(()=>{(async()=>{try{const d=await apiRequest("/notifications");setItems(d.notifications||[])}catch(e){alert(e.message)}})()},[]);async function read(id){try{await apiRequest(`/notifications/${id}/read`,{method:"PATCH"});setItems(x=>x.map(n=>n.id===id?{...n,isRead:true}:n))}catch(e){alert(e.message)}}return <div className="cart-page"><button className="back" onClick={go}><ArrowLeft size={18}/> Back</button><div className="cart-header"><h1>Notifications</h1><p>Updates about your FarmBridge activity</p></div><div className="notification-list">{!items.length?<div className="cart-empty"><Bell size={45}/><h2>No notifications</h2></div>:items.map(n=><div className={`notification-item ${n.isRead?"read":""}`} key={n.id}><Bell size={18}/><div><b>{n.title}</b><p>{n.message}</p><small>{new Date(n.createdAt).toLocaleString()}</small></div>{!n.isRead&&<button onClick={()=>read(n.id)}>Mark read</button>}</div>)}</div></div>;
}

function Auth({role,mode,lang,setLang,go}) {
  const t = T[lang];
  const farmer = role === "farmer";
  const reg = mode === "register";
  const [show,setShow] = useState(false);
  const [loading,setLoading] = useState(false);

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);

    const form = new FormData(e.currentTarget);

    const name = form.get("name")?.toString().trim() || "";
    const email = form.get("email")?.toString().trim() || "";
    const password = form.get("password")?.toString() || "";

    try {
      const endpoint = reg ? "/auth/register" : "/auth/login";

      const body = reg
        ? {
            name,
            email,
            password,
            role: farmer ? "farmer" : "consumer"
          }
        : {
            email,
            password,
            role: farmer ? "farmer" : "consumer"
          };

      const data = await apiRequest(endpoint, {
        method: "POST",
        body: JSON.stringify(body)
      });

      localStorage.setItem("farmbridge_token", data.token);
      localStorage.setItem("farmbridge_user", JSON.stringify(data.user));

      go(farmer ? "farmer" : "consumer");

    } catch (error) {
      alert(error.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="auth">
      <Top
        lang={lang}
        setLang={setLang}
        back={() => go(farmer ? "landing" : "consumer")}
      />

      <div className="auth-wrap">

        <div
          className={`auth-art ${farmer ? "farmer-auth" : "consumer-auth"}`}
          style={{
            backgroundImage:
              `url(${farmer ? farmerLoginHero : consumerLoginHero})`
          }}
        >
          <div className="art-label">
            <span>{farmer ? <Sprout/> : <ShoppingCart/>}</span>
            <b>{farmer ? t.farmer : t.consumer}</b>
            <small>
              {farmer
                ? "Grow your farm with smarter digital tools."
                : "Shop fresh produce directly from local farmers."}
            </small>
          </div>
        </div>

        <form className="auth-card" onSubmit={handleSubmit}>

          <div className="auth-icon">
            {farmer ? <Sprout/> : <ShoppingCart/>}
          </div>

          <h1>{reg ? t.register : t.welcome}</h1>
          <p>{reg ? t.registerHint : t.loginHint}</p>

          {reg && (
            <label>
              {t.name}
              <input
                name="name"
                required
                placeholder={t.name}
              />
            </label>
          )}

          <label>
            {t.email}
            <input
              name="email"
              type="email"
              required
              placeholder={t.email}
            />
          </label>

          <label>
            {t.password}

            <div className="pass">
              <input
                name="password"
                required
                minLength={6}
                type={show ? "text" : "password"}
                placeholder={t.password}
              />

              <button
                type="button"
                onClick={() => setShow(!show)}
              >
                {show ? <EyeOff size={16}/> : <Eye size={16}/>}
              </button>
            </div>
          </label>

          <button
            className="submit"
            type="submit"
            disabled={loading}
          >
            {loading
              ? "Please wait..."
              : reg
                ? t.create
                : t.login}

            {!loading && <ArrowRight size={17}/>}
          </button>

          <small>
            {reg
              ? "Your account will be securely stored in PostgreSQL."
              : "Login using your registered account."}
          </small>

          <div className="switch">
            {reg ? t.haveAccount : t.noAccount}

            <button
              type="button"
              onClick={() =>
                go(
                  (farmer ? "farmer" : "consumer") +
                  (reg ? "Login" : "Register")
                )
              }
            >
              {reg ? t.login : t.register}
            </button>
          </div>

        </form>
      </div>
    </div>
  );
}

const farmerMenu = [
  ["dashboard",BarChart3],["products",Boxes],["addProduct",Plus],["myOrders",ClipboardList],["deliveries",Truck],["assistant",BrainCircuit],["cropInfo",Leaf],["previous",History],["transport",Truck],["matching",Sparkles],["earnings",CircleDollarSign],["profile",UserRound]
];

function Farmer({lang,setLang,go}) {
  const t=T[lang]; const [view,setView]=useState("dashboard"); const [search,setSearch]=useState("");
  const [menuOpen,setMenuOpen]=useState(false);
  const [dashboard,setDashboard]=useState(null); const [products,setProducts]=useState([]); const [orders,setOrders]=useState([]); const [deliveries,setDeliveries]=useState([]); const [earnings,setEarnings]=useState(null); const [profile,setProfile]=useState(null); const [notifications,setNotifications]=useState([]);
  const load=async()=>{
    try{const [d,p,o,del,e,pr,n]=await Promise.all([apiRequest("/farmer/dashboard"),apiRequest("/farmer/products"),apiRequest("/orders"),apiRequest("/farmer/deliveries"),apiRequest("/farmer/earnings"),apiRequest("/profile"),apiRequest("/notifications")]);setDashboard(d);setProducts(p.products||[]);setOrders(o.orders||[]);setDeliveries(del.deliveries||[]);setEarnings(e);setProfile(pr.user);setNotifications(n.notifications||[])}catch(err){console.error(err);alert(err.message)}};
  useEffect(()=>{load()},[]);
  const filtered=products.filter(p=>`${p.name||""} ${p.category||""} ${p.location||""}`.toLowerCase().includes(search.toLowerCase()));
  function logout(){localStorage.removeItem("farmbridge_token");localStorage.removeItem("farmbridge_user");go("landing")}
  return <div className="farmer-app">
    <aside className={`farmer-side ${menuOpen ? "menu-open" : ""}`}>
      <Logo dark/>
      <div className="farmer-user"><div className="avatar">{(profile?.name||"FR").slice(0,2).toUpperCase()}</div><div><b>{profile?.name||"Farmer"}</b><small>Farmer ✓</small></div><ChevronDown size={15}/></div>
      <div className="side-links">{farmerMenu.map(([key,I])=><button className={view===key?"sel":""} key={key} onClick={()=>{setView(key);setMenuOpen(false)}}><I size={15}/>{t[key]}</button>)}<button onClick={logout}><LogOut size={15}/>{t.logout}</button></div>
      <div className="slogan">Grow Better.<br/>Sell Better.<br/>Live Better.</div>
    </aside>
    {menuOpen&&<button className="farmer-nav-backdrop" onClick={()=>setMenuOpen(false)} aria-label="Close navigation"/>}
    <main className="farmer-main">
      <header className="farmer-top"><button className="hamb" onClick={()=>setMenuOpen(open=>!open)} aria-label="Toggle navigation"><Menu/></button><div className="search"><Search size={16}/><input value={search} onChange={e=>setSearch(e.target.value)} placeholder={t.search}/>{search&&<X size={15} onClick={()=>setSearch("")}/>}</div><div className="farmer-actions"><Lang lang={lang} setLang={setLang}/><button className="plain-icon" onClick={()=>setView("notifications")}><Bell/><i>{notifications.filter(n=>!n.isRead).length}</i></button><b>{profile?.name||"Farmer"}⌄</b></div></header>
      <div className="farmer-content"><FarmerPanel view={view} t={t} dashboard={dashboard} products={filtered} allProducts={products} orders={orders} deliveries={deliveries} earnings={earnings} profile={profile} reload={load} setView={setView}/></div>
      <button className="float-back" onClick={()=>go("landing")}><ArrowLeft size={15}/>{t.back}</button>
    </main>
  </div>
}

function FarmerPanel({view,t,dashboard,products,allProducts,orders,deliveries,earnings,profile,reload,setView}){
  if(view==="dashboard") return <FarmerDashboardLive t={t} dashboard={dashboard} products={products} setView={setView}/>;
  if(view==="products") return <FarmerProductsLive t={t} products={products} reload={reload} setView={setView}/>;
  if(view==="addProduct") return <AddProductLive t={t} reload={reload} setView={setView}/>;
  if(view==="myOrders") return <FarmerOrdersLive t={t} orders={orders} reload={reload}/>;
  if(view==="deliveries") return <FarmerDeliveriesLive t={t} deliveries={deliveries}/>;
  if(view==="assistant") return <FarmerAILive t={t}/>;
  if(view==="cropInfo") return <CropLive t={t} />;
  if(view==="previous") return <PreviousCropLive t={t}/>;
  if(view==="transport") return <TransportLive t={t}/>;
  if(view==="matching") return <MatchingLive t={t} orders={orders}/>;
  if(view==="earnings") return <EarningsLive t={t} earnings={earnings}/>;
  if(view==="profile") return <ProfileLive t={t} profile={profile} reload={reload}/>;
  if(view==="notifications") return <FarmerNotifications t={t}/>;
  return null;
}

function FarmerDashboardLive({t,dashboard,products,setView}){const stats=dashboard?.stats||{};return <><section className="farmer-hero" style={{backgroundImage:`url(${farmerHero})`}}><div><h1><span>Fresh Produce</span><br/>Directly from Farmers<br/><span>to Your Home</span></h1><p>Good for you. Good for farmers.</p><button onClick={()=>setView("products")}>{t.products} <ArrowRight size={15}/></button></div></section><div className="farmer-stat-grid">{[["Products",stats.products??0,Boxes],["Orders",stats.orders??0,ClipboardList],["Pending Orders",stats.pendingOrders??0,History],["Delivered",stats.deliveries??0,PackageCheck],["Earnings",`₹${Number(stats.earnings||0).toFixed(2)}`,CircleDollarSign]].map(([a,b,I])=><div key={a}><I/><small>{a}</small><strong>{b}</strong></div>)}</div><div className="farmer-grid"><section className="box"><div className="title"><h2>{t.available}</h2><a onClick={()=>setView("products")}>{t.viewAll}</a></div><div className="farmer-products">{products.slice(0,6).map(p=><div key={p.id}><ProductImage product={p} alt={p.name}/><b>{p.name}</b><small>{p.location||"Farm"}</small><em>{p.stock} {p.unit||"kg"} available</em><strong>₹{p.price}</strong><button onClick={()=>setView("products")}>Manage</button></div>)}</div></section><CropLive t={t}/></div></>}

function FarmerProductsLive({t,products,reload,setView}){async function remove(id){if(!confirm("Remove this product?"))return;try{await apiRequest(`/products/${id}`,{method:"DELETE"});await reload()}catch(e){alert(e.message)}}return <section className="detail-view"><div className="detail-head"><button onClick={()=>setView("dashboard")}><ArrowLeft size={16}/>{t.back}</button><div><span className="eyebrow"><Leaf size={15}/>FarmBridge AI</span><h1>{t.products}</h1><p>Manage your active products, stock and prices.</p></div></div><div className="farmer-products large">{products.map(p=><div key={p.id}><ProductImage product={p} alt={p.name}/><b>{p.name}</b><small>{p.category} • {p.location||""}</small><em>{p.stock} {p.unit||"kg"} available</em><strong>₹{p.price}</strong><button onClick={()=>remove(p.id)}>Remove</button></div>)}{!products.length&&<div className="empty">No products found.</div>}</div></section>}

function AddProductLive({t,reload,setView}){const [form,setForm]=useState({name:"",category:"vegetables",description:"",price:"",unit:"kg",stock:"",location:""});const [busy,setBusy]=useState(false);const change=e=>setForm({...form,[e.target.name]:e.target.value});async function submit(e){e.preventDefault();try{setBusy(true);await apiRequest("/products",{method:"POST",body:JSON.stringify({...form,price:Number(form.price),stock:Number(form.stock)})});alert("Product added successfully");await reload();setView("products")}catch(e){alert(e.message)}finally{setBusy(false)}}return <section className="detail-view"><div className="detail-head"><div><span className="eyebrow"><Plus size={15}/>FarmBridge AI</span><h1>{t.addProduct}</h1><p>Add a product to the consumer marketplace.</p></div></div><form className="form-grid" onSubmit={submit}><label>Product Name<input name="name" value={form.name} onChange={change} required placeholder="Tomato"/></label><label>Category<select name="category" value={form.category} onChange={change}><option value="vegetables">vegetables</option><option value="fruits">fruits</option><option value="grains">grains</option><option value="spices">spices</option><option value="dairy">dairy</option><option value="organic">organic</option></select></label><label>Price<input name="price" type="number" value={form.price} onChange={change} required/></label><label>Stock<input name="stock" type="number" value={form.stock} onChange={change} required/></label><label>Unit<input name="unit" value={form.unit} onChange={change}/></label><label>Location<input name="location" value={form.location} onChange={change}/></label><label className="wide">Description<textarea name="description" value={form.description} onChange={change}/></label><button className="submit small-submit" disabled={busy}>{busy?"Saving...":t.addProduct}<Plus size={16}/></button></form></section>}

function FarmerOrdersLive({t,orders,reload}){async function status(id,status){try{await apiRequest(`/orders/${id}/status`,{method:"PATCH",body:JSON.stringify({status})});await reload()}catch(e){alert(e.message)}}return <section className="detail-view"><div className="detail-head"><div><span className="eyebrow"><ClipboardList size={15}/>FarmBridge AI</span><h1>{t.myOrders}</h1><p>Customer orders received for your products.</p></div></div><div className="simple-list">{orders.map(o=><div key={o.id}><PackageCheck/><div><b>ORD{String(o.id).padStart(5,"0")} • ₹{Number(o.totalAmount||0).toFixed(2)}</b><small>{o.deliveryAddress||"No address"}</small><small>Status: {o.status}</small><small className="farmer-payment-detail">Payment: {orderPaymentLabel(o.paymentMethod)} · {o.paymentStatus||"Not recorded"}{o.isDemoPayment?" · DEMO ONLY":""}</small></div><select value={o.status} onChange={e=>status(o.id,e.target.value)}><option value="placed">placed</option><option value="confirmed">confirmed</option><option value="transport_assigned">transport assigned</option><option value="out_for_delivery">out for delivery</option><option value="delivered">delivered</option><option value="cancelled">cancelled</option></select></div>)}{!orders.length&&<p>No orders yet.</p>}</div></section>}

function FarmerDeliveriesLive({t,deliveries}){return <section className="detail-view"><div className="detail-head"><div><span className="eyebrow"><Truck size={15}/>FarmBridge AI</span><h1>{t.deliveries}</h1><p>Assigned, out-for-delivery and completed deliveries.</p></div></div><div className="simple-list">{deliveries.map(o=><div key={o.id}><Truck/><div><b>ORD{String(o.id).padStart(5,"0")}</b><small>{o.fromLocation||"Farm"} → {o.toLocation||"Customer"}</small><small>{o.status}</small></div><span>₹{o.totalAmount}</span></div>)}</div></section>}

function FarmerAILive({t}){return <FarmingAssistant t={t}/>}

function PreviousCropLive({t}){const [records,setRecords]=useState([]);const [form,setForm]=useState({cropName:"Tomato",year:new Date().getFullYear()-1,category:"vegetables",season:"",areaAcres:"",yieldAmount:"",averagePrice:"",totalIncome:"",soilType:"Loamy",soilPh:"",notes:""});const [summary,setSummary]=useState(null);async function load(){try{const [r,s]=await Promise.all([apiRequest("/crops/previous-year"),apiRequest("/crops/summary")]);setRecords(r.records||[]);setSummary(s.summary)}catch(e){alert(e.message)}}useEffect(()=>{load()},[]);const ch=e=>setForm({...form,[e.target.name]:e.target.value});async function save(e){e.preventDefault();try{await apiRequest("/crops/previous-year",{method:"POST",body:JSON.stringify({...form,year:Number(form.year)})});alert("Crop record saved");await load()}catch(e){alert(e.message)}}return <section className="detail-view"><div className="detail-head"><div><span className="eyebrow"><History size={15}/>FarmBridge AI</span><h1>{t.previous}</h1><p>Save and review previous-year crop performance.</p></div></div>{summary&&<div className="stats">{[[t.avgYield,summary.averageYield],[t.avgPrice,summary.averagePrice],[t.production,summary.totalProduction],[t.income,summary.totalIncome]].map(x=><div key={x[0]}><small>{x[0]}</small><b>{x[1]}</b><span>From saved records</span></div>)}</div>}<form className="form-grid crop-form" onSubmit={save}><label>Crop<input name="cropName" value={form.cropName} onChange={ch}/></label><label>Year<input name="year" type="number" value={form.year} onChange={ch}/></label><label>Area (acres)<input name="areaAcres" value={form.areaAcres} onChange={ch}/></label><label>Yield<input name="yieldAmount" value={form.yieldAmount} onChange={ch}/></label><label>Average Price<input name="averagePrice" value={form.averagePrice} onChange={ch}/></label><label>Total Income<input name="totalIncome" value={form.totalIncome} onChange={ch}/></label><label>Soil Type<input name="soilType" value={form.soilType} onChange={ch}/></label><label>Soil pH<input name="soilPh" value={form.soilPh} onChange={ch}/></label><label className="wide">Notes<textarea name="notes" value={form.notes} onChange={ch}/></label><button className="submit small-submit">Save Crop Record</button></form><div className="simple-list crop-records">{records.map(r=><div key={r.id}><Leaf/><div><b>{r.cropName} • {r.year}</b><small>{r.areaAcres||0} acres • Yield {r.yieldAmount||0}</small><small>{r.soilType||"Soil not recorded"} • pH {r.soilPh||"-"}</small></div><span>₹{r.totalIncome||0}</span></div>)}</div></section>}

function CropLive({t}){const [soil,setSoil]=useState("Loamy");const [ph,setPh]=useState("6.5");const [answer,setAnswer]=useState("");async function check(){try{const d=await apiRequest(`/crops/fertility?soilType=${encodeURIComponent(soil)}&ph=${encodeURIComponent(ph)}`);setAnswer(`${d.guidance} ${d.phNote||""}`)}catch(e){alert(e.message)}}return <section className="box crop"><div className="title"><h2>{t.cropInfo}</h2></div><div className="filters"><label>Soil<select value={soil} onChange={e=>setSoil(e.target.value)}><option>Loamy</option><option>Clay</option><option>Sandy</option></select></label><label>pH<input value={ph} onChange={e=>setPh(e.target.value)}/></label><button onClick={check}>{t.report}</button></div>{answer&&<div className="ai-answer">{answer}</div>}</section>}

function TransportLive({t}){const [partners,setPartners]=useState([]);useEffect(()=>{apiRequest("/transport/partners").then(d=>setPartners(d.partners||[])).catch(e=>alert(e.message))},[]);return <section className="detail-view"><div className="detail-head"><div><span className="eyebrow"><Truck size={15}/>FarmBridge AI</span><h1>{t.transport}</h1><p>Available transport partners and rates.</p></div></div><div className="simple-list">{partners.map(p=><div key={p.id}><Truck/><div><b>{p.name}</b><small>{p.vehicleType} • {p.capacityKg} kg • {p.location}</small><small>{p.phone||"Phone not listed"}</small></div><strong>₹{p.price}</strong></div>)}</div></section>}

function MatchingLive({t,orders}){const [weight,setWeight]=useState(50);const [from,setFrom]=useState("Mysore");const [matches,setMatches]=useState([]);async function match(){try{const d=await apiRequest("/transport/match",{method:"POST",body:JSON.stringify({from,totalWeight:Number(weight)})});setMatches(d.matches||[])}catch(e){alert(e.message)}}async function assign(orderId,partnerId){try{await apiRequest(`/orders/${orderId}/transport`,{method:"POST",body:JSON.stringify({transportPartnerId:partnerId})});alert("Transport assigned")}catch(e){alert(e.message)}}const order=orders.find(o=>!['delivered','cancelled'].includes(o.status));return <section className="detail-view"><div className="detail-head"><div><span className="eyebrow"><Sparkles size={15}/>FarmBridge AI</span><h1>{t.matching}</h1><p>AI-powered matching by location, capacity and price.</p></div></div><div className="match-form"><input value={from} onChange={e=>setFrom(e.target.value)} placeholder="From location"/><input type="number" value={weight} onChange={e=>setWeight(e.target.value)} placeholder="Weight kg"/><button onClick={match}>Find Best Match</button></div><div className="transport-match-grid">{matches.map((p,i)=><div className="transport-match-card" key={p.id}><small>{i===0?"BEST MATCH":"MATCH"}</small><h3>{p.name}</h3><p>{p.vehicleType} • {p.capacityKg} kg</p><strong>₹{p.price}</strong>{order&&<button onClick={()=>assign(order.id,p.id)}>{t.assign}</button>}</div>)}</div></section>}

function EarningsLive({t,earnings}){const s=earnings?.summary||{};return <section className="detail-view"><div className="detail-head"><div><span className="eyebrow"><CircleDollarSign size={15}/>FarmBridge AI</span><h1>{t.earnings}</h1><p>Real earnings calculated from delivered orders.</p></div></div><div className="earn-grid">{[[t.income,`₹${Number(s.totalIncome||0).toFixed(2)}`],[t.orders,s.totalOrders||0],[t.deliveries,s.deliveredOrders||0],["Pending Orders",s.pendingOrders||0]].map(([a,b])=><div key={a}><CircleDollarSign/><small>{a}</small><strong>{b}</strong></div>)}</div></section>}

function ProfileLive({t,profile,reload}){const [form,setForm]=useState({name:profile?.name||"",phone:profile?.phone||"",location:profile?.location||"",farmName:profile?.farmName||"",experienceYears:profile?.experienceYears||""});useEffect(()=>setForm({name:profile?.name||"",phone:profile?.phone||"",location:profile?.location||"",farmName:profile?.farmName||"",experienceYears:profile?.experienceYears||""}),[profile]);const ch=e=>setForm({...form,[e.target.name]:e.target.value});async function save(e){e.preventDefault();try{const d=await apiRequest("/profile",{method:"PUT",body:JSON.stringify({...form,experienceYears:form.experienceYears?Number(form.experienceYears):null})});localStorage.setItem("farmbridge_user",JSON.stringify(d.user));await reload();alert("Profile updated") }catch(e){alert(e.message)}}return <section className="detail-view"><div className="detail-head"><div><span className="eyebrow"><UserRound size={15}/>FarmBridge AI</span><h1>{t.profile}</h1><p>Manage your farmer profile details.</p></div></div><form className="form-grid" onSubmit={save}><label>Name<input name="name" value={form.name} onChange={ch}/></label><label>Phone<input name="phone" value={form.phone} onChange={ch}/></label><label>Location<input name="location" value={form.location} onChange={ch}/></label><label>Farm Name<input name="farmName" value={form.farmName} onChange={ch}/></label><label>Experience (years)<input name="experienceYears" value={form.experienceYears} onChange={ch}/></label><button className="submit small-submit">Save Profile</button></form></section>}

function FarmerNotifications({t}){const [items,setItems]=useState([]);useEffect(()=>{apiRequest("/notifications").then(d=>setItems(d.notifications||[])).catch(e=>alert(e.message))},[]);async function read(id){await apiRequest(`/notifications/${id}/read`,{method:"PATCH"});setItems(x=>x.map(n=>n.id===id?{...n,isRead:true}:n))}return <section className="detail-view"><div className="detail-head"><div><span className="eyebrow"><Bell size={15}/>FarmBridge AI</span><h1>Notifications</h1></div></div><div className="notification-list">{items.map(n=><div className={`notification-item ${n.isRead?"read":""}`} key={n.id}><Bell/><div><b>{n.title}</b><p>{n.message}</p></div>{!n.isRead&&<button onClick={()=>read(n.id)}>Mark read</button>}</div>)}</div></section>}


function App(){
  const [page,setPage]=useState("landing"),[lang,setLang]=useState("kn");
  const go=p=>setPage(p);
  useEffect(()=>{
    function returnToLogin(event){
      setPage(event.detail?.role==="farmer"?"farmerLogin":"consumerLogin");
    }
    window.addEventListener("farmbridge:session-expired",returnToLogin);
    return ()=>window.removeEventListener("farmbridge:session-expired",returnToLogin);
  },[]);
  const p={lang,setLang,go};
  if(page==="landing")return <Landing {...p}/>;
  if(page==="consumer")return <Consumer {...p}/>;
  if(page==="consumerLogin")return <Auth role="consumer" mode="login" {...p}/>;
  if(page==="consumerRegister")return <Auth role="consumer" mode="register" {...p}/>;
  if(page==="farmerLogin")return <Auth role="farmer" mode="login" {...p}/>;
  if(page==="farmerRegister")return <Auth role="farmer" mode="register" {...p}/>;
  if(page==="farmer")return <Farmer {...p}/>;
  return <Landing {...p}/>;
}
createRoot(document.getElementById("root")).render(<App/>);
