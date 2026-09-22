#!/usr/bin/env python3
"""Generate data/siaga_demo.db (and optionally enrich data/siaga.db) with a rich,
realistic-looking dataset for video demo, storytelling, and evaluation presentations.

THIS IS A CONTROLLED DEMO & PRESENTATION DATASET.
Features:
1. Two "hero" narrative scenarios with '(Simulated Scenario)' labels for ethical safety.
2. Rich background threat intelligence for Indonesian brands:
   - Banking: BCA, Bank Mandiri, BRI, BNI, CIMB Niaga
   - Fintech/E-Wallet: GoPay, DANA, OVO, ShopeePay
   - E-Commerce & Logistic: Shopee, Tokopedia, Paxel, Pos Indonesia, J&T Express
   - Public Sector & Gov: DJP Pajak, BPJS Ketenagakerjaan, Kemnaker BSU
3. Compromised government (.go.id) & university (.ac.id) subdomains for judol/porn
   with complete RFC 2350 CSIRT draft recommendations.
4. Active, live timestamps leading right up to TODAY so KPIs and trends are never empty.
5. Multi-domain infrastructure clusters (campaigns) sharing nameservers and registrars.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import os
from pathlib import Path
import random
import shutil
import sqlite3

import sys

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from lib.db import init_db
DEFAULT_OUT_PATH = BASE_DIR / "data" / "siaga_demo.db"
DEFAULT_ACTIVE_PATH = BASE_DIR / "data" / "siaga.db"

RNG_SEED = 20260929

REAL_PATTERN_BRANDS = [
    "BCA (Bank Central Asia)",
    "Bank Mandiri",
    "BRI (Bank Rakyat Indonesia)",
    "BNI (Bank Negara Indonesia)",
    "CIMB Niaga",
    "Shopee Indonesia",
    "Tokopedia",
    "GoPay Indonesia",
    "DANA Indonesia",
    "OVO Indonesia",
    "Telkomsel",
    "Indosat Ooredoo",
    "Pajak.go.id (DJP)",
    "BPJS Ketenagakerjaan",
    "Kemnaker BSU",
    "Pos Indonesia",
    "Paxel Indonesia",
    "J&T Express",
    "Investree Indonesia",
    "Ruangguru",
]

BRAND_SLUGS = {
    "BCA (Bank Central Asia)": ["bca-klik", "klikbca-auth", "bca-mobile", "bca-prioritas", "bca-verifikasi"],
    "Bank Mandiri": ["mandiri-livin", "bankmandiri-otp", "livin-poin", "mandiri-kartu", "mandiri-update"],
    "BRI (Bank Rakyat Indonesia)": ["bri-moch", "brimo-auth", "bri-layanan", "ib-bri-update", "bri-festival"],
    "BNI (Bank Negara Indonesia)": ["bni-mobile", "wondr-bni", "bni-layanan", "ebanking-bni", "bni-aktivasi"],
    "CIMB Niaga": ["octo-cimb", "cimb-klik", "cimbniaga-auth", "octomobile-update"],
    "Shopee Indonesia": ["shopee-promo", "shopeepay-klaim", "shopee-gebyar", "shopee-voucher", "shopee-undian"],
    "Tokopedia": ["tokopedia-hadiah", "tokopedia-promo", "tokopedia-verifikasi", "tokocash-klaim"],
    "GoPay Indonesia": ["gopay-klaim", "gopay-promo", "gopay-cashback", "gopay-saldo-gratis"],
    "DANA Indonesia": ["dana-kaget", "dana-gebyar", "dana-verifikasi", "dana-saldo-klaim", "dana-undian"],
    "OVO Indonesia": ["ovo-poin-cashback", "ovo-verifikasi-akun", "ovo-promo-gebyar"],
    "Telkomsel": ["telkomsel-poin-tukar", "my-telkomsel-kuota", "telkomsel-hadiah"],
    "Indosat Ooredoo": ["indosat-im3-kuota", "myim3-promo-bonus", "indosat-poin-tukar"],
    "Pajak.go.id (DJP)": ["djp-pajak-ebilling", "pajak-spt-online", "djp-validasi-nik", "pajak-tagihan-update"],
    "BPJS Ketenagakerjaan": ["bpjs-ketenagakerjaan-klaim", "jmo-bpjs-saldo", "bpjstk-bantuan"],
    "Kemnaker BSU": ["kemnaker-bsu-bantuan", "cek-bsu-kemnaker", "pencairan-bsu-pemerintah"],
    "Pos Indonesia": ["posindonesia-lacak-resi", "pos-kurir-paket-apk", "cekresi-pos-indo"],
    "Paxel Indonesia": ["paxel-cek-resi", "paxel-lacak-paket", "paxelbox-verifikasi"],
    "J&T Express": ["jnt-lacak-paket-resi", "jnt-kurir-apk-update", "jet-express-tracking"],
    "Investree Indonesia": ["investree-pinjaman-kilat", "investree-dana-cair", "investree-modal-usaha"],
    "Ruangguru": ["ruangguru-beasiswa", "ruangguru-diskon-langganan", "ruangbelajar-promo"],
}

CHEAP_TLDS = ["xyz", "top", "online", "site", "vip", "live", "click", "cloud", "store", "cc"]
ID_TLDS = ["web.id", "my.id", "biz.id", "co.id"]

KEYWORD_BAIT = [
    "klaim", "verifikasi", "promo", "gebyar", "hadiah", "gratis",
    "update", "aktivasi", "cek-poin", "undian", "login", "auth",
    "bantuan", "cairkan", "ebilling", "lacak", "otp"
]

HERO_BRAND = "Bank Nusantara Sejahtera (Simulated Scenario)"
HERO_NAMESERVER_SIG = "ns1.demo-shared-host.example"
HERO_INSTITUTION = "Universitas Cendekia Bangsa (Simulated Scenario)"
HERO_INSTITUTION_DOMAIN = "portal.cendekiabangsa-demo.ac.id"

JUDOL_KEYWORDS_POOL = ["slot", "gacor", "maxwin", "toto", "rtp", "jackpot", "zeus", "olympus", "mahjong", "scatter", "prada88", "slot777"]

HIJACKED_GOV_ACAD_DOMAINS = [
    ("disdik.bantenprov.go.id/slot-gacor-olympus", "go.id", "slot,gacor,olympus", "Subdomain portal pendidikan provinsi disusupi direktori judi online luar."),
    ("bkpsdm.karawangkab.go.id/zeus88-login", "go.id", "zeus,slot88,login", "Injeksi script redirect pada direktori kepegawaian daerah."),
    ("perpustakaan.unand.ac.id/mahjong-wins", "ac.id", "mahjong,slot,scatter", "Subdomain repositori perpustakaan universitas disisipi tautan slot gacor."),
    ("journal.ui.ac.id/slot777-prada", "ac.id", "slot777,prada88,jackpot", "Arsip e-journal universitas negeri ditembus melalui celah plugin CMS OJS."),
    ("dinkes.semarangkota.go.id/rtp-live-maxwin", "go.id", "rtp,maxwin,slot", "Portal informasi kesehatan kota disisipi halaman landing judi online."),
    ("lppm.unpad.ac.id/togel-resmi", "ac.id", "toto,togel,jackpot", "Halaman pengabdian masyarakat kampus disusupi iklan togel toto online."),
    ("kelurahan-cibaduyut.bandung.go.id/gacor88", "go.id", "gacor,slot,maxwin", "Portal administrasi kelurahan disusupi file defacement judi online."),
    ("simpeg.malangkab.go.id/slot-server-kamboja", "go.id", "slot,kamboja,gacor", "Server kepegawaian kabupaten mengalami injeksi backlink slot server luar."),
    ("alumni.ipb.ac.id/jackpot-sensational", "ac.id", "jackpot,slot,maxwin", "Portal tracer study alumni universitas negeri disisipi direktori promosi judi."),
    ("desa-sukamaju.magelangkab.go.id/link-gacor", "desa.id", "slot,gacor,maxwin", "Website Sistem Informasi Desa (.desa.id) disusupi link landing page slot."),
    ("jdih.kemenpora.go.id/slot-pragmatic", "go.id", "slot,pragmatic,olympus", "Portal dokumentasi hukum kementerian disisipi landing judi slot online."),
    ("dpmptsp.jabarprov.go.id/olympus88", "go.id", "olympus,slot,zeus", "Layanan perizinan terpadu provinsi mengalami injeksi SEO judi online."),
    ("pasca.uny.ac.id/mahjong-ways-2", "ac.id", "mahjong,slot,rtp", "Subdomain pascasarjana universitas disusupi artikel promosi judi slot."),
    ("dishub.surabaya.go.id/zeus-slot-resmi", "go.id", "zeus,slot,resmi", "Subdomain dinas perhubungan kota disisipi direktori tersembunyi judi online."),
    ("pkk.semarangkab.go.id/slot-gacor-hari-ini", "go.id", "slot,gacor,hari-ini", "Portal organisasi masyarakat daerah mengalami injeksi halaman judi."),
]

PORN_DOMAINS = [
    ("streaming-dewasa-indo.cc", "video,streaming,dewasa", 0, None, "Situs streaming konten pornografi tanpa verifikasi usia target audiens Indonesia."),
    ("nonton-film-dewasa88.top", "film,dewasa,nonton", 0, None, "Portal video dewasa ilegal menyebarkan malware dan iklan judi online."),
    ("bokep-indo-terbaru.xyz", "video,dewasa,viral", 0, None, "Situs agregator konten pornografi ilegal melanggar UU ITE pasal 27 ayat 1."),
    ("live-dewasa-stream.online", "live,cam,dewasa", 0, None, "Platform live webcam streaming pornografi tanpa filter konten."),
    ("video-dewasa-viral.site", "video,dewasa,viral", 0, None, "Situs penyebaran video asusila ilegal dan phishing kredensial media sosial."),
    ("streaming-panas-vip.live", "streaming,dewasa,vip", 0, None, "Layanan streaming konten dewasa melanggar TrustPositif Kominfo."),
    ("nonton-gratis-18plus.com", "dewasa,18plus,video", 0, None, "Portal agregasi video pornografi berkedok forum diskusi online."),
    ("download-bokep-indo.vip", "download,dewasa,video", 0, None, "Situs pengunduhan konten pornografi yang menyisipkan trojan perbankan."),
    ("arsip-surat.kabbogor.go.id/streaming-dewasa", "video,dewasa,streaming", 1, "go.id", "Subdomain pemerintah daerah disusupi tautan konten dewasa ilegal."),
    ("download.itats.ac.id/video-dewasa", "video,dewasa,nonton", 1, "ac.id", "Repositori unduhan kampus disusupi direktori pornografi oleh pihak luar."),
    ("forum-dewasa-nusantara.top", "forum,dewasa,komunitas", 0, None, "Forum distribusi konten pornografi dan transaksi ilegal."),
    ("film-dewasa-jepang-subindo.xyz", "film,dewasa,subindo", 0, None, "Situs nonton streaming ilegal berisiko pencurian data pengguna."),
    ("koleksi-dewasa-viral.cloud", "koleksi,dewasa,viral", 0, None, "Cloud hosting penyimpan materi asusila ilegal."),
    ("streaming-dewasa-live.site", "streaming,dewasa,live", 0, None, "Situs live streaming konten pornografi."),
    ("video-panas-terbaru.online", "video,panas,dewasa", 0, None, "Portal agregasi video asusila menyebarkan adware berbahaya."),
]

_domain_counter = [0]


def rand_domain(brand: str, tld: str) -> str:
    _domain_counter[0] += 1
    slug_list = BRAND_SLUGS.get(brand, [brand.lower().split()[0]])
    slug = random.choice(slug_list)
    bait = random.choice(KEYWORD_BAIT)
    rand_num = random.randint(100, 9999)
    return f"{slug}-{bait}{rand_num}.{tld}"


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def build(out_path: Path, days: int = 30) -> None:
    random.seed(RNG_SEED)

    if out_path.exists():
        try:
            out_path.unlink()
        except Exception:
            pass

    os.makedirs(out_path.parent, exist_ok=True)
    init_db(out_path)
    conn = sqlite3.connect(str(out_path))
    conn.execute("PRAGMA foreign_keys=OFF;")

    now = datetime.now(timezone.utc)
    day0 = now - timedelta(days=days - 1)  # oldest day in the window

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

    REGISTRARS = [
        "Hostinger Operations, UAB",
        "NameSilo, LLC",
        "PANDI Registry .ID",
        "Cloudflare, Inc.",
        "GoDaddy.com, LLC",
        "Namecheap, Inc.",
        "Tucows Domains Inc.",
    ]

    for d in range(days):
        day_dt = day0 + timedelta(days=d)
        is_burst = burst_start_day <= d <= burst_end_day
        is_today = (d == days - 1)
        is_yesterday = (d == days - 2)

        # Base CT logs scanned
        base_count = random.randint(14500, 22000)
        if is_today:
            base_count = 24850
        elif is_yesterday:
            base_count = 22100
        elif is_burst:
            base_count = int(base_count * 1.45)

        # Sample CT raw logs
        sample_logs = 120 if not is_today else 240
        for i in range(sample_logs):
            t = day_dt + timedelta(seconds=random.randint(0, 86399 if not is_today else int((now - day_dt.replace(hour=0, minute=0, second=0)).total_seconds())))
            tld = random.choice(CHEAP_TLDS + ID_TLDS)
            slug = f"ct-log-d{d:02d}-{i:04d}"
            ct_raw_rows.append(
                (f"{slug}.{tld}", iso(t), iso(t - timedelta(minutes=random.randint(1, 90))), tld, "demo-ctlogs")
            )

        # Collector runs
        n_runs = 4
        for r in range(n_runs):
            c_status = "ok" if (is_today or random.random() > 0.1) else "partial"
            started = day_dt + timedelta(hours=5 * r + 1, minutes=random.randint(10, 45))
            collector_runs_rows.append(
                (
                    iso(started),
                    iso(started + timedelta(minutes=random.randint(2, 5))),
                    iso(started),
                    "demo-ctlogs",
                    base_count // n_runs,
                    base_count // n_runs,
                    base_count // n_runs,
                    base_count // n_runs,
                    c_status,
                    None if c_status == "ok" else "partial fetch: upstream timeout resolved",
                )
            )

        # Domain findings for this day
        n_findings_today = random.randint(5, 9)
        if is_today:
            n_findings_today = 18
        elif is_yesterday:
            n_findings_today = 14
        elif is_burst:
            n_findings_today = 15

        for fi in range(n_findings_today):
            brand = random.choice(REAL_PATTERN_BRANDS)
            tld = random.choice(CHEAP_TLDS + ID_TLDS)
            domain = rand_domain(brand, tld)
            
            # For today, make timestamps fresh
            if is_today:
                mins_ago = random.randint(3, 480)
                t = now - timedelta(minutes=mins_ago)
            else:
                t = day_dt + timedelta(seconds=random.randint(0, 86399))

            score = random.randint(62, 98)
            level = "INDIKASI PENIPUAN" if score >= 70 else "HATI-HATI"
            is_live = (is_today or random.random() > 0.3)
            in_bl = (not is_today and random.random() > 0.65)
            reg = random.choice(REGISTRARS)
            ns = f"ns{random.randint(1, 4)}.{random.choice(['fastdns-host','bulletproof-dns','cf-nameserver','cloud-edge-dns'])}.example"
            reasoning = f"Impersonasi merek '{brand}' dengan pola tipuan kata kunci urgensi tinggi. Terdaftar pada {reg}."

            fid = add_finding(
                domain=domain,
                first_seen=t,
                brand=brand,
                method=random.choice(["edit_distance", "keyword", "homoglyph", "permutation"]),
                score=score,
                level=level,
                is_live=is_live,
                in_blacklist=in_bl,
                registrar=reg,
                nameservers=ns,
                reasoning=reasoning,
            )

        # Hero Campaign (Bank Nusantara Sejahtera)
        if is_burst:
            for _ in range(random.randint(4, 7)):
                tld = random.choice(CHEAP_TLDS)
                domain = rand_domain("Bank Mandiri", tld).replace("mandiri", "bns-bank")
                t = day_dt + timedelta(seconds=random.randint(0, 86399))
                score = random.randint(84, 99)
                is_live = d < report_day
                fid = add_finding(
                    domain=domain,
                    first_seen=t,
                    brand=HERO_BRAND,
                    method="edit_distance",
                    score=score,
                    level="INDIKASI PENIPUAN",
                    is_live=is_live,
                    in_blacklist=False,
                    registrar="Hostinger Operations, UAB",
                    nameservers=HERO_NAMESERVER_SIG,
                    reasoning=(
                        f"[{HERO_BRAND}] Domain meniru institusi perbankan dengan klaim gebyar undian fiktif; "
                        f"berbagi infrastruktur nameserver identical -> terindikasi sindikat penipuan terorganisir."
                    ),
                )
                campaign_members.setdefault("hero_bns", []).append(fid)

        # Impact metric for hero campaign
        if d == resolved_day:
            for fid in campaign_members.get("hero_bns", []):
                for idx, row in enumerate(domain_findings_rows):
                    if row[0] == fid:
                        r_list = list(row)
                        r_list[10] = 0  # is_live -> 0
                        r_list[11] = 403
                        r_list[15] = 1  # in_blacklist -> 1
                        r_list[17] = iso(day_dt)
                        domain_findings_rows[idx] = tuple(r_list)

        # Daily stats aggregate
        flagged_today = n_findings_today + (len(campaign_members.get("hero_bns", [])) if is_burst else 0)
        live_today = max(2, int(flagged_today * (0.6 if is_today else 0.35)))
        tahap1 = int(base_count * 0.065)
        tahap2 = int(tahap1 * 0.28)
        tahap3 = int(tahap2 * 0.35)

        daily_stats_rows.append(
            (
                day_dt.date().isoformat(),
                base_count,
                flagged_today,
                live_today,
                random.randint(90, 160) if is_today else random.randint(45, 120),
                random.randint(18, 32) if is_today else random.randint(6, 20),
                max(2, flagged_today - random.randint(1, 4)),
                1,
                1,
                random.randint(58, 74),
                tahap1,
                tahap2,
                tahap3,
            )
        )

    # Insert CT raw & Collector runs
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

    # Hero Campaign Row
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

    # Secondary Campaign Clusters
    CLUSTER_TEMPLATES = [
        ("nameserver", "ns1.bulletproof-asia-host.example", 14),
        ("nameserver", "ns2.fastflux-phish-cluster.online", 12),
        ("brand_pattern", "BCA (Bank Central Asia)", 10),
        ("brand_pattern", "Pajak.go.id (DJP)", 8),
        ("brand_pattern", "DANA Indonesia", 9),
        ("brand_pattern", "Pos Indonesia", 7),
    ]

    for c_type, c_key, target_count in CLUSTER_TEMPLATES:
        matching = []
        if c_type == "brand_pattern":
            matching = [r[0] for r in domain_findings_rows if r[6] == c_key][:target_count]
        else:
            matching = [r[0] for r in domain_findings_rows if r[0] not in hero_ids][:target_count]

        if len(matching) >= 3:
            cur = conn.execute(
                """INSERT INTO campaigns (cluster_type, cluster_key, member_count, first_detected_at, last_updated_at)
                   VALUES (?, ?, ?, ?, ?)""",
                (c_type, c_key, len(matching), iso(day0 + timedelta(days=5)), iso(now)),
            )
            cid = cur.lastrowid
            conn.executemany(
                "UPDATE domain_findings SET campaign_id=? WHERE id=?",
                [(cid, fid) for fid in matching],
            )

    # Judol findings (Hero scenario + Real high-profile government/academic hijacks + Standalone slot domains)
    judol_rows = []
    
    # 1. Hero Scenario
    hero_judol_day = now - timedelta(days=3, hours=4)
    judol_rows.append(
        (
            HERO_INSTITUTION_DOMAIN,
            iso(hero_judol_day),
            "slot,gacor,olympus",
            1,
            "ac.id",
            iso(hero_judol_day + timedelta(hours=1)),
            "llm",
            (
                f"[{HERO_INSTITUTION}] Skenario simulasi: direktori repositori akademik disisipi tautan judi online. "
                "Data institusi ini adalah fiktif, dibuat khusus untuk demonstrasi platform."
            ),
        )
    )

    # 2. Compromised Institutional Subdomains (.go.id, .ac.id, .desa.id)
    for domain, suffix, kw, reasoning in HIJACKED_GOV_ACAD_DOMAINS:
        t = now - timedelta(days=random.randint(0, 14), hours=random.randint(1, 23))
        judol_rows.append(
            (
                domain,
                iso(t),
                kw,
                1,
                suffix,
                iso(t + timedelta(minutes=random.randint(15, 60))),
                "llm",
                reasoning,
            )
        )

    # 3. Standalone Judol Domains (65+ domains)
    SLOT_NAMES = ["zeus", "olympus", "gacor", "maxwin", "mahjong", "prada88", "slot777", "sensational", "rtp-live", "toto-macau", "nexus-slot", "pragmatic"]
    for i in range(65):
        t = now - timedelta(days=random.randint(0, days - 1), hours=random.randint(1, 23), minutes=random.randint(0, 59))
        tld = random.choice(CHEAP_TLDS + ID_TLDS)
        s_name = random.choice(SLOT_NAMES)
        dom = f"{s_name}-{random.choice(['vip','resmi','login','daftar','link'])}-{random.randint(10, 999)}.{tld}"
        kws = ",".join(random.sample(JUDOL_KEYWORDS_POOL, 3))
        judol_rows.append(
            (
                dom,
                iso(t),
                kws,
                0,
                None,
                iso(t + timedelta(minutes=random.randint(10, 90))),
                random.choice(["keyword", "llm"]),
                f"Domain penyedia taruhan online berbayar dengan kata kunci '{kws}'. Melanggar UU ITE pasal 27 ayat 2.",
            )
        )

    conn.executemany(
        """INSERT INTO judol_findings
           (domain, first_seen, matched_keywords, is_hijacked_institution, institution_suffix,
            detected_at, verification_method, llm_reasoning)
           VALUES (?,?,?,?,?,?,?,?)""",
        judol_rows,
    )

    # Porn findings
    porn_rows = []
    for dom, kw, is_hijacked, suffix, reasoning in PORN_DOMAINS:
        t = now - timedelta(days=random.randint(0, 20), hours=random.randint(1, 23))
        porn_rows.append(
            (
                dom,
                iso(t),
                kw,
                is_hijacked,
                suffix,
                iso(t + timedelta(hours=1)),
                "keyword" if not is_hijacked else "llm",
                reasoning,
            )
        )

    # Additional standalone adult content domains (30 domains)
    for i in range(30):
        t = now - timedelta(days=random.randint(0, days - 1), hours=random.randint(1, 23))
        dom = f"video-dewasa-{random.choice(['viral','streaming','nonton','live'])}-{random.randint(10, 999)}.{random.choice(['cc','top','xyz','site','online'])}"
        porn_rows.append(
            (
                dom,
                iso(t),
                "video,streaming,dewasa",
                0,
                None,
                iso(t + timedelta(hours=1)),
                "keyword",
                "Penyebaran konten asusila ilegal melanggar TrustPositif Kominfo RI.",
            )
        )

    conn.executemany(
        """INSERT INTO porn_findings
           (domain, first_seen, matched_keywords, is_hijacked_institution, institution_suffix,
            detected_at, verification_method, llm_reasoning)
           VALUES (?,?,?,?,?,?,?,?)""",
        porn_rows,
    )

    # Mode A Message Analyses (Telegram Triage)
    msg_rows = []
    for i in range(160):
        t = now - timedelta(days=random.randint(0, days - 1), hours=random.randint(0, 23), minutes=random.randint(0, 59))
        score = random.randint(5, 98)
        level = "INDIKASI PENIPUAN" if score >= 70 else ("HATI-HATI" if score >= 40 else "AMAN")
        msg_rows.append(
            (
                iso(t),
                "telegram",
                f"demo-hash-{i:04d}" + "a" * 50,
                random.randint(1, 3) if score >= 40 else 0,
                score,
                level,
                random.randint(450, 3200),
                1 if level == "INDIKASI PENIPUAN" and random.random() > 0.4 else 0,
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

    print(f"[OK] Rich demo database generated successfully: {out_path}")
    print(f"  Total ct_raw: {len(ct_raw_rows)} rows")
    print(f"  Total domain_findings: {len(domain_findings_rows)} rows")
    print(f"  Total judol_findings: {len(judol_rows)} rows ({sum(1 for r in judol_rows if r[3]==1)} compromised .go.id/.ac.id)")
    print(f"  Total porn_findings: {len(porn_rows)} rows")
    print(f"  Total message_analyses: {len(msg_rows)} rows")
    print(f"  Total daily_stats: {len(daily_stats_rows)} days (Up to TODAY {now.date()})")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT_PATH)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument(
        "--target",
        choices=["demo", "active", "both"],
        default="both",
        help="Target database: 'demo' (data/siaga_demo.db), 'active' (data/siaga.db), or 'both' (default)",
    )
    args = parser.parse_args()

    if args.target in ("demo", "both"):
        print(f"--- Generating Demo Database: {args.out} ---")
        build(args.out, args.days)

    if args.target in ("active", "both"):
        print(f"--- Generating Active Database: {DEFAULT_ACTIVE_PATH} ---")
        if DEFAULT_ACTIVE_PATH.exists():
            backup_file = DEFAULT_ACTIVE_PATH.parent / f"siaga_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            print(f"Creating safety backup -> {backup_file}")
            shutil.copy2(DEFAULT_ACTIVE_PATH, backup_file)
        build(DEFAULT_ACTIVE_PATH, args.days)


if __name__ == "__main__":
    main()
