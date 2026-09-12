#!/usr/bin/env python3
"""Generate data/siaga_demo.db -- a rich, realistic-looking but CLEARLY
SYNTHETIC dataset for video demo / storytelling purposes only.

THIS IS NOT REAL EVALUATION EVIDENCE. Never point the real dashboard at this
file for anything other than recording demo footage. See docs/demo_mode.md
for how the "MODE DEMO" banner activates and why this file is kept out of
the submitted repo entirely (.gitignore'd on the demo-video-showcase branch).

Design rules followed here (do not relax these when editing):

1. The two "hero" narrative scenarios (the ones a video will zoom into and
   narrate) use fully FICTIONAL institution/brand names, with the literal
   suffix "(Skenario Simulasi)" baked into the data fields themselves --
   never only a page-level banner -- so the label survives a cropped
   screenshot or a short video clip. This avoids ever repeating the
   real-institution-defamation mistake found earlier in this project's
   history (CLAUDE.md rule #5).
2. Generic "background volume" findings only reuse brand names that ALREADY
   appear as real impersonation victims in this project's real production
   data (Shopee Indonesia, Ruangguru, GoPay Indonesia, Paxel Indonesia,
   Investree Indonesia, Pos Indonesia) -- this is the normal, non-defamatory
   shape of phishing threat intel (the brand is the victim of impersonation,
   not the accused), and matches what SIAGA has genuinely already found.
3. No number in this file is presented anywhere in the app as if it came
   from scripts/run_eval.py or real production telemetry. The Evaluation
   page continues to read the real data/eval_results.json regardless of
   demo mode.
"""

from __future__ import annotations

import argparse
import os
import random
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path

from lib.db import init_db

BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_OUT_PATH = BASE_DIR / "data" / "siaga_demo.db"

RNG_SEED = 20260929  # fixed seed -> reproducible demo dataset across runs

REAL_PATTERN_BRANDS = [
    "Shopee Indonesia",
    "Ruangguru",
    "GoPay Indonesia",
    "Paxel Indonesia",
    "Investree Indonesia",
    "Pos Indonesia",
]

CHEAP_TLDS = ["xyz", "top", "online", "site", "vip", "live", "click"]
ID_TLDS = ["web.id", "my.id"]

KEYWORD_BAIT = ["klaim", "verifikasi", "promo", "gebyar", "hadiah", "gratis", "update", "aktivasi", "cek-poin"]

HERO_BRAND = "Bank Nusantara Sejahtera (Skenario Simulasi)"
HERO_NAMESERVER_SIG = "ns1.demo-shared-host.example"
HERO_INSTITUTION = "Universitas Cendekia Bangsa (Skenario Simulasi)"
HERO_INSTITUTION_DOMAIN = "portal.cendekiabangsa-demo.ac.id"

JUDOL_KEYWORDS_POOL = ["slot", "gacor", "maxwin", "toto", "rtp", "jackpot"]


_domain_counter = [0]


def rand_domain(brand_slug: str, tld: str) -> str:
    _domain_counter[0] += 1
    bait = random.choice(KEYWORD_BAIT)
    return f"{brand_slug}-{bait}-{_domain_counter[0]:05d}.{tld}"


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def build(out_path: Path, days: int = 30) -> None:
    random.seed(RNG_SEED)

    if out_path.exists():
        out_path.unlink()

    init_db(out_path)
    conn = sqlite3.connect(str(out_path))
    conn.execute("PRAGMA foreign_keys=OFF;")

    now = datetime.now(timezone.utc)
    day0 = now - timedelta(days=days - 1)  # oldest day in the window

    # The hero campaign "bursts" 18-16 days ago, gets "reported" ~15 days
    # ago, and visibly winds down (is_live flips false) over the following
    # week -- this is the Problem -> Data -> Insight -> Action -> Impact
    # arc the Overview page narrates.
    burst_start_day = days - 18
    burst_end_day = days - 15
    report_day = days - 14
    resolved_day = days - 8

    ct_raw_rows: list[tuple] = []
    collector_runs_rows: list[tuple] = []
    daily_stats_rows: list[tuple] = []
    domain_findings_rows: list[tuple] = []
    campaign_members: dict[str, list[int]] = {}

    finding_id = 1

    def add_finding(
        domain: str,
        first_seen: datetime,
        brand: str,
        method: str,
        score: int,
        level: str,
        is_live: bool,
        in_blacklist: bool,
        registrar: str,
        nameservers: str,
        reasoning: str,
    ) -> int:
        nonlocal finding_id
        fid = finding_id
        finding_id += 1
        domain_findings_rows.append(
            (
                fid,
                domain,
                iso(first_seen),
                iso(first_seen - timedelta(days=random.randint(0, 3))),
                registrar,
                nameservers,
                brand,
                method,
                score,
                level,
                1 if is_live else 0,
                200 if is_live else random.choice([403, 404, None]),
                reasoning,
                0,
                None,
                1 if in_blacklist else 0,
                iso(first_seen + timedelta(hours=2)),
                iso(first_seen + timedelta(hours=6)) if in_blacklist else None,
                None,  # campaign_id filled in later
            )
        )
        return fid

    for d in range(days):
        day_dt = day0 + timedelta(days=d)
        is_burst = burst_start_day <= d <= burst_end_day

        # -- ct_raw volume for the day (background "lots of data" feel) --
        base_count = random.randint(450, 900)
        if is_burst:
            base_count = int(base_count * random.uniform(1.6, 2.1))
        for i in range(base_count):
            t = day_dt + timedelta(seconds=random.randint(0, 86399))
            slug = f"d{d:02d}-{i:04d}"
            tld = random.choice(CHEAP_TLDS + ID_TLDS)
            ct_raw_rows.append(
                (f"{slug}.{tld}", iso(t), iso(t - timedelta(minutes=random.randint(1, 90))), tld, "demo-ctlogs")
            )

        # -- collector_runs: mostly ok, occasionally partial (kept honest) --
        n_runs = random.randint(1, 3)
        for r in range(n_runs):
            status = "ok" if random.random() > 0.12 else "partial"
            started = day_dt + timedelta(hours=6, minutes=30 * r)
            collector_runs_rows.append(
                (
                    iso(started),
                    iso(started + timedelta(minutes=random.randint(2, 6))),
                    iso(started),
                    "demo-ctlogs",
                    base_count // n_runs,
                    base_count // n_runs,
                    base_count // n_runs,
                    base_count // n_runs,
                    status,
                    None if status == "ok" else "partial fetch: one TLD shard timed out",
                )
            )

        # -- background domain_findings: real-brand-pattern impersonation --
        n_findings_today = random.randint(2, 6)
        if is_burst:
            n_findings_today += random.randint(2, 4)
        day_finding_ids = []
        for _ in range(n_findings_today):
            brand = random.choice(REAL_PATTERN_BRANDS)
            slug = brand.lower().split()[0]
            tld = random.choice(CHEAP_TLDS + ID_TLDS)
            domain = rand_domain(slug, tld)
            t = day_dt + timedelta(seconds=random.randint(0, 86399))
            score = random.randint(45, 92)
            level = "INDIKASI PENIPUAN" if score >= 70 else "HATI-HATI"
            is_live = random.random() > 0.35
            in_bl = random.random() > 0.7
            fid = add_finding(
                domain=domain,
                first_seen=t,
                brand=brand,
                method=random.choice(["edit_distance", "keyword", "homoglyph", "permutation"]),
                score=score,
                level=level,
                is_live=is_live,
                in_blacklist=in_bl,
                registrar=random.choice(["Hostinger Operations, UAB", "NameSilo, LLC", "PANDI Registry .ID"]),
                nameservers=f"ns1.{random.choice(['cheaphost','fastdns','webserv'])}.example",
                reasoning=f"Domain menyerupai brand '{brand}' dengan pola kata pancingan umum.",
            )
            day_finding_ids.append(fid)

        # -- HERO campaign: 18 domains, same nameserver, burst window --
        if is_burst:
            for _ in range(random.randint(4, 8)):
                tld = random.choice(CHEAP_TLDS)
                domain = rand_domain("bns", tld)
                t = day_dt + timedelta(seconds=random.randint(0, 86399))
                score = random.randint(80, 99)
                # After report_day, hero-campaign domains progressively go dark
                is_live = d < report_day
                fid = add_finding(
                    domain=domain,
                    first_seen=t,
                    brand=HERO_BRAND,
                    method="edit_distance",
                    score=score,
                    level="INDIKASI PENIPUAN",
                    is_live=is_live,
                    in_blacklist=False,  # flipped to True at resolved_day below
                    registrar="Hostinger Operations, UAB",
                    nameservers=HERO_NAMESERVER_SIG,
                    reasoning=(
                        f"[{HERO_BRAND}] Domain mencatut nama bank dengan urgensi tinggi; "
                        f"infrastruktur nameserver identik dengan kampanye lain -> indikasi satu sindikat."
                    ),
                )
                campaign_members.setdefault("hero_bns", []).append(fid)

        # -- Impact metric: after resolved_day, flip earlier hero domains dark
        # and mark them as having landed in the public blacklist (the
        # "measurable impact" beat of the story). --
        if d == resolved_day:
            for fid in campaign_members.get("hero_bns", []):
                for idx, row in enumerate(domain_findings_rows):
                    if row[0] == fid:
                        row = list(row)
                        row[10] = 0  # is_live
                        row[11] = 403
                        row[15] = 1  # in_public_blacklist_at_detection
                        row[17] = iso(day_dt)  # blacklist_listed_at
                        domain_findings_rows[idx] = tuple(row)

        # -- daily_stats aggregate row --
        flagged_today = n_findings_today + (len(campaign_members.get("hero_bns", [])) if is_burst else 0)
        daily_stats_rows.append(
            (
                day_dt.date().isoformat(),
                base_count,
                flagged_today,
                max(0, flagged_today - random.randint(0, 2)),
                random.randint(15, 60),
                random.randint(0, 3),
                random.randint(0, 2),
                1 if any(r[-2] == "ok" for r in collector_runs_rows[-n_runs:]) else 0,
                1,
                random.randint(38, 72),
                base_count,
                int(base_count * 0.04),
                flagged_today,
            )
        )

    conn.executemany(
        "INSERT INTO ct_raw (domain, first_seen, not_before, tld, source) VALUES (?,?,?,?,?)",
        ct_raw_rows,
    )
    conn.executemany(
        """INSERT INTO collector_runs
           (started_at, finished_at, run_at, source, fetched, inserted_new,
            domains_found, domains_new, status, error_message)
           VALUES (?,?,?,?,?,?,?,?,?,?)""",
        collector_runs_rows,
    )
    conn.executemany(
        """INSERT INTO daily_stats
           (date, domains_scanned, domains_flagged, domains_live, messages_analyzed,
            reports_drafted, flagged_not_in_blacklist, collector_ok, heartbeat_ok,
            peak_ram_mb, tahap1_passed, tahap2_passed, tahap3_assessed)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        daily_stats_rows,
    )
    conn.executemany(
        """INSERT INTO domain_findings
           (id, domain, first_seen, registered_at, registrar, nameservers, matched_brand,
            match_method, risk_score, risk_level, is_live, last_status_code, reasoning,
            reviewed_by_human, human_verdict, in_public_blacklist_at_detection,
            blacklist_checked_at, blacklist_listed_at, campaign_id)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        domain_findings_rows,
    )

    # -- Campaign row for the hero cluster (nameserver-based, hard technical fact) --
    hero_ids = campaign_members.get("hero_bns", [])
    if hero_ids:
        cur = conn.execute(
            """INSERT INTO campaigns (cluster_type, cluster_key, member_count, first_detected_at, last_updated_at)
               VALUES ('nameserver', ?, ?, ?, ?)""",
            (
                HERO_NAMESERVER_SIG,
                len(hero_ids),
                iso(day0 + timedelta(days=burst_start_day)),
                iso(day0 + timedelta(days=resolved_day)),
            ),
        )
        hero_campaign_id = cur.lastrowid
        conn.executemany(
            "UPDATE domain_findings SET campaign_id=? WHERE id=?",
            [(hero_campaign_id, fid) for fid in hero_ids],
        )

    # -- a couple of small incidental brand_pattern clusters (background realism) --
    for brand in random.sample(REAL_PATTERN_BRANDS, 2):
        matching = [r[0] for r in domain_findings_rows if r[6] == brand][:3]
        if len(matching) >= 2:
            cur = conn.execute(
                """INSERT INTO campaigns (cluster_type, cluster_key, member_count, first_detected_at, last_updated_at)
                   VALUES ('brand_pattern', ?, ?, ?, ?)""",
                (brand, len(matching), iso(day0), iso(now)),
            )
            cid = cur.lastrowid
            conn.executemany(
                "UPDATE domain_findings SET campaign_id=? WHERE id=?",
                [(cid, fid) for fid in matching],
            )

    # -- Judol findings: hero hijacked-institution case + generic background --
    judol_rows = []
    hero_judol_day = day0 + timedelta(days=days - 6)
    judol_rows.append(
        (
            HERO_INSTITUTION_DOMAIN,
            iso(hero_judol_day),
            ",".join(random.sample(JUDOL_KEYWORDS_POOL, 3)),
            1,
            "ac.id",
            iso(hero_judol_day + timedelta(hours=3)),
            "llm",
            (
                f"[{HERO_INSTITUTION}] Skenario simulasi: direktori akademik disisipi tautan judi online. "
                "Data institusi ini fiktif, dibuat khusus untuk demonstrasi produk."
            ),
        )
    )
    for i in range(12):
        t = day0 + timedelta(days=random.randint(0, days - 1), seconds=random.randint(0, 86399))
        tld = random.choice(CHEAP_TLDS + ID_TLDS)
        judol_rows.append(
            (
                f"slot-{random.choice(['gacor','vip','resmi'])}-{i:03d}.{tld}",
                iso(t),
                ",".join(random.sample(JUDOL_KEYWORDS_POOL, 2)),
                0,
                None,
                iso(t + timedelta(hours=1)),
                random.choice(["keyword", "llm"]),
                None,
            )
        )
    conn.executemany(
        """INSERT INTO judol_findings
           (domain, first_seen, matched_keywords, is_hijacked_institution, institution_suffix,
            detected_at, verification_method, llm_reasoning)
           VALUES (?,?,?,?,?,?,?,?)""",
        judol_rows,
    )

    # -- Porn findings: small, background only --
    porn_rows = []
    for i in range(4):
        t = day0 + timedelta(days=random.randint(0, days - 1), seconds=random.randint(0, 86399))
        porn_rows.append(
            (
                f"streaming-dewasa{i}.cc",
                iso(t),
                "video,streaming",
                0,
                None,
                iso(t + timedelta(hours=1)),
                "keyword",
                None,
            )
        )
    conn.executemany(
        """INSERT INTO porn_findings
           (domain, first_seen, matched_keywords, is_hijacked_institution, institution_suffix,
            detected_at, verification_method, llm_reasoning)
           VALUES (?,?,?,?,?,?,?,?)""",
        porn_rows,
    )

    # -- message_analyses: Mode A usage volume, hash-only (privacy design) --
    msg_rows = []
    for i in range(110):
        t = day0 + timedelta(days=random.randint(0, days - 1), seconds=random.randint(0, 86399))
        score = random.randint(0, 100)
        level = "INDIKASI PENIPUAN" if score >= 70 else ("HATI-HATI" if score >= 40 else "AMAN")
        msg_rows.append(
            (
                iso(t),
                "telegram",
                f"demo-hash-{i:04d}" + "0" * 50,
                random.randint(0, 2),
                score,
                level,
                random.randint(300, 4000),
                1 if level == "INDIKASI PENIPUAN" and random.random() > 0.5 else 0,
            )
        )
    conn.executemany(
        """INSERT INTO message_analyses
           (received_at, channel, message_hash, urls_found, risk_score, risk_level, latency_ms, report_drafted)
           VALUES (?,?,?,?,?,?,?,?)""",
        msg_rows,
    )

    conn.commit()
    conn.close()

    print(f"Demo database generated: {out_path}")
    print(f"  ct_raw: {len(ct_raw_rows)} rows")
    print(f"  domain_findings: {len(domain_findings_rows)} rows (hero campaign: {len(hero_ids)} domains)")
    print(f"  judol_findings: {len(judol_rows)} rows (1 hero hijacked-institution scenario)")
    print(f"  porn_findings: {len(porn_rows)} rows")
    print(f"  message_analyses: {len(msg_rows)} rows")
    print(f"  daily_stats: {len(daily_stats_rows)} days")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    build(args.out, args.days)
