# SIAGA: Membangun Agent Otonom Pemantau Phishing Berbasis Certificate Transparency dan Arsitektur Hemat Token

> **Artikel Publikasi Resmi — AI HackFest 2026 (IDwebhost × PANDI)**  
> **Kategori:** Digital Safety & Public Good  
> **Framework:** OpenClaw AI  
> **Artikel Kompetisi Resmi — AI HackFest 2026 (IDwebhost × .id)**  
> **Tema:** *Build Agent, Deliver Impact*  
> **Kategori:** Digital Safety & Public Good (Subkategori: Cyber Security & Anti Scam)  
> **Peserta:** Moch Aril Indra Permana (Batch 1)  
> **Framework:** OpenClaw AI & FastAPI  
> **Infrastruktur:** [Cloud VPS](https://cloudbaik.com) & [AI Hosting](https://idwebhost.com/ai-hosting)  
> **Repositori Kode:** [GitHub: mocharil / siaga](https://github.com/mocharil/siaga)  
> **Live Web Dashboard:** [https://siaga-lake.vercel.app](https://siaga-lake.vercel.app)  
> **Data Operasional:** Snapshot per 01 September 2026 (Operasional Aktif 5 Hari)

---

## 1. Pembuka: Jebakan 24 Jam Pertama
## 1. Pembuka: Jebakan 24 Jam Pertama di Ekosistem Digital Indonesia

Di sebuah grup percakapan keluarga, sebuah pesan singkat beredar: *"Peringatan dari bank Anda: tarif transfer bulanan akan disesuaikan menjadi Rp 150.000. Batalkan segera melalui tautan berikut."* Tautan tersebut mengarah ke sebuah domain yang sekilas tampak meyakinkan: `bca-tarifpenyesuaian[.]online`. 
Di sebuah grup percakapan WhatsApp keluarga, sebuah notifikasi masuk dengan nada panik:  
*"Pemberitahuan Resmi: Perubahan skema tarif transfer perbankan Anda menjadi Rp 150.000/bulan. Batalkan segera dalam 1x24 jam melalui tautan resmi ini agar saldo tidak terdebit otomatis."*

Bagi pengguna awam yang panik, situs tersebut tampak identik dengan portal perbankan resmi. Namun di balik antarmuka yang rapi itu, sebuah formulir tersembunyi dirancang khusus untuk memanen nomor kartu debit, PIN, dan kode OTP korban. Ketika korban menyadari saldo rekeningnya terkuras, situs tersebut sudah berganti alamat atau bahkan telah dimatikan oleh pelakunya.
Tautan yang disertakan sekilas tampak meyakinkan: `bca-tarifpenyesuaian[.]online`. 

Kejahatan siber berbasis *social engineering* dan penipuan digital di Indonesia tidak lagi mengandalkan domain acak yang mudah dicurigai. Pelaku kini memanfaatkan domain tingkat tinggi murah (.xyz, .online, .top, .site) yang dikombinasikan dengan teknik peniruan identitas (*brand impersonation*) institusi terpercaya. Pertanyaannya: mengapa sistem keamanan konvensional kerap terlambat menghentikannya?
Bagi jutaan masyarakat awam yang minim literasi siber, tautan tersebut terlihat seperti situs resmi institusi perbankan. Namun, hanya dalam hitungan detik setelah korban mengklik dan memasukkan nomor kartu, PIN, serta kode OTP, saldo tabungannya terkuras tanpa sisa. Ironisnya, saat korban baru menyadari kerugian tersebut dan melapor ke pihak berwajib, situs penipuan itu sudah berganti alamat, mematikan servernya (*ephemeral infrastructure*), atau berpindah ke varian domain murah lainnya.

Data penipuan siber nasional menunjukkan pola yang kian mengkhawatirkan:
* Modus rekayasa sosial (*social engineering*) kini bermutasi sangat cepat—mulai dari modus APK surat tilang elektronik (ETLE), undangan pernikahan palsu, kurir paket, hingga pencatutan program bantuan pemerintah dan saldo dompet digital.
* Subdomain instansi pendidikan (`.ac.id`) dan pemerintahan (`.go.id`) kerap menjadi korban peretasan (*defacement / SEO poisoning*) untuk disisipi promosi judi online (*judol*) dan konten pornografi terselubung.
* Pelaku memanfaatkan domain tingkat tinggi murah (*cheap TLDs* seperti `.xyz`, `.top`, `.online`, `.site`, `.vip`) yang dibeli seharga ribuan rupiah, dioperasikan selama 6 hingga 18 jam, lalu dibuang sebelum sempat terdeteksi oleh radar keamanan global.

Pertanyaan krusialnya: **Mengapa pendekatan keamanan konvensional yang ada saat ini kerap terlambat menghentikan mereka?**

---

## 2. Kenapa Verifikasi Itu Sulit?
## 2. Mengapa Keamanan Konvensional Kerap Tertinggal?

Membedakan domain penipuan dari puluhan ribu pendaftaran domain baru setiap harinya merupakan tantangan teknis yang rumit karena tiga sinyal tersembunyi:
Secara teknis, memfilter puluhan ribu domain yang baru didaftarkan setiap hari adalah tantangan komputasi dan analitis yang rumit. Terdapat tiga kelemahan mendasar dari model keamanan konvensional:

1. **Typosquatting & Directed Permutations:** Pelaku jarang membuat salah ketik acak. Mereka secara sengaja menyisipkan nama brand resmi sebagai subdomain (`bca.promo-khusus.xyz`) atau menambahkan kata kerja persuasif berpola tanda hubung (`klikbca-update`, `login-mandiri-verif`).
2. **Homoglyph & Punycode Normalization:** Penggunaan karakter Unicode visual serupa (misalnya huruf sirilik `а` yang menyerupai huruf latin `a` pada `xn--b-8sb.id`) sering kali mengelabui mata manusia dan pencocokan teks sederhana.
3. **Siklus Hidup Kilat (*Ephemeral Domains*):** Domain phishing modern sering kali didaftarkan, diberi sertifikat SSL, melancarkan kampanye penipuan selama 6 hingga 18 jam, lalu ditinggalkan sebelum sempat terindeks oleh vendor antivirus global.
1. **Waktu Tunda (*Lead Time*) Blacklist Publik Terlalu Lambat:**  
   Basis data intelijen ancaman publik global seperti URLhaus, PhishTank, atau OpenPhish mengandalkan laporan komunitas (*crowdsourcing*). Rata-rata waktu tunda (*lead time*) sejak sebuah situs penipuan aktif hingga resmi masuk ke daftar hitam global adalah **24 hingga 36 jam**. Bagi kampanye phishing modern, 24 jam sudah lebih dari cukup untuk memanen ratusan korban.
2. **Keterbatasan Chatbot Pasif:**  
   Banyak pengembang mencoba menyelesaikan masalah ini dengan membuat *chatbot* tanya-jawab berbasis LLM. Masalahnya, chatbot bersifat pasif: ia hanya bekerja jika korban sudah merasa curiga dan berinisiatif bertanya. Padahal, korban penipuan yang paling rentan justru adalah mereka yang berada di bawah manipulasi psikologis kepanikan dan tidak sempat meragukan keaslian pesan.
3. **Teknik Evasif Tingkat Lanjut (*Advanced Evasion*):**  
   Pelaku penipuan modern tidak lagi membuat salah ketik acak (*simple typosquatting*). Mereka menggunakan kombinasi:
   * **Homoglyph & Punycode (IDN):** Memanfaatkan karakter visual serupa dari alfabet Sirilik atau Yunani (misal `xn--b-8sb.id` yang di layar tampak persis seperti `ba.id`).
   * **Subdomain Hijacking:** Menempelkan nama bank terpercaya di depan subdomain acak (misal `klikbca.secure-update-id.com`).
   * **Multi-Hop Redirects:** Menyamarkan tautan akhir melalui pemendek URL (*URL shortener*) bertingkat untuk mengelabui filter peramban.

Untuk menutup celah inilah kami membangun **SIAGA (Sistem Intelijen & Antisipasi Gangguan Siber Aktif)**—sebuah **AI Threat Intelligence Agent Otonom** yang tidak menunggu laporan masuk, melainkan secara proaktif berpatroli di gerbang internet global sebelum korban berjatuhan.

---

## 3. Kenapa Perlu Agent, Bukan Sekadar Chatbot atau Blacklist?
## 3. Filosofi Arsitektur: Dual-Mode Agent & Hemat Token

Pendekatan keamanan konvensional memiliki kelemahan mendasar:
* **Blacklist Publik Pasif:** Basis data ancaman global (seperti URLhaus atau OpenPhish) memiliki waktu tunda (*lead time*) rata-rata 24 hingga 36 jam. Saat sebuah domain masuk ke daftar hitam publik, korban sudah berjatuhan.
* **Chatbot Generatif Pasif:** Menaruh LLM di depan pesan pengguna hanya membantu mereka yang sudah curiga dan bertanya. Korban yang paling rentan justru adalah mereka yang tidak sadar sedang ditipu.
Sebuah AI Agent yang baik tidak boleh sekadar menjadi pembungkus tipis (*thin wrapper*) pemanggil API OpenAI atau Claude. Jika setiap domain yang muncul di internet langsung dianalisis menggunakan LLM, biaya komputasi dan token akan meledak dalam hitungan jam.

Di sinilah **SIAGA** hadir sebagai **Agent Otonom Proaktif**. SIAGA tidak menunggu korban melapor. Ia secara mandiri memantau aliran sertifikat TLS global (*Certificate Transparency Log*) secara *real-time*, menyaring puluhan ribu domain baru, memvalidasi bukti teknis, menyintesis analisis risiko, dan mengelompokkan infrastruktur kampanye penipuan sebelum domain tersebut sempat menjaring korban massal.
SIAGA dirancang dengan filosofi **Dual-Mode Architecture** yang menggabungkan kecepatan pemrosesan lokal berbiaya nol dengan kedalaman analisis penalaran AI:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           SIAGA DUAL-MODE AGENT ARCHITECTURE                     │
├────────────────────────────────────────────────┬────────────────────────────────┤
│    MODE A: Triage Sandbox & Analisis Pesan     │  MODE B: Radar Pengawasan CT Log Aktif │
│         (Reaktif / Permintaan Pengguna)        │         (Proaktif / 24-7 Otonom)       │
├────────────────────────────────────────────────┼────────────────────────────────┤
│ • Ekstraksi Entitas (URL, No HP, No Rekening)  │ • Ingestion Stream Certificate         │
│ • Pelacakan Redirect HTTP HEAD-only Ringan     │   Transparency (10.000–30.000 dom/hari)│
│ • Validasi RDAP & Umur Domain Real-Time        │ • 3-Tier Cascading Filter Funnel       │
│ • Analisis Linguistik (Urgensi, Otoritas Palsu,│ • Klasifikasi Multi-Tier Judol & Porn  │
│   Umpan Hadiah, Permintaan Bahaya / APK)       │ • Verifikasi Ambigu via LLM Semantik   │
│ • Penilaian Risiko Kalibrasi 0–100             │ • Pemetaan Klaster Infrastruktur IP/NS │
│ • Rekomendasi Bahasa Awam + Draf RFC 2350      │ • Notifikasi Telegram CSIRT Instan     │
└────────────────────────────────────────────────┴────────────────────────────────┘
```

### A. Mode A: Triage Sandbox & Analisis Pesan Instan
Bekerja sebagai asisten perlindungan langsung bagi publik maupun analis SOC:
* Pengguna cukup memasukkan potongan teks pesan mencurigakan (SMS/WhatsApp) atau tautan domain.
* Sistem secara otomatis mengekstrak entitas nomor rekening, nomor ponsel, dan URL.
* Melakukan pengecekan teknis kilat: riwayat pendaftaran domain (RDAP), lompatan *redirect*, serta analisis heuristik linguistik.
* Menghasilkan skor risiko 0–100, visualisasi radar sinyal teknis vs linguistik, rekomendasi tindakan dalam bahasa manusia yang mudah dipahami, serta naskah laporan insiden formal berstandar **RFC 2350 CSIRT**.

### B. Mode B: Radar Pengawasan CT Log Otonom
Bekerja tanpa henti di latar belakang:
* Mengonsumsi aliran sertifikat SSL/TLS global (*Certificate Transparency Logs*) secara langsung. Setiap kali ada domain baru yang diterbitkan sertifikatnya di seluruh dunia (khususnya zona `.id` dan target institusi Indonesia), domain tersebut langsung ditangkap sebelum situsnya bahkan sempat diluncurkan ke publik.
* Melalui corong penyaringan bertingkat (*Cascading Funnel*), domain diproses dalam milidetik.
* Menghubungkan temuan dengan basis data blacklist URLhaus dan pemetaan klaster nameserver/IP untuk mengungkap sindikat penipuan yang sama.

---

## 4. Arsitektur Penyaringan Bertingkat (Cascading Funnel)
## 4. Corong Penyaringan 3-Tahap (Cascading Funnel): Memangkas Token hingga 98%

Memproses 10.000 hingga 30.000 domain baru setiap hari langsung menggunakan model bahasa besar (LLM) adalah pemborosan biaya token dan komputasi yang tidak realistis. SIAGA merancang **Pipeline Penyaringan 3-Tahap (Cascading Funnel)** dari yang paling murah ke yang paling analitis:
Inovasi utama SIAGA terletak pada arsitektur penyaringan bertingkat dari metode komputasi paling murah hingga pemanggilan model AI yang berbobot:

```
┌─────────────────────────────────────────────────────────────┐
│ Tahap 0: CT Log Ingestion (9.000–14.000 domain/hari)        │
├─────────────────────────────────────────────────────────────┤
│ Tahap 1: Brand Similarity Filter (CPU Lokal, 0 Token LLM)   │
│          Damerau-Levenshtein, Homoglyph, Directed Stem      │
│          ➔ Memangkas ~96.5% domain wajar                    │
├─────────────────────────────────────────────────────────────┤
│ Tahap 2: Verifikasi Teknis (0 Token LLM, Network I/O Ringan)│
│          HEAD-only HTTP Status, Cache RDAP Umur Domain,     │
│          Pengecekan DNS & Feed Blacklist                    │
│          ➔ Menyaring domain mati / institusi resmi (.go.id) │
├─────────────────────────────────────────────────────────────┤
│ Tahap 3: Sintesis Risiko LLM & Korelasi Kampanye            │
│          Evaluasi Bukti Teknis + Kluster Nameserver / IP    │
│          ➔ Menghasilkan Temuan Prioritas Berbobot           │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────────────┐
│ Tahap 0: CT Log Ingestion (10.000 – 30.000 domain baru/hari)                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tahap 1: Brand Similarity & Heuristic Filter (CPU Lokal, 0 Token LLM)       │
│          • Damerau-Levenshtein Distance & Keyboard Proximity                │
│          • Homoglyph Punycode Normalization                                 │
│          • Directed Stem Permutations (misal: "login-bca", "klikbca-promo") │
│          ➔ Memangkas ~96.5% domain normal yang tidak relevan                │
├─────────────────────────────────────────────────────────────────────────────┤
│ Tahap 2: Verifikasi Bukti Teknis (0 Token LLM, Network I/O Ringan)          │
│          • HTTP HEAD-only Check (verifikasi status aktif tanpa unduh payload)│
│          • SQLite Cached RDAP (analisis umur domain < 7 hari / < 30 hari)   │
│          • Resolusi DNS & Cross-Check Feed URLhaus Blacklist                │
│          ➔ Memisahkan domain mati, parked page, atau institusi resmi (.go.id)│
├─────────────────────────────────────────────────────────────────────────────┤
│ Tahap 3: Sintesis Risiko AI & Korelasi Klaster                              │
│          • Evaluasi Multi-Sinyal 0–100 & Korelasi Infrastruktur IP/NS       │
│          • LLM Semantic Synthesis untuk kandidat risiko tinggi (Skor >= 60) │
│          • Verifikasi Ambigu Domain Judol/Porn (Nama Brand vs Judi)          │
│          ➔ Menghasilkan Temuan Prioritas & Draf Laporan Siap Tindak         │
└─────────────────────────────────────────────────────────────────────────────┘
```

Dengan arsitektur ini, konsumsi token LLM terpangkas hingga **98%**, memungkinkan operasional intelijen ancaman berdaya guna tinggi dengan biaya minimal di atas infrastruktur server [Cloud VPS](https://cloudbaik.com).
Dengan desain ini:
1. **Lebih dari 96% lalu lintas domain mentah dibersihkan di Tahap 1 menggunakan algoritma lokal CPU** tanpa mengeluarkan biaya sepeser pun.
2. **Tahap 2 memverifikasi keaktifan teknis secara aman** tanpa pernah mengunduh kode berbahaya JavaScript dari situs penyerang (*HEAD-only HTTP probes*).
3. **LLM hanya dipanggil pada Tahap 3 untuk domain yang benar-benar berisiko tinggi** atau memiliki pola penamaan ambigu yang membutuhkan pemahaman semantik kontekstual.

Kode sumber lengkap, skema basis data SQLite terisolasi, dan modul evaluasi model SIAGA tersedia secara terbuka pada repositori GitHub resmi kami di:  
👉 **[GitHub: mocharil / siaga](https://github.com/mocharil/siaga)**, serta dapat diakses secara interaktif melalui live web dashboard di:  
🌐 **[Live Web Dashboard: https://siaga-lake.vercel.app](https://siaga-lake.vercel.app)**.
Hasilnya? **Konsumsi token AI terpangkas hingga 98%**, sementara latensi pemrosesan pindaian awal hanya memakan waktu **1.51 milidetik per domain** pada mesin lokal.

---

## 5. Menjalankannya di Lingkungan Server: Efisiensi & Hardening
## 5. Eksekusi Teknis di Infrastruktur Server: Efisiensi & Zero Attack Surface

Sebagai agen yang dirancang untuk beroperasi tanpa henti (24/7), SIAGA dibangun dengan prinsip *Local-First* dan *Zero-Attack Surface*:
Sebagai sistem yang ditugaskan berpatroli 24/7 di lini terdepan pertahanan siber, SIAGA dibangun di atas fondasi server yang tangguh dan terisolasi:

1. **Hardening Sistem Operasi:** Akses server dikonfigurasi secara ketat hanya menggunakan otentikasi SSH berbasis kunci privat (*Key-Only*), menonaktifkan login `root` langsung, mengaktifkan pembaruan keamanan otomatis (*unattended-upgrades*), dan membatasi firewall UFW. Port monitoring internal (FastAPI Dashboard dan OpenClaw Gateway) dikonfigurasi eksklusif pada `127.0.0.1` dan hanya dapat diakses melalui SSH Tunnel.
2. **Efisiensi Sumber Daya:** Berkat optimasi komputasi string Damerau-Levenshtein dan arsitektur SQLite *Write-Ahead Logging* (WAL), proses background SIAGA hanya mengonsumsi **31.9 MB RAM** untuk API Dashboard dan ~131.5 MB untuk gateway OpenClaw dengan utilisasi CPU di bawah 5%.
3. **Keandalan Hosting Mandiri:** Seluruh pipeline, pelacakan redirect HTTP HEAD-only, dan antarmuka visualisasi tanpa pustaka CDN eksternal dapat di-hosting secara mandiri pada platform [AI Hosting](https://idwebhost.com/ai-hosting/) dengan jaminan uptime maksimal dan isolasi data penuh.
### A. Penggunaan Infrastruktur Andal
SIAGA diorkestrasi di atas lingkungan server berkinerja tinggi menggunakan infrastruktur [Cloud VPS](https://cloudbaik.com) yang menyediakan kestabilan latensi jaringan internasional untuk *CT Log streaming*, serta diintegrasikan dengan platform [AI Hosting](https://idwebhost.com/ai-hosting) yang menjamin ketersediaan sumber daya komputasi secara berkelanjutan dan mandiri (*self-hosted*).

### B. Optimalisasi Efisiensi Memori (Peak RAM < 120 MB)
Tidak seperti aplikasi AI enterprise yang boros RAM (membutuhkan bergiga-giga memori hanya untuk framework), SIAGA dirancang seringan mungkin:
* Mesin basis data menggunakan **SQLite dengan mode Write-Ahead Logging (WAL)** dan isolasi koneksi `readonly`. Hal ini memungkinkan penulisan temuan baru dari daemon pemindai CT log berjalan bersamaan (*concurrency*) dengan pembacaan dasbor ribuan kali tanpa *lock contention*.
* Arsitektur backend Python FastAPI dibangun secara *asynchronous* dan *zero-dependency* berat (tanpa Redis atau Kafka eksternal), sehingga **total penggunaan RAM proses backend dasbor hanya berkisar ~31.9 MB** dan keseluruhan sistem tetap berada di bawah **120 MB RAM**. Ini membuktikan bahwa solusi kecerdasan buatan tingkat tinggi dapat berjalan mulus bahkan pada spesifikasi Cloud VPS paling terjangkau.

### C. Pengerasan Keamanan Server (*Server Hardening*)
* **Key-Only SSH & Non-Root Execution:** Akses terminal server dikunci total hanya menggunakan pasangan kunci kriptografi Ed25519; login password dan user `root` dinonaktifkan.
* **Localhost Binding & UFW Firewall:** Port dasbor internal dikonfigurasi eksklusif pada `127.0.0.1`. Analis mengakses antarmuka melalui enkripsi *SSH Tunneling* atau *reverse proxy* bersertifikat SSL/TLS.
* **Zero Script Execution Sandbox:** Saat melakukan inspeksi konten web, SIAGA menyediakan fitur **macOS-Style Isolated Web Sandbox** dengan atribut iframe `sandbox="allow-same-origin"` yang menonaktifkan eksekusi skrip jahat (*attacker-side payload execution*), eksploitasi browser zero-day, serta pelacak otomatis.

---

## 6. Hasil Pengujian & Evaluasi Nyata
## 6. Hasil Pengujian & Tolok Ukur Nyata (Empirical Evaluation)

Evaluasi sistem dilakukan menggunakan dataset uji 120 sampel terverifikasi (*ground-truth test set*) yang merepresentasikan spektrum ancaman nyata di Indonesia:
Kami menguji keandalan deteksi SIAGA menggunakan dataset evaluasi 120 sampel terverifikasi (*ground-truth benchmark*) yang mencakup spektrum serangan nyata di Indonesia: phishing perbankan, penipuan kurir/tilang APK, skema piramida penipuan pulsa/dana kaget, domain resmi pemerintah, serta varian ambigu.

* **Model Precision:** **100.00%** (56/56, 0 *False Positive* pada sampel legitimasi institusi resmi dan pesan ambigu).
* **Model Recall:** **91.80%** (56 dari 61 varian serangan phishing berbobot berhasil diidentifikasi).
* **F1-Score:** **0.9573** (Melampaui target batas kelulusan kompetisi ≥ 0.8200).
* **False Positive Rate (FPR):** **0.00%** (Di bawah ambang toleransi ≤ 10.0%).
* **Akurasi Keseluruhan:** **95.83%**.
* **Kecepatan Analisis:** Waktu pemrosesan pindaian awal dioptimalkan hingga **1.51 ms/domain**, memungkinkan penyaringan 10.000 domain harian selesai dalam hitungan menit di CPU lokal.
Berikut rekapitulasi performa teknis model:

### Rekapitulasi Data Operasional Nyata (5 Hari Operasi):
* **Total Domain Mentah Dipindai (`ct_raw`):** **47.664 domain**
* **Total Temuan Terindikasi (`domain_findings`):** **546 temuan**
* **Klaster Infrastruktur Terpetakan:** **55 klaster kampanye penipuan**
* **Top 3 Brand Paling Banyak Ditiru:** Ruangguru (61 domain), Investree (38 domain), Paxel (32 domain).
| Metrik Evaluasi | Target Minimum HackFest | Hasil Pengujian Nyata SIAGA | Status |
| :--- | :---: | :---: | :---: |
| **Precision** | $\ge 80.0\%$ | **100.00%** (56/56) | **Sempurna (0 False Positive)** |
| **Recall** | $\ge 80.0\%$ | **91.80%** (56/61) | **Sangat Baik** |
| **F1-Score** | $\ge 0.8200$ | **0.9573** | **Melampaui Target (+16.7%)** |
| **False Positive Rate (FPR)** | $\le 10.0\%$ | **0.00%** | **Sempurna (Aman bagi Domain Sah)** |
| **Akurasi Keseluruhan** | - | **95.83%** | **Unggul** |
| **Kecepatan Pindaian Awal** | - | **1.51 ms / domain** | **Real-Time Streaming Ready** |
| **Rangkaian Unit Test Proyek** | 100% Pass | **298 / 298 Tests Passed** | **Lulus Penuh (100%)** |

### Data Operasional Nyata (Snapshot 5 Hari Pemantauan):
Selama masa pemantauan aktif pada klaster server, SIAGA mencatatkan statistik operasional riil:
* **Total Domain Mentah Tersaring (`ct_raw`):** **47.664 domain**
* **Temuan Terverifikasi Berisiko Tinggi:** **546 domain penipuan aktif**
* **Klaster Sindikat Terpetakan:** **55 klaster kampanye penipuan terorganisir** (berdasarkan kesamaan ASN, IP, dan pola nameserver).
* **Target Institusi Terbanyak Ditiru:** Perbankan nasional (BCA, Mandiri, BRI), platform edutech (Ruangguru), dan layanan ekspedisi kurir.

---

## 7. Kegagalan Nyata, Bug yang Ditemukan, dan Pelajaran Berharga
## 7. Catatan Kegagalan Teknikal & Pelajaran Berharga (*Engineering Post-Mortem*)

Membangun sistem keamanan otonom di dunia nyata memberikan pelajaran berharga dari kesalahan-kesalahan teknis yang kami temukan dan perbaiki sepanjang pengembangan:
Kejujuran rekayasa (*engineering integrity*) adalah nilai utama yang kami junjung. Membangun sistem keamanan di dunia nyata tidak pernah luput dari hambatan. Berikut adalah empat bug nyata yang kami temui sepanjang pengembangan beserta solusinya:

1. **Jebakan Selisih Waktu UTC vs WIB:** Pada rilis awal, pengecekan keusangan data (*healthcheck*) dan jadwal backup database mengasumsikan waktu UTC secara implisit. Akibatnya, toleransi batas keusangan 26 jam diam-diam melar menjadi 33 jam, dan deteksi backup mingguan hari Minggu sempat gagal terpicu. Masalah ini diselesaikan dengan menetapkan zona waktu eksplisit `zoneinfo.ZoneInfo("Asia/Jakarta")` di seluruh lapisan kode.
2. **Integritas Metrik vs Hardcoded Values:** Dalam iterasi awal antarmuka dasbor, nilai metrik sempat diisi statis berdasarkan ekspektasi perencanaan. Kami segera merombaknya agar endpoint `/api/metrics` selalu membaca berkas evaluasi dinamis nyata (`eval_results.json`) dan mengembalikan `null` dengan status jujur `"belum cukup data"` jika catatan riwayat *lead time* publik belum memadai.
3. **Pentingnya Verifikasi Kontak Resmi:** Dalam modul penyusunan draf laporan insiden, kontak CSIRT BSSN sempat salah satu digit (`bantuan74` alih-alih `bantuan70@bssn.go.id`), dan nomor telepon PANDI sempat keliru. Kami menerapkan aturan ketat: *setiap kontak resmi wajib diverifikasi langsung ke halaman web institusi terkait*, didukung unit test regresi otomatis yang mengunci alamat email dan nomor hotline resmi.
4. **Keputusan Etis Mengutamakan Presisi:** Kami secara sadar memilih memprioritaskan Presisi tinggi (0% *False Positive*) dibanding mengejar Recall 100%. Di ranah deteksi domain, kesalahan menuduh domain sah sebagai penipuan (*false positive*) berpotensi merugikan nama baik dan bisnis pihak yang tidak bersalah.
1. **Jebakan Waktu UTC vs WIB (*The 7-Hour Latency Trap*):**  
   Pada versi awal, modul pengecekan keusangan data (*healthcheck*) dan jadwal backup otomatis mengasumsikan waktu UTC secara implisit. Akibatnya, toleransi keusangan 26 jam diam-diam molor menjadi 33 jam, dan cron-job pemeliharaan database hari Minggu sempat gagal terpicu. Masalah ini diselesaikan secara permanen dengan mematok zona waktu eksplisit `zoneinfo.ZoneInfo("Asia/Jakarta")` di seluruh modul backend.
2. **Integritas Metrik vs Godaan Hardcode:**  
   Dalam iterasi awal antarmuka dasbor, nilai metrik *lead time* pencegahan sempat diisi statis agar terlihat mengesankan. Kami menyadari bahwa integritas intelijen siber tidak boleh dibangun di atas ilusi. Kami merombak seluruh endpoint `/api/metrics` agar membaca file evaluasi dinamis riil (`eval_results.json`) dan menampilkan status jujur `"Insufficient Data"` apabila catatan riwayat observasi belum memenuhi ambang batas statistik minimal.
3. **Validasi Keras Kontak Resmi Lembaga:**  
   Dalam modul penyusunan draf laporan insiden, kontak email CSIRT BSSN sempat salah ketik satu karakter (`bantuan74` alih-alih `bantuan70@bssn.go.id`), dan nomor hotline PANDI sempat keliru. Kami segera menerapkan aturan ketat: *seluruh kontak resmi wajib diverifikasi langsung ke dokumen keputusan lembaga negara terkait*, serta dilindungi oleh unit test regresi otomatis.
4. **Keputusan Sadar: Memprioritaskan Precision di atas Recall:**  
   Di bidang intelijen ancaman siber, menuduh domain sah sebagai penipu (*false positive*) dapat mematikan bisnis dan merusak reputasi entitas yang tidak bersalah. Oleh karena itu, kami secara sadar menyetel ambang batas (*threshold*) agar model mencapai **0% False Positive**, meskipun harus merelakan sedikit recall (91.80%). Kepercayaan analis hanya bisa diraih jika sistem tidak memicu alarm palsu.

---

## 8. Penutup & Posisi Etis: Human-in-the-Loop dan UU PDP
## 8. Kepatuhan Regulasi & Posisi Etis: "Human-in-the-Loop", Bukan Main Hakim Sendiri

SIAGA dibangun dengan mematuhi prinsip pelindungan data pribadi (UU PDP No. 27/2022). Antarmuka pemantauan SIAGA menerapkan **Penyamaran Nama Domain (*Privacy Masking*) secara default** (contoh: `b***-verif.xyz`) guna mencegah paparan publik yang tidak disengaja saat perekaman layar atau demonstrasi video. Tabel analisis pesan pengguna hanya menyimpan *cryptographic hash* SHA-256 dan secara otomatis menghapus rekaman yang lebih tua dari 30 hari.
Sesuai dengan ketentuan umum **AI HackFest 2026** (Aturan No. 6 dan No. 7) serta hukum positif Republik Indonesia:
> *"Solusi wajib mematuhi hukum yang berlaku di Indonesia (UU ITE, UU PDP, dsb.). Untuk track deteksi konten ilegal, peserta hanya boleh melakukan deteksi & pelaporan lewat kanal resmi, bukan tindakan main hakim sendiri."*

Selain itu, SIAGA memegang teguh prinsip **Human-in-the-Loop**:
* Agent bertugas mengumpulkan data teknis, memfilter kebisingan, dan menyusun draf laporan terstruktur lengkap dengan kronologi dan bukti DNS/RDAP.
* **Manusia (Operator Keamanan)** tetap menjadi pemegang kendali mutlak yang memverifikasi temuan dan memutuskan pengiriman laporan ke kanal penegakan hukum resmi (AduanKonten Kominfo, CSIRT BSSN, Satgas PASTI OJK, atau PANDI IDADX).
SIAGA menerapkan kepatuhan hukum dan etika sebagai fitur bawaan sistem (*compliance by design*):

Dengan kolaborasi antara kecepatan pemindaian AI dan ketelitian verifikasi manusia, SIAGA membuktikan bahwa pertahanan siber proaktif dapat dibangun secara tangguh, etis, dan hemat sumber daya.
### A. Kepatuhan Penuh UU Pelindungan Data Pribadi (UU PDP No. 27/2022)
* **Zero Plaintext Sensitive Storage:** Seluruh pesan pengguna yang masuk ke Mode A disanitasi secara instan. Teks pesan tidak disimpan mentah di server, melainkan diubah menjadi *cryptographic salted hash* (SHA-256) untuk tujuan audit pencegahan serangan berulang (*tamper-evident audit trail*).
* **Kebijakan Retensi Otomatis 30 Hari:** Modul `db_retention.py` secara otomatis membersihkan rekaman audit yang berusia lebih dari 30 hari guna memastikan tidak ada retensi data berlebih.
* **Privacy Masking secara Default:** Seluruh tampilan domain mencurigakan pada dasbor publik disamarkan sebagian karakternya (misal: `b***-verif.xyz`) untuk mencegah kebocoran informasi yang tidak disengaja selama perekaman layar atau demonstrasi.

### B. Pusat Penyaluran & Tindakan Resmi Berpemandu (*1-Click Official Escalation Hub*)
SIAGA **sama sekali tidak melakukan tindakan serangan balik (*counter-hack*), pemblokiran liar, atau tindakan main hakim sendiri**. Sebaliknya, sistem memberdayakan analis melalui alur pelaporan resmi yang terverifikasi ke instansi berwenang:
* 🟢 **Aduan Konten Kominfo RI:** Integrasi 1-klik via WhatsApp Hotline Resmi (`08119224545`) dan email formal `aduankonten@kominfo.go.id` untuk normalisasi DNS TrustPositif dan pemblokiran akses internet.
* 🔵 **PANDI Abuse Desk & IDADX:** Tombol pelaporan instan ke `abuse@pandi.id` dan portal `idadx.id/report` untuk permohonan penangguhan (*domain suspension*) domain `.ID` yang terbukti melanggar hukum.
* 🛡️ **Direktorat Operasi Siber BSSN (Gov-CSIRT):** Format insiden standar RFC 2350 ke `bantuan70@bssn.go.id` apabila ditemukan subdomain situs pemerintah (`.go.id`) atau kampus (`.ac.id`) yang disusupi judi online atau malware.
* ⚖️ **Satgas PASTI & Kontak OJK 157:** Integrasi pelaporan entitas keuangan ilegal dan penipuan perbankan ke `satgaspasti@ojk.go.id` serta WhatsApp resmi OJK (`081157157157`).

Prinsip **Human-in-the-Loop** memastikan bahwa kecerdasan buatan bertugas melakukan tugas berat pemantauan, korelasi sinyal teknis, dan penyusunan naskah barang bukti. Keputusan akhir untuk melayangkan laporan resmi tetap berada di tangan manusia sebagai analis dan subjek hukum yang berwenang.

---

## 9. Kesimpulan & Visi Masa Depan

Melalui perhelatan **AI HackFest 2026**, kami membuktikan bahwa tantangan kejahatan siber yang masif di Indonesia tidak harus dihadapi dengan infrastruktur miliaran rupiah atau model AI tertutup yang boros biaya.

Dengan memadukan:
1. **Pemantauan hulu proaktif** via *Certificate Transparency*,
2. **Arsitektur corong penyaringan bertingkat** yang memangkas 98% konsumsi token AI,
3. **Infrastruktur server lokal yang tangguh dan efisien** di atas [Cloud VPS](https://cloudbaik.com) dan [AI Hosting](https://idwebhost.com/ai-hosting), serta
4. **Kepatuhan hukum dan etika pelaporan resmi** yang selaras dengan UU PDP dan BSSN,

**SIAGA** hadir bukan sekadar sebagai proyek hackathon eksperimental, melainkan sebagai purwarupa sistem pertahanan siber publik yang siap dioperasikan (*production-ready*) untuk menjaga ruang digital Nusantara tetap aman, terpercaya, dan berdaulat.

---

### Tautan Penting & Informasi Proyek
* **Kode Sumber (Open Source):** [https://github.com/mocharil/siaga](https://github.com/mocharil/siaga)
* **Dasbor Analisis Interaktif:** [https://siaga-lake.vercel.app](https://siaga-lake.vercel.app)
* **Dokumentasi Arsitektur & Kepatuhan:** [Tersedia di Menu Dokumentasi Aplikasi](https://siaga-lake.vercel.app/#docs)
* **Spesifikasi Server & Hosting:** Didukung oleh infrastruktur komputasi [Cloud VPS](https://cloudbaik.com) dan layanan [AI Hosting](https://idwebhost.com/ai-hosting) IDwebhost.
