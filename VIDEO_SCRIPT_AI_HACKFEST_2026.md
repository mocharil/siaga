# MASTER SCRIPT & STORYBOARD: SUBMISSION VIDEO DEMO AI HACKFEST 2026

> **Judul Proyek:** SIAGA — Autonomous Threat Intelligence & Anti-Scam Agent  
> **Kategori:** Digital Safety & Public Good (Cyber Security & Anti Scam)  
> **Peserta:** Moch Aril Indra Permana (Batch 1)  
> **Target Durasi:** 7 Menit 30 Detik (Rentang Ketentuan: 5 – 10 Menit)  
> **Format:** 16:9 Landscape, 1080p 60fps  
> **Watermark Ketentuan:** Logo **IDwebhost** di pojok kanan atas (Top-Right Corner) sepanjang video.  
> **Wajib Verbal & Visual:** Menyebutkan **"AI Hosting"** dan **"IDwebhost"** (verbal + lower-third).  

---

## PANDUAN PRA-PRODUKSI & SETUP REKAMAN

1. **Persiapan Layar & Resolusi:**
   * Atur resolusi monitor ke **1920×1080 (Full HD)** dengan rasio **16:9**.
   * Buka browser dalam kondisi bersih (*incognito* atau profil khusus presentasi tanpa tab pengganggu).
   * Buka Dasbor SIAGA di `http://localhost:8000` atau `https://siaga-lake.vercel.app`.
   * Siapkan terminal SSH Cloud VPS dengan font besar (minimal 16pt - 18pt), tema kontras tinggi (gelap dengan teks hijau/putih terang) agar mudah dibaca oleh juri di layar kecil/smartphone.
2. **Watermark & Lower-Third:**
   * Pasang PNG logo IDwebhost dengan transparansi 80% di pojok kanan atas video dari detik pertama hingga akhir.
   * Pasang lower-third bertuliskan: *"Infrastruktur: Cloud VPS & AI Hosting IDwebhost"* saat membahas arsitektur dan terminal.
3. **Audio & Narasi:**
   * Gunakan mikrofon dengan filter *noise-suppression*.
   * Jangan gunakan musik berhak cipta (gunakan BGM lofi instrumental *copyright-free* dengan volume -24dB atau tanpa musik).
   * Baca narasi dengan artikulasi jelas, tempo tenang, dan intonasi meyakinkan (tone: pakar keamanan siber & solutif).

---

## TIME-CODED STORYBOARD & SCRIPT LENGKAP (7 Menit 30 Detik)

---

### SEGMENT 1: HOOK & RELEVANSI MASALAH (0:00 – 0:50)
* **Tujuan Rubrik:** Menjawab kriteria *Relevansi & Kejelasan Masalah* (Bobot 20%). Menarik perhatian juri dalam 30 detik pertama.
* **Durasi:** 50 Detik

| Waktu | Visual / On-Screen Action | Audio / Narasi Kata-per-Kata | Checklist Juri |
| :---: | :--- | :--- | :---: |
| **0:00 - 0:15** | Layar menampilkan cuplikan pesan WhatsApp/SMS penipuan: *"Pemberitahuan: Tarif transfer BCA naik Rp150.000/bln, batalkan di bca-tarifpenyesuaian[.]online dalam 1x24 jam"*. Zoom pelan ke tautan. | *"Di Indonesia, jutaan masyarakat setiap hari dihujani pesan manipulatif seperti ini: ancaman tagihan palsu, APK tilang elektronik, hingga pencatutan program sosial. Korban panik, mengklik tautan, dan dalam hitungan detik—saldo perbankan mereka ludes."* | Kasus nyata, relatable |
| **0:15 - 0:35** | Buka browser, ketik alamat domain penipuan. Tampilkan halaman tiruan yang sangat mirip aslinya. Lalu sorot URL bar di mana domainnya berakhiran `.online` atau `.xyz`. | *"Bagi masyarakat awam, tampilan situs ini terlihat sangat meyakinkan. Tapi bagi pelaku kejahatan, domain ini hanyalah infrastruktur sekali pakai. Mereka membelinya seharga sepuluh ribu rupiah, beroperasi selama beberapa jam, memanen korban, lalu membuang domain tersebut sebelum ada yang sempat melapor."* | Anatomi serangan |
| **0:35 - 0:50** | Transisi ke judul video: **"SIAGA: Autonomous Threat Intelligence Agent"**. Tampilkan tagline: *"Build Agent, Deliver Impact"*. Pojok kanan atas sudah ada watermark IDwebhost. | *"Pertanyaannya: Mengapa sistem keamanan konvensional selalu tertinggal? Dan bagaimana jika kita bisa mendeteksi domain penipuan ini sejak detik pertama sertifikatnya diterbitkan—bahkan sebelum situsnya diluncurkan ke publik? Inilah SIAGA."* | Title Card, Watermark IDwebhost aktif |

---

### SEGMENT 2: GAP TEKNOLOGI & INOVASI SIAGA (0:50 – 1:40)
* **Tujuan Rubrik:** Menjawab kriteria *Orisinalitas & Nilai Tambah Agent* (Bobot 15%). Menjelaskan mengapa chatbot biasa dan blacklist publik gagal.
* **Durasi:** 50 Detik

| Waktu | Visual / On-Screen Action | Audio / Narasi Kata-per-Kata | Checklist Juri |
| :---: | :--- | :--- | :---: |
| **0:50 - 1:15** | Animasi/diagram perbandingan: Menampilkan grafis garis waktu deteksi URLhaus/PhishTank (46 jam) vs SIAGA (0.12 detik). | *"Ada dua masalah fatal dari sistem keamanan saat ini. Pertama, blacklist publik global seperti URLhaus rata-rata membutuhkan waktu 24 hingga 46 jam untuk mengindeks situs penipuan—karena mereka menunggu laporan korban terlebih dahulu. Kedua, chatbot AI biasa bersifat pasif: mereka hanya bekerja jika pengguna berinisiatif bertanya."* | Problem statement teknis |
| **1:15 - 1:40** | Tampilkan diagram arsitektur **SIAGA Dual-Mode Engine**: Mode A (Triage Sandbox Reaktif) dan Mode B (Radar Otonom Proaktif). | *"SIAGA memecahkan kebuntuan ini melalui arsitektur Dual-Mode Agent. Mode A bekerja sebagai Triage Sandbox interaktif untuk analisis instan pesan mencurigakan. Sedangkan Mode B adalah Autonomous Agent otonom yang berpatroli 24/7 memantau aliran Certificate Transparency global tanpa henti."* | Pengenalan Dual-Mode |

---

### SEGMENT 3: LIVE DEMO MODE A — TRIAGE SANDBOX (1:40 – 3:15)
* **Tujuan Rubrik:** Menjawab kriteria *Efektivitas Solusi & Human-in-the-Loop* (Bobot 30%). Membuktikan agent benar-benar bekerja memecahkan masalah.
* **Durasi:** 1 Menit 35 Detik

| Waktu | Visual / On-Screen Action | Audio / Narasi Kata-per-Kata | Checklist Juri |
| :---: | :--- | :--- | :---: |
| **1:40 - 2:05** | Layar berpindah ke antarmuka **Triage Sandbox** (`#triage`). Kursor menempelkan teks pesan WhatsApp penipuan ke kotak input. Klik tombol **"Analyze Threat"**. | *"Mari kita uji Mode A. Saya memasukkan teks pesan penipuan transfer perbankan lengkap dengan tautannya. Dalam waktu kurang dari dua detik, SIAGA mengeksekusi pipeline investigasi end-to-end tanpa mengeksekusi kode berbahaya."* | Live demo tanpa rekayasa |
| **2:05 - 2:30** | Sorot hasil ekstraksi entitas: No Rekening, No HP, URL domain. Sorot indikator risiko: **Risk Score 85/100 (HIGH RISK)** dan radar pentagram sinyal teknis vs linguistik. | *"Perhatikan bagaimana agent ini mengekstrak nomor rekening, nomor kontak, serta menganalisis urgensi manipulatif pesan. Sistem melakukan DNS lookup, memeriksa riwayat RDAP—yang mengungkap bahwa domain baru berumur 2 hari—serta melacak rantai redirect HTTP secara aman."* | Fitur ekstraksi & analisa heuristik |
| **2:30 - 2:50** | Klik tombol **"Open Isolated Sandbox"**. Tunjukkan preview halaman web phishing yang dirender aman di dalam iframe sandbox terisolasi macOS-style. | *"Untuk pembuktian analis, SIAGA menyediakan Isolated Web Sandbox terisolasi dengan atribut sandbox ketat. Analis dapat melihat tampilan visual situs phishing tanpa risiko terkena malware atau zero-day exploit browser."* | Keamanan analis (Sandbox) |
| **2:50 - 3:15** | Scroll ke bawah ke bagian **RFC 2350 CSIRT Pack** dan tombol tindakan cepat: **Aduan Kominfo (WhatsApp)**, **PANDI Abuse Desk**, **Gov-CSIRT BSSN**, dan **Satgas OJK**. | *"Dan yang paling penting, sesuai regulasi dan kepatuhan hukum, SIAGA tidak melakukan tindakan main hakim sendiri. Sistem otomatis menyusun draf laporan berstandar RFC 2350 dan menyediakan tombol eskalasi resmi satu-klik ke Kominfo, PANDI, BSSN, dan OJK. Ini adalah prinsip Human-in-the-Loop yang bertanggung jawab."* | **Kepatuhan Aturan No. 6 & 7 Playbook (No Main Hakim Sendiri)** |

---

### SEGMENT 4: LIVE DEMO MODE B — AUTONOMOUS RADAR & TELEMETRY (3:15 – 4:45)
* **Tujuan Rubrik:** Menunjukkan kemampuan otonom agent di Certificate Transparency stream & visualisasi intelijen.
* **Durasi:** 1 Menit 30 Detik

| Waktu | Visual / On-Screen Action | Audio / Narasi Kata-per-Kata | Checklist Juri |
| :---: | :--- | :--- | :---: |
| **3:15 - 3:45** | Klik menu navigasi **Radar**. Tampilkan antarmuka radar pemantau CT Log dengan badge hijau berdenyut: *"LIVE CT TELEMETRY STREAM"*. Tunjukkan domain-domain yang masuk secara real-time. | *"Sekarang, mari kita masuk ke jantung kekuatan SIAGA: Mode B — Autonomous Radar. Di layar ini, agent memantau aliran sertifikat SSL/TLS global secara langsung. Setiap kali ada domain baru diterbitkan di dunia yang menargetkan brand Indonesia, agent langsung menangkapnya dalam milidetik."* | Real-time agentic workflow |
| **3:45 - 4:15** | Tunjukkan tabel temuan aktif phishing perbankan, filter judi online, dan konten pornografi terselubung pada subdomain `.go.id` dan `.ac.id`. | *"Lihat daftar temuan ini: ada 292 domain phishing perbankan aktif, 81 insiden penyusupan judi online pada domain publik, dan 45 konten berbahaya. Agent mengelompokkan temuan berdasarkan klaster infrastruktur IP dan ASN untuk mengungkap sindikat penipuan yang sama."* | Sinkronisasi data & klastering sindikat |
| **4:15 - 4:45** | Tampilkan layar smartphone atau jendela Telegram yang menerima notifikasi instan dari Bot SIAGA: *"🚨 CRITICAL ALERT: Phishing BCA Terdeteksi: klikbca-verif[.]online"*. | *"Bahkan tanpa ada operator yang membuka dasbor, SIAGA bekerja otonom. Saat domain risiko kritis terdeteksi, bot intelijen langsung mengirimkan cascade alert ke kanal Telegram tim tanggap insiden lengkap dengan bukti forensiknya."* | Otonom 24/7 tanpa intervensi |

---

### SEGMENT 5: INFRASTRUKTUR CLOUD VPS & AI HOSTING IDWEBHOST (4:45 – 5:50)
* **Tujuan Rubrik:** **WAJIB PLAYBOOK** (Kualitas Eksekusi Teknis 20% & Syarat Wajib Video No. 2, 3). Tampilkan terminal VPS, dashboard hosting, verbal & lower-third IDwebhost.
* **Durasi:** 1 Menit 05 Detik

| Waktu | Visual / On-Screen Action | Audio / Narasi Kata-per-Kata | Checklist Juri |
| :---: | :--- | :--- | :---: |
| **4:45 - 5:10** | Layar terbagi (*split screen*): Sebelah kiri menampilkan **Terminal SSH VPS Linux**, sebelah kanan menampilkan **Dashboard Cloud VPS / CloudBaik**. Lower-third muncul: *"Infrastruktur: Cloud VPS & AI Hosting IDwebhost"*. | *"Untuk memastikan agent dapat berpatroli otonom selama 24 jam nonstop selama sebulan penuh, SIAGA diorkestrasi di atas infrastruktur **Cloud VPS** yang sangat stabil dan didukung oleh ekosistem **AI Hosting** dari **IDwebhost**."* | **Wajib Verbal & Lower Third "AI Hosting" & "IDwebhost"** |
| **5:10 - 5:30** | Di terminal, ketik perintah: `systemctl status siaga` (menunjukkan status *active (running)* dan uptime panjang). Lalu ketik `htop` atau `free -m`. | *"Mari kita intip langsung lingkungan server-nya. Service SIAGA berjalan sebagai background daemon mandiri dengan uptime sempurna. Perhatikan penggunaan sumber dayanya: berkat arsitektur async dan database SQLite WAL yang hemat, backend ini hanya mengonsumsi RAM di bawah 120 Megabyte dari 4 Gigabyte yang disediakan Cloud VPS."* | Menunjukkan environment VPS sedang digunakan |
| **5:30 - 5:50** | Tampilkan log rotasi dan skrip backup: `ls -la backups/daily/` dan `python -m pytest tests/` yang menunjukkan 298 passed. | *"Server ini juga telah kami perkuat dengan keamanan ketat: otentikasi SSH key Ed25519, non-root user, firewall UFW, serta backup database otomatis harian. Seluruh 298 unit test lulus 100% menjamin keandalan sistem di tingkat produksi."* | Reliability, Hardening & 298 Tests Passed |

---

### SEGMENT 6: INOVASI CASCADING FUNNEL & EVALUATION BENCHMARK (5:50 – 6:50)
* **Tujuan Rubrik:** Menjelaskan penghematan 98% token AI & memamerkan metrik evaluasi yang baru saja kita poles.
* **Durasi:** 1 Menit 00 Detik

| Waktu | Visual / On-Screen Action | Audio / Narasi Kata-per-Kata | Checklist Juri |
| :---: | :--- | :--- | :---: |
| **5:50 - 6:15** | Buka menu navigasi **Evaluation** (`#evaluation`). Sorot 6 kartu metrik KPI yang tersusun proporsional: **Precision 100.0%**, **Recall 91.8%**, **F1 0.9573**, **AUC-ROC 0.994**, **Specificity 100.0%**, **Latency 128ms**. | *"Banyak pengembang membuat agen AI dengan cara memboroskan token LLM untuk setiap data yang lewat. SIAGA berbeda. Kami merancang Cascading Filter 3-Tahap: 96% domain disaring secara lokal di CPU menggunakan algoritma Levenshtein dan normalisasi homoglyph dengan nol token. LLM hanya dipanggil untuk domain yang benar-benar berisiko tinggi. Hasilnya: konsumsi token terpangkas 98%!"* | Inovasi hemat 98% token |
| **6:15 - 6:50** | Scroll ke panel **Detection Lead-Time Advantage** (46.4 hrs) dan **Tabel Benchmark Kompetitif**. | *"Pada pengujian ground-truth 120 sampel terverifikasi, SIAGA meraih Presisi sempurna 100% tanpa ada satupun domain resmi yang salah dituduh, Recall 91.8%, dan skor AUC-ROC 0.994. Yang paling revolusioner: rata-rata waktu deteksi SIAGA adalah 46.4 jam lebih awal dibandingkan blacklist publik global seperti URLhaus. Kita menghentikan penipuan sebelum ada korban jatuh."* | Lead time 46.4h & Precision 100% |

---

### SEGMENT 7: DAMPAK PUBLIK & PENUTUP (6:50 – 7:30)
* **Tujuan Rubrik:** Menjawab kriteria *Storytelling & Public Good* (Bobot 15%). Closing yang kuat, profesional, dan berkesan.
* **Durasi:** 40 Detik

| Waktu | Visual / On-Screen Action | Audio / Narasi Kata-per-Kata | Checklist Juri |
| :---: | :--- | :--- | :---: |
| **6:50 - 7:15** | Tampilkan kompilasi cepat: Peta Sebaran Ancaman Regional, Draf Laporan BSSN, dan Repositori GitHub publik (`github.com/mocharil/siaga`). | *"Keamanan siber bukan tentang seberapa mahal server yang kita sewa, melainkan seberapa cerdas arsitektur yang kita rancang. SIAGA hadir untuk melindungi ruang digital Indonesia—dari ibu rumah tangga yang menerima SMS palsu hingga institusi negara yang menjaga kedaulatan informasinya."* | Deliver Impact (Visi Public Good) |
| **7:15 - 7:30** | Layar Penutup (Outro): Logo SIAGA, Tautan Live Demo (`siaga-lake.vercel.app`), GitHub Repo, dan logo **IDwebhost** serta **CloudBaik**. | *"Seluruh kode sumber SIAGA bersifat open source dan siap diimplementasikan. Terima kasih kepada IDwebhost dan CloudBaik atas ekosistem AI Hosting dan Cloud VPS yang andal. Mari bersama kita bangun agen kecerdasan buatan yang menghadirkan dampak nyata bagi bangsa. Saya Moch Aril Indra Permana, salam SIAGA!"* | Closing formal, credits partner & tagline |

---

## CHECKLIST VERIFIKASI SEBELUM SUBMIT VIDEO

- [x] **Durasi Video:** 7 Menit 30 Detik (Memenuhi syarat 5–10 menit).
- [x] **Rasio & Resolusi:** 16:9 Landscape, 1080p Full HD.
- [x] **Watermark:** Logo IDwebhost terpasang di sudut layar sepanjang video.
- [x] **Verbal Mention Wajib:** Disebutkan kata **"AI Hosting"** dan **"IDwebhost"** secara gamblang pada Menit 4:45 – 5:10.
- [x] **Lower-Third Wajib:** Teks banner *"Infrastruktur: Cloud VPS & AI Hosting IDwebhost"* muncul di layar.
- [x] **Lingkungan Server:** Menampilkan Terminal SSH VPS (`systemctl status siaga`, resource memory, port binding) dan dashboard cloud.
- [x] **Proses End-to-End:** Menampilkan input pesan, analisis, visualisasi radar, hingga pembuatan laporan resmi CSIRT.
- [x] **Kepatuhan Hukum:** Ditegaskan bahwa agent menggunakan prinsip *Human-in-the-Loop* dan eskalasi resmi (bukan main hakim sendiri).
- [x] **Hak Cipta Audio:** Suara asli jernih tanpa backsound komersial berlisensi.
- [x] **Status Unggah:** Disetel ke **Public** di YouTube.

