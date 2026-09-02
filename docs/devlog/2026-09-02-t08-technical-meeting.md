# T08 — Technical Meeting: 4 Jawaban Wajib

> Dicatat 2 September 2026, berdasarkan keterangan langsung dari peserta (Aril) yang hadir di
> technical meeting. Bukan hasil investigasi/asumsi asisten — empat jawaban di bawah adalah apa
> yang disampaikan panitia, dikonfirmasi ulang lewat pengecekan config VPS nyata di poin 1.

## 1. Model AI default: apa, kuotanya berapa, cara aksesnya bagaimana?

Panitia **tidak menyebutkan secara eksplisit** nama atau angka kuota model default di sesi
technical meeting. Dicek langsung dari config OpenClaw yang sudah aktif di VPS:

- Model: `9router/oc/hy3-free`
- Provider: `9router` (`https://9router.jcamp.io/v1`)
- Biaya: $0 di semua sisi (input, output, cache read, cache write) — gratis
- Context window: 200.000 token · maxTokens per respons: 8.192
- **Kuota harian/bulanan: tidak terlihat di config, tidak diumumkan panitia.** Diasumsikan
  best-effort/rate-limited di sisi provider tanpa angka pasti yang bisa dikutip.

Cara akses: sudah otomatis terkonfigurasi di `agents.defaults.model.primary` pada `openclaw.json`
VPS sejak instance diaktifkan — tidak perlu setup tambahan dari peserta.

**Panitia mengonfirmasi secara lisan bahwa peserta boleh memakai API/model sendiri di luar
default ini.** Proyek ini memanfaatkan izin tersebut: `lib/llm.py` (dipakai untuk Tahap 3 pipeline
dan Mode A) memakai provider terpisah (`api.justwoker.icu`, model `claude-opus-5`) yang dipilih
sendiri, bukan model default OpenClaw di atas. Keduanya independen — model default tetap dipakai
oleh agent OpenClaw untuk percakapan Telegram, sedangkan `lib/llm.py` khusus untuk skoring
otomatis dalam pipeline.

## 2. Kapan batch VPS aktif?

**Batch 1: 1-5 September 2026.** Video (footage/rekaman) harus selesai direkam sebelum **5
September**, karena VM akan dinonaktifkan panitia persis di tanggal itu (aturan resmi playbook,
bukan estimasi). Artikel dan proses editing/produksi video **boleh dikerjakan setelah VPS mati**
— yang tidak bisa ditunda adalah pengambilan footage yang butuh VPS hidup (dashboard, terminal SSH,
demo end-to-end).

**Implikasi perencanaan:** prioritas 3 hari tersisa (2-5 September) adalah merekam semua segmen
yang butuh VPS aktif — dashboard + terminal berdampingan, service `systemctl status`, demo bot
Telegram, backup/healthcheck — sebelum VM mati. Penulisan artikel, editing video, dan finalisasi
narasi bisa menyusul kapan saja setelahnya, karena tidak bergantung VPS tetap hidup.

## 3. "Favorite Project" ditentukan bagaimana?

**Pilihan juri.** Bukan voting publik atau metrik otomatis — murni penilaian subjektif juri di
luar skor teknis reguler.

## 4. Boleh menyertakan link repo GitHub di artikel?

**Ya, tidak ada ketentuan pembatas.** Tidak disebutkan syarat format/posisi tertentu selain yang
sudah ada di playbook (anchor "Cloud VPS" dan "AI Hosting" wajib, link repo di bagian arsitektur —
lihat `plan/10-build-runbook.md` T30).
