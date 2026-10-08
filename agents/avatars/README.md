# Avatar 3D Agent

Figur 3D (gaya figurine chibi, latar mint `#DDF4EE`) untuk 12 agent di `registry.json`. Dibuat dengan image generator dari paket prompt CLAU, dikirim owner pada 2026-10-08.

| Lokasi | Isi |
|---|---|
| `agents/avatars/<id>.webp` | Master 1248×832 (seluruh badan) |
| `frontend/public/agents/<id>.webp` | Crop kepala & bahu 256×256, dipakai komponen `Avatar` |

Agent konsep (belum ada di registry) tetap memakai karakter SVG (`frontend/components/Character.tsx`).

## Aturan

- Karakter fiktif; tidak meniru wajah staf atau orang nyata.
- UI tetap menandai bahwa ini agent AI (role "AI …", persona README prinsip 1).
- Batik hanya sebagai pakaian; tanpa simbol sakral (brand-guideline §6–7).
- Ganti gambar = ganti master + crop dengan nama file yang sama (`<id>.webp`).

## Status per gambar

> 2026-10-08: gambar report-builder (Galih) dan sales-assistant (Intan) ditukar (permintaan di sesi Claude 2026-10-08) agar sesuai nama. Akibatnya alat yang dipegang tidak sesuai peran: Galih (laporan) memegang buku reservasi & key card, Intan (reservasi) memegang tablet grafik.

| Agent | Status | Catatan |
|---|---|---|
| caption-writer, reel-scripter, story-writer, listing-writer, review-responder, calendar-planner, campaign-planner, localizer, report-builder, sales-assistant | `ASSUMPTION` | Diterima di sesi 2026-10-08; menunggu konfirmasi Pak Indra / Dea Karisna saat review PR |
| guest-messenger | `NEXT ACTION` | Layar HP memuat teks "How can help?" (salah grammar); generate ulang tanpa teks |
| sop-writer | `NEXT ACTION` | Proporsi kepala lebih kecil dari 11 figur lain |

Prompt dasar yang dipakai:

```
3D chibi vinyl figurine character, Pixar-style, soft matte clay and fabric materials,
big head small body proportions, large warm brown eyes, gentle closed-mouth smile,
rosy cheeks, Indonesian appearance, full body standing, front view, centered,
plain soft mint background (#DDF4EE) with subtle floor shadow, soft studio lighting,
high detail, clean, friendly, professional. No text, no letters, no logo, no watermark.
```
