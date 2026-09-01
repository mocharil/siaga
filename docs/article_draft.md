# SIAGA: Membangun Agent Otonom Pemantau Phishing Berbasis Certificate Transparency dan Arsitektur Hemat Token

> **Artikel Publikasi Resmi — AI HackFest 2026 (IDwebhost × PANDI)**  
> **Kategori:** Digital Safety & Public Good  
> **Framework:** OpenClaw AI  
> **Repositori Kode:** [GitHub: IDwebhost / SIAGA Phishing Intelligence](https://github.com/idwebhost-pandi/siaga)  
> **Data Operasional:** Snapshot per 01 September 2026 (Operasional Aktif 5 Hari)

---

## 1. Pembuka: Jebakan 24 Jam Pertama

Di sebuah grup percakapan keluarga, sebuah pesan singkat beredar: *"Peringatan dari bank Anda: tarif transfer bulanan akan disesuaikan menjadi Rp 150.000. Batalkan segera melalui tautan berikut."* Tautan tersebut mengarah ke sebuah domain yang sekilas tampak meyakinkan: `bca-tarifpenyesuaian[.]online`. 

Bagi pengguna awam yang panik, situs tersebut tampak identik dengan portal perbankan resmi. Namun di balik antarmuka yang rapi itu, sebuah formulir tersembunyi dirancang khusus untuk memanen nomor kartu debit, PIN, dan kode OTP korban. Ketika korban menyadari saldo rekeningnya terkuras, situs tersebut sudah berganti alamat atau bahkan telah dimatikan oleh pelakunya.

Kejahatan siber berbasis *social engineering* dan penipuan digital di Indonesia tidak lagi mengandalkan domain acak yang mudah dicurigai. Pelaku kini memanfaatkan domain tingkat tinggi murah (.xyz, .online, .top, .site) yang dikombinasikan dengan teknik peniruan identitas (*brand impersonation*) institusi terpercaya. Pertanyaannya: mengapa sistem keamanan konvensional kerap terlambat menghentikannya?

---

## 2. Kenapa Verifikasi Itu Sulit?

Membedakan domain penipuan dari puluhan ribu pendaftaran domain baru setiap harinya merupakan tantangan teknis yang rumit karena tiga sinyal tersembunyi:

1. **Typosquatting & Directed Permutations:** Pelaku jarang membuat salah ketik acak. Mereka secara sengaja menyisipkan nama brand resmi sebagai subdomain (`bca.promo-khusus.xyz`) atau menambahkan kata kerja persuasif berpola tanda hubung (`klikbca-update`, `login-mandiri-verif`).
2. **Homoglyph & Punycode Normalization:** Penggunaan karakter Unicode visual serupa (misalnya huruf sirilik `а` yang menyerupai huruf latin `a` pada `xn--b-8sb.id`) sering kali mengelabui mata manusia dan pencocokan teks sederhana.
3. **Siklus Hidup Kilat (*Ephemeral Domains*):** Domain phishing modern sering kali didaftarkan, diberi sertifikat SSL, melancarkan kampanye penipuan selama 6 hingga 18 jam, lalu ditinggalkan sebelum sempat terindeks oleh vendor antivirus global.

---

## 3. Kenapa Perlu Agent, Bukan Sekadar Chatbot atau Blacklist?

Pendekatan keamanan konvensional memiliki kelemahan mendasar:
* **Blacklist Publik Pasif:** Basis data ancaman global (seperti URLhaus atau OpenPhish) memiliki waktu tunda (*lead time*) rata-rata 24 hingga 36 jam. Saat sebuah domain masuk ke daftar hitam publik, korban sudah berjatuhan.
* **Chatbot Generatif Pasif:** Menaruh LLM di depan pesan pengguna hanya membantu mereka yang sudah curiga dan bertanya. Korban yang paling rentan justru adalah mereka yang tidak sadar sedang ditipu.

Di sinilah **SIAGA** hadir sebagai **Agent Otonom Proaktif**. SIAGA tidak menunggu korban melapor. Ia secara mandiri memantau aliran sertifikat TLS global (*Certificate Transparency Log*) secara *real-time*, menyaring puluhan ribu domain baru, memvalidasi bukti teknis, menyintesis analisis risiko, dan mengelompokkan infrastruktur kampanye penipuan sebelum domain tersebut sempat menjaring korban massal.

---

## 4. Arsitektur Penyaringan Bertingkat (Cascading Funnel)

Memproses 10.000 hingga 30.000 domain baru setiap hari langsung menggunakan model bahasa besar (LLM) adalah pemborosan biaya token dan komputasi yang tidak realistis. SIAGA merancang **Pipeline Penyaringan 3-Tahap (Cascading Funnel)** dari yang paling murah ke yang paling analitis:

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
```

Dengan arsitektur ini, konsumsi token LLM terpangkas hingga **98%**, memungkinkan operasional intelijen ancaman berdaya guna tinggi dengan biaya minimal di atas infrastruktur server [Cloud VPS](https://cloudbaik.com).

Kode sumber lengkap, skema basis data SQLite terisolasi, dan modul evaluasi model SIAGA tersedia secara terbuka pada repositori GitHub resmi kami di:  
👉 **[GitHub: IDwebhost / SIAGA Phishing Intelligence](https://github.com/idwebhost-pandi/siaga)**.

---

## 5. Menjalankannya di Lingkungan Server: Efisiensi & Hardening

Sebagai agen yang dirancang untuk beroperasi tanpa henti (24/7), SIAGA dibangun dengan prinsip *Local-First* dan *Zero-Attack Surface*:

1. **Hardening Sistem Operasi:** Akses server dikonfigurasi secara ketat hanya menggunakan otentikasi SSH berbasis kunci privat (*Key-Only*), menonaktifkan login `root` langsung, mengaktifkan pembaruan keamanan otomatis (*unattended-upgrades*), dan membatasi firewall UFW. Port monitoring internal (FastAPI Dashboard dan OpenClaw Gateway) dikonfigurasi eksklusif pada `127.0.0.1` dan hanya dapat diakses melalui SSH Tunnel.
2. **Efisiensi Sumber Daya:** Berkat optimasi komputasi string Damerau-Levenshtein dan arsitektur SQLite *Write-Ahead Logging* (WAL), proses background SIAGA hanya mengonsumsi **31.9 MB RAM** untuk API Dashboard dan ~131.5 MB untuk gateway OpenClaw dengan utilisasi CPU di bawah 5%.
3. **Keandalan Hosting Mandiri:** Seluruh pipeline, pelacakan redirect HTTP HEAD-only, dan antarmuka visualisasi tanpa pustaka CDN eksternal dapat di-hosting secara mandiri pada platform [AI Hosting](https://idwebhost.com/ai-hosting/) dengan jaminan uptime maksimal dan isolasi data penuh.

---

## 6. Hasil Pengujian & Evaluasi Nyata

Evaluasi sistem dilakukan menggunakan dataset uji 120 sampel terverifikasi (*ground-truth test set*) yang merepresentasikan spektrum ancaman nyata di Indonesia:

* **Model Precision:** **100.00%** (56/56, 0 *False Positive* pada sampel legitimasi institusi resmi dan pesan ambigu).
* **Model Recall:** **91.80%** (56 dari 61 varian serangan phishing berbobot berhasil diidentifikasi).
* **F1-Score:** **0.9573** (Melampaui target batas kelulusan kompetisi ≥ 0.8200).
* **False Positive Rate (FPR):** **0.00%** (Di bawah ambang toleransi ≤ 10.0%).
* **Akurasi Keseluruhan:** **95.83%**.
* **Kecepatan Analisis:** Waktu pemrosesan pindaian awal dioptimalkan hingga **1.51 ms/domain**, memungkinkan penyaringan 10.000 domain harian selesai dalam hitungan menit di CPU lokal.

### Rekapitulasi Data Operasional Nyata (5 Hari Operasi):
* **Total Domain Mentah Dipindai (`ct_raw`):** **47.664 domain**
* **Total Temuan Terindikasi (`domain_findings`):** **546 temuan**
* **Klaster Infrastruktur Terpetakan:** **55 klaster kampanye penipuan**
* **Top 3 Brand Paling Banyak Ditiru:** Ruangguru (61 domain), Investree (38 domain), Paxel (32 domain).

---

## 7. Kegagalan Nyata, Bug yang Ditemukan, dan Pelajaran Berharga

Membangun sistem keamanan otonom di dunia nyata memberikan pelajaran berharga dari kesalahan-kesalahan teknis yang kami temukan dan perbaiki sepanjang pengembangan:

1. **Jebakan Selisih Waktu UTC vs WIB:** Pada rilis awal, pengecekan keusangan data (*healthcheck*) dan jadwal backup database mengasumsikan waktu UTC secara implisit. Akibatnya, toleransi batas keusangan 26 jam diam-diam melar menjadi 33 jam, dan deteksi backup mingguan hari Minggu sempat gagal terpicu. Masalah ini diselesaikan dengan menetapkan zona waktu eksplisit `zoneinfo.ZoneInfo("Asia/Jakarta")` di seluruh lapisan kode.
2. **Integritas Metrik vs Hardcoded Values:** Dalam iterasi awal antarmuka dasbor, nilai metrik sempat diisi statis berdasarkan ekspektasi perencanaan. Kami segera merombaknya agar endpoint `/api/metrics` selalu membaca berkas evaluasi dinamis nyata (`eval_results.json`) dan mengembalikan `null` dengan status jujur `"belum cukup data"` jika catatan riwayat *lead time* publik belum memadai.
3. **Pentingnya Verifikasi Kontak Resmi:** Dalam modul penyusunan draf laporan insiden, kontak CSIRT BSSN sempat salah satu digit (`bantuan74` alih-alih `bantuan70@bssn.go.id`), dan nomor telepon PANDI sempat keliru. Kami menerapkan aturan ketat: *setiap kontak resmi wajib diverifikasi langsung ke halaman web institusi terkait*, didukung unit test regresi otomatis yang mengunci alamat email dan nomor hotline resmi.
4. **Keputusan Etis Mengutamakan Presisi:** Kami secara sadar memilih memprioritaskan Presisi tinggi (0% *False Positive*) dibanding mengejar Recall 100%. Di ranah deteksi domain, kesalahan menuduh domain sah sebagai penipuan (*false positive*) berpotensi merugikan nama baik dan bisnis pihak yang tidak bersalah.

---

## 8. Penutup & Posisi Etis: Human-in-the-Loop dan UU PDP

SIAGA dibangun dengan mematuhi prinsip pelindungan data pribadi (UU PDP No. 27/2022). Antarmuka pemantauan SIAGA menerapkan **Penyamaran Nama Domain (*Privacy Masking*) secara default** (contoh: `b***-verif.xyz`) guna mencegah paparan publik yang tidak disengaja saat perekaman layar atau demonstrasi video. Tabel analisis pesan pengguna hanya menyimpan *cryptographic hash* SHA-256 dan secara otomatis menghapus rekaman yang lebih tua dari 30 hari.

Selain itu, SIAGA memegang teguh prinsip **Human-in-the-Loop**:
* Agent bertugas mengumpulkan data teknis, memfilter kebisingan, dan menyusun draf laporan terstruktur lengkap dengan kronologi dan bukti DNS/RDAP.
* **Manusia (Operator Keamanan)** tetap menjadi pemegang kendali mutlak yang memverifikasi temuan dan memutuskan pengiriman laporan ke kanal penegakan hukum resmi (AduanKonten Kominfo, CSIRT BSSN, Satgas PASTI OJK, atau PANDI IDADX).

Dengan kolaborasi antara kecepatan pemindaian AI dan ketelitian verifikasi manusia, SIAGA membuktikan bahwa pertahanan siber proaktif dapat dibangun secara tangguh, etis, dan hemat sumber daya.
