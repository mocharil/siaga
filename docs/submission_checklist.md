# SIAGA — AI HackFest 2026 Final Submission Checklist (T30)

> **Status Kesiapan Submit:** ✅ **READY FOR SUBMISSION**  
> **Batas Waktu Pengumpulan:** 29 September 2026  
> **Formulir Pengumpulan:** `forms.gle/s6y8vLzTgosz8rZ39`

---

## 1. Checklist Deliverable Video (15% Bobot Penjurian)

- [x] **Durasi & Format:** 8 Menit (dalam batas 5–10 menit), format MP4 Full HD 1080p, aspek rasio 16:9 Landscape.
- [x] **Watermark Sponsor:** Logo resmi IDwebhost terpasang di sudut kanan atas dari menit 0:00 hingga 8:00 tanpa terputus.
- [x] **Segmen Wajib VPS (Menit 4:00–5:45):** Menampilkan dashboard CloudBaik dan terminal SSH VPS produksi secara berdampingan.
- [x] **Segmen Keandalan & Hosting (Menit 6:15–6:45):** Menampilkan service systemd, backup SQLite, rotasi logrotate, dan isolasi UFW.
- [x] **Penyebutan Verbal Produk:** Nama **"AI Hosting"** dan **"IDwebhost"** diucapkan secara verbal pada segmen VPS dan hosting.
- [x] **Kualitas Audio & Visual:** Font terminal berukuran besar (≥ 16pt) dengan kontras tinggi (Dark Theme), narasi suara jernih tanpa noise.
- [x] **Slide Metrik Nyata:** Seluruh angka bersumber dari snapshot `docs/metrics_snapshot_01sep.txt` (tercantum tanggal snapshot dan 5 hari operasi nyata).
- [x] **Akses Video:** Di-upload ke YouTube sebagai **Publik / Unlisted** (bukan Private) dan sudah diuji dapat dibuka dari browser mode incognito.

---

## 2. Checklist Deliverable Artikel (Target 1.200–1.500 Kata)

- [x] **Jumlah Kata:** ~1.450 kata (memenuhi syarat minimal 800 kata).
- [x] **Dua Backlink Wajib (Anchor Text Persis):**
  - [x] Anchor **`[AI Hosting](https://idwebhost.com/ai-hosting/)`** terpasang secara kontekstual pada Bagian 5 (Menjalankannya di Lingkungan Server).
  - [x] Anchor **`[Cloud VPS](https://cloudbaik.com)`** terpasang secara kontekstual pada Bagian 4 (Arsitektur).
- [x] **Tautan Repositori GitHub & Live Webapp:**
  - Repositori Publik: `https://github.com/mocharil/siaga`
  - Live Web Dashboard: `https://siaga-lake.vercel.app`
- [x] **Kejujuran Teknis & Evaluasi:** Mencantumkan bagian *"Kegagalan Nyata, Bug yang Ditemukan, dan Pelajaran Berharga"* (UTC vs WIB, hardcoded metrics, validasi kontak BSSN/PANDI).
- [x] **Kesesuaian Angka:** Seluruh angka di artikel identik dengan video dan snapshot database.
- [x] **Platform Publik:** Dipublikasikan di platform otoritas tinggi (Dev.to / LinkedIn Articles / Medium) tanpa paywall dan diajukan ke Google Search Console.

---

## 3. Checklist Kebersihan & Kepatuhan Repositori (GitHub)

- [x] **Bebas Kredensial Sensitif:**
  - File `.env` sudah masuk `.gitignore` dan tidak ada API key / Telegram token di riwayat commit.
  - Kredensial root password awal di `VPS.txt` telah di-redact.
- [x] **Dokumentasi Lengkap:**
  - `README.md` komprehensif dengan badges, diagram arsitektur, panduan instalasi, dan kepatuhan UU PDP.
  - `CLAUDE.md` dan runbook devlog (`docs/devlog/`) lengkap dan terstruktur.
- [x] **Integritas Pengujian:**
  - Seluruh 225 unit test (`pytest`) lulus 100% di lokal dan di VPS produksi.

---

## 4. Checklist Infrastruktur Server Produksi (Cloud VPS)

- [x] **SSH Hardening:** SSH Key-Only (ed25519), root login disabled & locked, port 4422.
- [x] **Firewall UFW:** Default DENY incoming, hanya port 4422 yang dibuka. Port 18789 dan 8000 terisolasi di localhost.
- [x] **Collector Harian:** Crontab aktif berjalan otomatis setiap 06:30 WIB.
- [x] **Pemeliharaan Otomatis:**
  - Backup basis data harian (`0 2 * * *`) dengan retensi 7 hari.
  - Healthcheck berkala (`0 */6 * * *`) dengan peringatan instan via Telegram.
  - Rotasi log (`logrotate`) terpasang di `/etc/logrotate.d/siaga`.
- [x] **Dashboard Read-Only:** Berjalan persisten via `siaga-dashboard.service` di `127.0.0.1:8000` (akses aman via SSH tunnel).
- [x] **OpenClaw Gateway:** Berjalan persisten via `openclaw-gateway.service` dengan cron produksi `siaga-daily-cycle` (07:00 WIB).

---

## 5. Ringkasan Data Snapshot untuk Formulir Submit

| Field Pendaftaran | Nilai Resmi yang Digunakan |
|---|---|
| **Nama Proyek** | SIAGA (Sistem Deteksi & Pemantauan Penipuan Digital) |
| **Kategori** | Digital Safety & Public Good |
| **Framework AI** | OpenClaw AI |
| **Model Evaluasi** | Precision: 100.00% · Recall: 91.80% · F1: 0.9573 · FPR: 0.00% |
| **Volume Pemindaian** | 47.664 domain mentah · 546 temuan phishing · 55 klaster kampanye |
| **Infrastruktur** | Cloud VPS (4 vCPU, 4GB RAM, 20GB SSD, Ubuntu 24.04 LTS) |
| **Hosting Partner** | IDwebhost AI Hosting & CloudBaik |
