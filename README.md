# SIAGA — Sistem Deteksi & Pemantauan Penipuan Digital

<div align="center">

![Python 3.12](https://img.shields.io/badge/python-3.12-blue.svg)
![Framework OpenClaw](https://img.shields.io/badge/framework-OpenClaw%20AI-orange.svg)
![Tests Passing](https://img.shields.io/badge/tests-225%2F225%20passing-brightgreen.svg)
![Precision](https://img.shields.io/badge/precision-100%25-success.svg)
![Recall](https://img.shields.io/badge/recall-91.8%25-blue.svg)
![F1-Score](https://img.shields.io/badge/F1--score-0.9573-success.svg)
![Privacy](https://img.shields.io/badge/privacy-UU%20PDP%20Compliant-purple.svg)
![Live Dashboard](https://img.shields.io/badge/live%20demo-siaga--lake.vercel.app-blueviolet.svg)

**Agent AI Otonom Pemantau Phishing Proaktif Berbasis Certificate Transparency dan Arsitektur Hemat Token**  
*Karya untuk AI HackFest 2026 (IDwebhost × PANDI) — Kategori Digital Safety & Public Good*  
🌐 **Live Web Dashboard:** [https://siaga-lake.vercel.app](https://siaga-lake.vercel.app) | 📦 **Repository:** [https://github.com/mocharil/siaga](https://github.com/mocharil/siaga)

</div>

---

## 📌 Ringkasan Masalah & Solusi

Setiap hari di Indonesia, ribuan domain baru didaftarkan untuk melancarkan serangan *social engineering* dan *brand impersonation* perbankan serta e-commerce. Sistem keamanan konvensional (daftar hitam publik) rata-rata memiliki waktu tunda (*lead time*) 24–36 jam sebelum sebuah domain ditandai sebagai berbahaya—waktu yang lebih dari cukup bagi penipu untuk menguras rekening korban.

**SIAGA** hadir sebagai sistem pertahanan siber otonom dengan dua mode operasional:
1. **Mode A (Asisten Interaktif):** Pengguna meneruskan pesan atau URL mencurigakan ke Bot Telegram (`@siaga_ai_bot`) untuk mendapatkan penilaian risiko instan, verifikasi teknis (RDAP, redirect HEAD-only, homoglyph), dan penjelasan bahasa awam dengan 3 bukti konkret.
2. **Mode B (Intelijen Ancaman Proaktif):** Agen secara otomatis memantau aliran pendaftaran domain baru global via *Certificate Transparency (CT) Log*, menyaring puluhan ribu domain per hari, mengidentifikasi kampanye phishing, dan merangkum temuan prioritas ke dalam *Daily Threat Brief*.

---

## 🏗️ Arsitektur Sistem: Cascading Funnel

Memproses puluhan ribu domain harian langsung dengan LLM adalah pemborosan biaya komputasi. SIAGA menggunakan arsitektur penyaringan 3-tahap bertingkat (*Cascading Funnel*) yang menghemat hingga **98% konsumsi token AI**:

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Tahap 0: CT Log Ingestion (10.000+ domain/hari)                         │
├──────────────────────────────────────────────────────────────────────────┤
│ Tahap 1: Brand Similarity Filter (CPU Lokal, 0 Token LLM)                │
│          • Damerau-Levenshtein Distance (<= 2 pendek, <= 3 panjang)      │
│          • Homoglyph & Punycode Cyrillic/Greek Normalizer                │
│          • Subdomain & Directed Keyword Stem Matching                    │
│          ➔ Memangkas ~96.5% domain wajar dalam 1.51 ms/domain            │
├──────────────────────────────────────────────────────────────────────────┤
│ Tahap 2: Verifikasi Teknis Ringan (0 Token LLM, Network I/O Ringan)     │
│          • Pengecekan status respon HTTP (Strictly HEAD-Only)            │
│          • Cache RDAP umur pendaftaran domain                            │
│          • Verifikasi DNS nameserver & Feed Blacklist (URLhaus)          │
│          ➔ Menyaring domain mati & subdomain institusi resmi             │
├──────────────────────────────────────────────────────────────────────────┤
│ Tahap 3: Sintesis Risiko LLM & Korelasi Kampanye                         │
│          • Analisis linguistik pesan + evaluasi bukti teknis             │
│          • Klasterisasi infrastruktur kampanye penipuan                  │
│          ➔ Menghasilkan Temuan Berbobot Tinggi & Brief Harian            │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Hasil Evaluasi Model & Data Operasional

### Metrik Evaluasi Model (Ground-Truth 120 Sampel):
* **Precision:** **100.00%** (56/56 — 0 False Positive pada sampel sah dan ambigu)
* **Recall:** **91.80%** (56 dari 61 varian penipuan terdeteksi)
* **F1-Score:** **0.9573** (Batas target kompetisi ≥ 0.8200)
* **False Positive Rate (FPR):** **0.00%** (Ambang batas toleransi ≤ 10.0%)
* **Akurasi Keseluruhan:** **95.83%**
* **Latensi Inferensi p50:** **3.539 ms**

### Data Operasional Nyata (Snapshot 5 Hari Operasi di Cloud VPS):
* **Total Domain Mentah Dipindai (`ct_raw`):** **47.664 domain**
* **Total Temuan Terindikasi (`domain_findings`):** **546 temuan**
* **Klaster Infrastruktur Kampanye:** **55 klaster**
* **Top 3 Brand Paling Banyak Ditiru:** Ruangguru (61 domain), Investree (38 domain), Paxel (32 domain).
* **RAM Peak Aktual:** **31.9 MB** (Dashboard API) / **131.5 MB** (OpenClaw Gateway).

---

## 🔒 Privasi & Kepatuhan Regulasi (UU PDP No. 27/2022)

1. **Zero-Raw Storage:** Modul analisis pesan pengguna hanya mencatat *cryptographic hash* SHA-256 dan skor risiko—tidak pernah menyimpan isi pesan, nomor telepon, atau nomor rekening.
2. **Auto-Retention 30 Hari:** Seluruh hash pesan dihapus secara otomatis dari basis data setelah 30 hari via job retensi berkala.
3. **Privacy Masking UI:** Dasbor pemantauan menyamarkan nama domain temuan secara default (`b***-verif.xyz`) guna mencegah pencemaran nama baik pihak yang tidak bersalah pada saat presentasi atau demonstrasi publik.
4. **Human-in-the-Loop:** Agen menyusun draf bukti teknis, namun aksi pelaporan ke otoritas (Kominfo, CSIRT BSSN, OJK Satgas PASTI, PANDI IDADX) sepenuhnya berada di bawah kendali operator manusia.

---

## 🚀 Panduan Instalasi & Menjalankan

### 1. Prasyarat Sistem
* Python 3.11 atau 3.12
* SQLite3
* Node.js v20+ (untuk OpenClaw Gateway)

### 2. Setup Lingkungan
```bash
# Clone repositori
git clone https://github.com/idwebhost-pandi/siaga.git
cd siaga

# Buat virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# atau: .venv\Scripts\Activate.ps1  # Windows

# Pasang dependensi
pip install -r requirements.txt
```

### 3. Konfigurasi Environment (`.env`)
Salin template berkas `.env.example` ke `.env`:
```ini
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
SIAGA_OWNER_CHAT_ID=your_telegram_chat_id
LLM_PROVIDER=openai
LLM_API_KEY=your_api_key
SIAGA_DB_PATH=data/siaga.db
```

### 4. Menjalankan Komponen
```bash
# 1. Menjalankan pengujian lengkap
pytest tests/ -v

# 2. Menjalankan CT Collector harian
python collector/ct_collector.py

# 3. Menjalankan Siklus Analisis Harian (Pipeline Mode B)
python scripts/run_daily_cycle.py --date $(date +%Y-%m-%d) --allow-network

# 4. Menjalankan Dashboard Read-Only (Bind 127.0.0.1:8000)
python dashboard/api.py
```

---

## 🛡️ Panduan Operasional di Server Produksi (Cloud VPS)

SIAGA telah di-hardening dan berjalan secara persisten di lingkungan **Cloud VPS**:
* **SSH Hardening:** Otentikasi SSH *Key-Only* ed25519, `PermitRootLogin no`, `PasswordAuthentication no`.
* **Firewall UFW:** Default DENY incoming, hanya membuka port 4422 (SSH). Seluruh antarmuka internal terisolasi di `127.0.0.1` dan diakses via SSH Tunnel.
* **Cron & Maintenance:**
  - `30 6 * * *` — CT Collector Harian
  - `0 */6 * * *` — Healthcheck & Telegram Alerting
  - `0 2 * * *` — Online SQLite Backup Harian
  - `logrotate` — Rotasi log harian terkompresi dengan retensi 7 hari.

---

## 👥 Pengembang & Pengakuan

* **Pengembang:** Moch. Aril Indra Permana
* **Kompetisi:** [AI HackFest 2026](https://idwebhost.com) (IDwebhost × PANDI)
* **Infrastruktur Komputasi:** [Cloud VPS](https://cloudbaik.com) & [AI Hosting IDwebhost](https://idwebhost.com/ai-hosting/)

---

## 📄 Lisensi

Proyek ini dirilis di bawah lisensi [MIT License](LICENSE).
