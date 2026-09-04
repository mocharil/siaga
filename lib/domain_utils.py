"""Domain Utility Functions.

Shared utility module for extracting the registrable (apex) domain from
an arbitrary hostname or fully-qualified domain name.

Moved here from lib/campaign.py so that both lib/rdap.py and lib/campaign.py
can import from a single authoritative source rather than one depending on the
other.
"""

from __future__ import annotations

# Indonesian second-level TLDs where the registrable unit is three labels
# (e.g. "provider.co.id", not "co.id"). Mirrors collector/ct_collector.py's
# CTLOGS_ID_TLDS — kept as a separate literal here since this module has no
# reason to depend on the collector.
ID_SECOND_LEVEL_TLDS = {"co.id", "go.id", "ac.id", "or.id", "web.id"}

# Suffixes of officially-issued Indonesian institutional domains. Moved here
# from lib/judol_detect.py (2026-09-03) so lib/porn_detect.py could reuse the
# same "hijacked institution" concept without duplicating the literal — a
# match under one of these suffixes means the domain itself is legitimate
# government/education infrastructure that has had a harmful subdomain
# planted on it, not merely a newly-registered lookalike.
INSTITUTIONAL_ID_SUFFIXES: tuple[str, ...] = (".go.id", ".ac.id", ".sch.id", ".or.id", ".desa.id")


def registrable_domain(hostname: str) -> str | None:
    """Extract the registrable (apex) domain from any hostname or FQDN.

    Examples:
        "ns1.badhost.xyz"                          -> "badhost.xyz"
        "ns1.provider.co.id"                       -> "provider.co.id"
        "login.namabank.web.id"                    -> "namabank.web.id"
        "investors.spotify.com.id2.bumiayuvpn.web.id" -> "bumiayuvpn.web.id"
        "bumiayuvpn.web.id"                        -> "bumiayuvpn.web.id"
        "a"                                        -> None  (single label)

    For Indonesian .id second-level TLDs (co.id, go.id, ac.id, or.id, web.id)
    the registrable domain is the three-label suffix; for all other TLDs it is
    the two-label suffix (last label = TLD, second-to-last = SLD).

    Generic compound TLDs beyond the .id family (e.g. "co.uk") are not handled —
    acceptable here because SIAGA targets .id and generic TLDs (.com, .net) where
    the two-label rule is always correct.

    Args:
        hostname: Any hostname string, with or without trailing dot.

    Returns:
        The registrable domain string in lowercase, or None if the input has
        fewer than two labels (i.e. it is not a valid hostname).
    """
    host = hostname.strip().lower().rstrip(".")
    labels = host.split(".")
    if len(labels) < 2:
        return None

    last_two = ".".join(labels[-2:])
    if last_two in ID_SECOND_LEVEL_TLDS and len(labels) >= 3:
        return ".".join(labels[-3:])
    return last_two


def extract_domain_labels(domain: str) -> list[str]:
    """Split a domain into its individual labels plus hyphen sub-parts.

    Moved from lib/similarity.py (2026-09-02) so lib/judol_detect.py could
    reuse the exact same label-boundary logic instead of re-deriving it --
    naive substring matching on the full hostname produces false positives
    that this project already learned to avoid for brand matching (e.g. a
    keyword like "bandar" substring-matches the real city name
    "bandarlampungkota.go.id", but "bandar" is not one of its labels).

    Examples:
        "bca-promo.xyz"        -> ["bca-promo", "bca", "promo"]
        "slot-gacor.selumakab.go.id" -> ["slot-gacor", "slot", "gacor", "selumakab"]
        "bandarlampungkota.go.id"    -> ["bandarlampungkota"]  (no hyphen, one token)
    """
    clean = domain.strip().lower().rstrip(".")
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
            if "-" in label:
                subparts = [p for p in label.split("-") if p]
                tokens.extend(subparts)
    return tokens
