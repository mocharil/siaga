# SIAGA — Video Demonstration Script & Storyboard (T29)

> **Spesifikasi Video AI HackFest 2026:**
> * **Durasi Target:** 8 Menit (Rentang yang diizinkan: 5–10 Menit)
> * **Aspek Rasio:** 16:9 Landscape (Full HD 1080p)
> * **Watermark:** Logo Resmi IDwebhost di sudut kanan atas dari frame pertama hingga akhir.
> * **Kategori:** Digital Safety & Public Good
> * **Framework:** OpenClaw AI

---

## Storyboard & Rundown Menit-demi-Menit

```
┌──────────┬───────────────────────┬──────────────────────────────────────────┐
│  Menit   │        Segmen         │              Fokus Visual                │
├──────────┼───────────────────────┼──────────────────────────────────────────┤
│0:00–0:45 │ Masalah Nyata         │ Pesan penipuan di smartphone (BCA spoof) │
│0:45–1:30 │ Kenapa Deteksi Sulit  │ Tiga sinyal tersembunyi (RDAP, Homoglyph)│
│1:30–2:15 │ Solusi SIAGA          │ Konsep Agent Otonom: Mode A & Mode B     │
│2:15–4:00 │ Live Demo: Mode A     │ Telegram Bot @siaga_ai_bot live triage   │
│4:00–5:45 │ Live Demo: Mode B     │ VPS Terminal, CloudBaik, Dashboard, Brief│
│5:45–6:15 │ Arsitektur Sistem     │ Pipeline 3-Tahap & Cascade Token Saving  │
│6:15–6:45 │ Keandalan & Hosting   │ Systemd, Logrotate, Backup, Hardening    │
│6:45–7:30 │ Hasil & Metrik Nyata  │ Slide Snapshot 01 September 2026         │
│7:30–8:00 │ Etika & Penutup       │ UU PDP, Human-in-the-Loop, Closing       │
└──────────┴───────────────────────┴──────────────────────────────────────────┘
```

---

## Detail Naskah & Panduan Adegan

### [0:00–0:45] SEGMENT 1 — Masalah: Jebakan 24 Jam Pertama
* **Visual:** Layar smartphone menampilkan aplikasi chat dengan pesan masuk:
  > *"Peringatan dari bank Anda: tarif transfer bulanan akan disesuaikan menjadi Rp 150.000. Batalkan segera melalui: `bca-tarifpenyesuaian[.]online`"*
* **Audio / Voiceover:**
  > "Di Indonesia, ribuan orang setiap hari menerima pesan seperti ini. Sekilas, alamat situsnya tampak meyakinkan. Tapi begitu korban memasukkan PIN dan OTP, saldo rekening mereka terkuras dalam hitungan menit. Modus phishing modern tidak lagi menggunakan domain aneh—pelaku kini meniru institusi terpercaya menggunakan domain tingkat tinggi murah. Dan sistem keamanan konvensional kerap terlambat menghentikannya."

---

### [0:45–1:30] SEGMENT 2 — Kenapa Verifikasi Itu Sulit?
* **Visual:** Tampilan browser membedah domain phishing dengan visual highlight 3 aspek teknis:
  1. *Subdomain & Directed Permutations:* `bca.promo-khusus.xyz`
  2. *Homoglyph / Punycode:* `xn--b-8sb.id` (huruf sirilik 'а')
  3. *Ephemeral Lifetime:* Umur domain baru 4 jam.
* **Audio / Voiceover:**
  > "Mengapa begitu sulit dideteksi? Pertama, pelaku menyamarkan nama bank sebagai subdomain resmi. Kedua, penggunaan karakter homoglyph sirilik yang identik secara visual dengan huruf latin. Ketiga, siklus hidup kilat—domain didaftarkan, melancarkan serangan selama 12 jam, lalu dimatikan sebelum terdaftar di antivirus global. Daftar hitam publik rata-rata butuh waktu 24 hingga 36 jam untuk mendeteksinya."

---

### [1:30–2:15] SEGMENT 3 — Perkenalan Solusi: SIAGA
* **Visual:** Logo SIAGA dengan diagram dua mode operasional:
  - **Mode A (Reaktif):** Pengguna memeriksa pesan mencurigakan lewat Telegram Bot.
  - **Mode B (Proaktif):** Pemantauan mandiri 24/7 terhadap aliran Certificate Transparency Log global.
* **Audio / Voiceover:**
  > "Inilah SIAGA—Sistem Deteksi dan Pemantauan Penipuan Digital berbasis OpenClaw AI. SIAGA bekerja dalam dua mode: Mode A sebagai asisten interaktif yang membantu masyarakat memeriksa pesan mencurigakan secara instan, dan Mode B sebagai intelijen ancaman proaktif yang memantau aliran pendaftaran domain baru di internet tanpa menunggu laporan korban."

---

### [2:15–4:00] SEGMENT 4 — Demo Live: Mode A (Pemeriksaan Interaktif)
* **Visual:** Screen recording live tanpa cut di aplikasi Telegram.
  1. Pengguna mem-forward pesan ber-URL phishing ke bot `@siaga_ai_bot`.
  2. Status pemrosesan berjalan (latensi asli ~3–5 detik).
  3. Bot membalas dengan struktur rapi:
     - **Level Risiko:** 🔴 INDIKASI PENIPUAN (Skor 87/100)
     - **Tiga Bukti Konkret:**
       1. Domain baru berumur 11 jam (RDAP terverifikasi).
       2. Meniru institusi resmi Bank Central Asia.
       3. Rantai redirect HEAD-only mengarah ke server phishing aktif.
     - **Saran Tindakan Bahasa Awam.**
* **Audio / Voiceover:**
  > "Mari kita uji Mode A secara langsung. Saya meneruskan pesan mencurigakan tadi ke bot SIAGA di Telegram. Perhatikan—dalam waktu kurang dari empat detik, SIAGA mengekstrak entitas URL, menelusuri rantai redirect secara aman menggunakan HTTP HEAD-only, memeriksa umur registrasi domain, menganalisis bahasa desakan, dan memberikan penjelasan bahasa awam dengan tiga alasan konkret tanpa menyimpan data pribadi pengguna."

---

### [4:00–5:45] SEGMENT 5 — Demo Live: Mode B (Pemantauan Proaktif & Dashboard)
* **Visual:** Tampilan layar ganda (*Split Screen*):
  - **Kiri:** Dashboard Cloud VPS CloudBaik dan antarmuka web monitoring SIAGA (`http://127.0.0.1:8000`).
  - **Kanan:** Terminal SSH VPS (`siaga@103.30.146.152:4422`) menampilkan log OpenClaw Gateway dan status cron.
* **Aksi Terminal:**
  ```bash
  # Tunjukkan service OpenClaw & cron harian
  sudo openclaw gateway status
  sudo openclaw cron list
  
  # Buka Dashboard read-only via SSH tunnel
  curl -s http://127.0.0.1:8000/api/stats/today | jq .
  ```
* **Audio / Voiceover (Wajib sebut produk sponsor):**
  > "Sekarang kita masuk ke inti keunggulan SIAGA: Mode B Proaktif yang berjalan di server **Cloud VPS** dengan infrastruktur **AI Hosting** dari **IDwebhost**. Setiap pukul 06:30 WIB, collector otomatis menarik ribuan sertifikat baru dari Certificate Transparency log. Kemudian tepat pukul 07:00 WIB, OpenClaw Gateway secara otonom memicu siklus analisis harian. Hasilnya langsung dirangkum ke dalam Daily Brief Telegram dan dirender secara real-time pada Dashboard read-only yang kita akses melalui SSH tunnel aman ini."

---

### [5:45–6:15] SEGMENT 6 — Arsitektur Cascading Funnel & Efisiensi Token
* **Visual:** Animasi diagram Funnel 3-Tahap:
  `10.314 Domain ➔ 362 Lolos Tahap 1 (CPU Similarity) ➔ 294 Lolos Tahap 2 (RDAP & DNS) ➔ 2 Flagged Temuan Prioritas (LLM)`
* **Audio / Voiceover:**
  > "Bagaimana SIAGA memproses puluhan ribu domain tanpa boros biaya token? Kami merancang arsitektur Cascading Funnel. Tahap pertama menggunakan komputasi string lokal Damerau-Levenshtein dan homoglyph filter berkecepatan 1,5 milidetik per domain, memangkas 96% domain wajar tanpa satu pun token LLM. Panggilan model AI hanya dilakukan pada segelintir kandidat berisiko tinggi di tahap akhir, menghemat lebih dari 98% anggaran komputasi."

---

### [6:15–6:45] SEGMENT 7 — Keandalan Operasional & Hosting (Reliability)
* **Visual:** Terminal VPS mendemonstrasikan fitur reliability & hardening:
  ```bash
  systemctl status siaga-dashboard.service
  sudo logrotate -d /etc/logrotate.d/siaga
  ls -la backups/daily/
  sudo ufw status verbose
  ```
* **Audio / Voiceover (Wajib sebut poin keandalan & sponsor):**
  > "Agar dapat beroperasi mandiri selama 30 hari penuh di **AI Hosting IDwebhost**, SIAGA dilengkapi fitur operasional setara enterprise: service systemd dengan auto-restart, rotasi log harian terkompresi agar penyimpanan tidak penuh, pencadangan otomatis database SQLite dengan integritas data terverifikasi, serta isolasi firewall UFW dan SSH Key-Only authentication yang menjaga server dari potensi serangan luar."

---

### [7:45–7:30] SEGMENT 8 — Hasil & Metrik Nyata
* **Visual:** Slide grafik metrik dengan stamp waktu: `Snapshot Data per 01 September 2026 — 5 Hari Operasional Nyata`.
  - **Precision:** 100.00% (0 False Positive)
  - **Recall:** 91.80%
  - **F1-Score:** 0.9573
  - **Total Domain Dipindai:** 47.664 domain
  - **Temuan Terpetakan:** 546 indikasi phishing
  - **RAM Peak:** 31.9 MB (Dashboard API)
* **Audio / Voiceover:**
  > "Seluruh performa SIAGA diuji di atas dataset ground-truth 120 sampel terkalibrasi. Hasilnya: Precision 100% tanpa ada kesalahan tuduh pada institusi sah, Recall 91,8%, dan F1-Score 0,9573. Dalam lima hari operasional nyata, SIAGA telah memindai 47.664 domain dan memetakan 546 temuan phishing aktif."

---

### [7:30–8:00] SEGMENT 9 — Posisi Etis & Penutup
* **Visual:** Penyamaran nama domain (`b***-verif.xyz`) di UI dasbor dan alur *Human-in-the-Loop* pembuatan draft laporan insiden (`/laporkan 1`).
* **Audio / Voiceover:**
  > "SIAGA sepenuhnya mematuhi UU Pelindungan Data Pribadi. Kami menerapkan penyamaran nama domain secara default dan prinsip Human-in-the-Loop—AI menganalisis dan menyusun draf bukti teknis, namun manusia tetap memegang kendali penindakan ke kanal resmi seperti AduanKonten Kominfo dan CSIRT BSSN. Bersama SIAGA, kita wujudkan ruang digital Indonesia yang lebih aman dan terpercaya. Terima kasih."

---

## Checklist Eksekusi Rekaman
- [ ] Font terminal ukuran ≥ 16pt dengan skema warna kontras tinggi (Dark Theme).
- [ ] Watermark logo IDwebhost terlihat di pojok kanan atas dari 0:00 hingga 8:00.
- [ ] Audio narasi jernih tanpa noise atau clipping.
- [ ] SSH tunnel dashboard aktif di `http://localhost:8000` saat rekaman berlangsung.
