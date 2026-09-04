# SIAGA — Submission Checklist v2 (Revisi Jujur)

> **Status Kesiapan Submit:** ❌ **BELUM SIAP** — v1 (`docs/submission_checklist.md`) menandai semua item selesai
> padahal video belum direkam, artikel belum dipublikasikan, dan beberapa angka sudah basi. Dokumen ini menggantikan
> v1 sebagai sumber kebenaran sementara sampai v1 diperbaiki atau dihapus.
>
> **Batas Waktu Pengumpulan:** 29/30 September 2026 · **Akses VPS kompetisi berakhir:** ~5 September 2026
>
> Kolom **Eksekutor** menjawab pertanyaan "siapa yang bisa mengerjakan ini": **Claude** (bisa saya kerjakan lewat
> tool yang tersedia di sesi ini), **User** (butuh tangan/akun/perangkat Anda — saya tidak punya akses), atau
> **Bersama** (saya bisa siapkan/verifikasi sebagian, tapi keputusan/eksekusi akhir tetap di Anda).

---

## 🚨 Temuan kritis yang belum ada di v1 — perlu keputusan Anda

- **Repo GitHub `mocharil/siaga` sudah PUBLIC dan live** (`gh repo view` → `"visibility":"PUBLIC"`), dan commit
  `5895b69` (redesign UI dari sesi lain) sudah ter-push. Commit itu membawa kembali katalog ancaman palsu yang
  menyebut UNP/UGM/Kemenag/BRI/Mandiri/DJP/BPJS/Pos Indonesia sebagai "diretas".
- **Situs live `siaga-lake.vercel.app` juga menyajikan konten yang sama** — saya cek `public/static/app.js`
  (file yang benar-benar disajikan Vercel) dan katalog palsu itu ada di sana juga (6 referensi). Ini bukan cuma
  ada di kode sumber, tapi **sedang tersaji ke pengunjung nyata saat ini**.
- Saya belum menyentuh `public/` atau melakukan commit/push apa pun sesuai instruksi sebelumnya untuk tidak
  menyentuh deployment Vercel tanpa izin eksplisit — jadi ini murni laporan, menunggu keputusan Anda.
- Sedang ada sesi lain yang mengerjakan UI enhancement di `dashboard/static/*` — saya tahan dulu perbaikan
  `app.js` supaya tidak bentrok, sesuai permintaan Anda barusan.

---

## 1. Video Deliverable (15% Bobot Penjurian)

| Item | Status Nyata | Eksekutor |
|---|---|---|
| Durasi & format (8 menit, MP4 1080p 16:9) | ❌ Belum ada file video sama sekali | **User** — saya tidak bisa merekam layar/mengedit video |
| Watermark sponsor IDwebhost | ❌ Belum ada | **User** — proses editing video |
| Segmen wajib VPS (dashboard + terminal SSH berdampingan) | ❌ Belum direkam — lihat `docs/vps_recording_checklist.md` | **User** — saya tidak punya akses SSH ke VPS di sesi ini |
| Segmen keandalan & hosting (systemd, backup, logrotate, UFW) | ❌ Belum direkam | **User** — sama, butuh akses VPS langsung |
| Penyebutan verbal "AI Hosting" & "IDwebhost" | ❌ Belum ada | **User** — narasi suara |
| Kualitas audio & visual | ❌ Belum bisa dinilai, belum ada rekaman | **User** |
| Slide metrik nyata dari snapshot | ⚠️ Saya bisa siapkan angka & teks slide yang akurat | **Bersama** — saya siapkan angka terverifikasi, Anda yang taruh ke slide/video |
| Upload ke YouTube (Publik/Unlisted) | ❌ Belum ada video untuk di-upload | **User** — butuh akun YouTube Anda |

## 2. Artikel Deliverable (target 1.200–1.500 kata)

| Item | Status Nyata | Eksekutor |
|---|---|---|
| Draft artikel (`docs/article_draft.md`) | ⚠️ Belum saya baca/verifikasi isinya terhadap angka real | **Bersama** — saya bisa tulis/revisi draft, Anda putuskan kata final |
| Dua backlink wajib (anchor text persis) | ⚠️ Bisa saya tulis ke draft | **Claude** untuk penulisan, **User** untuk publish |
| Link repo GitHub & live webapp | ✅ Keduanya terverifikasi hidup: repo public, Vercel HTTP 200 | **Claude** (sudah diverifikasi) |
| Bagian kejujuran teknis ("kegagalan nyata & pelajaran") | ⚠️ Bahan mentahnya ada di `docs/devlog/*` (lengkap s.d. 3 Sept, entri 4 Sept belum dibuat) | **Claude** bisa susun dari devlog, **User** approve isi akhir |
| Kesesuaian angka artikel vs video vs snapshot | ❌ Belum bisa dicek — video belum ada | **Bersama** — setelah video jadi, saya cross-check angkanya |
| Publikasi ke platform publik (Dev.to/LinkedIn/Medium) + submit Google Search Console | ❌ Belum dipublikasikan | **User** — butuh akun Anda |

## 3. Kebersihan & Kepatuhan Repositori

| Item | Status Nyata (terverifikasi hari ini) | Eksekutor |
|---|---|---|
| Tidak ada `.env`/token/API key di history git | ✅ Diverifikasi: `git log --all` untuk `.env`/token/password — nihil | **Claude** (sudah dicek) |
| Tidak ada `VPS.txt` atau file kredensial ter-commit | ✅ Diverifikasi: tidak pernah ada di history maupun working tree | **Claude** (sudah dicek) |
| `.gitignore` mengecualikan `.env` & data sensitif | ✅ Terverifikasi (`.env`, `data/raw/`, dll ada di `.gitignore`) | **Claude** (sudah dicek) |
| README & CLAUDE.md lengkap | ⚠️ README ada (161 baris, terakhir diubah 1 Sept) — belum saya audit apakah sudah mencakup fitur judol/porn/LLM verification terbaru | **Claude** bisa audit & update |
| Devlog lengkap | ⚠️ Ada 8 entri s.d. 2 September; **entri 3–4 September (audit hardcoding, fix pipeline, dst) belum ditulis** | **Claude** bisa tulis dari riwayat sesi ini |
| Seluruh unit test lulus | ✅ **298 test lulus** hari ini (bukan 225 seperti klaim v1 — v1 basi) | **Claude** (sudah dijalankan) |
| Test lulus juga di VPS produksi | ❓ Tidak bisa saya verifikasi — tidak ada akses SSH VPS di sesi ini | **User** — jalankan `pytest` di VPS sebelum akses hilang, atau paste hasilnya ke saya |

## 4. Infrastruktur Server Produksi (VPS)

Saya **tidak punya akses SSH ke VPS ini** (tidak ada kredensial/tunnel tersimpan di sesi ini) — semua baris di
bawah butuh Anda menjalankannya sendiri di VPS (ikuti `docs/vps_recording_checklist.md`), atau menempel hasilnya
ke saya supaya saya bisa bantu baca/verifikasi.

| Item | Status Nyata | Eksekutor |
|---|---|---|
| SSH hardening (key-only, root disabled, port 4422) | ❓ Belum diverifikasi ulang sesi ini | **User** menjalankan, **Claude** bisa bantu baca output |
| Firewall UFW (deny-all kecuali 4422) | ❓ Belum diverifikasi ulang | **User** + **Claude** baca output |
| Collector harian via crontab | ❓ Belum diverifikasi ulang dari VPS (lokal sudah terkonfirmasi jalan) | **User** + **Claude** baca output |
| Backup harian DB, retensi 7 hari | ❓ Belum diverifikasi ulang | **User** + **Claude** baca output |
| Healthcheck 6-jam via Telegram | ❓ Belum diverifikasi ulang | **User** + **Claude** baca output |
| Logrotate `/etc/logrotate.d/siaga` | ❓ Belum diverifikasi ulang | **User** + **Claude** baca output |
| Dashboard read-only service (`127.0.0.1:8000`) | ❓ Belum diverifikasi ulang | **User** + **Claude** baca output |
| OpenClaw gateway service + cron `siaga-daily-cycle` | ❓ Belum diverifikasi ulang | **User** + **Claude** baca output |

## 5. Ringkasan Data Snapshot (untuk Formulir Submit)

| Field | Klaim v1 | Nilai Real Hari Ini (dicek langsung dari `data/siaga.db` lokal) |
|---|---|---|
| Precision / Recall / F1 | 100.00% / 91.80% / 0.9573 | ✅ **Cocok** — sesuai `data/eval_results.json` asli |
| `ct_raw` (domain mentah) | 47.664 | **74.447** — klaim v1 basi (data terus bertambah tiap hari) |
| `domain_findings` (temuan phishing) | 546 | **659** — klaim v1 basi |
| `campaigns` (klaster kampanye) | 55 | **55** — cocok, kebetulan belum berubah |
| Infrastruktur (4 vCPU/4GB/20GB) | sesuai spec kompetisi | tidak diverifikasi ulang dari VPS sesi ini, tapi konsisten dengan CLAUDE.md |

**Catatan penting**: angka-angka ini bergerak tiap hari karena collector jalan otomatis. Snapshot final untuk
video/artikel/formulir sebaiknya **dibekukan di satu tanggal tetap** (idealnya tanggal terakhir VPS hidup, atau
tanggal terakhir sebelum submit) dan disebutkan tanggalnya secara eksplisit — jangan biarkan angka di tiga tempat
(video, artikel, formulir) diambil di hari yang berbeda-beda.

---

## Ringkasan: yang HANYA bisa Anda lakukan

1. Apa pun yang butuh SSH fisik ke VPS (saya tidak punya kredensial/tunnel di sesi ini)
2. Merekam layar/webcam, mengedit video, menambahkan watermark & narasi
3. Upload ke YouTube, publish artikel ke platform pihak ketiga, submit ke Google Search Console
4. Keputusan: tanggal snapshot mana yang dibekukan sebagai angka final submission
5. Keputusan: bagaimana menangani konten yang sudah live publik (repo GitHub + Vercel) yang menyebut nama
   institusi nyata sebagai "diretas" — saya butuh izin eksplisit sebelum menyentuh `public/` atau melakukan commit/push

## Yang bisa saya kerjakan sekarang (menunggu instruksi Anda)

- Audit & perbarui README.md
- Tulis entri devlog yang hilang (3–4 September)
- Revisi/tulis draft artikel dari bahan devlog + data real
- Perbaiki `dashboard/static/app.js` (setelah sesi UI enhancement selesai, supaya tidak bentrok)
- Perbaiki `docs/submission_checklist.md` (v1) begitu Anda putuskan langkahnya
