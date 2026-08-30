# SIAGA Security Monitoring Dashboard

Dashboard pemantauan harian dan visualisasi intelijen ancaman phishing SIAGA (**AI HackFest 2026**).

---

## 1. Arsitektur & Prinsip Keamanan (Local-First / Zero-Attack Surface)

* **Strict Read-Only:** Koneksi SQLite dibuka secara eksklusif dalam mode read-only (`file:data/siaga.db?mode=ro`). Seluruh request `POST`, `PUT`, `PATCH`, dan `DELETE` ditolak langsung dengan `HTTP 405 Method Not Allowed`.
* **Zero External Dependencies:** Antarmuka dibangun dengan vanilla HTML/CSS/JS dan SVG inline rendering. Tidak ada ketergantungan CDN eksternal (100% offline-ready & andal saat demo/video).
* **Privacy Masking by Default:** Domain temuan disamarkan secara otomatis di UI (contoh: `p***.web.id`) sesuai prinsip kepatuhan UU PDP dan `plan/06` untuk melindungi nama baik pihak yang dicatut.
* **Low Memory Footprint:** Mengonsumsi RAM hanya ~50–60 MB (jauh di bawah batas anggaran VPS 200 MB).

---

## 2. Cara Menjalankan

### Di Lingkungan Lokal (Windows PowerShell):
```powershell
.\dashboard\run.ps1
```

### Di Lingkungan Linux / VPS (Bash):
```bash
./dashboard/run.sh
```

Buka peramban di: **`http://127.0.0.1:8000`**

---

## 3. Catatan Hardening Deploy VPS (Checklist T09)

> [!CAUTION]
> **JANGAN PERNAH** mem-bind atau mengekspos port 8000 ke `0.0.0.0` atau IP publik VPS.

Untuk mengakses dashboard di VPS secara aman:
1. Pastikan dashboard hanya listen pada `127.0.0.1:8000`.
2. Gunakan **SSH Port Forwarding / Tunnel** dari mesin lokal Anda:
   ```bash
   ssh -N -L 8000:127.0.0.1:8000 user@vps-ip -i ~/.ssh/id_ed25519
   ```
3. Buka peramban lokal di `http://localhost:8000`.
