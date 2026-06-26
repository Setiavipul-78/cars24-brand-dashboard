"""
Cars24 brand keyword classifier — 10 categories.

Priority order (first match wins):
  PDI → ELITE → Cars24 Challan → Cars24 Customer Care →
  Cars24 Sell → Cars24 + Car Model → Cars24 Buy →
  Others → Cars24 Cities → Cars24
"""

import re
from typing import Set

CATEGORIES = [
    "Cars24 Challan",
    "Cars24 Customer Care",
    "Cars24 Sell",
    "Cars24 + Car Model",
    "Cars24 Buy",
    "PDI",
    "ELITE",
    "Cars24 Cities",
    "Others",
    "Cars24",
]

CATEGORY_COLORS = {
    # Cars24 brand palette: Blue primary, Mint secondary, Orange sparingly
    "Cars24":              "#4736FE",   # Brand Blue 300 — core brand
    "Cars24 Cities":       "#2B2098",   # Brand Blue 700 — geo layer
    "Cars24 Challan":      "#FF4F01",   # Safety Orange — high-action service
    "Cars24 Customer Care":"#FD9A00",   # Amber — support
    "Cars24 Buy":          "#63FFB1",   # Mint Green — purchase intent
    "Cars24 Sell":         "#20E2BF",   # Cool Mint 500 — sell intent
    "Cars24 + Car Model":  "#E3E1FF",   # Brand Blue Light — model search
    "PDI":                 "#456DFF",   # Vehicle Info blue — inspection
    "ELITE":               "#FEE685",   # Amber 200 — premium
    "Others":              "#A1A1A1",   # Neutral 400
}

# ─── Challan signals ────────────────────────────────────────────
CHALLAN_SIGNALS = [
    "challan", "chalan", "callan",
    "e-challan", "echallan", "e challan", "e memo", "ememo",
    "traffic challan", "vehicle challan", "bike challan",
    "challan check", "challan status", "challan payment",
    "challan pay", "pay challan", "online challan",
    "pending challan", "challan details", "challan with photo",
    "fine check", "memo check", "memo",
    "चालान",
]

# ─── Customer Care / Support signals ────────────────────────────
SUPPORT_SIGNALS = [
    "customer care", "helpline", "toll free", "complaint",
    "contact number", "mobile number", "care number",
    "helpline number", "customer service", "head office",
    "complaint number", "support",
    "pdi customer care", "finance customer care",
    "loan customer care", "e challan customer care",
    "challan customer care", "financial services customer care",
]

# ─── Sell signals ────────────────────────────────────────────────
SELL_SIGNALS = [
    "sell car", "sell my car", "sell used car",
    "car valuation", "valuation",
    "car value", "delhi car value",
    "sell used cars",
]
SELL_WORD_BOUNDARY = ["sell"]   # use \bsell\b to avoid matching "bestseller"

# ─── Car model names (separate category) ─────────────────────────
# Multi-word first for correct priority in matching
CAR_MODELS_MULTIWORD = [
    "innova crysta", "honda city", "honda civic", "honda elevate",
    "honda jazz", "honda amaze", "honda wrv", "honda wr-v",
    "honda cr-v", "honda hr-v",
    "thar roxx", "scorpio n", "xuv 700", "xuv700", "xuv500", "xuv400",
    "ford ecosport", "ford endeavour", "ford figo", "ford aspire",
    "skoda kushaq", "kia sonet", "kia seltos", "kia carens", "kia carnival",
    "tata nano", "tata safari", "tata tiago", "tata punch", "tata nexon",
    "jeep compass", "jeep meridian",
    "wagon r", "alto k10", "grand i10", "grand vitara", "vitara brezza",
    "mg hector", "mg astor", "mg gloster", "mg comet", "mg zs",
    "maruti swift", "maruti baleno", "maruti brezza",
    "hyundai creta", "hyundai i20", "hyundai verna",
    "mahindra thar", "mahindra scorpio", "mahindra xuv",
    "new cars",   # catches "new cars cars24 triber" etc.
]

# Single-word models: matched with word boundaries (\bmodel\b) to avoid
# partial matches like "aura" inside "aurangabad"
CAR_MODELS_SINGLEWORD = [
    # Maruti/Suzuki
    "swift", "baleno", "brezza", "fronx", "jimny", "ertiga", "xl6",
    "celerio", "ignis", "ciaz", "dzire", "spresso",
    # Hyundai
    "creta", "verna", "alcazar", "tucson", "elantra", "santro",
    "venue", "ioniq", "aura",
    # Tata
    "nexon", "harrier", "safari", "tiago", "punch", "altroz", "tigor",
    "zest", "hexa", "nano", "curvv",
    # Mahindra
    "thar", "scorpio", "bolero", "marazzo", "alturas",
    # Toyota
    "innova", "fortuner", "camry", "glanza", "etios", "corolla", "hyryder",
    # Skoda / VW
    "octavia", "superb", "rapid", "slavia", "kodiaq", "karoq",
    "taigun", "virtus", "polo", "vento",
    # Renault / Nissan
    "kwid", "triber", "duster", "kiger", "magnite", "terrano",
    # Jeep / MG
    "wrangler",
    # Honda (single-word)
    "amaze",
    # Luxury brands
    "bmw", "mercedes", "audi", "lexus", "volvo", "jaguar",
    "porsche", "bentley",
    # Generic
    "alto", "i20",
]

# ─── Buy signals (no RC/RTO/vehicle details — those go to Others) ─
BUY_SIGNALS = [
    "buy car", "buy used car", "buy used cars",
    "used car", "used cars", "second hand", "secondhand",
    "pre-owned", "preowned", "new car",
    "auction",
    "loan", "emi", "financial services", "insurance",
    "price list", "luxury cars", "ev cars", "electric car",
    "automatic cars", "commercial vehicle", "cng car",
    "axle",
    "second hand car", "second hand cars",
    "buy cars",
]
BUY_WORD_BOUNDARY = ["buy", "price"]

# ─── PDI signals ────────────────────────────────────────────────
PDI_SIGNALS = ["pdi", "pre delivery inspection", "pre-delivery inspection"]

# ─── Elite signals ──────────────────────────────────────────────
ELITE_SIGNALS = ["elite"]

# ─── Others signals (RC/RTO/vehicle info + career + misc) ────────
OTHERS_SIGNALS = [
    # RC / RTO / vehicle lookup (tool usage, not buy intent)
    "rto check", "rto details", "rto transfer",
    "rc check", "rc details", "rc transfer", "rc transfer status",
    "vehicle details", "vehicle info", "vehicle information",
    "car details", "car info", "car detail",
    "owner details", "registration check", "number check",
    "service history", "check vehicle details", "vehicle challan",
    "car challan", "car number",
    # Careers / jobs
    "career", "careers", "job", "jobs", "internship",
    "vacancy", "vacancies", "job vacancy", "hiring",
    # Reviews / misc
    "review", "reviews", "logo",
    "login", "partner login", "services private limited",
    # Finance (separate tool usage)
    "finance customer care", "loan customer care",
    "financial services customer care",
]
OTHERS_WORD_BOUNDARY = ["rto"]   # standalone "rto" e.g. "cars24 rto"

# ─── City / location data ────────────────────────────────────────
CITIES: Set[str] = {
    # Metro
    "delhi", "mumbai", "bangalore", "bengaluru", "hyderabad", "chennai",
    "kolkata", "ahmedabad", "pune", "surat",
    # Tier 2
    "lucknow", "jaipur", "kanpur", "nagpur", "indore", "bhopal", "patna",
    "vadodara", "coimbatore", "agra", "ghaziabad", "noida", "chandigarh",
    "ludhiana", "rajkot", "nashik", "faridabad", "meerut", "varanasi",
    "aurangabad", "thane", "gurgaon", "gurugram",
    # Tier 3
    "kochi", "cochin", "dehradun", "ranchi", "mysore", "mysuru",
    "bhubaneswar", "dombivli", "vijayawada", "vizag", "visakhapatnam",
    "raipur", "gwalior", "jamshedpur", "dhanbad", "siliguri", "jammu",
    "jodhpur", "madurai", "trichy", "tiruchirappalli", "mangalore",
    "mangaluru", "kolhapur", "belgaum", "belagavi", "jamnagar", "karnal",
    "mohali", "hubli", "hubballi", "udaipur", "guwahati", "gauhati",
    "salem", "jalandhar", "jabalpur", "thiruverkadu", "tiruverkadu",
    "pondicherry", "puducherry", "trivandrum", "thiruvananthapuram",
    "gorakhpur", "muzaffarpur", "purnia", "agartala",
    "allahabad", "prayagraj", "haridwar", "rishikesh", "roorkee",
    "aligarh", "bareilly", "moradabad", "saharanpur", "mathura",
    "ajmer", "bikaner", "kota", "alwar",
    "amritsar", "patiala", "bathinda",
    "panipat", "ambala", "rohtak", "hisar",
    "gaya", "bhagalpur", "darbhanga",
    "cuttack", "rourkela", "berhampur",
    "dibrugarh", "silchar",
    "tirunelveli", "vellore", "erode", "tirupur", "thanjavur",
    "dharwad", "tumkur", "shimoga", "bellary", "gulbarga",
    "kozhikode", "calicut", "thrissur", "kannur", "kollam", "palakkad",
    "guntur", "warangal", "nellore", "tirupati", "karimnagar", "rajahmundry",
    "nanded", "solapur", "amravati", "akola",
    "gandhinagar", "anand", "mehsana", "nadiad", "bhavnagar",
    "panaji", "margao", "ujjain", "sagar", "srinagar",
    "ranchi", "bokaro", "kakinada", "eluru", "ongole",
    "kompally", "jakkur", "bellahalli", "bachupally", "tathawade",
    "naroda", "sholinganallur", "kakkanad", "goregaon",
    "maharashtra", "punjab", "kerala", "gujarat", "goa",
    "meerut", "agartala", "muzaffarpur", "purnia",
    "vizag",
}

MULTI_WORD_CITIES = [
    "navi mumbai", "greater noida", "delhi ncr", "rajouri garden",
    "s.g. highway",
]


# ─── Helpers ─────────────────────────────────────────────────────

def _has_any(text: str, signals: list) -> bool:
    return any(s in text for s in signals)


def _has_word(text: str, word: str) -> bool:
    return bool(re.search(r"\b" + re.escape(word) + r"\b", text))


def _has_city(text: str) -> bool:
    if "near me" in text:
        return True
    for mwc in MULTI_WORD_CITIES:
        if mwc in text:
            return True
    tokens = set(re.split(r"[\s\-\./]+", text))
    return bool(tokens & CITIES)


def _has_challan(text: str) -> bool:
    return _has_any(text, CHALLAN_SIGNALS)


def _has_support(text: str) -> bool:
    return _has_any(text, SUPPORT_SIGNALS)


def _has_sell(text: str) -> bool:
    if _has_any(text, SELL_SIGNALS):
        return True
    return any(_has_word(text, w) for w in SELL_WORD_BOUNDARY)


def _has_model(text: str) -> bool:
    # Multi-word models: substring OK (no city name risk)
    for m in CAR_MODELS_MULTIWORD:
        if m in text:
            return True
    # Single-word models: must be whole-word match to avoid e.g. "aura" in "aurangabad"
    for m in CAR_MODELS_SINGLEWORD:
        if _has_word(text, m):
            return True
    return False


def _has_buy(text: str) -> bool:
    if _has_any(text, BUY_SIGNALS):
        return True
    return any(_has_word(text, w) for w in BUY_WORD_BOUNDARY)


def _has_pdi(text: str) -> bool:
    return _has_word(text, "pdi") or _has_any(text, PDI_SIGNALS[1:])


def _has_elite(text: str) -> bool:
    return _has_word(text, "elite")


def _has_others(text: str) -> bool:
    if _has_any(text, OTHERS_SIGNALS):
        return True
    return any(_has_word(text, w) for w in OTHERS_WORD_BOUNDARY)


# ─── Main classifier ─────────────────────────────────────────────

def classify_keyword(keyword: str) -> str:
    kw = keyword.lower().strip()

    if _has_pdi(kw):
        return "PDI"

    if _has_elite(kw):
        return "ELITE"

    if _has_challan(kw):
        return "Cars24 Challan"

    if _has_support(kw):
        return "Cars24 Customer Care"

    if _has_sell(kw):
        return "Cars24 Sell"

    if _has_model(kw):
        return "Cars24 + Car Model"

    if _has_buy(kw):
        return "Cars24 Buy"

    if _has_others(kw):
        return "Others"

    if _has_city(kw):
        return "Cars24 Cities"

    return "Cars24"
