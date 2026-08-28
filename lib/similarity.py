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

logger = logging.getLogger("siaga.similarity")

DEFAULT_WATCHLIST_PATH = Path(__file__).resolve().parent.parent / "data" / "watchlist.csv"

# ------------------------------------------------------------------------------
# CONSTANTS & THRESHOLDS (Calibratable in T21)
# ------------------------------------------------------------------------------
SHORT_NAME_MAX_LEN = 4           # Token length <= 4 uses exact keyword matching only
MEDIUM_NAME_MAX_DIST = 2         # Length 5-8 allowed max edit distance
LONG_NAME_MAX_DIST = 3           # Length > 8 allowed max edit distance

# Visual Homoglyph character map (Latin lookalikes + Cyrillic lookalikes)
HOMOGLYPH_MAP = {
    "0": "o",
    "1": "l",
    "3": "e",
    "4": "a",
    "5": "s",
    "8": "b",
    # Cyrillic lookalikes
    "\u0430": "a",  # cyrillic small a
    "\u0441": "c",  # cyrillic small es
    "\u0435": "e",  # cyrillic small ie
    "\u0456": "i",  # cyrillic small byelorussian-ukrainian i
    "\u0458": "j",  # cyrillic small je
    "\u043e": "o",  # cyrillic small o
    "\u0440": "p",  # cyrillic small er
    "\u0455": "s",  # cyrillic small dze
    "\u0445": "x",  # cyrillic small ha
    "\u0443": "y",  # cyrillic small u
}


@dataclass
class Match:
    brand_name: str
    official_domain: str
    method: str  # "keyword" | "edit_distance" | "homoglyph" | "permutation"
    similarity_score: float  # 0.0 - 1.0 (1.0 = identical/highest risk)
    matched_term: str


def damerau_levenshtein_distance(s1: str, s2: str) -> int:
    """Compute Damerau-Levenshtein distance between two strings with transpositions."""
    s1, s2 = s1.lower(), s2.lower()
    len1, len2 = len(s1), len(s2)

    # Edge cases
    if s1 == s2:
        return 0
    if len1 == 0:
        return len2
    if len2 == 0:
        return len1

    # Matrix initialization
    d = [[0] * (len2 + 2) for _ in range(len1 + 2)]
    max_dist = len1 + len2
    d[0][0] = max_dist

    for i in range(0, len1 + 1):
        d[i + 1][0] = max_dist
        d[i + 1][1] = i
    for j in range(0, len2 + 1):
        d[0][j + 1] = max_dist
        d[1][j + 1] = j

    da = {}

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


def normalize_homoglyphs(text: str) -> str:
    """Normalize visually confusing homoglyphs and Cyrillic characters into canonical Latin."""
    result = []
    text_lower = text.lower()

    # Normalize double-characters: rn -> m, vv -> w
    normalized_pairs = text_lower.replace("rn", "m").replace("vv", "w")

    for char in normalized_pairs:
        result.append(HOMOGLYPH_MAP.get(char, char))
    return "".join(result)


def decode_punycode_domain(domain: str) -> tuple[str, bool]:
    """Decode IDN / punycode domain (xn--) to unicode representation."""
    is_punycode = "xn--" in domain.lower()
    if not is_punycode:
        return domain.lower(), False
    try:
        decoded = domain.encode("ascii").decode("idna")
        return decoded.lower(), True
    except Exception:
        return domain.lower(), True


def load_watchlist(csv_path: Path | str | None = None) -> list[dict[str, str]]:
    """Load and cache institutional watchlist from CSV."""
    resolved_path = Path(csv_path) if csv_path else DEFAULT_WATCHLIST_PATH
    if not resolved_path.exists():
        logger.warning("Watchlist file not found at %s", resolved_path)
        return []

    entries: list[dict[str, str]] = []
    with open(resolved_path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            entries.append({
                "brand_name": row["brand_name"].strip(),
                "aliases": row["aliases"].strip(),
                "official_domain": row["official_domain"].strip().lower(),
                "category": row["category"].strip(),
                "match_mode": row["match_mode"].strip(),
            })
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
    watchlist: list[dict[str, str]] | None = None,
    watchlist_path: Path | str | None = None,
) -> list[Match]:
    """Identify phishing similarities between target domain and monitored institutions.

    Runs 4 sequential methods from lowest to highest cost, stopping upon strong matches:
    1. Keyword positioning (subdomain, path, hyphenated brand prefix/suffix)
    2. Damerau-Levenshtein distance (calibrated by target token length)
    3. Homoglyph and Punycode normalization
    4. Directed typo permutations

    Args:
        domain: Domain to inspect (e.g. "bca-update.online", "tokopdia.com").
        watchlist: Optional pre-loaded watchlist list. If None, loads from CSV.
        watchlist_path: Optional path to watchlist CSV.

    Returns:
        List of Match objects describing matched brand, method, and similarity score.
    """
    clean_domain = domain.strip().lower().rstrip(".")
    if not clean_domain or "." not in clean_domain:
        return []

    entries = watchlist if watchlist is not None else load_watchlist(watchlist_path)
    if not entries:
        return []

    # 1. Whitelist Check: If domain is the official domain or official subdomain -> NOT a match
    for entry in entries:
        off_domain = entry["official_domain"]
        if clean_domain == off_domain or clean_domain.endswith(f".{off_domain}"):
            return []

    matches: list[Match] = []
    domain_labels = _extract_domain_labels(clean_domain)
    decoded_domain, is_punycode = decode_punycode_domain(clean_domain)
    homoglyph_domain = normalize_homoglyphs(decoded_domain)
    homoglyph_labels = _extract_domain_labels(homoglyph_domain)

    # --------------------------------------------------------------------------
    # TECHNIQUE 1: Keyword in Misleading Position (Subdomain / Hyphen)
    # --------------------------------------------------------------------------
    keyword_matches: list[Match] = []
    for entry in entries:
        brand = entry["brand_name"]
        off_domain = entry["official_domain"]
        candidate_terms = [brand] + [a.strip() for a in entry["aliases"].split(";") if a.strip()]

        for term in candidate_terms:
            term_clean = term.lower().replace(" ", "")
            if len(term_clean) < 3:
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
                if len(term_clean) >= 4 and (
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
            brand = entry["brand_name"]
            off_domain = entry["official_domain"]
            candidate_terms = [brand] + [a.strip() for a in entry["aliases"].split(";") if a.strip()]

            for term in candidate_terms:
                term_clean = term.lower().replace(" ", "")
                if len(term_clean) < 3:
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
    # TECHNIQUE 3: Damerau-Levenshtein Distance
    # --------------------------------------------------------------------------
    dl_matches: list[Match] = []
    for entry in entries:
        brand = entry["brand_name"]
        off_domain = entry["official_domain"]
        candidate_terms = [brand] + [a.strip() for a in entry["aliases"].split(";") if a.strip()]

        for term in candidate_terms:
            term_clean = term.lower().replace(" ", "")
            term_len = len(term_clean)

            # Strategy based on length of the specific string being compared:
            # - Short strings (<= 4 chars, like BCA, BRI, DJP): skip edit distance to prevent FP explosion
            # - Medium strings (5-8 chars): distance <= 1 or 2
            # - Long strings (> 8 chars): distance <= 2 or 3
            if term_len <= SHORT_NAME_MAX_LEN:
                continue

            max_allowed_dist = 1 if term_len <= 5 else (MEDIUM_NAME_MAX_DIST if term_len <= 8 else LONG_NAME_MAX_DIST)

            for label in domain_labels:
                # Skip if label length differs too much
                if abs(len(label) - term_len) > max_allowed_dist:
                    continue

                dist = damerau_levenshtein_distance(label, term_clean)
                if 1 <= dist <= max_allowed_dist:
                    score = max(0.60, 1.0 - (dist / max(term_len, len(label))))
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
        brand = entry["brand_name"]
        off_domain = entry["official_domain"]
        off_stem = off_domain.split(".")[0]
        if len(off_stem) > 4:
            for label in domain_labels:
                if label != off_stem and damerau_levenshtein_distance(label, off_stem) == 1:
                    return [Match(
                        brand_name=brand,
                        official_domain=off_domain,
                        method="permutation",
                        similarity_score=0.85,
                        matched_term=off_stem,
                    )]

    return []
