"""Similarity Detection Module (T16).

Implements four sequential matching techniques (Damerau-Levenshtein, homoglyph normalization,
misleading keyword positions, and directed permutations) without external dependencies.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import logging
from pathlib import Path
import re
import urllib.parse

from lib.homoglyph import decode_punycode, normalize as normalize_homoglyphs

logger = logging.getLogger("siaga.similarity")

DEFAULT_WATCHLIST_PATH = Path(__file__).resolve().parent.parent / "data" / "watchlist.csv"

# ------------------------------------------------------------------------------
# CONSTANTS & THRESHOLDS (Calibratable in T21)
# ------------------------------------------------------------------------------
SHORT_NAME_MAX_LEN = 4           # Token length <= 4 uses exact keyword matching only
MEDIUM_NAME_MAX_DIST = 2         # Length 5-8 allowed max edit distance
LONG_NAME_MAX_DIST = 3           # Length > 8 allowed max edit distance


@dataclass
class Match:
    brand_name: str
    official_domain: str
    method: str  # "keyword" | "edit_distance" | "homoglyph" | "permutation"
    similarity_score: float  # 0.0 - 1.0 (1.0 = identical/highest risk)
    matched_term: str


@dataclass
class WatchlistEntry:
    brand_name: str
    official_domain: str
    category: str
    match_mode: str
    clean_terms: list[tuple[str, str, int, set[str]]]  # (term, term_clean, len, char_set)
    off_stem: str


_WATCHLIST_CACHE: list[WatchlistEntry] | None = None


def damerau_levenshtein_distance(s1: str, s2: str) -> int:
    """Fast Damerau-Levenshtein distance calculation with transposition."""
    s1, s2 = s1.lower(), s2.lower()
    len1, len2 = len(s1), len(s2)

    if s1 == s2:
        return 0
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    # Matrix
    d = [[0] * (len2 + 2) for _ in range(len1 + 2)]
    max_dist = len1 + len2
    d[0][0] = max_dist

    for i in range(0, len1 + 1):
        d[i + 1][0] = max_dist
        d[i + 1][1] = i
    for j in range(0, len2 + 1):
        d[0][j + 1] = max_dist
        d[1][j + 1] = j

    da: dict[str, int] = {}

    for i in range(1, len1 + 1):
        db = 0
        for j in range(1, len2 + 1):
            k = da.get(s2[j - 1], 0)
            l = db
            cost = 0 if s1[i - 1] == s2[j - 1] else 1
            if cost == 0:
                db = j

            d[i + 1][j + 1] = min(
                d[i][j + 1] + 1,        # Deletion
                d[i + 1][j] + 1,        # Insertion
                d[i][j] + cost,         # Substitution
                d[k][l] + (i - k - 1) + 1 + (j - l - 1),  # Transposition
            )
        da[s1[i - 1]] = i

    return d[len1 + 1][len2 + 1]


def load_watchlist(csv_path: Path | str | None = None) -> list[WatchlistEntry]:
    """Load, pre-index, and cache institutional watchlist from CSV."""
    global _WATCHLIST_CACHE
    if _WATCHLIST_CACHE is not None and csv_path is None:
        return _WATCHLIST_CACHE

    resolved_path = Path(csv_path) if csv_path else DEFAULT_WATCHLIST_PATH
    if not resolved_path.exists():
        logger.warning("Watchlist file not found at %s", resolved_path)
        return []

    entries: list[WatchlistEntry] = []
    with open(resolved_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            brand = row["brand_name"].strip()
            off_domain = row["official_domain"].strip().lower()
            raw_aliases = [brand] + [a.strip() for a in row["aliases"].split(";") if a.strip()]

            clean_terms: list[tuple[str, str, int, set[str]]] = []
            seen_clean = set()
            for t in raw_aliases:
                tc = t.lower().replace(" ", "")
                if tc and tc not in seen_clean:
                    seen_clean.add(tc)
                    clean_terms.append((t, tc, len(tc), set(tc)))

            off_stem = off_domain.split(".")[0]

            entries.append(WatchlistEntry(
                brand_name=brand,
                official_domain=off_domain,
                category=row["category"].strip(),
                match_mode=row["match_mode"].strip(),
                clean_terms=clean_terms,
                off_stem=off_stem,
            ))

    if csv_path is None:
        _WATCHLIST_CACHE = entries
    return entries


def _extract_domain_labels(domain: str) -> list[str]:
    """Extract individual domain labels, subdomains, and hyphenated parts."""
    clean = domain.strip().lower().rstrip(".")
    # Remove common TLD extensions (.co.id, .com, .xyz, etc.)
    tld_parts = clean.split(".")
    if len(tld_parts) >= 3 and tld_parts[-2] in ["co", "web", "my", "or", "go", "ac", "biz"] and tld_parts[-1] == "id":
        core_labels = tld_parts[:-2]
    elif len(tld_parts) >= 2:
        core_labels = tld_parts[:-1]
    else:
        core_labels = tld_parts

    tokens: list[str] = []
    for label in core_labels:
        if label:
            tokens.append(label)
            # Split hyphenated parts: e.g. bca-promo -> ['bca-promo', 'bca', 'promo']
            if "-" in label:
                subparts = [p for p in label.split("-") if p]
                tokens.extend(subparts)
    return tokens


def find_similar(
    domain: str,
    watchlist: list[WatchlistEntry] | list[dict[str, str]] | None = None,
    watchlist_path: Path | str | None = None,
) -> list[Match]:
    """Identify phishing similarities between target domain and monitored institutions."""
    clean_domain = domain.strip().lower().rstrip(".")
    if not clean_domain or "." not in clean_domain:
        return []

    raw_entries = watchlist if watchlist is not None else load_watchlist(watchlist_path)
    if not raw_entries:
        return []

    # Normalize entries to WatchlistEntry objects
    entries: list[WatchlistEntry] = []
    for item in raw_entries:
        if isinstance(item, WatchlistEntry):
            entries.append(item)
        else:
            b = item["brand_name"].strip()
            od = item["official_domain"].strip().lower()
            aliases = [b] + [a.strip() for a in item.get("aliases", "").split(";") if a.strip()]
            clean_terms = []
            seen_clean = set()
            for t in aliases:
                tc = t.lower().replace(" ", "")
                if tc and tc not in seen_clean:
                    seen_clean.add(tc)
                    clean_terms.append((t, tc, len(tc)))
            entries.append(WatchlistEntry(
                brand_name=b,
                official_domain=od,
                category=item.get("category", ""),
                match_mode=item.get("match_mode", "edit_distance"),
                clean_terms=clean_terms,
                off_stem=od.split(".")[0],
            ))

    # 1. Whitelist Check: If domain is official domain or subdomain -> NOT a match
    for entry in entries:
        off_domain = entry.official_domain
        if clean_domain == off_domain or clean_domain.endswith(f".{off_domain}"):
            return []

    # 2. Institutional TLD Safety Rules:
    # - .go.id domains are strictly vetted by Kominfo; legitimate for government brands
    # - .ac.id / .sch.id / .mil.id are strictly vetted academic/military institutions
    is_gov_tld = clean_domain.endswith(".go.id")
    is_academic_tld = clean_domain.endswith(".ac.id") or clean_domain.endswith(".sch.id") or clean_domain.endswith(".mil.id")

    domain_labels = _extract_domain_labels(clean_domain)
    decoded_domain, is_punycode = decode_punycode(clean_domain)
    homoglyph_domain = normalize_homoglyphs(decoded_domain)
    homoglyph_labels = _extract_domain_labels(homoglyph_domain)

    # --------------------------------------------------------------------------
    # TECHNIQUE 1: Keyword in Misleading Position (Subdomain / Hyphen)
    # --------------------------------------------------------------------------
    keyword_matches: list[Match] = []
    for entry in entries:
        if is_gov_tld and entry.category == "pemerintah":
            continue
        brand = entry.brand_name
        off_domain = entry.official_domain

        for term, term_clean, term_len, _ in entry.clean_terms:
            if term_len < 3:
                continue
            if is_academic_tld and term_len <= 4:
                continue

            for label in domain_labels:
                # Exact label match in non-official domain (e.g. bca.promo-site.xyz -> 'bca')
                if label == term_clean:
                    keyword_matches.append(Match(
                        brand_name=brand,
                        official_domain=off_domain,
                        method="keyword",
                        similarity_score=0.98,
                        matched_term=term,
                    ))
                    break

                # Word boundary / hyphenated match (e.g. 'klikbca-update', 'bank-mandiri')
                if term_len >= 4 and (
                    label.startswith(f"{term_clean}-")
                    or label.endswith(f"-{term_clean}")
                    or f"-{term_clean}-" in label
                ):
                    keyword_matches.append(Match(
                        brand_name=brand,
                        official_domain=off_domain,
                        method="keyword",
                        similarity_score=0.92,
                        matched_term=term,
                    ))
                    break

    if keyword_matches:
        keyword_matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return [keyword_matches[0]]

    # --------------------------------------------------------------------------
    # TECHNIQUE 2: Homoglyph & Punycode Normalization
    # --------------------------------------------------------------------------
    homoglyph_matches: list[Match] = []
    if is_punycode or homoglyph_domain != clean_domain:
        for entry in entries:
            brand = entry.brand_name
            off_domain = entry.official_domain

            for term, term_clean, term_len, _ in entry.clean_terms:
                if term_len < 3:
                    continue

                for h_label in homoglyph_labels:
                    if h_label == term_clean:
                        homoglyph_matches.append(Match(
                            brand_name=brand,
                            official_domain=off_domain,
                            method="homoglyph",
                            similarity_score=0.95,
                            matched_term=term,
                        ))
                        break

    if homoglyph_matches:
        homoglyph_matches.sort(key=lambda m: m.similarity_score, reverse=True)
        return [homoglyph_matches[0]]

    # --------------------------------------------------------------------------
    # TECHNIQUE 3: Damerau-Levenshtein Distance with Set Pre-filtering
    # --------------------------------------------------------------------------
    dl_matches: list[Match] = []
    for entry in entries:
        brand = entry.brand_name
        off_domain = entry.official_domain

        for term, term_clean, term_len, term_set in entry.clean_terms:
            if term_len <= SHORT_NAME_MAX_LEN:
                continue

            max_allowed_dist = 1 if term_len <= 5 else (MEDIUM_NAME_MAX_DIST if term_len <= 8 else LONG_NAME_MAX_DIST)

            for label in domain_labels:
                label_len = len(label)
                if abs(label_len - term_len) > max_allowed_dist:
                    continue

                # Set pre-filter: common characters must be at least (len - max_allowed_dist)
                if len(set(label) & term_set) < (term_len - max_allowed_dist):
                    continue

                dist = damerau_levenshtein_distance(label, term_clean)
                if 1 <= dist <= max_allowed_dist:
                    score = max(0.60, 1.0 - (dist / max(term_len, label_len)))
                    dl_matches.append(Match(
                        brand_name=brand,
                        official_domain=off_domain,
                        method="edit_distance",
                        similarity_score=round(score, 2),
                        matched_term=term,
                    ))

    if dl_matches:
        dl_matches.sort(key=lambda m: (m.similarity_score, -len(m.matched_term)), reverse=True)
        return [dl_matches[0]]

    # --------------------------------------------------------------------------
    # TECHNIQUE 4: Directed Typo Permutations
    # --------------------------------------------------------------------------
    for entry in entries:
        off_stem = entry.off_stem
        if len(off_stem) > 4:
            for label in domain_labels:
                if label != off_stem and damerau_levenshtein_distance(label, off_stem) == 1:
                    return [Match(
                        brand_name=entry.brand_name,
                        official_domain=entry.official_domain,
                        method="permutation",
                        similarity_score=0.85,
                        matched_term=off_stem,
                    )]

    return []
