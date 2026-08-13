# Amaara World — Shopify Inventory Sync

Automated sync from **amaaraworld.com** PHP catalog → Shopify store.

## Schedule
- **Monday 2am UTC** — Full sync + archive "New Collections" into proper categories
- **Wednesday 2am UTC** — Full sync
- **Friday 2am UTC** — Full sync

## What it does
1. Scrapes each PHP category (choker, classic, collar, traditional, earrings, bracelets, pendants, rings)
2. Groups color variants under one listing (by image filename prefix)
3. **Creates** new products with 3 images (main + A + B angles)
4. **Updates** price/images on existing products if they changed
5. **Retires** products missing from PHP → moves to "Out of Stock" collection, inventory = 0
6. **New Collections** — everything new this week goes there; archived to categories every Monday

## Setup

### 1. Fork this repo

### 2. Add GitHub Secrets
Go to **Settings → Secrets and variables → Actions → New repository secret**

| Secret | Value |
|--------|-------|
| `SHOPIFY_TOKEN` | `<your-shopify-admin-api-token>` |
| `SHOPIFY_STORE` | `amaaraworld.myshopify.com` |

### 3. Enable Actions
Go to **Actions tab** → Enable workflows

### 4. Test with manual run
Go to **Actions → Amaara Inventory Sync → Run workflow**
- Leave "category" empty for full sync
- Or enter `choker` to test just one category
- Check "dry run" to scrape without writing to Shopify

## Manual run (local Mac)
```bash
cd amaara-sync
pip3 install -r requirements.txt
SHOPIFY_TOKEN=<your-shopify-admin-api-token> python3 sync.py
# Or one category:
SHOPIFY_TOKEN=<your-shopify-admin-api-token> python3 sync.py choker
```

## Collections managed

| Shopify Collection | PHP Category | ID |
|--------------------|-------------|-----|
| Choker Necklaces | choker-necklaces | 504236278060 |
| Classic Necklaces | classic-necklace | 504236376364 |
| Collar Necklaces | collar-necklace | 504236343596 |
| Traditional Necklaces | traditional-necklaces | 504236409132 |
| Earrings | medium-earrings + others | 504236474668 |
| CZ Bracelets | cz-braclets + cz-bangles | 504236146988 |
| Pendant Sets | pendant-sets | 504546361644 |
| Finger Rings | finger-rings | 504546328876 |
| **New Collections** | All new this week | auto-created |
| **Out of Stock** | Products removed from PHP | auto-created |

## How variant grouping works
Products with matching image filename prefixes (minus last 2 digits) are grouped
as one Shopify listing with Style 1, Style 2, etc. as variants.

Example: `553032AQ12CA33617.jpg` and `553032AQ12CA33618.jpg` share prefix
`553032AQ12CA3361` → grouped as one product with 2 variants.
