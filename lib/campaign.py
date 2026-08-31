"""Campaign Clustering Module (T23).

Groups domain_findings that likely belong to the same phishing campaign,
using two independent signals of very different strength:

  - nameserver: the finding's nameservers point at the same operator
    infrastructure. This is a hard technical fact — an attacker running
    multiple lookalike domains from the same DNS provider account leaves
    this trace whether or not they intend to.
  - brand_pattern: multiple distinct domains target the same watchlist
    brand within a short time window, with no shared infrastructure
    confirmed. This is a coincidence-level heuristic, not proof of a
    single actor — it is reported separately and must never be presented
    with the same confidence as a nameserver match.

Clustering is idempotent: running it repeatedly on the same domain_findings
re-derives the same cluster_key -> campaign_id mapping (UNIQUE(cluster_type,
cluster_key) in the campaigns table) rather than creating duplicates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path
import sqlite3

from lib.domain_utils import registrable_domain as _registrable_domain

logger = logging.getLogger("siaga.campaign")

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "siaga.db"

# _registrable_domain is now imported from lib.domain_utils (shared authoritative source).
# lib/rdap.py also imports from there — this ensures both modules always use
# identical extraction logic without a circular import.

MIN_NAMESERVER_CLUSTER_SIZE = 2
MIN_BRAND_PATTERN_CLUSTER_SIZE = 3
BRAND_PATTERN_WINDOW_DAYS = 7


@dataclass
class CampaignClusteringSummary:
    nameserver_clusters_found: int = 0
    nameserver_domains_labeled: int = 0
    brand_pattern_clusters_found: int = 0
    brand_pattern_domains_labeled: int = 0



def nameserver_signature(nameservers_field: str | None) -> str | None:
    """Compute a stable signature for a domain's nameserver set.

    Two findings sharing this signature point at the same operator
    infrastructure regardless of which specific ns1/ns2/... hostnames they
    were assigned. Returns None if there is not enough information to form
    a signature (empty, or every nameserver fails to parse).
    """
    if not nameservers_field:
        return None

    raw_hosts = [h.strip() for h in nameservers_field.split(";") if h.strip()]
    parents = {p for p in (_registrable_domain(h) for h in raw_hosts) if p}
    if not parents:
        return None

    return ",".join(sorted(parents))


def _upsert_campaign(
    conn: sqlite3.Connection,
    cluster_type: str,
    cluster_key: str,
    member_count: int,
    now_iso: str,
) -> int:
    """Insert or update a campaigns row, returning its id."""
    conn.execute(
        """
        INSERT INTO campaigns (cluster_type, cluster_key, member_count, first_detected_at, last_updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(cluster_type, cluster_key) DO UPDATE SET
            member_count = excluded.member_count,
            last_updated_at = excluded.last_updated_at
        """,
        (cluster_type, cluster_key, member_count, now_iso, now_iso),
    )
    row = conn.execute(
        "SELECT id FROM campaigns WHERE cluster_type = ? AND cluster_key = ?",
        (cluster_type, cluster_key),
    ).fetchone()
    return row[0]


def _cluster_by_nameserver(conn: sqlite3.Connection, now_iso: str) -> tuple[int, int]:
    """Group findings sharing a nameserver signature. Returns (clusters, domains_labeled)."""
    rows = conn.execute(
        "SELECT id, domain, nameservers FROM domain_findings WHERE nameservers IS NOT NULL AND nameservers != ''"
    ).fetchall()

    groups: dict[str, list[int]] = {}
    for finding_id, domain, ns_field in rows:
        sig = nameserver_signature(ns_field)
        if sig:
            groups.setdefault(sig, []).append(finding_id)

    clusters_found = 0
    domains_labeled = 0
    for sig, finding_ids in groups.items():
        if len(finding_ids) < MIN_NAMESERVER_CLUSTER_SIZE:
            continue
        campaign_id = _upsert_campaign(conn, "nameserver", sig, len(finding_ids), now_iso)
        conn.executemany(
            "UPDATE domain_findings SET campaign_id = ? WHERE id = ?",
            [(campaign_id, fid) for fid in finding_ids],
        )
        clusters_found += 1
        domains_labeled += len(finding_ids)

    return clusters_found, domains_labeled


def _cluster_by_brand_pattern(conn: sqlite3.Connection, now_iso: str) -> tuple[int, int]:
    """Group findings targeting the same brand within a rolling time window.

    Only labels findings that did NOT already receive a (stronger)
    nameserver-based campaign_id — a confirmed infrastructure link should
    never be downgraded to a coincidence-level one.

    Returns (clusters, domains_labeled).
    """
    rows = conn.execute(
        """
        SELECT id, domain, matched_brand, match_method, first_seen
        FROM domain_findings
        WHERE campaign_id IS NULL
          AND matched_brand IS NOT NULL AND matched_brand != ''
        """
    ).fetchall()

    groups: dict[tuple[str, str], list[tuple[int, str]]] = {}
    for finding_id, domain, brand, method, first_seen in rows:
        key = (brand.strip().lower(), (method or "").strip().lower())
        groups.setdefault(key, []).append((finding_id, first_seen or ""))

    clusters_found = 0
    domains_labeled = 0
    for (brand, method), members in groups.items():
        members_sorted = sorted(members, key=lambda m: m[1])
        window_members = _largest_time_window(members_sorted, BRAND_PATTERN_WINDOW_DAYS)
        if len(window_members) < MIN_BRAND_PATTERN_CLUSTER_SIZE:
            continue

        cluster_key = f"{brand}|{method}"
        campaign_id = _upsert_campaign(conn, "brand_pattern", cluster_key, len(window_members), now_iso)
        conn.executemany(
            "UPDATE domain_findings SET campaign_id = ? WHERE id = ?",
            [(campaign_id, fid) for fid, _ in window_members],
        )
        clusters_found += 1
        domains_labeled += len(window_members)

    return clusters_found, domains_labeled


def _largest_time_window(
    members_sorted: list[tuple[int, str]], window_days: int
) -> list[tuple[int, str]]:
    """Return the largest subset of chronologically sorted members whose
    first_seen timestamps all fall within `window_days` of each other.

    Uses a simple sliding window over ISO timestamp strings; entries with
    unparseable timestamps are dropped rather than crashing the clustering
    pass.
    """
    parsed: list[tuple[int, datetime]] = []
    for fid, ts_str in members_sorted:
        try:
            clean = ts_str.replace("Z", "+00:00")
            dt = datetime.fromisoformat(clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            parsed.append((fid, dt))
        except (ValueError, AttributeError):
            continue

    parsed.sort(key=lambda p: p[1])
    best: list[tuple[int, datetime]] = []
    left = 0
    for right in range(len(parsed)):
        while (parsed[right][1] - parsed[left][1]).days > window_days:
            left += 1
        if right - left + 1 > len(best):
            best = parsed[left:right + 1]

    return [(fid, dt.isoformat()) for fid, dt in best]


def apply_campaign_labels(db_path: Path | str | None = None) -> CampaignClusteringSummary:
    """Run both clustering passes over the current domain_findings table.

    Idempotent: safe to call repeatedly (e.g. once per pipeline run) as
    findings accumulate. Nameserver clustering always runs first since it
    is the stronger signal; brand_pattern clustering only considers
    findings the nameserver pass left unlabeled.
    """
    resolved_db = Path(db_path) if db_path else DEFAULT_DB_PATH
    now_iso = datetime.now(timezone.utc).isoformat()
    summary = CampaignClusteringSummary()

    with sqlite3.connect(str(resolved_db)) as conn:
        ns_clusters, ns_domains = _cluster_by_nameserver(conn, now_iso)
        summary.nameserver_clusters_found = ns_clusters
        summary.nameserver_domains_labeled = ns_domains

        bp_clusters, bp_domains = _cluster_by_brand_pattern(conn, now_iso)
        summary.brand_pattern_clusters_found = bp_clusters
        summary.brand_pattern_domains_labeled = bp_domains

        conn.commit()

    logger.info(
        "Campaign clustering: %d nameserver cluster(s) / %d domains, "
        "%d brand-pattern cluster(s) / %d domains",
        summary.nameserver_clusters_found,
        summary.nameserver_domains_labeled,
        summary.brand_pattern_clusters_found,
        summary.brand_pattern_domains_labeled,
    )
    return summary
