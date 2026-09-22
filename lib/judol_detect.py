"""Judol (Online Gambling) Domain Detection Module.

Flags domains in ct_raw whose labels match a curated Indonesian online-
gambling keyword glossary, using the same label/hyphen-boundary matching
lib/similarity.py already uses for phishing brand matching -- naive
substring matching on the full hostname produces false positives (a keyword
like "bandar" substring-matches the real city name "bandarlampungkota.go.id",
but is not one of its labels).

A special "hijacked institution" flag is raised when the match sits on a
subdomain of an official Indonesian institutional domain (.go.id, .ac.id,
.sch.id, .or.id, .desa.id) -- a well-documented real pattern where gambling
operators inject subdomains onto poorly-secured government/education sites
to inherit their domain authority for SEO. This is the platform's strongest,
most credible signal, and the one most likely to be useful for a Komdigi-
style site-filtering use case.

The keyword list is necessarily incomplete -- gambling site branding rotates
constantly. It captures generic Indonesian gambling vocabulary (slot, gacor,
togel, judi, ...) rather than any single brand name, so detection should
keep working as specific brand names come and go.

Two confidence tiers, both surfaced honestly via `verification_method`:
  - "keyword": JUDOL_KEYWORDS match -- unambiguous, always auto-flagged.
  - "llm": JUDOL_AMBIGUOUS_KEYWORDS match (dual-use terms like "toto", "bola",
    "domino" that were dropped from the strict list after producing real
    false positives) confirmed by an LLM judging the FULL domain string for
    contextual clues (e.g. "toto-macau-2026" vs "domino-printer") -- opt-in
    via scan_ct_raw(allow_llm=True), since it costs LLM budget and the
    verdict is a judgment call rather than a deterministic rule. Never
    auto-flagged on the ambiguous list alone.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import logging
from pathlib import Path
import re
import sqlite3

from lib.domain_utils import extract_domain_labels, INSTITUTIONAL_ID_SUFFIXES
from lib.llm import complete, LLMBudgetExceeded, LLMProviderError, LLMSchemaError

logger = logging.getLogger("siaga.judol_detect")

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "siaga.db"

# Indonesian online-gambling vocabulary, deliberately restricted to terms
# with LOW ambiguity outside a gambling context. Every entry must match a
# full domain LABEL (or a hyphen sub-part of one) via
# lib.domain_utils.extract_domain_labels -- never a raw substring of the
# hostname.
#
# Several plausible-looking candidates were tried against the real local
# ct_raw dataset (2026-09-02, 60,863 domains) and DROPPED from this strict
# tier after producing confirmed false positives or being judged too generic
# to trust unqualified -- they now live in JUDOL_AMBIGUOUS_KEYWORDS below,
# gated behind LLM confirmation instead of an automatic flag:
#   - "rtp"    -> false-positived on "pt-rtp.co.id" (a company name, not
#                 "Return To Player")
#   - "domino" -> false-positived on "domino-printer.co.id" (a printer brand)
#   - "toto"   -> also a common personal name and an established bathroom-
#                 fixture brand (PT Toto)
#   - "bola"   -> generic Indonesian word for "ball"; used by ordinary
#                 sports/business domains
#   - "joker"  -> ambiguous outside slot-game branding (pop culture, given
#                 names); flagged a .ac.id domain with no other evidence
#   - "mahjong", "pragmatic" (bare) -> legitimate board game / common
#                 English adjective; kept only as compounds below
#   - "hoki", "cuan", "jackpot", "wla" -> too generic ("luck", "profit",
#                 generic prize term, unclear abbreviation)
# This list trades recall for precision on purpose -- CLAUDE.md rule #2
# (never fabricate results) means a demoed finding must survive scrutiny.
JUDOL_KEYWORDS: set[str] = {
    "slot", "gacor", "maxwin", "togel", "judi", "bandarqq", "sbobet",
    "scatter", "parlay", "sabung", "poker", "casino", "sv388", "pgsoft",
    "spaceman", "qq288", "domino99", "pragmaticplay", "situsslot",
    "slotgacor", "jpmaxwin",
}

# Dual-use terms excluded from the strict list above -- real gambling sites
# do use them, but so do unrelated legitimate domains. Only ever flagged
# after an LLM judges the FULL domain string plausible in context (see
# _verify_ambiguous_with_llm). Never auto-flagged on this list alone.
JUDOL_AMBIGUOUS_KEYWORDS: set[str] = {
    "rtp", "domino", "toto", "bola", "joker", "mahjong", "pragmatic",
    "hoki", "cuan", "jackpot", "wla",
}

# Real judol domains overwhelmingly append/prepend a handful of digits (or a
# trailing "d" for the togel "4d" convention: togel4d, toto4d) around the
# bare keyword -- e.g. "gacor88", "toto4d", "88slot" -- rather than using it
# as a whole label on its own. Matching is anchored to the FULL token (whole
# label or hyphen sub-part from extract_domain_labels) with only digits/one
# trailing "d" allowed on either side, so a keyword can never match as a mere
# substring buried inside an unrelated word (e.g. "bandarlampungkota" is not
# "bandar" + digits, "aspindo" contains no listed keyword at all).
_KEYWORD_PATTERN = re.compile(
    r"^\d{0,3}(?P<kw>" + "|".join(re.escape(k) for k in sorted(JUDOL_KEYWORDS, key=len, reverse=True)) + r")\d{0,3}d?$"
)
_AMBIGUOUS_PATTERN = re.compile(
    r"^\d{0,3}(?P<kw>" + "|".join(re.escape(k) for k in sorted(JUDOL_AMBIGUOUS_KEYWORDS, key=len, reverse=True)) + r")\d{0,3}d?$"
)

_LLM_VERIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "is_match": {"type": "boolean"},
        "reasoning": {"type": "string"},
    },
    "required": ["is_match", "reasoning"],
}
_LLM_SYSTEM_PROMPT = (
    "Kamu adalah classifier yang HANYA boleh membalas dengan satu objek JSON valid, "
    'persis dua field: {"is_match": true/false, "reasoning": "..."}. '
    "Jangan gunakan nama field lain (jangan 'is_gambling', 'confidence', 'keyword', dll). "
    "Jangan tambahkan teks, markdown, atau penjelasan di luar objek JSON itu. "
    "Field reasoning: satu kalimat singkat bahasa Indonesia, diikuti terjemahan Inggrisnya, "
    "dipisah ' / '."
)


@dataclass
class JudolMatch:
    domain: str
    matched_keywords: list[str]
    is_hijacked_institution: bool
    institution_suffix: str | None
    verification_method: str = "keyword"  # "keyword" | "llm"
    llm_reasoning: str | None = None


def _label_matches(domain: str, pattern: re.Pattern) -> list[str]:
    tokens = extract_domain_labels(domain)
    matched: set[str] = set()
    for token in tokens:
        m = pattern.match(token)
        if m:
            matched.add(m.group("kw"))
    return sorted(matched)


def check_judol(domain: str) -> JudolMatch | None:
    """Check a single domain for judol-keyword label matches (strict tier only).

    Returns None when the domain is empty/malformed or has no keyword match.
    """
    clean = domain.strip().lower().rstrip(".")
    if not clean or "." not in clean:
        return None

    matched = _label_matches(clean, _KEYWORD_PATTERN)
    if not matched:
        return None

    institution_suffix = next(
        (suffix.lstrip(".") for suffix in INSTITUTIONAL_ID_SUFFIXES if clean.endswith(suffix)),
        None,
    )
    return JudolMatch(
        domain=clean,
        matched_keywords=matched,
        is_hijacked_institution=institution_suffix is not None,
        institution_suffix=institution_suffix,
    )


def check_judol_ambiguous(domain: str) -> list[str]:
    """Return ambiguous-tier keyword matches only (empty list if none).

    Does NOT check the strict tier -- callers should call check_judol()
    first and only fall back to this for domains it didn't already flag.
    """
    clean = domain.strip().lower().rstrip(".")
    if not clean or "." not in clean:
        return []
    return _label_matches(clean, _AMBIGUOUS_PATTERN)


def _verify_ambiguous_with_llm(
    domain: str,
    matched_keywords: list[str],
    db_path: Path | str | None,
) -> tuple[bool, str] | None:
    """Ask the LLM to judge an ambiguous domain-name match in context.

    Returns None (never flag) if the LLM call fails for any reason --
    budget exceeded, schema mismatch, provider error -- rather than falling
    back to a guess. The LLM sees ONLY the domain string, per CLAUDE.md's
    network rules (no page content fetching); it is reasoning about naming
    pattern plausibility, not verifying actual page content.
    """
    prompt = (
        f"Domain: {domain}\n"
        f"Kata kunci yang cocok pada nama domain ini: {', '.join(matched_keywords)}.\n\n"
        "Kata kunci ini bisa berarti perjudian online ATAU makna lain yang sah "
        "(nama perusahaan, kata umum, dll), tergantung konteks nama domain "
        "secara keseluruhan.\n\n"
        "PENTING: Kamu HANYA melihat string nama domain di atas -- tidak ada "
        "akses ke isi halaman apa pun. Nilai murni dari pola penamaan: apakah "
        "nama domain ini kemungkinan besar situs perjudian online, atau lebih "
        "mungkin nama bisnis/institusi/pribadi yang sah yang kebetulan "
        "mengandung kata itu? Jika ragu atau bukti dari nama domainnya sendiri "
        "lemah, jawab false -- jangan menuduh tanpa indikasi kuat.\n\n"
        "Balas HANYA dengan JSON persis seperti contoh ini (dua field ini saja), dengan "
        "reasoning berisi satu kalimat singkat bahasa Indonesia diikuti terjemahan "
        "Inggrisnya dipisah ' / ':\n"
        '{"is_match": true, "reasoning": "alasan singkat di sini / concise reasoning in English"}'
    )
    try:
        result = complete(prompt, _LLM_VERIFY_SCHEMA, system_prompt=_LLM_SYSTEM_PROMPT, db_path=db_path)
        return bool(result["is_match"]), (result.get("reasoning") or "").strip()
    except LLMBudgetExceeded:
        logger.info("Judol LLM verification skipped for %s: daily budget exceeded.", domain)
        return None
    except (LLMSchemaError, LLMProviderError) as e:
        logger.warning("Judol LLM verification failed for %s: %s", domain, e)
        return None


@dataclass
class JudolScanSummary:
    domains_scanned: int = 0
    domains_flagged: int = 0
    hijacked_institutions_flagged: int = 0
    newly_inserted: int = 0
    llm_candidates_checked: int = 0
    llm_confirmed: int = 0


def scan_ct_raw(db_path: Path | str | None = None, allow_llm: bool = False) -> JudolScanSummary:
    """Scan the full ct_raw table for judol matches and rebuild judol_findings.

    Idempotent: re-running re-derives the same matches from ct_raw every
    time. The table is fully rebuilt on each run (rather than upserted) so
    that a domain which no longer matches under the current JUDOL_KEYWORDS
    (e.g. after a keyword is removed for being too generic) does not linger
    as a stale, no-longer-justified finding. Each domain's original
    detected_at is preserved across rebuilds where already known.

    allow_llm: when True, domains that only match JUDOL_AMBIGUOUS_KEYWORDS
    (not the strict list) are additionally checked via _verify_ambiguous_with_llm
    and flagged only if the LLM confirms. Off by default -- costs LLM budget
    and is a judgment call, not a deterministic rule.
    """
    resolved_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    summary = JudolScanSummary()
    now_iso = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(str(resolved_path)) as conn:
        existing_detected_at = dict(conn.execute("SELECT domain, detected_at FROM judol_findings"))
        existing_domains = set(existing_detected_at)

        conn.execute("DELETE FROM judol_findings")

        rows = conn.execute("SELECT domain, first_seen FROM ct_raw").fetchall()
        summary.domains_scanned = len(rows)

        def _insert(match: JudolMatch, first_seen: str) -> None:
            summary.domains_flagged += 1
            if match.is_hijacked_institution:
                summary.hijacked_institutions_flagged += 1
            if match.domain not in existing_domains:
                summary.newly_inserted += 1

            conn.execute(
                """
                INSERT INTO judol_findings
                    (domain, first_seen, matched_keywords, is_hijacked_institution,
                     institution_suffix, detected_at, verification_method, llm_reasoning)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    match.domain,
                    first_seen,
                    ",".join(match.matched_keywords),
                    match.is_hijacked_institution,
                    match.institution_suffix,
                    existing_detected_at.get(match.domain, now_iso),
                    match.verification_method,
                    match.llm_reasoning,
                ),
            )

        ambiguous_candidates: list[tuple[str, str]] = []
        for domain, first_seen in rows:
            match = check_judol(domain)
            if match is not None:
                _insert(match, first_seen)
                continue
            if allow_llm:
                ambiguous_kws = check_judol_ambiguous(domain)
                if ambiguous_kws:
                    ambiguous_candidates.append((domain, first_seen))

        if allow_llm:
            for domain, first_seen in ambiguous_candidates:
                clean = domain.strip().lower().rstrip(".")
                ambiguous_kws = check_judol_ambiguous(clean)
                summary.llm_candidates_checked += 1
                verdict = _verify_ambiguous_with_llm(clean, ambiguous_kws, resolved_path)
                if verdict is None:
                    continue
                confirmed, reasoning = verdict
                if not confirmed:
                    continue
                summary.llm_confirmed += 1

                institution_suffix = next(
                    (s.lstrip(".") for s in INSTITUTIONAL_ID_SUFFIXES if clean.endswith(s)),
                    None,
                )
                match = JudolMatch(
                    domain=clean,
                    matched_keywords=ambiguous_kws,
                    is_hijacked_institution=institution_suffix is not None,
                    institution_suffix=institution_suffix,
                    verification_method="llm",
                    llm_reasoning=reasoning,
                )
                _insert(match, first_seen)

        conn.commit()

    logger.info(
        "Judol scan: %d domains scanned, %d flagged (%d hijacked institutions), %d newly inserted"
        " | LLM: %d candidates checked, %d confirmed",
        summary.domains_scanned,
        summary.domains_flagged,
        summary.hijacked_institutions_flagged,
        summary.newly_inserted,
        summary.llm_candidates_checked,
        summary.llm_confirmed,
    )
    return summary
