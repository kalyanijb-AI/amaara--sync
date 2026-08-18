"""
sync.py — Amaara World Inventory Sync (Main Entry Point)
=========================================================
Runs every other day via GitHub Actions.

Logic:
  1. Monday only: archive last week's "New Collections" → proper categories,
     then create a fresh "New Collections" for this week.
  2. Every run: sync each collection from PHP site one by one:
       - New products → create, add to category + New Collections
       - Changed price/title → update in Shopify
       - Missing from PHP (out of stock/retired) → move to "Out of Stock"
  3. Variant grouping: products sharing the same image-filename prefix
     (minus last 2 digits) are grouped as one listing with multiple options.
"""

import sys, time
from datetime import datetime, timezone
from collections import defaultdict

import config, state, shopify, scraper

# ── Monday: archive old New Collections → proper categories ───────────────────
def monday_archive(st):
    print("\n📦 MONDAY TASK: Archive last week's New Collections")
    nc_id = st.get("new_collections_id")
    if not nc_id:
        print("  No previous New Collections found — skipping archive")
        return st

    products_to_move = st.get("new_products_this_week", [])
    if not products_to_move:
        print("  No products to archive")
    else:
        print(f"  Moving {len(products_to_move)} products to their category collections...")
        nc_collects = shopify.get_collects(nc_id)
        moved = 0
        for pid in products_to_move:
            # Find this product's proper category collection from its tags
            prods = shopify.api("get", f"products/{pid}.json",
                                params={"fields": "id,tags,product_type"})
            if not prods or not prods.ok:
                continue
            p = prods.json().get("product", {})
            tags = p.get("tags", "").lower()
            ptype = p.get("product_type", "").lower()

            # Map tags/type → collection ID
            target_col = None
            for key, col_id in config.COLLECTIONS.items():
                tag_name = config.PHP_TAGS.get(key, "").split(",")[0].lower()
                if tag_name in tags or key in tags or key in ptype:
                    target_col = col_id
                    break

            if target_col:
                shopify.add_to_collection(pid, target_col)
                # Remove from New Collections
                collect_id = nc_collects.get(pid)
                if collect_id:
                    shopify.remove_from_collection(collect_id)
                moved += 1

        print(f"  ✓ Moved {moved}/{len(products_to_move)} products to categories")

    # Reset "New Collections" for this week
    print("  Creating fresh 'New Collections' for this week...")
    new_id = shopify.get_or_create_collection(
        f"{config.NEW_COLLECTIONS_TITLE}",
        sort_order="created-desc"
    )
    st["new_collections_id"]       = new_id
    st["new_collections_date"]     = state.today_iso()
    st["new_products_this_week"]   = []
    print(f"  ✓ New Collections ID: {new_id}")
    return st

# ── Sync one collection ────────────────────────────────────────────────────────
def sync_collection(cat_key, st):
    slugs  = config.PHP_SLUGS[cat_key]
    col_id = config.COLLECTIONS[cat_key]
    ptype  = config.PHP_TYPES[cat_key]
    tags   = config.PHP_TAGS[cat_key]

    print(f"\n{'─'*55}")
    print(f"  COLLECTION: {cat_key.upper()}  |  Shopify ID: {col_id}")
    print(f"{'─'*55}")

    # ── 1. Scrape PHP ────────────────────────────────────────────────────────
    print("  [1/4] Scraping PHP site...")
    php_map, php_groups = scraper.scrape_category(slugs)
    print(f"  → {len(php_map)} in-stock products | {len(php_groups)} variant groups")

    # ── 2. Load Shopify state ────────────────────────────────────────────────
    print("  [2/4] Loading Shopify collection...")
    shopify_sku_map = shopify.get_sku_map(col_id)
    print(f"  → {len(shopify_sku_map)} products already in Shopify")

    # ── 3. Diff ──────────────────────────────────────────────────────────────
    php_skus      = set(php_map.keys())
    shopify_skus  = set(shopify_sku_map.keys())

    to_create     = php_skus - shopify_skus      # new on PHP, not in Shopify
    to_retire     = shopify_skus - php_skus      # in Shopify but gone from PHP
    to_check      = php_skus & shopify_skus      # in both — check for updates

    print(f"  → New: {len(to_create)} | Retire: {len(to_retire)} | Update-check: {len(to_check)}")

    # ── 4a. Create new products ──────────────────────────────────────────────
    nc_id       = st.get("new_collections_id")
    oos_id      = st.get("out_of_stock_id")
    new_pids    = []
    created     = updated = retired = errors = 0

    # Group new SKUs by their variant group
    new_groups  = defaultdict(list)
    for sku in to_create:
        p = php_map[sku]
        new_groups[p["group"]].append(p)

    print(f"\n  [3/4] Creating {len(to_create)} new products...")
    for group_key, group_prods in new_groups.items():
        if len(group_prods) == 1:
            payload = scraper.build_single_payload(group_prods[0], ptype, tags)
        else:
            payload = scraper.build_variant_payload(group_prods, ptype, tags)

        prod = shopify.create_product(payload)
        if prod:
            pid = prod["id"]
            new_pids.append(pid)
            # Link each variant to its matching image so the storefront
            # switches photos correctly when a variant is selected
            if len(group_prods) > 1:
                prod_variants = prod.get("variants", [])
                prod_images = prod.get("images", [])
                for vi, variant in enumerate(prod_variants):
                    if vi < len(prod_images):
                        shopify.update_variant_image(variant["id"], prod_images[vi]["id"])
        # Add to category collection
        shopify.add_to_collection(pid, col_id)
        # Add to New Collections
            if nc_id:
            shopify.add_to_collection(pid, nc_id)
                st.setdefault("new_products_this_week", []).append(pid)
        created += len(group_prods)
            if created <= 10 or created % 100 == 0:
                name = group_prods[0]["name"]
                print(f"    [{created}] {name[:50]} (${group_prods[0]['price']})", flush=True)
        else:
            errors += len(group_prods)
        time.sleep(config.API_DELAY)

    # ── 4b. Check existing products for price/title drift ────────────────────
    print(f"\n  [3b] Checking {len(to_check)} existing products for changes...")
    changed = 0
    for sku in to_check:
        php_p   = php_map[sku]
        shop_p  = shopify_sku_map[sku]

        # Price changed?
        php_price = f"{float(php_p['price']):.2f}"
        if shop_p["price"] != php_price:
            shopify.update_variant(shop_p["variant_id"], price=php_price)
            changed += 1

        # No image?
        if not shop_p["has_img"]:
            imgs = scraper.get_images(php_p["imgfile"], php_p["name"], sku)
            for img in imgs:
                shopify.add_image(shop_p["product_id"], img["src"], img["alt"])
            changed += 1

        time.sleep(config.API_DELAY * 0.5)

    if changed:
        updated = changed
        print(f"    Updated {updated} products")

    # ── 4c. Retire products missing from PHP ──────────────────────────────────
    print(f"\n  [4/4] Retiring {len(to_retire)} products no longer on PHP site...")
    if to_retire:
        # Ensure "Out of Stock" collection exists
        if not oos_id:
            oos_id = shopify.get_or_create_collection(
                config.OUT_OF_STOCK_TITLE, sort_order="created-desc")
            st["out_of_stock_id"] = oos_id

        # Get current collects for this category (for removal)
        cat_collects = shopify.get_collects(col_id)

        for sku in to_retire:
            pid = shopify_sku_map[sku]["product_id"]
            # Set inventory to 0
            shopify.update_variant(shopify_sku_map[sku]["variant_id"],
                                   inventory_quantity=0)
            # Add to Out of Stock
            if oos_id:
                shopify.add_to_collection(pid, oos_id)
            # Remove from category collection
            collect_id = cat_collects.get(pid)
            if collect_id:
                shopify.remove_from_collection(collect_id)
            retired += 1
            time.sleep(config.API_DELAY)

    # ── Summary ───────────────────────────────────────────────────────────────
    stats = {"created": created, "updated": updated, "retired": retired, "errors": errors}
    st.setdefault("last_sync_stats", {})[cat_key] = stats
    print(f"\n  ✓ {cat_key}: Created={created} Updated={updated} Retired={retired} Errors={errors}")
    return stats

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    run_start = datetime.now(timezone.utc)
    print(f"\n{'='*60}")
    print(f"  AMAARA WORLD — INVENTORY SYNC")
    print(f"  {run_start.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"  Store: {config.SHOPIFY_STORE}")
    print(f"{'='*60}")

    # Load state
    st = state.load()

    # Ensure "Out of Stock" collection exists
    if not st.get("out_of_stock_id"):
        st["out_of_stock_id"] = shopify.get_or_create_collection(
            config.OUT_OF_STOCK_TITLE, sort_order="created-desc")
        print(f"  Out of Stock collection: {st['out_of_stock_id']}")

    # Ensure "New Collections" collection exists
    if not st.get("new_collections_id"):
        st["new_collections_id"] = shopify.get_or_create_collection(
            config.NEW_COLLECTIONS_TITLE, sort_order="created-desc")
        st["new_collections_date"] = state.today_iso()
        print(f"  New Collections: {st['new_collections_id']}")

    # Monday: archive last week's New Collections
    if state.is_monday():
        nc_date = st.get("new_collections_date")
        today   = state.today_iso()
        if nc_date != today:   # Only archive if it was created on a previous Monday
            st = monday_archive(st)

    # Sync each collection in order
    order = st.get("collection_run_order", list(config.COLLECTIONS.keys()))
    if len(sys.argv) > 1 and sys.argv[1].strip():
        requested = sys.argv[1].strip().lower()
        if requested in config.COLLECTIONS:
            order = [requested]
            print(f"  Running single category: {requested}")
        else:
            print(f"  ⚠ Unknown category '{requested}' — running full order instead")
    total = {"created": 0, "updated": 0, "retired": 0, "errors": 0}

    for cat_key in order:
        if cat_key not in config.COLLECTIONS:
            continue
        try:
            stats = sync_collection(cat_key, st)
            for k in total:
                total[k] += stats.get(k, 0)
        except Exception as e:
            print(f"\n  ✗ Error syncing {cat_key}: {e}")
            import traceback; traceback.print_exc()

        # Save state after each collection (resilient to interruption)
        st["last_run"] = run_start.isoformat()
        if shopify.DRY_RUN:
            print("  [DRY RUN] Skipping state.json write")
        else:
            state.save(st)

    # Final summary
    elapsed = (datetime.now(timezone.utc) - run_start).seconds // 60
    print(f"\n{'='*60}")
    print(f"  SYNC COMPLETE — {elapsed} minutes")
    print(f"  Created: {total['created']}")
    print(f"  Updated: {total['updated']}")
    print(f"  Retired: {total['retired']} (moved to Out of Stock)")
    print(f"  Errors:  {total['errors']}")
    print(f"  New Collections: {config.SHOPIFY_STORE}/collections/new-collections")
    print(f"{'='*60}\n")

    # Exit with error code if too many errors
    if total["errors"] > total["created"] * 0.5 and total["created"] > 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
