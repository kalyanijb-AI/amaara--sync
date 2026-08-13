"""
scraper.py — PHP site scraper for amaaraworld.com
"""
import requests, re, time
from bs4 import BeautifulSoup
from collections import defaultdict
from config import PHP_BASE, PHP_IMG, PHP_WEB, SCRAPE_DELAY, MAX_PAGES

# ── Scrape one page of a PHP category ────────────────────────────────────────
def scrape_page(slug, page):
    url = f"{PHP_BASE}/category/{slug}?page={page}"
    try:
        r = requests.get(url, headers=PHP_WEB, timeout=20)
        if r.status_code != 200:
            return None   # None = error/stop
        soup = BeautifulSoup(r.text, "html.parser")
        cards = soup.select(".f-prod")
        if not cards:
            return []     # Empty list = no more products

        products = []
        for card in cards:
            img = card.find("img", class_="img-responsive")
            if not img:
                continue
            src = img.get("src", "")
            if "product_medium_images" not in src:
                continue

            text = card.get_text()
            sm = re.search(r"Code\s*:\s*(\d{5,8})", text)
            pm = re.search(r"USD\s+([\d.]+)", text)
            if not sm or not pm:
                continue

            # Stock: if no "Add to Cart" it's sold out
            in_stock = "Add to Cart" in text and "out of stock" not in text.lower()

            sku  = sm.group(1)
            imgfile = src.split("/")[-1]

            # Product title: first clean text line in card
            lines = [l.strip() for l in card.get_text("\n").split("\n")
                     if l.strip() and not l.strip().isdigit()
                     and "Code" not in l and "USD" not in l
                     and "Cart" not in l and len(l.strip()) > 5]
            name = lines[0] if lines else "Jewelry"

            # Variant group = image filename without last 2 digits before .jpg
            base = imgfile.replace(".jpg", "")
            group = base[:-2] if len(base) > 2 else base

            products.append({
                "sku":      sku,
                "name":     name,
                "price":    pm.group(1),
                "imgfile":  imgfile,
                "img_url":  src,
                "group":    group,
                "in_stock": in_stock,
            })
        return products

    except requests.Timeout:
        return None
    except Exception as e:
        print(f"    Scrape error {slug} p{page}: {e}", flush=True)
        return []

# ── Scrape full category (all pages, all slugs) ───────────────────────────────
def scrape_category(slugs):
    """
    Returns (sku_map, variant_groups)
    sku_map:       {sku: product_dict}
    variant_groups: {group_key: [product_dict, ...]}
    """
    all_raw = {}
    seen = set()

    for slug in slugs:
        print(f"    Scraping /{slug}...", flush=True)
        empty = 0
        for page in range(1, MAX_PAGES + 1):
            result = scrape_page(slug, page)
            if result is None:  # error
                time.sleep(2)
                continue
            if not result:      # empty page
                empty += 1
                if empty >= 2:
                    break
                continue
            empty = 0
            new = 0
            for p in result:
                if p["sku"] not in seen:
                    seen.add(p["sku"])
                    all_raw[p["sku"]] = p
                    new += 1
            if new:
                print(f"    p{page}: +{new} ({len(all_raw)} total)", flush=True)
            time.sleep(SCRAPE_DELAY)

    # Group variants by image filename prefix
    groups = defaultdict(list)
    for p in all_raw.values():
        groups[p["group"]].append(p)

    return all_raw, dict(groups)

# ── Build 3-image list for a product ─────────────────────────────────────────
def get_images(imgfile, name, sku):
    base = imgfile.replace(".jpg", "")
    return [
        {"src": f"{PHP_IMG}/{base}.jpg",  "alt": f"{name} - Amaara World USA - SKU {sku}"},
        {"src": f"{PHP_IMG}/{base}A.jpg", "alt": f"{name} - View 2 - Amaara World"},
        {"src": f"{PHP_IMG}/{base}B.jpg", "alt": f"{name} - View 3 - Amaara World"},
    ]

# ── Build Shopify product payload for a single SKU ───────────────────────────
def build_single_payload(p, ptype, tags):
    return {
        "title":       f"{p['name']} - {p['sku']}",
        "body_html":   f"<p><strong>{p['name']}</strong></p><ul><li>SKU: {p['sku']}</li>"
                       f"<li>Free shipping over $100</li><li>30-day returns</li></ul>",
        "vendor":      "Amaara World",
        "product_type": ptype,
        "tags":        tags,
        "status":      "active",
        "variants": [{
            "price":                str(p["price"]),
            "sku":                  p["sku"],
            "inventory_management": "shopify",
            "inventory_quantity":   99 if p["in_stock"] else 0,
            "requires_shipping":    True,
        }],
        "images": get_images(p["imgfile"], p["name"], p["sku"]),
    }

# ── Build Shopify product payload for a variant GROUP ────────────────────────
def build_variant_payload(group_prods, ptype, tags):
    group_prods = sorted(group_prods, key=lambda x: x["sku"])
    base = group_prods[0]
    variants, images = [], []
    for i, p in enumerate(group_prods):
        option = f"Style {i+1}"
        variants.append({
            "option1":              option,
            "price":                str(p["price"]),
            "sku":                  p["sku"],
            "inventory_management": "shopify",
            "inventory_quantity":   99 if p["in_stock"] else 0,
            "requires_shipping":    True,
        })
        imgbase = p["imgfile"].replace(".jpg", "")
        images.append({"src": f"{PHP_IMG}/{imgbase}.jpg",
                        "alt": f"{base['name']} - {option} - Amaara World"})

    # Add A/B angles for first variant
    imgbase0 = group_prods[0]["imgfile"].replace(".jpg", "")
    images.append({"src": f"{PHP_IMG}/{imgbase0}A.jpg", "alt": "View 2"})
    images.append({"src": f"{PHP_IMG}/{imgbase0}B.jpg", "alt": "View 3"})

    return {
        "title":        base["name"],
        "body_html":    f"<p><strong>{base['name']}</strong></p><p>Available in {len(group_prods)} styles.</p>"
                        f"<ul><li>Free shipping over $100</li><li>30-day returns</li></ul>",
        "vendor":       "Amaara World",
        "product_type": ptype,
        "tags":         tags,
        "status":       "active",
        "options":      [{"name": "Style", "values": [f"Style {i+1}" for i in range(len(group_prods))]}],
        "variants":     variants,
        "images":       images[:10],  # Shopify max
    }
