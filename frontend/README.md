# Frontend (Next.js scaffold)

Halaman tunggal yang menampilkan registry agent (`../agents/registry.json`) per pilar. Belum ada login, form request, atau koneksi ke backend.

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
