# Mode Demo — Panduan Penggunaan

> Ini hanya ada di branch lokal `demo-video-showcase`. **Jangan pernah merge
> branch ini ke `master`** — repo yang disubmit ke juri harus tetap hanya
> berisi data & evidence real yang sudah diverifikasi.

## Apa ini

Dataset sintetis (`data/siaga_demo.db`) dan mode tampilan khusus untuk
kebutuhan rekaman video demo — supaya dashboard terlihat sudah punya volume
data, riwayat, dan skenario nyata untuk storytelling, tanpa pernah
mencampurnya dengan data produksi asli atau mengklaimnya sebagai hasil
evaluasi nyata (lihat CLAUDE.md aturan #2).

## Cara menjalankan

```bash
# 1. (Re)generate dataset demo — aman dijalankan berkali-kali, selalu
#    menghasilkan data yang sama (seeded) dan tidak pernah menyentuh
#    data/siaga.db yang asli.
PYTHONPATH=. python scripts/generate_demo_data.py

# 2. Jalankan dashboard menunjuk ke dataset demo
PYTHONPATH=. SIAGA_DEMO_MODE=1 SIAGA_DB_PATH=data/siaga_demo.db \
  python -m uvicorn dashboard.api:app --host 127.0.0.1 --port 8000
```

Buka `http://127.0.0.1:8000` — akan muncul banner kuning bergaris
"MODE DEMO — Data Simulasi" di paling atas, tampil di semua halaman selama
`SIAGA_DEMO_MODE=1` aktif.

## Kenapa aman dipakai untuk video

- **Label ada di dua lapis**: banner halaman (bisa hilang kalau ter-crop di
  video), DAN label `(Skenario Simulasi)` tertanam langsung di field data
  itu sendiri (`matched_brand`, `llm_reasoning`) untuk dua skenario utama —
  jadi tetap jelas simulasi walau banner tidak kelihatan di suatu klip.
- **Institusi/brand di skenario utama fiktif**: "Bank Nusantara Sejahtera"
  dan "Universitas Cendekia Bangsa" tidak merujuk entitas nyata mana pun.
- **Data volume latar belakang** (di luar 2 skenario utama) memakai brand
  yang SAMA seperti yang sudah benar-benar ditemukan sistem asli (Shopee,
  Ruangguru, GoPay, dst sebagai korban peniruan merek) — pola normal
  threat-intel, bukan tuduhan baru.
- **Halaman Evaluation tetap memakai `data/eval_results.json` asli** —
  angka precision/recall/F1 tidak pernah diganti data demo.

## Skenario yang dibangun

1. **Kampanye "Bank Nusantara Sejahtera"** — 28 domain berbagi nameserver
   yang sama, meledak dalam 4 hari, "dilaporkan", lalu terlihat sudah tidak
   aktif + masuk blacklist publik (endpoint `/api/insight/case-study`,
   tampil sebagai kartu "Insight Prioritas" di halaman Overview).
2. **Institusi fiktif "Universitas Cendekia Bangsa"** — satu temuan judol
   dengan `is_hijacked_institution=1`, contoh kasus subdomain resmi
   disusupi.

## File yang terlibat

- `scripts/generate_demo_data.py` — generator (idempotent, seeded)
- `data/siaga_demo.db` — hasil generate, sudah di `.gitignore` (`*.db`)
- `dashboard/api.py` — flag `demo_mode` di `/api/health`, endpoint baru
  `/api/insight/case-study`
- `dashboard/static/index.html` / `app.js` / `style.css` — banner + kartu
  Insight Prioritas
