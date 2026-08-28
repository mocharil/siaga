"""Homoglyph & Punycode Normalization Module (T17).

Detects visual spoofing, IDN punycode attacks, and normalizes lookalike glyphs
(Cyrillic, Greek, numbers, digraphs) to canonical Latin representations.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
import re
import unicodedata

logger = logging.getLogger("siaga.homoglyph")

# ------------------------------------------------------------------------------
# HOMOGLYPH LOOKALIKE MAPPINGS
# ------------------------------------------------------------------------------

CYRILLIC_TO_LATIN: dict[str, str] = {
    "\u0430": "a",  # cyrillic small a
    "\u0410": "a",  # cyrillic capital a
    "\u0432": "b",  # cyrillic small ve
    "\u0412": "b",  # cyrillic capital ve
    "\u0441": "c",  # cyrillic small es
    "\u0421": "c",  # cyrillic capital es
    "\u0434": "d",  # cyrillic small de
    "\u0435": "e",  # cyrillic small ie
    "\u0415": "e",  # cyrillic capital ie
    "\u0454": "e",  # cyrillic small ukrainian ie
    "\u04bb": "h",  # cyrillic small shha
    "\u0456": "i",  # cyrillic small byelorussian-ukrainian i
    "\u0406": "i",  # cyrillic capital byelorussian-ukrainian i
    "\u0458": "j",  # cyrillic small je
    "\u0408": "j",  # cyrillic capital je
    "\u043a": "k",  # cyrillic small ka
    "\u041a": "k",  # cyrillic capital ka
    "\u043c": "m",  # cyrillic small em
    "\u041c": "m",  # cyrillic capital em
    "\u043d": "h",  # cyrillic small en (looks like H)
    "\u041d": "h",  # cyrillic capital en
    "\u043e": "o",  # cyrillic small o
    "\u041e": "o",  # cyrillic capital o
    "\u0440": "p",  # cyrillic small er (looks like p)
    "\u0420": "p",  # cyrillic capital er
    "\u0455": "s",  # cyrillic small dze
    "\u0405": "s",  # cyrillic capital dze
    "\u0442": "t",  # cyrillic small te
    "\u0422": "t",  # cyrillic capital te
    "\u0445": "x",  # cyrillic small ha
    "\u0425": "x",  # cyrillic capital ha
    "\u0443": "y",  # cyrillic small u (looks like y)
    "\u0423": "y",  # cyrillic capital u
}

GREEK_TO_LATIN: dict[str, str] = {
    "\u03b1": "a",  # alpha
    "\u0391": "a",  # capital alpha
    "\u03b2": "b",  # beta
    "\u0392": "b",  # capital beta
    "\u03b5": "e",  # epsilon
    "\u0395": "e",  # capital epsilon
    "\u03b7": "n",  # eta
    "\u0397": "h",  # capital eta
    "\u03b9": "i",  # iota
    "\u0399": "i",  # capital iota
    "\u03ba": "k",  # kappa
    "\u039a": "k",  # capital kappa
    "\u03bd": "v",  # nu
    "\u03bf": "o",  # omicron
    "\u039f": "o",  # capital omicron
    "\u03c1": "p",  # rho
    "\u03a1": "p",  # capital rho
    "\u03c4": "t",  # tau
    "\u03a4": "t",  # capital tau
    "\u03c5": "u",  # upsilon
    "\u03a5": "y",  # capital upsilon
    "\u03c7": "x",  # chi
    "\u03a7": "x",  # capital chi
}

NUMBER_LEET_MAP: dict[str, str] = {
    "0": "o",
    "1": "i",
    "3": "e",
    "4": "a",
    "5": "s",
    "8": "b",
}


@dataclass
class HomoglyphResult:
    original_domain: str
    decoded_domain: str
    normalized_domain: str
    is_punycode: bool
    has_homoglyphs: bool
    detected_spoofs: list[str]


def decode_punycode(domain: str) -> tuple[str, bool]:
    """Decode IDN/Punycode domain (containing 'xn--') to unicode text.

    Returns:
        tuple (decoded_domain_str, is_punycode_bool)
    """
    clean = domain.strip().lower()
    is_puny = "xn--" in clean
    if not is_puny:
        return clean, False

    try:
        # Split by dots to handle label-by-label IDNA decoding
        labels = clean.split(".")
        decoded_labels = []
        for lbl in labels:
            if lbl.startswith("xn--"):
                decoded_labels.append(lbl.encode("ascii").decode("idna"))
            else:
                decoded_labels.append(lbl)
        return ".".join(decoded_labels), True
    except Exception as e:
        logger.debug("Punycode decoding fallback for %s: %s", domain, e)
        return clean, True


def normalize(domain: str, include_leet: bool = True) -> str:
    """Normalize visually confusing homoglyphs, non-Latin scripts, and digraphs.

    Preserves standard ASCII letters, numbers, hyphens, and dots in legitimate domains.
    """
    decoded, _ = decode_punycode(domain)
    # Normalize unicode to NFKC to resolve composite characters
    nfkc = unicodedata.normalize("NFKC", decoded).lower()

    # Digraph replacement: rn -> m, vv -> w, cl -> d
    normalized_digraphs = nfkc.replace("rn", "m").replace("vv", "w")

    chars: list[str] = []
    for char in normalized_digraphs:
        if char in CYRILLIC_TO_LATIN:
            chars.append(CYRILLIC_TO_LATIN[char])
        elif char in GREEK_TO_LATIN:
            chars.append(GREEK_TO_LATIN[char])
        elif include_leet and char in NUMBER_LEET_MAP:
            chars.append(NUMBER_LEET_MAP[char])
        else:
            chars.append(char)

    return "".join(chars)


def analyze_homoglyph(domain: str) -> HomoglyphResult:
    """Comprehensive visual spoofing analysis for a given domain."""
    decoded, is_puny = decode_punycode(domain)
    normalized = normalize(domain, include_leet=True)

    spoofs: list[str] = []
    if is_puny:
        spoofs.append("punycode_idn_encoding")

    # Detect non-ASCII / Cyrillic / Greek characters
    has_cyrillic = any(c in CYRILLIC_TO_LATIN for c in decoded)
    if has_cyrillic:
        spoofs.append("cyrillic_script_spoof")

    has_greek = any(c in GREEK_TO_LATIN for c in decoded)
    if has_greek:
        spoofs.append("greek_script_spoof")

    # Detect leet / digit lookalikes (e.g. b0a, t0k0pedia)
    if re.search(r"[a-z][013458][a-z]", decoded.lower()):
        spoofs.append("digit_substitution_leet")

    # Detect digraphs
    if "rn" in decoded.lower() or "vv" in decoded.lower():
        spoofs.append("digraph_substitution")

    has_homoglyphs = len(spoofs) > 0 or is_puny or (normalized != decoded.lower())

    return HomoglyphResult(
        original_domain=domain,
        decoded_domain=decoded,
        normalized_domain=normalized,
        is_punycode=is_puny,
        has_homoglyphs=has_homoglyphs,
        detected_spoofs=spoofs,
    )
