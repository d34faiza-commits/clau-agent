# Brief UI v3 — "AI Workforce" (ringkasan)

> Brief "CLAU AI Content Studio — Sintra-inspired AI Workforce UI/UX Redesign, Version 2.0" dari Dea Karisna (2026-10-07), ditempel di chat. Ringkasan poin yang diimplementasikan di branch `ui-v3-workforce`.

| # | Poin brief | Implementasi |
|---|---|---|
| 1 | Konsep "Meet your AI team": agent terasa seperti karyawan digital profesional | Halaman **My AI Team**, kartu agent (avatar, nama, peran, headline, kemampuan, status, level, "Open agent") |
| 2 | Terinspirasi Sintra **tanpa menyalin** branding, layout, ilustrasi, wording | Desain orisinal: avatar siluet geometris tanpa wajah, palet navy/teal CLAU, copy sendiri |
| 3 | Navy + Deep Teal + White + Soft Mint, sedikit warna sekunder untuk kepribadian agent | Token di `frontend/app/globals.css`; tiap agent satu nada aksen (keluarga teal/biru/indigo/violet) |
| 4 | Bukan brosur Bali | Tidak ada ornamen tropis di UI; Bali hanya di konten klien |
| 5 | Inter, sidebar navy, top bar (judul, search, notifikasi, profil) | Sesuai; plus **pilihan bahasa EN/ID (tanpa bendera)** dan **dark mode** (permintaan Dea) |
| 6 | Dashboard: greeting, KPI, Meet your AI team, AI activity, proyek, jadwal | Sesuai, data diberi label SIMULASI |
| 7 | Agent detail: profil, tugas, output, performa, workflow, instruksi | Sesuai. **Quality score tidak dikarang**: "Not measured yet" + jumlah kasus uji nyata |
| 8 | "Generate monthly content" dengan progres per agent | Modal alur memakai agent yang benar-benar ada; diberi label SIMULASI (tidak memanggil AI) |
| 9 | Workflow Strategy → Planner → Copywriter → Visual → Video → QC → Human → Published | Sesuai; peran yang belum ada (Nova, Aruna, Dara) ditandai **Concept** |
| 10 | Client workspace dengan tab | Overview, Brand, Strategy, Content, Calendar, Media, Campaigns, Reports, AI Team |
| 11 | Content: status + filter format, preview (hook, caption, CTA, hashtag), aksi | Sesuai; aksi Edit/Regenerate/Approve/Reject nonaktif sampai login & backend ada |
| 12 | Reports tanpa data karangan | Produksi konten saja; reach/engagement/leads = "Not connected yet" |
| 13 | Demo client "Sunset Villa Uluwatu" | Dipakai **Villa Contoh Uluwatu** (aturan nama fiktif wajib "Contoh") |

Penyimpangan yang disengaja: muted text `#94A3B8` dari brief hanya untuk non-teks di mode terang (kontras 2,56:1 gagal WCAG AA); teks muted memakai `#64748B`.
