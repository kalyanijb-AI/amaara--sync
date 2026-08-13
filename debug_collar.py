import json
import config, shopify

col_id = config.COLLECTIONS["collar"]
print(f"Collection ID: {col_id}")
print(f"SHOPIFY_API base: {config.SHOPIFY_API}")

r = shopify.api("get", f"custom_collections/{col_id}.json")
print(f"\ncustom_collections/{{id}}.json -> status {r.status_code if r else 'NO RESPONSE'}")
if r is not None:
    print(f"  body: {r.text[:400]}")

r2 = shopify.api("get", f"smart_collections/{col_id}.json")
print(f"\nsmart_collections/{{id}}.json -> status {r2.status_code if r2 else 'NO RESPONSE'}")
if r2 is not None:
    print(f"  body: {r2.text[:400]}")

r3 = shopify.api("get", "products.json", params={"collection_id": col_id, "limit": 5, "fields": "id,title,variants"})
print(f"\nproducts.json?collection_id filter -> status {r3.status_code if r3 else 'NO RESPONSE'}")
if r3 is not None and r3.ok:
    data = r3.json().get("products", [])
    print(f"  returned {len(data)} products")
    for p in data[:3]:
        skus = [v.get("sku") for v in p.get("variants", [])]
        print(f"    id={p['id']} title={p['title'][:40]!r} skus={skus}")
elif r3 is not None:
    print(f"  body: {r3.text[:400]}")

r4 = shopify.api("get", f"collections/{col_id}/products.json", params={"limit": 5})
print(f"\ncollections/{{id}}/products.json -> status {r4.status_code if r4 else 'NO RESPONSE'}")
if r4 is not None and r4.ok:
    data = r4.json().get("products", [])
    print(f"  returned {len(data)} products")
    for p in data[:3]:
        print(f"    id={p.get('id')} title={str(p.get('title'))[:40]!r}")
elif r4 is not None:
    print(f"  body: {r4.text[:400]}")

r5 = shopify.api("get", "collects.json", params={"collection_id": col_id, "limit": 5})
print(f"\ncollects.json?collection_id filter -> status {r5.status_code if r5 else 'NO RESPONSE'}")
if r5 is not None and r5.ok:
    collects = r5.json().get("collects", [])
    print(f"  returned {len(collects)} collects")
    for c in collects[:3]:
        print(f"    {c}")
elif r5 is not None:
    print(f"  body: {r5.text[:400]}")

r6 = shopify.api("get", "products/count.json", params={"collection_id": col_id})
print(f"\nproducts/count.json?collection_id -> status {r6.status_code if r6 else 'NO RESPONSE'}")
if r6 is not None:
    print(f"  body: {r6.text[:200]}")

