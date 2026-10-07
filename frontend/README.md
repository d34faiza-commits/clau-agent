# Frontend (Next.js) — UI v2 Enterprise (pratinjau)

Pratinjau platform **CLAU · Bali AI Content Studio** mengikuti [`docs/design/2026-10-07-enterprise-ui-brief.txt`](../docs/design/2026-10-07-enterprise-ui-brief.txt). Belum ada login, database, atau koneksi ke backend AI.

## Versi UI

| Versi | Branch | Ringkasan |
|---|---|---|
| v1 "Pasir" | `ui-v1-pasir` | Palet brand CLAU: Pasir ±60% latar, Arang ±20% teks, Teal Laut ±10% aksen, Terracotta 3–5% highlight. Karakter ilustrasi per agent. **Disimpan** atas permintaan Dea Karisna (2026-10-07) |
| v2 "Enterprise" | `ui-v2-enterprise` | Navy + Deep Teal + putih + slate, sidebar, dashboard SaaS, agent pakai monogram (tanpa kartun) |

## Halaman

| Route | Isi |
|---|---|
| `/` | Dashboard: KPI, proyek, perlu tindakan, aktivitas agent, jadwal tayang |
| `/clients`, `/clients/<id>` | Daftar klien & profil (info bisnis, brand voice, akun sosial, riwayat konten) |
| `/projects` | Proyek per klien dengan progres |
| `/content` | Tab status (Draft → Tayang), tabel konten, modal **Buat konten** (tombol generate nonaktif sampai backend AI ada) |
| `/calendar` | Kalender bulan dengan status semantik |
| `/agents`, `/agents/<id>` | Kartu agent (monogram, status, level) & profil dari `../agents/personas/<id>.md` |
| `/workflows` | Alur brief → agent → cek otomatis → review manusia → publish oleh manusia |
| `/reports` | Produksi konten; engagement **tidak** ditampilkan sampai data platform asli tersedia |
| `/settings` | Workspace & integrasi (read-only) |

## Data

- `lib/team.ts`: nama, peran, fokus agent (registry tetap sumber daftar agent).
- `lib/demo.ts`: **DATA SIMULASI**. Nama properti fiktif mengandung "Contoh"; setiap halaman yang memakainya menampilkan label SIMULASI.

## Design system

- Token warna di `app/globals.css` (`:root`, brief §31). Ganti tema cukup di sana.
- Font Inter. Ikon garis gaya Lucide di `components/Icon.tsx` (tanpa dependency tambahan).
- Status: warna semantik + label teks (tidak mengandalkan warna saja).

## Jalankan

```bash
npm ci
npm run dev        # http://localhost:3000
npm run build
```

## Keputusan yang masih terbuka

- `ASSUMPTION`: nama produk "Bali AI Content Studio" (brief) vs "CLAU Content Studio" (brand-guideline). Di UI: wordmark **CLAU** + deskriptor **Bali AI Content Studio**.
- `ASSUMPTION`: palet navy/slate (brief) berbeda dari token brand (stone/pasir). Perlu keputusan Pak Indra/Dea sebelum brand-guideline diubah.
- Nama agent (Tara, Raka, …) masih draft.

## Batas

UI tidak boleh punya tombol yang langsung publish ke platform sosial/OTA atau mengirim pesan ke tamu (`core/AI-CONSTITUTION.md` §4).
