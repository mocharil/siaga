"""Clear stale RDAP negative-cache entries for subdomains.

Before the bug fix in lib/rdap.py (commit TBD), lookup() stored the raw
subdomain string as the cache key.  This meant entries like:
  "investors.spotify.com.id2.bumiayuvpn.web.id" -> is_not_found=1
were cached, permanently blocking future network lookups.

Post-fix, lookup() always uses the registrable domain as the cache key.
This script removes all negative-cache entries (is_not_found=1) that
contain more than two dot-separated labels for generic TLDs, or more than
three labels for .id compound SLDs — i.e. entries that are clearly
subdomains, not registrable domains.

Safe to run repeatedly; the correct entries will be re-fetched on next
pipeline run with --allow-network.
"""
import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "siaga.db"

ID_COMPOUND_SLDS = {"co.id", "go.id", "ac.id", "or.id", "web.id"}


def is_subdomain_entry(domain: str) -> bool:
    """Return True if 'domain' in rdap_cache is a subdomain (not registrable)."""
    labels = domain.strip().lower().rstrip(".").split(".")
    if len(labels) < 2:
        return False  # shouldn't happen, but don't delete
    last_two = ".".join(labels[-2:])
    if last_two in ID_COMPOUND_SLDS:
        # registrable = 3 labels; anything with > 3 labels is a subdomain
        return len(labels) > 3
    # generic TLD: registrable = 2 labels; anything with > 2 is a subdomain
    return len(labels) > 2


with sqlite3.connect(str(DB_PATH)) as conn:
    cur = conn.execute(
        "SELECT domain FROM rdap_cache WHERE is_not_found = 1"
    )
    all_negative = [r[0] for r in cur.fetchall()]

    to_delete = [d for d in all_negative if is_subdomain_entry(d)]
    print(f"Total negative cache entries: {len(all_negative)}")
    print(f"Entries that are subdomains (to delete): {len(to_delete)}")

    if to_delete:
        conn.executemany(
            "DELETE FROM rdap_cache WHERE domain = ?",
            [(d,) for d in to_delete]
        )
        conn.commit()
        print("Deleted stale subdomain negative-cache entries.")
    else:
        print("No stale subdomain entries found — cache already clean.")

    # Show remaining negative cache for sanity
    remaining = conn.execute(
        "SELECT COUNT(*) FROM rdap_cache WHERE is_not_found = 1"
    ).fetchone()[0]
    print(f"Remaining negative cache entries: {remaining}")
    total_positive = conn.execute(
        "SELECT COUNT(*) FROM rdap_cache WHERE is_not_found = 0"
    ).fetchone()[0]
    print(f"Positive cache entries (kept): {total_positive}")
