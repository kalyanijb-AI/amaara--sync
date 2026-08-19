"""
create_finger_rings_collection.py — Create a published "Finger Rings" collection
==================================================================================

The existing "CZ Finger Rings" collection (467 products, id from
config.COLLECTIONS["rings"]) is not published to any sales channel, so there
is no browsable Rings page on the storefront even though direct product
links work fine.

This creates a brand-new collection titled "Finger Rings" (published=True at
creation, per shopify.get_or_create_collection), and adds every product
currently in the old collection to it.

After this runs, update config.COLLECTIONS["rings"] to the new collection id
printed at the end, so future syncs/backfills target the new published
collection going forward.

Usage:
  python create_finger_rings_collection.py
"""
import time
import config, shopify

def main():
    old_col_id = config.COLLECTIONS["rings"]
    print(f"Fetching products from existing collection {old_col_id} (CZ Finger Rings)...")
    products = shopify.get_collection_products(old_col_id, "id,title")
    print(f" -> {len(products)} products found")

    print("\nCreating/finding 'Finger Rings' collection...")
    new_col_id = shopify.get_or_create_collection("Finger Rings")
    if not new_col_id or new_col_id == -1:
        print("ERROR: could not create/find collection")
        return
    print(f" -> Finger Rings collection id: {new_col_id}")

    added = errors = 0
    for i, p in enumerate(products, 1):
        ok = shopify.add_to_collection(p["id"], new_col_id)
        if ok:
            added += 1
        else:
            errors += 1
        if i <= 10 or i % 50 == 0:
            name = p.get("title", "?")[:50]
            status = "OK" if ok else "FAIL"
            print(f"  [{i}/{len(products)}] {name} -> {status}", flush=True)
        time.sleep(config.API_DELAY)

    print(f"\nDone. Added={added} Errors={errors} New collection id={new_col_id}")
    print("NOTE: update config.COLLECTIONS['rings'] to this new id so future syncs use it.")

if __name__ == "__main__":
    main()
