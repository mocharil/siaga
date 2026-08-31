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
