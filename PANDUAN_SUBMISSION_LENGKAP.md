# PANDUAN LENGKAP SUBMISSION, ARTIKEL & VIDEO AI — AI HACKFEST 2026

Dokumen ini memuat seluruh materi, strategi publikasi, naskah video, serta kumpulan prompt AI video generator untuk keperluan submission kompetisi **AI HackFest 2026**.

---

## DAFTAR ISI
1. [Rekomendasi Tempat Upload & Strategi Penjurian](#1-rekomendasi-tempat-upload--strategi-penjurian)
2. [Paket Prompt Video AI Generator (Kling / Runway / Luma / Midjourney)](#2-paket-prompt-video-ai-generator)
3. [Naskah Voiceover Dubbing (ElevenLabs / AI Voice)](#3-naskah-voiceover-dubbing-elevenlabs)
4. [Rencana Alur Video Lengkap 7 Menit 30 Detik](#4-rencana-alur-video-lengkap-7-menit-30-detik)
5. [Ketentuan Wajib Penjurian & Checklist Sebelum Submit](#5-ketentuan-wajib-penjurian--checklist-sebelum-submit)
6. [Tautan Berkas Pendukung di Repositori](#6-tautan-berkas-pendukung-di-repositori)

---

## 1. REKOMENDASI TEMPAT UPLOAD & STRATEGI PENJURIAN

Sesuai ketentuan buku panduan (*Playbook*), dewan juri menilai karya Anda **hanya melalui 2 tautan: Video Demo dan Artikel**.

### A. Rekomendasi Publikasi Artikel
* **Pilihan #1 (Sangat Direkomendasikan): [Dev.to](https://dev.to)**
  * **Alasan:** Memiliki otoritas domain (DA 91) sangat tinggi. Google mengindeks artikel Dev.to dalam **hitungan jam**.
  * **Format:** Mendukung penuh format Markdown, tabel benchmark, dan blok kode. Bebas paywall dan sangat disukai komunitas developer serta dewan juri teknis.
* **Pilihan #2: [LinkedIn Articles](https://www.linkedin.com/post/new/)**
  * **Alasan:** Sangat profesional, langsung mengikat karya dengan profil Anda (**Moch Aril Indra Permana**), terindeks publik oleh Google, dan mempermudah mendulang likes/komentar untuk kategori **Favorite Project**.
* **Pilihan Alternatif: [Medium](https://medium.com)**
  * **Perhatian Wajib:** Saat mempublikasikan di Medium, **uncheck/hilangkan centang** *"Paywall this story / Meter this story"* agar artikel dapat dibaca publik tanpa kuota batas baca.
* **⚠️ Hindari Blog Pribadi Baru:** Domain baru membutuhkan 2–4 minggu untuk diindeks oleh Google. Berisiko gugur administrasi saat juri mengecek tautan.

> **Syarat Wajib Artikel (Telah Terpenuhi di File Artikel):**
> 1. Minimal 800 kata (artikel SIAGA versi Bahasa Inggris memiliki **4.390 kata** lengkap dengan arahan screenshot/gambar).
> 2. Backlink 1: Anchor text **`AI Hosting`** mengarah ke `https://idwebhost.com/ai-hosting`.
> 3. Backlink 2: Anchor text **`Cloud VPS`** mengarah ke `https://cloudbaik.com`.

---

### B. Rekomendasi Publikasi Video Demo
* **Platform Wajib: [YouTube](https://youtube.com) (Status: Public atau Unlisted, Resolusi: 1080p 60fps)**
  * **Alasan:** Format video berdurasi **7–8 menit** dalam rasio **16:9 Landscape**. Menampilkan terminal Linux dan live dashboard yang membutuhkan layar lebar agar teks terbaca tajam.
  * YouTube memiliki fitur **Video Chapters / Timestamps** pada deskripsi, sehingga memudahkan dewan juri melompat langsung ke segmen penilaian teknis (Terminal VPS atau Model Evaluation).
* **Strategi Tambahan (Untuk Kategori Favorite Project):**
  * Buat video pendek (60 detik) cuplikan visual radar dan alert Telegram otomatis, lalu unggah ke **TikTok / Instagram Reels / LinkedIn Video** dengan tautan menuju video YouTube lengkap.

---

## 2. PAKET PROMPT VIDEO AI GENERATOR

Gunakan prompt di bawah ini pada AI video generator seperti **Runway Gen-3 / Kling AI / Luma Dream Machine / Hailuo (Minimax)** atau buat gambar dasar di **Midjourney / Flux** terlebih dahulu.

### Scene 1: Pesan Ancaman Palsu & Kepanikan Korban (0:00 – 0:18)
* **Visual:** Close-up wajah cemas seorang wanita Indonesia di ruang tamu temaram melihat layar HP yang berkedip merah.
* **Prompt Video (Runway Gen-3 / Kling AI / Luma):**
  ```text
  Cinematic close-up, Indonesian woman sitting in a dimly lit modern living room, looking at her smartphone in distress, screen glowing with an urgent red bank notification, cinematic lighting, photorealistic 8k, slow camera push-in, shallow depth of field, 24fps.
  ```
* **Prompt Gambar (Midjourney v6 / Flux):**
  ```text
  A close-up of a middle-aged Indonesian woman looking shocked at her glowing smartphone screen in a dim cozy room, soft cinematic bokeh, dramatic rim lighting, photorealistic 8k --ar 16:9 --style raw
  ```

### Scene 2: Pabrik Phishing di Balik Layar (0:18 – 0:35)
* **Visual:** Siluet pelaku kejahatan siber di ruangan gelap di depan jajaran layar monitor kode terminal.
* **Prompt Video (Runway Gen-3 / Kling AI / Luma):**
  ```text
  Moody cyberpunk aesthetic, silhouette of an anonymous cyber operator typing fast in a dark room filled with glowing blue and green monitors, rapid code stream, glitching fake bank logos on screens, slow panning camera, volumetric smoke, high cinematic realism.
  ```
* **Prompt Gambar (Midjourney v6 / Flux):**
  ```text
  Silhouette of a cyber hacker in front of glowing multi-screen terminal setup, displaying fake domain registration code and cybersecurity maps, dark moody room, dramatic neon blue backlighting --ar 16:9 --style raw
  ```

### Scene 3: Jeda Waktu 46 Jam & Uang Raib (0:35 – 0:52)
* **Visual:** Transisi waktu cepat (*time-lapse*), jarum jam berputar liar, angka saldo digital turun drastis ke nol.
* **Prompt Video (Runway Gen-3 / Kling AI / Luma):**
  ```text
  Cinematic fast time-lapse, analog wall clock hands spinning rapidly, motion blur, overlapping holographic countdown timers in red light, dramatic tension, camera tilting up, 4k cinematic grading.
  ```
* **Prompt Gambar (Midjourney v6 / Flux):**
  ```text
  A dynamic conceptual shot of a spinning glowing clock face dissolving into digital red binary numbers, dark background, cinematic motion blur, hyper-detailed --ar 16:9
  ```

### Scene 4: Kelahiran SIAGA — Perisai Siber Proaktif (0:52 – 1:10)
* **Visual:** Pemandangan malam kota Jakarta dari udara, kubah perisai digital heksagonal biru menyala memfilter paket data merah.
* **Prompt Video (Runway Gen-3 / Kling AI / Luma):**
  ```text
  Aerial night view of Jakarta skyline, futuristic glowing blue holographic energy shield expanding across the city, digital particle streams intercepting red malicious data packets, epic sci-fi realism, cinematic drone flying shot.
  ```
* **Prompt Gambar (Midjourney v6 / Flux):**
  ```text
  Jakarta cityscape at night with a radiant blue semi-transparent digital cybersecurity grid dome overhead, glowing fiber optic lines connecting servers, cinematic photorealism --ar 16:9
  ```

### Scene 5: Transisi Masuk ke Dasbor Nyata (1:10 – 1:22)
* **Visual:** Kamera bergerak menembus kabel serat optik ke belakang bahu analis keamanan yang memandangi layar dasbor.
* **Prompt Video (Runway Gen-3 / Kling AI / Luma):**
  ```text
  First-person transition flying through glowing blue fiber optic cables into a high-tech cybersecurity operations center, camera lands over the shoulder of a cybersecurity analyst looking at a clean threat dashboard monitor.
  ```

---

## 3. NASKAH VOICEOVER DUBBING (ELEVENLABS)

* **Rekomendasi Suara:** Pria Bahasa Indonesia (Model: ElevenLabs `Multilingual v2`, Voice: *Adam*, *Daniel*, atau *Antoni*).
* **Karakter Narasi:** Berwibawa, empati, tegas, dan solutif.

```text
[0:00 - 0:18] (Nada tegang, lambat)
"Satu pesan singkat. Satu kepanikan. Dalam hitungan detik, tabungan kerja keras bertahun-tahun... lenyap tanpa jejak."

[0:18 - 0:35] (Tempo meningkat, nada analitis)
"Setiap hari, ribuan domain penipuan lahir di ruang gelap internet. Dibuat dalam lima menit, mengeksploitasi kepanikan korban, lalu lenyap sebelum radar keamanan publik sempat menyadarinya."

[0:35 - 0:52] (Nada tegas, membongkar fakta)
"Daftar hitam konvensional terlambat empat puluh enam jam. Dan korban tidak punya waktu untuk menunggu."

[0:52 - 1:10] (Musik berubah optimis & bersemangat)
"Bagaimana jika kita menghentikan ancaman ini sebelum situsnya diluncurkan? Sejak detik pertama sertifikatnya diterbitkan di gerbang internet dunia?"

[1:10 - 1:22] (Nada bangga & mantap)
"Inilah SIAGA. Autonomous Threat Intelligence Agent. Menjaga ruang digital Indonesia, tanpa henti."
```

---

## 4. RENCANA ALUR VIDEO LENGKAP (7 MENIT 30 DETIK)

| Menit | Bagian Video | Tindakan Layar & Konten | Syarat Lomba / Poin Nilai |
| :---: | :--- | :--- | :---: |
| **0:00 - 1:22** | **Cerita AI Sinematik** | 5 Scene Video AI di atas + Voiceover ElevenLabs. | Hook masalah nyata (Bobot 20%). |
| **1:22 - 3:15** | **Live Demo Mode A (Triage)** | Transisi ke dasbor asli. Tempel pesan penipuan $\rightarrow$ analisa 1,5 detik $\rightarrow$ ekstraksi entitas, radar sinyal, isolated sandbox, draf laporan RFC 2350, tombol 1-klik lapor Kominfo/PANDI/OJK. | **Human-in-the-Loop (Bukan main hakim sendiri)** (Bobot 30%). |
| **3:15 - 4:45** | **Live Demo Mode B (Radar)** | Menu Radar: Aliran CT Log real-time, filter 292 phishing, 81 judol, 45 porn, klastering IP/ASN, alert otomatis Telegram. | Agen otonom 24/7 (Bobot 30%). |
| **4:45 - 5:50** | **Lingkungan Cloud VPS & AI Hosting** | Split screen: Dashboard CloudBaik & Terminal SSH Linux. Perintah: `systemctl status siaga`, `free -m` (< 120MB), `pytest` (298 passed). | **Wajib Playbook:** Tampilkan terminal & dashboard. Sebut verbal **"AI Hosting"** & **"IDwebhost"**. |
| **5:50 - 6:50** | **Inovasi & Model Evaluation** | Menu Evaluation: 6 kartu metrik (Precision 100%, Recall 91.8%, F1 0.9573, AUC 0.994, Latensi 128ms, Lead-Time 46.4h) & corong hemat 98% token. | Eksekusi teknis tingkat tinggi (Bobot 20%). |
| **6:50 - 7:30** | **Penutup & Dampak** | Repositori GitHub open-source, ucapan terima kasih kepada IDwebhost & CloudBaik, penutup misi *"Build Agent, Deliver Impact"*. | Watermark IDwebhost sepanjang video. |

---

## 5. KETENTUAN WAJIB PENJURIAN & CHECKLIST SEBELUM SUBMIT

Pastikan seluruh poin berikut tercentang sebelum Anda mengirimkan link submission:

- [ ] **Resolusi Video:** Minimal 1080p, format landscape 16:9.
- [ ] **Durasi Video:** Berada di antara 5 hingga 10 menit (Target kita: ~7:30).
- [ ] **Watermark IDwebhost:** Logo IDwebhost terpasang di pojok layar sepanjang video.
- [ ] **Penyebutan Wajib (Verbal & Lower-Third):** Nama produk **"AI Hosting"** dan **"IDwebhost"** disebutkan secara verbal di segmen server (menit 4:45) dan terdapat tulisan di banner layar.
- [ ] **Lingkungan VPS:** Menampilkan terminal SSH Linux dan dashboard Cloud VPS.
- [ ] **Status Video:** Disetel ke **Public** atau **Unlisted** di YouTube (bukan Private).
- [ ] **Panjang Artikel:** Minimal 800 kata (artikel SIAGA memiliki **2.765 kata**).
- [ ] **Dua Backlink Wajib di Artikel:**
  - `[AI Hosting](https://idwebhost.com/ai-hosting)`
  - `[Cloud VPS](https://cloudbaik.com)`
- [ ] **Artikel Terindeks:** Dipublikasikan di platform publik (Dev.to / LinkedIn Articles) dan sudah bisa diakses tanpa login.
- [ ] **Kepatuhan Hukum:** Bebas dari tindakan main hakim sendiri (*Human-in-the-Loop via official escalation channels*).

---

## 6. TAUTAN BERKAS PENDUKUNG DI REPOSITORI

* 📄 **Naskah Artikel Lengkap (Siap Copy ke Dev.to/LinkedIn):**  
  [`siaga/ARTICLE_AI_HACKFEST_2026.md`](file:///c:/Users/Aril%20Indra%20Permana/AI_HACKFEST/siaga/ARTICLE_AI_HACKFEST_2026.md)
* 🎬 **Naskah Video Detik demi Detik (Kata-per-Kata):**  
  [`siaga/VIDEO_SCRIPT_AI_HACKFEST_2026.md`](file:///c:/Users/Aril%20Indra%20Permana/AI_HACKFEST/siaga/VIDEO_SCRIPT_AI_HACKFEST_2026.md)
* 🤖 **Kumpulan Prompt Video AI Generator:**  
  [`siaga/AI_VIDEO_PROMPTS.md`](file:///c:/Users/Aril%20Indra%20Permana/AI_HACKFEST/siaga/AI_VIDEO_PROMPTS.md)
* 🌐 **Live Web Dasbor Demo:**  
  [https://siaga-lake.vercel.app](https://siaga-lake.vercel.app)
* 💻 **Repositori Kode Sumber:**  
  [https://github.com/mocharil/siaga](https://github.com/mocharil/siaga)

