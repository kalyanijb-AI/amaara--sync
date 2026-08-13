"""
state.py — Persist sync state between GitHub Actions runs
State is committed back to the repo after each run.
"""
import json, os
from datetime import datetime, timezone
from config import STATE_FILE

_DEFAULT = {
    "last_run":             None,
    "last_monday_run":      None,
    "new_collections_id":   None,   # Current week's "New Collections" collection ID
    "new_collections_date": None,   # ISO date it was created (Monday)
    "new_products_this_week": [],   # product_ids added to New Collections this week
    "out_of_stock_id":      None,   # "Out of Stock" collection ID
    "collection_run_order": ["choker","classic","collar","traditional",
                             "earrings","bracelets","pendants","rings"],
    "last_sync_stats":      {},
}

def load():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                data = json.load(f)
            # Merge in any missing keys from default
            for k, v in _DEFAULT.items():
                data.setdefault(k, v)
            return data
        except Exception as e:
            print(f"  Warning: could not load state ({e}) — using defaults")
    return dict(_DEFAULT)

def save(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)
    print(f"  State saved to {STATE_FILE}")

def commit_and_push(message):
    """Commit state.json to git and push, so progress survives a crash/timeout.
    Safe to call repeatedly — no-ops if there's nothing staged to commit."""
    import subprocess
    try:
        subprocess.run(["git", "config", "user.name", "Amaara Sync Bot"], check=False)
        subprocess.run(["git", "config", "user.email", "sync@amaaraworld.com"], check=False)
        subprocess.run(["git", "add", STATE_FILE], check=False)
        diff = subprocess.run(["git", "diff", "--staged", "--quiet"])
        if diff.returncode == 0:
            print("  No state changes to commit")
            return
        subprocess.run(["git", "commit", "-m", message], check=False)
        push = subprocess.run(["git", "push"], capture_output=True, text=True)
        if push.returncode != 0:
            print(f"  Warning: git push failed: {push.stderr.strip()}")
        else:
            print(f"  ✓ Committed and pushed: {message}")
    except Exception as e:
        print(f"  Warning: commit_and_push failed: {e}")

def is_monday():
    return datetime.now(timezone.utc).weekday() == 0

def today_iso():
    return datetime.now(timezone.utc).date().isoformat()
