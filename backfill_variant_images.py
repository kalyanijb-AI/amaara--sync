"""
backfill_variant_images.py — Backfill variant-to-image links
============================================================

Retroactively links each variant of an existing multi-variant product
to its matching image (Shopify variant.image_id), for products created
BEFORE the variant-image-linking fix landed in sync.py (2026-08-18).

Without this, clicking a variant option on the storefront does not
switch the displayed photo, because the variant has no image_id set.

sync.py now sets this link at creation time for every category going
forward. This script is a one-time (per category) catch-up pass for
products that were created earlier.

Usage:
  python backfill_variant_images.py collar,choker,classic,traditional
  python backfill_variant_images.py all
"""
import sys, time
import config, shopify


def backfill_category(cat_key):
    if cat_key not in config.COLLECTIONS:
        print(f"  ! Unknown category '{cat_key}' — skipping")
        return {"checked": 0, "fixed_products": 0, "fixed_variants": 0, "already_linked": 0, "errors": 0}

    col_id = config.COLLECTIONS[cat_key]
    print(f"\n{'='*60}")
    print(f" BACKFILL VARIANT IMAGES — {cat_key.upper()} (collection {col_id})")
    print(f"{'='*60}")

    products = shopify.get_collection_products(col_id, "id,title,variants,images")
    print(f"  → {len(products)} products in collection")

    checked = fixed_products = fixed_variants = already_linked = errors = 0

    for p in products:
        variants = p.get("variants", [])
        images = p.get("images", [])
        checked += 1
        if len(variants) <= 1:
            continue
        if all(v.get("image_id") for v in variants):
            already_linked += 1
            continue

        product_fixed = False
        for vi, variant in enumerate(variants):
            if variant.get("image_id"):
                continue
            if vi < len(images):
                ok = shopify.update_variant_image(variant["id"], images[vi]["id"])
                if ok:
                    fixed_variants += 1
                    product_fixed = True
                else:
                    errors += 1
                time.sleep(config.API_DELAY * 0.5)

        if product_fixed:
            fixed_products += 1
            if fixed_products <= 10 or fixed_products % 50 == 0:
                name = p.get("title", "?")[:50]
                print(f"  [{fixed_products}] Fixed: {name} ({len(variants)} variants)", flush=True)

    stats = {"checked": checked, "fixed_products": fixed_products,
             "fixed_variants": fixed_variants, "already_linked": already_linked,
             "errors": errors}
    print(f"\n  ✓ {cat_key}: Checked={checked} Fixed={fixed_products} products "
          f"({fixed_variants} variants) | Already linked={already_linked} | Errors={errors}")
    return stats


def main():
    if len(sys.argv) < 2 or not sys.argv[1].strip():
        print("Usage: python backfill_variant_images.py <cat1,cat2,...|all>")
        sys.exit(1)

    arg = sys.argv[1].strip().lower()
    if arg == "all":
        cat_keys = list(config.COLLECTIONS.keys())
    else:
        cat_keys = [c.strip() for c in arg.split(",") if c.strip()]

    print(f"\n{'#'*60}")
    print(f"# VARIANT IMAGE BACKFILL — categories: {', '.join(cat_keys)}")
    print(f"{'#'*60}")

    total = {"checked": 0, "fixed_products": 0, "fixed_variants": 0, "errors": 0}
    for cat_key in cat_keys:
        try:
            stats = backfill_category(cat_key)
            for k in total:
                total[k] += stats.get(k, 0)
        except Exception as e:
            print(f"\n  ✗ Error backfilling {cat_key}: {e}")
            import traceback; traceback.print_exc()

    print(f"\n{'='*60}")
    print(f" BACKFILL COMPLETE")
    print(f" Total checked:  {total['checked']}")
    print(f" Total fixed:    {total['fixed_products']} products / {total['fixed_variants']} variants")
    print(f" Total errors:   {total['errors']}")
    print(f"{'='*60}\n")

    if total["errors"] > 0 and total["fixed_products"] == 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
