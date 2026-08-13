"""
config.py — Amaara World Sync Configuration
All environment variables are injected by GitHub Actions secrets.
"""
import os

# ── Shopify ───────────────────────────────────────────────────────────────────
SHOPIFY_STORE = os.environ.get("SHOPIFY_STORE") or "amaaraworld.myshopify.com"
SHOPIFY_TOKEN = os.environ.get("SHOPIFY_TOKEN")
if not SHOPIFY_TOKEN:
    raise RuntimeError("SHOPIFY_TOKEN environment variable is not set")
SHOPIFY_API   = f"https://{SHOPIFY_STORE}/admin/api/2026-04"

SHOPIFY_HEADERS = {
    "X-Shopify-Access-Token": SHOPIFY_TOKEN,
    "Content-Type": "application/json"
}

# ── PHP Source ────────────────────────────────────────────────────────────────
PHP_BASE   = "https://amaaraworld.com"
PHP_IMG    = "https://indian-jewellery.com/core/thumb_images/product_images"
PHP_WEB    = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/124 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://amaaraworld.com",
}

# ── Shopify Collection IDs ────────────────────────────────────────────────────
COLLECTIONS = {
    "choker":      504236278060,
    "classic":     504236376364,
    "collar":      504236343596,
    "traditional": 504236409132,
    "earrings":    504236474668,
    "bracelets":   504236146988,
    "pendants":    504546361644,
    "rings":       504546328876,
}

# ── PHP category slugs per collection key ─────────────────────────────────────
PHP_SLUGS = {
    "choker":      ["choker-necklaces"],
    "classic":     ["classic-necklace"],
    "collar":      ["collar-necklace"],
    "traditional": ["traditional-necklaces"],
    "earrings":    ["medium-earrings", "big-size-earrings", "cute-earrings",
                    "jhumka-earrings", "ad-earrings", "cz-tops-and-studs"],
    "bracelets":   ["cz-braclets", "cz-bangles"],
    "pendants":    ["pendant-sets"],
    "rings":       ["finger-rings"],
}

PHP_TYPES = {
    "choker":      "Necklaces",
    "classic":     "Necklaces",
    "collar":      "Necklaces",
    "traditional": "Necklaces",
    "earrings":    "Earrings",
    "bracelets":   "Bracelets",
    "pendants":    "Pendants",
    "rings":       "Rings",
}

PHP_TAGS = {
    "choker":      "Choker Necklaces, amaara, cz-jewelry, necklace",
    "classic":     "Classic Necklaces, amaara, cz-jewelry, necklace",
    "collar":      "Collar Necklaces, amaara, cz-jewelry, necklace",
    "traditional": "Traditional Necklaces, amaara, cz-jewelry, necklace",
    "earrings":    "Earrings, amaara, cz-jewelry, earring",
    "bracelets":   "CZ Bracelets, amaara, cz-jewelry, bracelet",
    "pendants":    "Pendant Sets, amaara, cz-jewelry, pendant",
    "rings":       "Finger Rings, amaara, cz-jewelry, ring",
}

# ── Special collections (created/managed by this script) ─────────────────────
NEW_COLLECTIONS_TITLE  = "New Collections"
OUT_OF_STOCK_TITLE     = "Out of Stock"

# ── Timing ────────────────────────────────────────────────────────────────────
API_DELAY    = 0.35   # seconds between Shopify API calls
SCRAPE_DELAY = 0.40   # seconds between PHP page fetches
MAX_PAGES    = 200    # max pages to scrape per category

# ── State file ────────────────────────────────────────────────────────────────
STATE_FILE = "state.json"
