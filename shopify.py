"""
shopify.py — Shopify API helpers
"""
import os, requests, time, re
from config import SHOPIFY_API, SHOPIFY_HEADERS, API_DELAY

DRY_RUN = os.environ.get("DRY_RUN", "false").strip().lower() in ("true", "1", "yes")

# ── Core request with retry ───────────────────────────────────────────────────
def api(method, endpoint, payload=None, params=None):
    url = f"{SHOPIFY_API}/{endpoint}"
    for attempt in range(5):
        try:
            s = requests.Session()
            r = getattr(s, method)(url, headers=SHOPIFY_HEADERS,
                                   json=payload, params=params, timeout=30)
            if r.status_code == 429:
                wait = float(r.headers.get("Retry-After", 5))
                print(f"    Rate limited — waiting {wait:.0f}s", flush=True)
                time.sleep(wait)
                continue
            return r
        except Exception as e:
            print(f"    API retry {attempt+1}: {e}", flush=True)
            time.sleep(10)
    return None

# ── Get or create a collection by title ──────────────────────────────────────
def get_or_create_collection(title, sort_order="created-desc"):
    r = api("get", "custom_collections.json",
            params={"title": title, "limit": 1})
    if r and r.ok:
        cols = r.json().get("custom_collections", [])
        if cols:
            return cols[0]["id"]
    if DRY_RUN:
        print(f"    [DRY RUN] Would create collection: {title}", flush=True)
        return -1
    r = api("post", "custom_collections.json", {
        "custom_collection": {
            "title": title,
            "published": True,
            "sort_order": sort_order,
            "body_html": f"<p>{title} — Amaara World CZ Jewelry. Free shipping over $100.</p>"
        }
    })
    if r and r.status_code == 201:
        return r.json()["custom_collection"]["id"]
    return None

# ── Get all products in a collection (paginated) ──────────────────────────────
def get_collection_products(col_id, fields="id,title,variants,images,tags,status"):
    products = []
    path = f"products.json"
    params = {"collection_id": col_id, "limit": 250, "fields": fields}
    while path:
        r = api("get", path, params=params)
        if not r or not r.ok:
            break
        products.extend(r.json().get("products", []))
        params = None
        link = r.headers.get("Link", "")
        nxt = re.search(r"<[^>]*/2026-04/([^>]+)>;\s*rel=\"next\"", link)
        path = nxt.group(1) if nxt else None
        time.sleep(API_DELAY)
    return products

# ── Get SKU → product map for a collection ────────────────────────────────────
def get_sku_map(col_id):
    """Returns {sku: {product_id, variant_id, title, price, has_img, status, collect_id}}"""
    prods = get_collection_products(col_id, "id,title,variants,images,status")
    sku_map = {}
    for p in prods:
        for v in p.get("variants", []):
            sku = (v.get("sku") or "").strip()
            if not sku:
                continue
            sku_map[sku] = {
                "product_id":  p["id"],
                "variant_id":  v["id"],
                "title":       p["title"],
                "price":       v.get("price", "0"),
                "has_img":     bool(p.get("images")),
                "status":      p.get("status", "active"),
            }
    return sku_map

# ── Get all collects for a collection (for moving products) ──────────────────
def get_collects(col_id):
    """Returns {product_id: collect_id}"""
    result = {}
    params = {"collection_id": col_id, "limit": 250}
    path = "collects.json"
    while path:
        r = api("get", path, params=params)
        if not r or not r.ok:
            break
        for c in r.json().get("collects", []):
            result[c["product_id"]] = c["id"]
        params = None
        link = r.headers.get("Link", "")
        nxt = re.search(r"<[^>]*/2026-04/([^>]+)>;\s*rel=\"next\"", link)
        path = nxt.group(1) if nxt else None
        time.sleep(API_DELAY)
    return result

# ── Add product to collection ─────────────────────────────────────────────────
def add_to_collection(product_id, col_id):
    if DRY_RUN:
        print(f"    [DRY RUN] Would add product {product_id} to collection {col_id}", flush=True)
        return True
    r = api("post", "collects.json",
            {"collect": {"product_id": product_id, "collection_id": col_id}})
    return r and r.status_code in (200, 201)

# ── Remove product from collection (by collect_id) ────────────────────────────
def remove_from_collection(collect_id):
    if DRY_RUN:
        print(f"    [DRY RUN] Would remove collect {collect_id}", flush=True)
        return True
    r = api("delete", f"collects/{collect_id}.json")
    return r and r.status_code == 200

# ── Create a product ─────────────────────────────────────────────────────────
def create_product(payload):
    if DRY_RUN:
        print(f"    [DRY RUN] Would create product: {payload.get('title', '?')}", flush=True)
        return {"id": -1, "title": payload.get("title", "?")}
    r = api("post", "products.json", {"product": payload})
    if r and r.status_code == 201:
        return r.json()["product"]
    return None

# ── Update a product variant ─────────────────────────────────────────────────
def update_variant(variant_id, price=None, sku=None, inventory_quantity=None):
    if DRY_RUN:
        print(f"    [DRY RUN] Would update variant {variant_id} "
              f"(price={price}, sku={sku}, inventory_quantity={inventory_quantity})", flush=True)
        return True
    body = {"variant": {"id": variant_id}}
    if price is not None:
        body["variant"]["price"] = str(price)
    if sku is not None:
        body["variant"]["sku"] = sku
    if inventory_quantity is not None:
        body["variant"]["inventory_quantity"] = inventory_quantity
    r = api("put", f"variants/{variant_id}.json", body)
    return r and r.ok

# ── Update product title / status ────────────────────────────────────────────
def update_product(product_id, **kwargs):
    if DRY_RUN:
        print(f"    [DRY RUN] Would update product {product_id}: {kwargs}", flush=True)
        return True
    body = {"product": {"id": product_id, **kwargs}}
    r = api("put", f"products/{product_id}.json", body)
    return r and r.ok

# ── Link a variant to a specific image ───────────────────────────────────────
def update_variant_image(variant_id, image_id):
    if DRY_RUN:
        print(f"    [DRY RUN] Would link variant {variant_id} to image {image_id}", flush=True)
        return True
    r = api("put", f"variants/{variant_id}.json",
            {"variant": {"id": variant_id, "image_id": image_id}})
    return r and r.ok

# ── Add image to product ─────────────────────────────────────────────────────
def add_image(product_id, src, alt=""):
    if DRY_RUN:
        print(f"    [DRY RUN] Would add image to product {product_id}: {src}", flush=True)
        return True
    r = api("post", f"products/{product_id}/images.json",
            {"image": {"src": src, "alt": alt}})
    return r and r.status_code in (200, 201)
