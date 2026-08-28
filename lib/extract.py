"""Entity Extraction Module (T13).

Extracts and deobfuscates URLs, Indonesian phone numbers, and bank account details
from unstructured Indonesian text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import urllib.parse

# ------------------------------------------------------------------------------
# Obfuscation cleaning regex patterns
# ------------------------------------------------------------------------------

# Common deobfuscation replacement pairs
_OBFUSCATION_REPLACEMENTS = [
    # Scheme obfuscations with 's'
    (re.compile(r"\b(?:hxxps|h\*\*ps|h__ps)\s*:\s*(?://|\\\\)\s*", re.IGNORECASE), "https://"),
    # Scheme obfuscations without 's'
    (re.compile(r"\b(?:hxxp|h\*\*p|h__p)\s*:\s*(?://|\\\\)\s*", re.IGNORECASE), "http://"),
    # Spaced standard schemes: http : // or https : //
    (re.compile(r"\b(https?)\s*:\s*(?://|\\\\)\s*", re.IGNORECASE), r"\1://"),
    # Bracketed / parenthesized dots and slashes
    (re.compile(r"\[\.\]|\(\.\)|\{.\}", re.IGNORECASE), "."),
    (re.compile(r"\[dot\]|\(dot\)|\{dot\}|\bdot\b", re.IGNORECASE), "."),
    (re.compile(r"\[/\]|\(/\}|\{/\}|\bslash\b", re.IGNORECASE), "/"),
]

# TLDs to look for when identifying scheme-less URLs
COMMON_TLDS = (
    r"com|id|co\.id|web\.id|my\.id|or\.id|go\.id|ac\.id|biz\.id|net|org|xyz|top|"
    r"online|site|club|vip|live|store|shop|me|io|info|biz|cc|app|tech|fun|link"
)

# Regex for matching candidate URLs in text
_RAW_URL_PATTERN = re.compile(
    r"\b(?:https?://|www\.)[^\s<>\"'()]+"
    r"|"
    r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+(?:" + COMMON_TLDS + r")(?::\d+)?(?:/[^\s<>\"'()]*)?"
    r"|"
    r"\b(?:wa\.me|t\.me|bit\.ly|tinyurl\.com|s\.id|linktr\.ee)/[^\s<>\"'()]+",
    re.IGNORECASE,
)

# Regex for Indonesian Phone Numbers
# Matches +62..., 62..., 08... with optional spaces, dashes, or dots
_PHONE_PATTERN = re.compile(
    r"(?:(?:\+?62)|0)8[1-9][0-9\s\-\.]{7,13}[0-9]"
)

# Regex for Bank Account Numbers in Indonesian text
_BANK_NAMES_PATTERN = (
    r"bca|bri|mandiri|bni|bsi|btn|cimb(?:\s*niaga)?|danamon|permata|mega|ocbc|"
    r"panin|btpn|jenius|jago|blu|seabank|neo(?:\s*commerce)?|bjb|jatim|jateng|"
    r"dki|aladin|superbank|maybank|uob|hsbc|dana|ovo|gopay|linkaja"
)

_BANK_ACCOUNT_PATTERN = re.compile(
    rf"(?:(?:no\.?\s*rek(?:ening)?|rek(?:ening)?|rekening\s*tujuan|va|virtual\s*account)\s*"
    rf"(?:bank\s*)?(?:(?P<bank>{_BANK_NAMES_PATTERN})\s*)?[:\-\s]*"
    rf"(?P<account>[0-9]{{8,18}}))"
    r"|"
    rf"(?:(?:bank\s*)?(?P<bank_prefix>{_BANK_NAMES_PATTERN})\s*"
    rf"(?:no\.?\s*rek(?:ening)?|rek(?:ening)?)[:\-\s]*"
    rf"(?P<account_prefix>[0-9]{{8,18}}))",
    re.IGNORECASE,
)


@dataclass
class ExtractedEntities:
    urls: list[str] = field(default_factory=list)
    phone_numbers: list[str] = field(default_factory=list)
    bank_accounts: list[dict[str, str]] = field(default_factory=list)


def _clean_obfuscated_text(text: str) -> str:
    """Normalize common deobfuscation tricks in freeform text."""
    cleaned = text
    for pattern, replacement in _OBFUSCATION_REPLACEMENTS:
        cleaned = pattern.sub(replacement, cleaned)

    # Collapse space insertions around dots inside words: e.g. "bca . com" -> "bca.com"
    cleaned = re.sub(r"([a-zA-Z0-9_-]+)\s*\.\s*([a-zA-Z0-9_/-]+)", r"\1.\2", cleaned)
    # Collapse space insertions around slashes: e.g. "bit.ly / 12345" -> "bit.ly/12345"
    cleaned = re.sub(r"([a-zA-Z0-9_\.-]+)\s*/\s*([a-zA-Z0-9_/-]+)", r"\1/\2", cleaned)

    return cleaned


def normalize_url(raw_url: str) -> str | None:
    """Clean and normalize a detected URL string into canonical form."""
    cleaned = raw_url.strip()

    # Strip trailing punctuation commonly attached in conversational sentences
    cleaned = re.sub(r"[\.,;:!\?\)\(\]\[\}\'\"]+$", "", cleaned)

    if not cleaned:
        return None

    # Handle scheme
    if cleaned.lower().startswith("hxxps://"):
        cleaned = "https://" + cleaned[8:]
    elif cleaned.lower().startswith("hxxp://"):
        cleaned = "http://" + cleaned[7:]
    elif not cleaned.lower().startswith(("http://", "https://")):
        cleaned = "https://" + cleaned

    try:
        parsed = urllib.parse.urlparse(cleaned)
        netloc = parsed.netloc.strip().lower()

        # Handle port or username/password in netloc if present
        if "@" in netloc:
            _, netloc = netloc.split("@", 1)

        if not netloc or "." not in netloc:
            return None

        # Reconstruct clean URL
        path = parsed.path or ""
        # Ensure clean path structure
        path = re.sub(r"/+", "/", path) if path else ""
        query = f"?{parsed.query}" if parsed.query else ""

        canonical = f"{parsed.scheme.lower()}://{netloc}{path}{query}"
        return canonical
    except Exception:
        return None


def normalize_phone_number(raw_phone: str) -> str:
    """Normalize Indonesian phone number into standard local 08... or E.164 format."""
    digits = re.sub(r"[^\d+]", "", raw_phone)
    if digits.startswith("+62"):
        digits = "0" + digits[3:]
    elif digits.startswith("62") and len(digits) > 9:
        digits = "0" + digits[2:]
    return digits


def extract_entities(text: str) -> ExtractedEntities:
    """Extract and deobfuscate URLs, phone numbers, and bank account numbers from text.

    Args:
        text: Raw text string in Indonesian (e.g. from SMS, WhatsApp, Telegram, or email).

    Returns:
        ExtractedEntities object containing lists of normalized URLs, phone numbers,
        and bank account records.
    """
    if not text or not isinstance(text, str):
        return ExtractedEntities()

    # 1. Pre-process text to remove URL obfuscation artifacts
    cleaned_text = _clean_obfuscated_text(text)

    # 2. Extract URLs
    found_urls: list[str] = []
    for match in _RAW_URL_PATTERN.finditer(cleaned_text):
        raw_match = match.group(0)
        norm = normalize_url(raw_match)
        if norm and norm not in found_urls:
            found_urls.append(norm)

    # 3. Extract Indonesian phone numbers
    found_phones: list[str] = []
    for match in _PHONE_PATTERN.finditer(text):
        raw_phone = match.group(0)
        norm_phone = normalize_phone_number(raw_phone)
        # Valid mobile length in Indonesia is 10-14 digits (08xxxxxxxxxx)
        if 10 <= len(norm_phone) <= 14 and norm_phone not in found_phones:
            found_phones.append(norm_phone)

    # 4. Extract Bank Account Numbers
    found_accounts: list[dict[str, str]] = []
    seen_account_keys: set[str] = set()

    for match in _BANK_ACCOUNT_PATTERN.finditer(text):
        bank = match.group("bank") or match.group("bank_prefix") or "UNKNOWN"
        acc_num = match.group("account") or match.group("account_prefix")
        if acc_num:
            clean_bank = bank.strip().upper()
            clean_acc = acc_num.strip()
            key = f"{clean_bank}:{clean_acc}"
            if key not in seen_account_keys:
                seen_account_keys.add(key)
                found_accounts.append({
                    "bank": clean_bank,
                    "account_number": clean_acc,
                })

    return ExtractedEntities(
        urls=found_urls,
        phone_numbers=found_phones,
        bank_accounts=found_accounts,
    )
