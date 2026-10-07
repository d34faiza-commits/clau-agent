# Frontend (Next.js scaffold)

Platform "Tim AI": setiap agent di `../agents/registry.json` tampil sebagai karakter. Belum ada login, form request, atau koneksi ke backend.

| Halaman | Isi |
|---|---|
| `/` | Hero, carousel karakter, cara kerja (draft → manusia approve → manusia publish), tim per pilar |
| `/agents/<id>` | Profil agent: keahlian, untuk siapa, approval minimum, kapan berhenti & eskalasi (dibaca saat build dari `../agents/personas/<id>.md`) |

## Karakter

- Karakter **orisinal** CLAU, digambar sebagai SVG (`components/Character.tsx`), latar lanskap Nusantara (`components/Scene.tsx`). Tidak menyalin karakter/aset platform lain.
- Setiap karakter memakai badge **"AI"** di dada dan label "Agent AI": karakter adalah ilustrasi agent, **bukan** staf manusia (`../agents/personas/README.md` prinsip 1).
- Nama, warna, dan aksesori ada di `lib/team.ts`. Agent baru di registry wajib punya profil di file itu (build gagal bila tidak ada).
- `ASSUMPTION`: nama karakter (Tara, Raka, Sekar, …) dan gaya ilustrasi semi-3D adalah draft UI atas permintaan Dea Karisna (2026-10-07). `brand-guideline.md` §6 saat ini menyebut ilustrasi *flat*; `NEXT ACTION`: approval Pak Indra/Dea untuk menambahkan gaya karakter ini ke brand guideline.

## Jalankan

```bash
cd frontend
npm install
npm run dev        # http://localhost:3000
npm run build      # cek build produksi
```

Versi: Next.js 16.3.8, React 19.3.0, TypeScript 5.9.3 (dipin; dicek dari npm registry 2026-10-04).

## Batas

UI tidak boleh punya tombol yang langsung publish ke platform sosial/OTA atau mengirim pesan ke tamu. Release dilakukan manusia di tools resmi platform (`core/AI-CONSTITUTION.md` §4).
