# AI VIDEO GENERATION PROMPTS & STORYBOARD (SIAGA)

Panduan prompt AI video generator (Kling AI, Runway Gen-3, Luma Dream Machine, Hailuo/Minimax, Midjourney/Flux) untuk segmen sinematik pembuka (0:00–1:30) sebelum demonstrasi langsung aplikasi dan server.

---

## 1. STORY ARC SINOPSIS

* **Scene 1 (The Panic Hook):** Warga Indonesia (ibu/pekerja) menerima pesan penipuan darurat di ponsel, saldo perbankan terancam.
* **Scene 2 (The Dark Engine):** Ruang gelap pelaku siber mendaftarkan ratusan domain murah instan di depan monitor kode.
* **Scene 3 (The Lead-Time Gap):** Jam dinding berputar cepat melambangkan jeda 46 jam laporan manual, korban terlambat ditolong.
* **Scene 4 (The Awakening Sentinel):** Aliran kabel optik dan perisai data bercahaya biru melindungi kota digital Jakarta (Lahirnya SIAGA).
* **Scene 5 (Transition to Reality):** Zoom-in ke monitor analis keamanan yang membuka dashboard SIAGA di Cloud VPS.

---

## 2. PROMPT GENERATOR VIDEO (RUNWAY GEN-3 / KLING / LUMA / MINIMAX)

### Scene 1: Notifikasi Jebakan & Kepanikan Korban
* **Visual:** Close-up wajah cemas seorang wanita Indonesia di ruang tamu temaram, memegang smartphone yang menyala dengan notifikasi merah.
* **Text-to-Video Prompt (Kling / Runway Gen-3):**
  > *Cinematic close-up, Indonesian woman sitting in a dimly lit modern living room, looking at her smartphone in distress, screen glowing with an urgent red bank notification, cinematic lighting, photorealistic 8k, slow camera push-in, shallow depth of field, 24fps.*
* **Image Prompt (Midjourney v6 / Flux):**
  > *A close-up of a middle-aged Indonesian woman looking shocked at her glowing smartphone screen in a dim cozy room, soft cinematic bokeh, dramatic rim lighting, photorealistic 8k --ar 16:9 --style raw*

### Scene 2: Pabrik Phishing Bawah Tanah (The Ephemeral Trap)
* **Visual:** Sosok penyerang bertudung siluet di depan multi-monitor berisi terminal hitam-hijau, mendaftarkan domain tiruan kilat.
* **Text-to-Video Prompt (Kling / Runway Gen-3):**
  > *Moody cyberpunk aesthetic, silhouette of an anonymous cyber operator typing fast in a dark room filled with glowing blue and green monitors, rapid code stream, glitching fake bank logos on screens, slow panning camera, volumetric smoke, high cinematic realism.*
* **Image Prompt (Midjourney v6 / Flux):**
  > *Silhouette of a cyber hacker in front of glowing multi-screen terminal setup, displaying fake domain registration code and cybersecurity maps, dark moody room, dramatic neon blue backlighting --ar 16:9 --style raw*

### Scene 3: Jeda 46 Jam & Uang Raib (The Critical Window)
* **Visual:** Transisi waktu cepat (*time-lapse*), jarum jam dinding berputar liar, tumpukan kalender digital berganti, saldo tabungan merosot ke nol.
* **Text-to-Video Prompt (Kling / Runway Gen-3):**
  > *Cinematic fast time-lapse, analog wall clock hands spinning rapidly, motion blur, overlapping holographic countdown timers in red light, dramatic tension, camera tilting up, 4k cinematic grading.*
* **Image Prompt (Midjourney v6 / Flux):**
  > *A dynamic conceptual shot of a spinning glowing clock face dissolving into digital red binary numbers, dark background, cinematic motion blur, hyper-detailed --ar 16:9*

### Scene 4: Kemunculan SIAGA — AI Sentinel Proaktif
* **Visual:** Pemandangan udara Jakarta malam hari, perisai energi heksagonal digital biru menyala dari atas gedung menyaring ancaman masuk.
* **Text-to-Video Prompt (Kling / Runway Gen-3):**
  > *Aerial night view of Jakarta skyline, futuristic glowing blue holographic energy shield expanding across the city, digital particle streams intercepting red malicious data packets, epic sci-fi realism, cinematic drone flying shot.*
* **Image Prompt (Midjourney v6 / Flux):**
  > *Jakarta cityscape at night with a radiant blue semi-transparent digital cybersecurity grid dome overhead, glowing fiber optic lines connecting servers, cinematic photorealism --ar 16:9*

### Scene 5: Transisi ke Analis & Dasbor Nyata
* **Visual:** Kamera bergerak melewati jaringan kabel optik langsung menuju monitor ruang kontrol SOC, layar menampilkan dasbor SIAGA.
* **Text-to-Video Prompt (Kling / Runway Gen-3):**
  > *First-person transition flying through glowing blue fiber optic cables into a high-tech cybersecurity operations center, camera lands over the shoulder of a cybersecurity analyst looking at a clean threat dashboard monitor.*
* **Image Prompt (Midjourney v6 / Flux):**
  > *Over-the-shoulder view of a female cybersecurity analyst in a modern operations center, looking at clean web dashboard monitoring real-time domain threats, clean corporate tech lighting --ar 16:9*

---

## 3. PROMPT SUARA & SKRIP DUBBING (ELEVENLABS / AI VOICE)

* **Setting Karakter Suara:** Pria Indonesia, nada berat, tenang, berwibawa (*Authoritative & Empathetic Tech Narrator*).
* **Model:** ElevenLabs `Multilingual v2` (Voice: *Adam* / *Antoni* / *Daniel*).

### Skrip Voiceover Segmen Sinematik (Durasi: ~60 Detik):
```text
(0:00 - 0:15)
[Nada tegang, tempo lambat]
"Satu pesan singkat. Satu kepanikan. Dalam hitungan detik, tabungan kerja keras bertahun-tahun... lenyap tanpa jejak."

(0:15 - 0:35)
[Tempo sedikit meningkat, nada analitis]
"Setiap hari, ribuan domain penipuan lahir di ruang gelap internet. Dibuat dalam lima menit, mengeksploitasi kepanikan korban, lalu lenyap sebelum radar keamanan publik sempat menyadari keberadaannya."

(0:35 - 0:50)
[Nada tegas, membongkar masalah]
"Daftar hitam konvensional terlambat empat puluh enam jam. Dan korban tidak punya waktu menunggu."

(0:50 - 1:10)
[Musik transisi berubah optimis, percaya diri]
"Bagaimana jika kita menghentikan ancaman ini sebelum situsnya diluncurkan? Sejak detik pertama sertifikatnya diterbitkan di gerbang internet dunia?"

(1:10 - 1:25)
[Nada bangga, kuat]
"Inilah SIAGA. Agen intelijen siber otonom proaktif. Menjaga ruang digital Indonesia, tanpa henti."
```

---

## 4. PANDUAN INTEGRASI MASUK KE DEMO APLIKASI & SERVER

1. **Titik Potong (Cut Point 1:25):**  
   Saat narator mengucapkan *"Inilah SIAGA"*, akhiri scene video AI Scene 5, lalu gunakan efek *sound swoosh/glitch halus* langsung berpindah ke rekaman layar monitor Anda.
2. **Rekaman Layar Langsung (1:26 dst):**  
   * **Menit 1:26 - 3:00:** Tunjukkan antarmuka **Triage Sandbox** (Mode A), masukkan teks penipuan dari Scene 1 tadi. Ini menciptakan kesinambungan cerita yang kuat (*the app solves the exact problem shown in the AI video*).
   * **Menit 3:00 - 4:45:** Tunjukkan antarmuka **Radar & Telemetri** (Mode B) yang memantau aliran CT log secara otonom.
   * **Menit 4:45 - 5:50:** Masuk ke **Terminal SSH Cloud VPS** (`systemctl status siaga`, `free -m`) dan dashboard hosting, sambil menyebutkan *"AI Hosting IDwebhost"*.
   * **Menit 5:50 - 6:50:** Buka menu **Evaluation** dengan metrik akurasi 100% dan grafik keunggulan deteksi dini 46.4 jam.

