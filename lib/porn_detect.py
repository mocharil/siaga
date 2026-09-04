"""Pornographic/Adult Content Domain Detection Module.

Flags domains in ct_raw whose labels match a curated pornography/adult-
content keyword glossary, using the same label/hyphen-boundary matching as
lib/judol_detect.py (see lib/domain_utils.py::extract_domain_labels) --
naive substring matching on the full hostname produces false positives.

A special "hijacked institution" flag mirrors judol_detect.py: raised when
the match sits on a subdomain of an official Indonesian institutional domain
(.go.id, .ac.id, .sch.id, .or.id, .desa.id) -- defaced/compromised government
or education sites having unrelated content (gambling, adult, spam SEO)
injected as a subdomain is a well-documented real phenomenon in Indonesia,
not specific to any one content category.

This category is the platform's closest fit to Komdigi's actual "Trust+
Positif" content-filtering mandate, which blocks pornographic content as a
blanket policy regardless of whether the domain is a fresh registration or a
compromised legitimate one.

Two confidence tiers, both surfaced honestly via `verification_method`:
  - "keyword": PORN_KEYWORDS match -- unambiguous, always auto-flagged.
  - "llm": PORN_AMBIGUOUS_KEYWORDS match (body-part slang: kontol, toket,
    memek, ewe) confirmed by an LLM judging the FULL domain string for
    contextual clues -- opt-in via scan_ct_raw(allow_llm=True). "jilbob" is
    NOT in either list, on either tier, under any circumstance -- see the
    note below.
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

logger = logging.getLogger("siaga.porn_detect")

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "siaga.db"

# Adult-content descriptors, deliberately restricted to terms that name a
# genre/act rather than merely a body part or generic profanity. Every entry
# must match a full domain LABEL (or hyphen sub-part) via
# lib.domain_utils.extract_domain_labels -- never a raw substring.
#
# Tested against the real local ct_raw dataset (2026-09-03, 67,104 domains).
# A broader first draft that included body-part slang was DROPPED from this
# strict tier after producing a real false positive pattern -- it now lives
# in PORN_AMBIGUOUS_KEYWORDS below, gated behind LLM confirmation:
#   - "kontol", "toket", "memek", "ewe" (Indonesian genital slang) ->
#     all hits were subdomains under a single vulgar dynamic-DNS zone
#     ("kontol.dnm.web.id") with legitimate brand names appended
#     (blibli, gopay, netflix, zoom, ...) -- almost certainly a prank/
#     vandalism naming pattern on a free DDNS provider, not evidence of
#     actual pornographic content. Profanity in a domain name is not the
#     same signal as a content descriptor.
#
# "jilbob" is deliberately absent from BOTH tiers, permanently, regardless of
# detection performance -- it is a real but distasteful genre tag conflating
# religious dress with adult content, and the risk of ever mislabeling an
# unrelated Islamic-content domain this way (even via an LLM's judgment
# call) was judged unacceptable. This is a hard ethical exclusion, not a
# precision trade-off, so it is never offered as an LLM-arbitrable candidate.
#
# Surviving real strict-tier matches from the same dataset: "bokep.web.id"
# (bokep is unambiguous Indonesian slang specifically for pornographic
# video) and "www.xxx.kabulcipta.co.id".
PORN_KEYWORDS: set[str] = {
    "bokep", "porn", "porno", "xxx", "bugil", "hentai", "ngentot",
    "ngewe", "colmek", "crot", "sange", "bispak", "telanjang",
}

# Dual-use body-part slang excluded from the strict list above -- see the
# "jilbob" note above for the one term that is excluded on principle rather
# than gated here. Only ever flagged after an LLM judges the FULL domain
# string plausible in context (see _verify_ambiguous_with_llm).
PORN_AMBIGUOUS_KEYWORDS: set[str] = {"kontol", "toket", "memek", "ewe"}

# Same digit/trailing-"d" tolerance as lib/judol_detect.py -- real adult-site
# domains follow the identical "keyword + lucky/brand numbers" convention
# (bokep88, xxx21) rather than using the bare keyword as a whole label.
_KEYWORD_PATTERN = re.compile(
    r"^\d{0,3}(?P<kw>" + "|".join(re.escape(k) for k in sorted(PORN_KEYWORDS, key=len, reverse=True)) + r")\d{0,3}d?$"
)
_AMBIGUOUS_PATTERN = re.compile(
    r"^\d{0,3}(?P<kw>" + "|".join(re.escape(k) for k in sorted(PORN_AMBIGUOUS_KEYWORDS, key=len, reverse=True)) + r")\d{0,3}d?$"
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
    "Jangan gunakan nama field lain (jangan 'is_adult_content', 'confidence', 'keyword', dll). "
    "Jangan tambahkan teks, markdown, atau penjelasan di luar objek JSON itu."
)


@dataclass
class PornMatch:
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


def check_porn(domain: str) -> PornMatch | None:
    """Check a single domain for adult-content keyword label matches (strict tier only).

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
    return PornMatch(
        domain=clean,
        matched_keywords=matched,
        is_hijacked_institution=institution_suffix is not None,
        institution_suffix=institution_suffix,
    )


def check_porn_ambiguous(domain: str) -> list[str]:
    """Return ambiguous-tier keyword matches only (empty list if none).

    Does NOT check the strict tier -- callers should call check_porn() first
    and only fall back to this for domains it didn't already flag.
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
        "Kata kunci ini bisa muncul pada domain konten pornografi/dewasa ATAU "
        "sebagai bagian dari nama/istilah lain yang tidak berkaitan, tergantung "
        "konteks nama domain secara keseluruhan.\n\n"
        "PENTING: Kamu HANYA melihat string nama domain di atas -- tidak ada "
        "akses ke isi halaman apa pun. Nilai murni dari pola penamaan: apakah "
        "nama domain ini kemungkinan besar situs konten pornografi/dewasa, "
        "atau lebih mungkin sesuatu yang tidak berkaitan (misalnya nama brand "
        "lain yang ditempel di subdomain acak, lelucon/vandalism, dll)? Jika "
        "ragu atau bukti dari nama domainnya sendiri lemah, jawab false -- "
        "jangan menuduh tanpa indikasi kuat.\n\n"
        "Balas HANYA dengan JSON persis seperti contoh ini (dua field ini saja):\n"
        '{"is_match": false, "reasoning": "alasan singkat di sini"}'
    )
    try:
        result = complete(prompt, _LLM_VERIFY_SCHEMA, system_prompt=_LLM_SYSTEM_PROMPT, db_path=db_path)
        return bool(result["is_match"]), (result.get("reasoning") or "").strip()
    except LLMBudgetExceeded:
        logger.info("Porn LLM verification skipped for %s: daily budget exceeded.", domain)
        return None
    except (LLMSchemaError, LLMProviderError) as e:
        logger.warning("Porn LLM verification failed for %s: %s", domain, e)
        return None


@dataclass
class PornScanSummary:
    domains_scanned: int = 0
    domains_flagged: int = 0
    hijacked_institutions_flagged: int = 0
    newly_inserted: int = 0
    llm_candidates_checked: int = 0
    llm_confirmed: int = 0


def scan_ct_raw(db_path: Path | str | None = None, allow_llm: bool = False) -> PornScanSummary:
    """Scan the full ct_raw table for adult-content matches and rebuild porn_findings.

    Idempotent: re-running re-derives the same matches from ct_raw every
    time. The table is fully rebuilt on each run (rather than upserted), for
    the same reason as lib/judol_detect.py::scan_ct_raw -- a domain that no
    longer matches under the current PORN_KEYWORDS must not linger as a
    stale, no-longer-justified finding. Each domain's original detected_at
    is preserved across rebuilds where already known.

    allow_llm: when True, domains that only match PORN_AMBIGUOUS_KEYWORDS
    (not the strict list) are additionally checked via _verify_ambiguous_with_llm
    and flagged only if the LLM confirms. Off by default -- costs LLM budget
    and is a judgment call, not a deterministic rule.
    """
    resolved_path = Path(db_path) if db_path else DEFAULT_DB_PATH
    summary = PornScanSummary()
    now_iso = datetime.now(timezone.utc).isoformat()

    with sqlite3.connect(str(resolved_path)) as conn:
        existing_detected_at = dict(conn.execute("SELECT domain, detected_at FROM porn_findings"))
        existing_domains = set(existing_detected_at)

        conn.execute("DELETE FROM porn_findings")

        rows = conn.execute("SELECT domain, first_seen FROM ct_raw").fetchall()
        summary.domains_scanned = len(rows)

        def _insert(match: PornMatch, first_seen: str) -> None:
            summary.domains_flagged += 1
            if match.is_hijacked_institution:
                summary.hijacked_institutions_flagged += 1
            if match.domain not in existing_domains:
                summary.newly_inserted += 1

            conn.execute(
                """
                INSERT INTO porn_findings
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
            match = check_porn(domain)
            if match is not None:
                _insert(match, first_seen)
                continue
            if allow_llm:
                ambiguous_kws = check_porn_ambiguous(domain)
                if ambiguous_kws:
                    ambiguous_candidates.append((domain, first_seen))

        if allow_llm:
            for domain, first_seen in ambiguous_candidates:
                clean = domain.strip().lower().rstrip(".")
                ambiguous_kws = check_porn_ambiguous(clean)
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
                match = PornMatch(
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
        "Porn scan: %d domains scanned, %d flagged (%d hijacked institutions), %d newly inserted"
        " | LLM: %d candidates checked, %d confirmed",
        summary.domains_scanned,
        summary.domains_flagged,
        summary.hijacked_institutions_flagged,
        summary.newly_inserted,
        summary.llm_candidates_checked,
        summary.llm_confirmed,
    )
    return summary
