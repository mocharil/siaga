# SIAGA — Konteks Proyek

Agent deteksi penipuan digital untuk **AI HackFest 2026** (IDwebhost × PANDI), kategori Digital Safety & Public Good. Framework: **OpenClaw**. Deadline submit: **29 September 2026**.

Rencana lengkap ada di `plan/`. Runbook task-by-task ada di `plan/10-build-runbook.md`.

> Salin berkas ini ke root repo `siaga/` saat repo dibuat.

---

## Aturan keras — jangan dilanggar tanpa saya minta eksplisit

### 1. Jangan tulis kode OpenClaw dari ingatan

OpenClaw bergerak cepat dan API-nya mudah dihalusinasi. Setiap kali menyentuh integrasi OpenClaw (Gateway, Skill, heartbeat, konfigurasi channel):

1. Baca dokumentasi resmi lebih dulu — `docs.openclaw.ai`, repo `openclaw/openclaw`
2. Kutip bagian yang dipakai
3. Baru tulis kode

Kalau API yang dibutuhkan tidak ada di dokumentasi, **katakan begitu**. Jangan diisi tebakan yang terlihat masuk akal.

Aturan yang sama berlaku untuk format respons CT log dan RDAP: lakukan satu request nyata dan tunjukkan strukturnya sebelum menulis parser.

### 2. Jangan pernah mengarang angka atau hasil

Kredibilitas adalah seluruh nilai proyek ini di mata juri. Satu angka yang tidak cocok dengan demo menjatuhkan seluruh karya.

- Semua metrik harus keluar dari eksekusi nyata `scripts/run_eval.py`
- Kalau belum ada hasilnya, tulis `TODO: isi dari run_eval.py` — jangan diisi angka contoh
- Jangan buat log atau screenshot yang seolah-olah hasil eksekusi
- Sampel test set sintetis **boleh** dibuat, tapi wajib diberi `"source": "sintetis"`

### 3. Batasan jaringan — ini syarat kepatuhan lomba, bukan preferensi

Panitia melarang keras hacking, unauthorized access, DDoS, dan scraping yang melanggar ToS. Melanggar = diskualifikasi.

| Boleh | Tidak boleh |
|---|---|
| `HEAD` request untuk cek status dan redirect | `GET` halaman penuh |
| Baca CT log, RDAP, DNS — data publik | Port scan, uji kerentanan, percobaan login |
| Baca status blacklist publik | Mengirim data apa pun ke domain yang diperiksa |
| Timeout ketat, rate limit, User-Agent jujur | Headless browser, eksekusi JavaScript |

Kalau sebuah situs menolak `HEAD`, catat sebagai "tidak dapat diperiksa". **Jangan diubah jadi `GET`.**

### 4. Repo ini akan dipublikasikan

Link repo masuk ke artikel lomba. Selain itu saya bekerja di operator telekomunikasi, jadi kebocoran punya konsekuensi di luar lomba.

Tidak pernah masuk repo, log, atau prompt:
- Isi `.env`, token Telegram, API key
- Data apa pun dari tempat kerja — termasuk yang sudah dianonimkan
- Pesan pribadi milik siapa pun dalam bentuk asli
- `siaga.db` yang sudah berisi data nyata

### 5. Privasi ada di level arsitektur, bukan disclaimer

- `message_analyses` menyimpan **hash pesan, bukan isinya**
- Nomor telepon dan nomor rekening tidak pernah disimpan
- Hash dihapus otomatis setelah 30 hari — ini kode yang berjalan, bukan janji di dokumen
- Temuan selalu disebut "indikasi", tidak pernah "terbukti"
- Tidak pernah menyebut atau menyiratkan identitas orang; hanya infrastruktur teknis

---

## Yang paling menentukan keberhasilan proyek

**`collector/ct_collector.py` harus jalan setiap hari sejak 1 September.**

Domain yang lewat hari ini tidak bisa diambil ulang besok. Scoring selalu bisa dijalankan ulang ke data lama lewat `scripts/rescore_backlog.py`. Karena itu collector nyala jauh sebelum fitur lain jadi — di laptop kalau perlu, tanpa menunggu VPS.

Kalau ada konflik prioritas, collector menang.

**Pemeriksaan pertama tiap sesi:**
```bash
sqlite3 data/siaga.db "SELECT date(first_seen), COUNT(*) FROM ct_raw GROUP BY 1 ORDER BY 1 DESC LIMIT 5;"
```
Kalau kemarin kosong, hentikan semua pekerjaan lain sampai collector hidup lagi.

---

## Arsitektur singkat

```
ct_collector.py (cron 06:30, berdiri sendiri)  ──►  ct_raw
                                                      │
OpenClaw Gateway ──┬── Skill analyze-message (Mode A, dipicu pengguna)
                   └── Skill monitor-domains (Mode B, dipicu heartbeat 07:00)
                                │
                          lib/ (modul bersama)  ──►  SQLite
```

- `lib/llm.py` — **satu-satunya** tempat pemanggilan LLM, plus batas anggaran harian keras
- `lib/scoring.py` — semua bobot dan ambang batas di satu dict konstanta di puncak berkas
- `collector/` sengaja di luar `skills/` dan tidak mengimpor apa pun dari OpenClaw

## Stack

Python 3.11 · SQLite · OpenClaw · Telegram Bot · VPS 4 vCPU / 4 GB RAM / 20 GB SSD

### OpenClaw
- **Image:** `ghcr.io/openclaw/openclaw:2026.7.1-2`
- **Tag:** `2026.7.1-2`
- **Image Digest (SHA256):** `sha256:8789721d2e9b24b780a1504b56deb4c6bd5c7dbf96a1dd117e7c45c2ed72c8ac`
- **Gateway Port & Binding Security (KRITIS):**
  - **Gateway Port:** `18789`
  - `gateway.bind = "lan"` (wajib di container agar port publishing Docker bisa menjangkau container). Proteksi loopback berasal dari flag `-p 127.0.0.1:18789:18789` — **BUKAN dari konfigurasi aplikasi**.
  - **Konsekuensi:** Kalau nanti dijalankan tanpa Docker (misalnya systemd native di T11), gateway akan bind ke semua interface. Wajib ada firewall ketat atau ubah `gateway.bind = "loopback"` sebelum deployment native.

Model: **utamakan model default yang disediakan panitia.** API sendiri hanya kalau default tidak sanggup menghasilkan JSON terstruktur yang stabil.

**Keputusan model (T08 technical meeting, dikonfirmasi 2 September 2026):**
- Model default: `9router/oc/hy3-free` — provider `9router` (`https://9router.jcamp.io/v1`), gratis (biaya $0 di semua sisi: input/output/cache), context window 200.000 token, maxTokens per respons 8.192.
- Panitia **tidak menyebutkan angka kuota eksplisit** untuk model default ini di technical meeting — tidak didokumentasikan, kemungkinan best-effort di sisi provider.
- Panitia **mengizinkan pakai API sendiri** secara eksplisit (dikonfirmasi lisan di technical meeting, bukan cuma asumsi) — proyek ini memakai `api.justwoker.icu` (model `claude-opus-5`) untuk `lib/llm.py`, terpisah dari model default OpenClaw di atas.

---

## Cara kerja yang saya harapkan

- **Satu task per sesi**, sesuai `plan/10-build-runbook.md`. Jangan kerjakan task berikutnya sebelum DoD task ini terpenuhi.
- **Jangan tambah fitur yang tidak diminta.** Rencananya sudah ketat; scope creep adalah risiko nomor satu.
- **Modul murni sertakan pytest**, termasuk kasus negatif — false positive mahal di proyek ini.
- **Kalau belum yakin penyebab sebuah error, katakan** dan usulkan cara mendiagnosisnya. Jangan langsung menawarkan perbaikan yang menutupi gejala.
- **Aturan empat jam:** kalau satu masalah belum selesai dalam empat jam, kita ganti pendekatan atau potong fiturnya. Ingatkan saya kalau kita sudah berputar.

## Urutan pemotongan lingkup kalau tertinggal jadwal

1. Integrasi WhatsApp → cukup Telegram
2. Pengelompokan kampanye
3. Fitur draft laporan
4. Watchlist 200 → 80 institusi

**Tidak pernah dipotong:** collector harian, heartbeat brief, test set evaluasi, syarat administratif video dan artikel.

---

## Bahasa

Diskusi dan dokumentasi dalam **Bahasa Indonesia**. Nama variabel, fungsi, dan komentar kode dalam **bahasa Inggris**.
