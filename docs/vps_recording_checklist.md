# Checklist Rekam VPS Sebelum Akses Hilang

> Akses VPS kompetisi berakhir sekitar 5 September. Deadline video & artikel: 30 September.
> Prinsip: rekam per-klip terpisah, tidak perlu satu take berurutan. Sisa waktu sampai 30 September dipakai untuk editing dan bagian yang tidak butuh VPS.
>
> **Urutan prioritas kalau waktu mepet**: Sesi 3 (demo end-to-end) → Sesi 5 (backup data) → Sesi 1 → Sesi 2 → Sesi 4.
> Sesi 3 dan 5 tidak boleh terlewat apa pun yang terjadi.

---

## Sesi 0 — Persiapan (5 menit)

- [ ] Terminal dengan font besar (minimal 16pt), kontras tinggi
- [ ] HP sudah login Telegram, chat dengan bot SIAGA sudah terbuka
- [ ] Screen recorder jalan, rekam per-klip terpisah
- [ ] Pastikan SSH ke VPS berhasil dulu sebelum mulai rekam apa pun:

```bash
ssh <user>@<IP_VPS> -p 4422
```

Kalau ini gagal (timeout/refused): **STOP** — selesaikan masalah akses dulu (cek panel IDwebhost / firewall), jangan lanjut checklist ini.

---

## Sesi 1 — Bukti Deployment & Keamanan

Narasi kunci: *"ini bukan localhost, ini server produksi nyata dengan port dikunci sesuai desain keamanan di CLAUDE.md"*

```bash
# 1.1 Bukti container jalan, sudah berapa lama uptime-nya
docker ps

# 1.2 Bukti image yang dipakai sesuai yang didaftarkan ke panitia
docker inspect openclaw-gateway --format '{{.Config.Image}}'

# 1.3 Bukti port publishing hanya ke loopback (bagian KRITIS di CLAUDE.md)
docker port openclaw-gateway
# harus terlihat: 18789/tcp -> 127.0.0.1:18789
```

- [ ] **Ganti ke terminal LAPTOP (bukan VPS)**, buktikan port 18789 tidak bisa diakses dari luar:

```bash
curl -v --max-time 5 http://<IP_VPS>:18789
# harus timeout / connection refused, BUKAN 200 OK
```

```bash
# kembali ke VPS: bukti collector jalan sebagai job terjadwal, bukan manual
crontab -l
# atau kalau pakai systemd timer:
systemctl list-timers | grep -i siaga
```

---

## Sesi 2 — Bukti Operasional Historis

Narasi kunci: *"collector sudah jalan sejak awal lomba tanpa henti"*

```bash
# 2.1 Histori ct_raw per hari sejak awal lomba — PALING PENTING DI SESI INI
sqlite3 data/siaga.db "SELECT date(first_seen), COUNT(*) FROM ct_raw GROUP BY 1 ORDER BY 1;"

# 2.2 Status tiap run collector (ok/partial/failed)
sqlite3 data/siaga.db "SELECT date(started_at), status, COUNT(*) FROM collector_runs GROUP BY 1,2 ORDER BY 1;"

# 2.3 Histori daily cycle via OpenClaw
openclaw cron list
openclaw cron runs --id <CRON_ID>   # isi CRON_ID dari output baris sebelumnya

# 2.4 Ringkasan temuan harian
sqlite3 data/siaga.db "SELECT date, domains_scanned, domains_flagged FROM daily_stats ORDER BY date;"
```

---

## Sesi 3 — Demo End-to-End Live (PALING PENTING, jangan sampai terlewat)

Narasi kunci: *"ini Mode A jalan langsung di server publik, bukan simulasi"*

- [ ] Buka log gateway real-time di satu jendela terminal:

```bash
docker logs -f openclaw-gateway --tail 20
```

- [ ] Di jendela/perangkat terpisah, kirim pesan contoh ke bot Telegram, misalnya:
  > "Halo, saya dapat SMS dari BCA minta klik link bca-update-tarif.online buat verifikasi rekening, ini asli bukan ya?"
- [ ] Rekam log terminal memproses pesan itu **real-time** (baris log baru muncul saat pesan masuk)
- [ ] Rekam balasan bot muncul di HP dengan skor risiko + penjelasan
- [ ] (Opsional, memperkuat) ulangi dengan contoh domain judol untuk menunjukkan kategori berbeda

---

## Sesi 4 — Resource Footprint

Narasi kunci: *"jalan ringan di spec kompetisi yang terbatas"*

```bash
free -h
df -h
docker stats --no-stream openclaw-gateway
```

---

## Sesi 5 — Backup Data (WAJIB, paling akhir sebelum logout terakhir)

Ini yang menyambung cerita setelah VPS mati — jangan sampai lupa.

```bash
# 5.1 Jalankan backup di VPS
cd ~/siaga   # sesuaikan path
python3 scripts/backup_db.py --db-path data/siaga.db --backup-dir backups --retention-days 7
ls -la backups/daily/
```

- [ ] Dari **laptop**, tarik hasil backup ke lokal:

```bash
scp -P 4422 <user>@<IP_VPS>:~/siaga/backups/daily/siaga_<TANGGAL>.db "C:\Users\Aril Indra Permana\AI_HACKFEST\siaga\data\siaga_vps_backup.db"
```

- [ ] Verifikasi file tidak korup **sebelum** memutus akses VPS untuk terakhir kali:

```bash
sqlite3 "C:\Users\Aril Indra Permana\AI_HACKFEST\siaga\data\siaga_vps_backup.db" "SELECT COUNT(*) FROM ct_raw;"
```

- [ ] Kalau angka masuk akal (bukan 0 / error) → aman, boleh logout dari VPS.
- [ ] Catat manual: tanggal terakhir data VPS berakhir (dari query 2.1) — dipakai nanti untuk menjelaskan transisi VPS → laptop di artikel dengan jujur, bukan disembunyikan.

---

## Setelah Semua Sesi Selesai

1. Gabungkan `siaga_vps_backup.db` dengan database lokal supaya dashboard walkthrough (rekaman non-VPS) menampilkan riwayat penuh tanpa bolong.
2. Pastikan `dashboard/static/app.js` sudah bersih dari live-feed palsu sebelum merekam walkthrough dashboard apa pun — kalau belum, rekaman akan menampilkan data karangan (lihat catatan terpisah soal ini).
3. Baru mulai rekam Bagian C (walkthrough dashboard, arsitektur, evaluasi, narasi) kapan saja sampai 30 September.
