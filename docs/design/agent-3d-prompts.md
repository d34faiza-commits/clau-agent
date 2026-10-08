# Paket Prompt Karakter 3D — Tim AI CLAU

> Untuk membuat gambar 3D 15 karakter agent dengan **AI image generator gratis**. Keputusan Dea Karisna (2026-10-08): busana adat **sehari-hari** staf hospitality, gaya 3D seperti contoh Sintra, **tanpa** busana upacara.

## 1. Alat gratis yang disarankan

| Alat | Cara | Catatan |
|---|---|---|
| **Google Gemini** ⭐ | gemini.google.com → tulis prompt (atau minta "Create an image: …") | Sudah dipakai kakak. Bisa **unggah gambar referensi** agar gaya konsisten. Ada batas harian di akun gratis |
| Microsoft Designer / Bing Image Creator | designer.microsoft.com → Image creator | Kredit gratis harian |
| Leonardo.ai | leonardo.ai → Image Generation | Token gratis harian; gambar akun gratis bisa tampil publik |

`RISK`: syarat pakai komersial berbeda tiap alat dan bisa berubah. **Baca syarat layanan alat yang dipakai** sebelum gambar dipakai untuk klien berbayar.

## 2. Cara kerja agar 15 karakter terlihat satu keluarga

1. Buat **Tara dulu** dengan prompt di bawah. Ulangi sampai dapat yang paling bagus.
2. Untuk karakter berikutnya, **unggah gambar Tara** sebagai referensi lalu tambahkan kalimat pembuka: *"Same 3D style, lighting, proportions and background as the attached image, but a different character:"* lalu tempel prompt karakter.
3. Generate 2–4 kali per karakter, pilih yang paling mirip gayanya dengan Tara.
4. Simpan **persegi (1:1)**, minimal 1024×1024, PNG atau WebP.
5. Beri nama file **huruf kecil sesuai nama**: `tara.png`, `raka.png`, … lalu kirim ke chat. Aku yang pasang ke `frontend/public/agents/`.

Gambar yang belum ada otomatis memakai karakter SVG, jadi bisa dikirim bertahap.

## 3. Gaya dasar (tempel di AWAL setiap prompt)

```text
3D animated character render in a polished Pixar-like style, cute chibi proportions (large head, small body),
soft clay-like materials, smooth skin with gentle subsurface scattering, soft studio lighting, subtle soft shadow
under the feet, full body, standing straight, facing the camera, centered, the whole figure visible with space
around it. Plain smooth background, soft mint (#CCFBF1) fading to white, no scenery. A friendly, calm, professional
Indonesian hospitality staff member with a warm natural smile.
```

## 4. Larangan (tempel di AKHIR setiap prompt)

```text
No text, no letters, no logo, no watermark. No crown, no headdress, no flower crown, no feathers, no face paint,
no temple, no religious symbols, no ceremonial costume. Not a real person. Modest everyday clothing.
```

Label "AI" tidak perlu di gambar: UI sudah menampilkan label "Agent AI" dan status di kartu.

## 5. Prompt per karakter (tempel di TENGAH)

| File | Agent | Prompt karakter |
|---|---|---|
| `tara.png` | Tara · AI Copywriter | Young Indonesian woman, light-tan skin, black shoulder-length bob with bangs. Wears a light mint kebaya kutubaru with a deep teal center panel and three small gold brooches, and a brown batik wrap skirt with a simple geometric pattern. Holds an orange pencil in her right hand. |
| `raka.png` | Raka · AI Reels Strategist | Young Balinese man, warm brown skin, short black hair. Wears a navy batik udeng headband (everyday Balinese head cloth), a clean white short-sleeve shirt, a deep teal waist sash and an indigo batik kamen wrap. Holds a small film clapperboard. |
| `sekar.png` | Sekar · AI Stories Specialist | Young Indonesian woman, light skin, brown hair in a neat bun. Wears a cream lace kebaya with a teal selendang sash across the body and a teal batik wrap skirt. Holds a smartphone showing a colorful story screen. |
| `bayu.png` | Bayu · AI Listing Specialist | Young Indonesian man, tan skin, dark side-swept hair, round glasses. Wears a navy long-sleeve batik shirt with a small geometric pattern and dark trousers. Holds a tablet showing a small house icon. |
| `laras.png` | Laras · AI Review Specialist | Young Indonesian woman, warm brown skin, wearing a deep teal hijab and a light mint kebaya with a teal sash and a brown batik wrap skirt. Wears a light headset with a small microphone. Holds a white speech bubble card with three dots. |
| `dimas.png` | Dimas · AI Content Planner | Young Javanese man, light skin, curly black hair partly under a brown batik blangkon cap. Wears a brown sogan batik shirt and dark trousers. Holds a small desk calendar. |
| `ayu.png` | Ayu · AI Campaign Strategist | Young Indonesian woman, tan skin, long straight brown hair. Wears a soft lavender kebaya kutubaru with a violet center panel and gold brooches, and an indigo batik wrap skirt. Holds a white megaphone. |
| `nara.png` | Nara · AI Localization Specialist | Young Indonesian man, deep brown skin, curly black hair, round glasses. Wears a navy beskap jacket with small gold buttons and a brown batik jarik wrap. Holds a small globe. |
| `galih.png` | Galih · AI Insights Analyst | Young Indonesian man, tan skin, short dark hair, round glasses. Wears a dark teal long-sleeve batik shirt and dark trousers. Holds a small white board with a rising bar chart. |
| `intan.png` | Intan · AI Reservations Assistant | Young Indonesian woman, light skin, long straight black hair. Wears a pale grey-blue kebaya with a navy sash and an indigo batik wrap skirt, and a light headset. Holds a key card. |
| `sari.png` | Sari · AI Guest Messaging Specialist | Young Indonesian woman, warm brown skin, wearing a terracotta-brown hijab, a cream kebaya with a terracotta sash and a brown batik wrap skirt. Holds a small brass hotel reception bell. |
| `teguh.png` | Teguh · AI SOP Specialist | Indonesian man, deep brown skin, dark side-swept hair, wearing a brown batik udeng headband, a white short-sleeve shirt, a dark teal waist sash and a brown batik kamen wrap. Holds a clipboard with a checklist. |
| `nova.png` | Nova · AI Brand Strategist (konsep) | Young Indonesian woman, light skin, black bob, round glasses. Wears a pale grey-blue kebaya kutubaru with a navy center panel and a teal batik wrap skirt. Holds a small board with a chart. |
| `aruna.png` | Aruna · AI Visual Director (konsep) | Young Indonesian woman, tan skin, long black hair. Wears a cream kebaya with a teal sash and a brown batik wrap skirt. Holds a smartphone. |
| `dara.png` | Dara · AI Quality Controller (konsep) | Young Indonesian woman, warm brown skin, dark hair in a bun. Wears a light mint kebaya kutubaru with a dark teal center panel and an indigo batik wrap skirt. Holds a clipboard with check marks. |

## 6. Contoh prompt lengkap (Tara)

```text
3D animated character render in a polished Pixar-like style, cute chibi proportions (large head, small body),
soft clay-like materials, smooth skin with gentle subsurface scattering, soft studio lighting, subtle soft shadow
under the feet, full body, standing straight, facing the camera, centered, the whole figure visible with space
around it. Plain smooth background, soft mint (#CCFBF1) fading to white, no scenery. A friendly, calm, professional
Indonesian hospitality staff member with a warm natural smile.
Young Indonesian woman, light-tan skin, black shoulder-length bob with bangs. Wears a light mint kebaya kutubaru
with a deep teal center panel and three small gold brooches, and a brown batik wrap skirt with a simple geometric
pattern. Holds an orange pencil in her right hand.
No text, no letters, no logo, no watermark. No crown, no headdress, no flower crown, no feathers, no face paint,
no temple, no religious symbols, no ceremonial costume. Not a real person. Modest everyday clothing.
```

## 7. Cek sebelum kirim

- [ ] Badan penuh, menghadap depan, latar polos mint/putih
- [ ] Tidak ada teks/logo/huruf aneh di gambar
- [ ] Busana sesuai tabel; tidak ada mahkota, bulu, cat wajah, pura
- [ ] Wajah tidak mirip orang terkenal/orang nyata
- [ ] Gaya sama dengan Tara (cahaya, proporsi, latar)
