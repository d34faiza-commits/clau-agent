# Pemeriksaan fakta — batas runtime saat ini

Perbaikan audit Pilar 1, perintah Pak Indra 2026-10-28. Ini self-review AI.

- Pencocokan otomatis hanya menerima kutipan nilai utuh atau `label: nilai` dari fakta
  yang dikonfirmasi klien. Boolean harus menyertakan label; `tidak` tidak dapat
  membenarkan klaim fasilitas tersedia. Tanda baca, desimal, negasi dan syarat dipertahankan.
- Parafrasa tidak dibuktikan oleh substring. Klaim yang tidak cocok menjadi RISK dan
  memakai kunci sentinel agar tidak lolos gate fakta di database.
- `experience`/`other` tetap ASSUMPTION, tidak dianggap grounded. Kategori buatan model
  tidak membuktikan bahwa sebuah kalimat bebas klaim faktual.
- QA otomatis hanya Fail atau Conditional; tidak pernah Pass. Seluruh caption,
  termasuk klaim tersirat/yang tidak dilaporkan model, wajib dibaca reviewer manusia.
- Batas legacy: 10.000 karakter konten, 300 karakter per klaim, 30 klaim. Output kosong
  atau berlebih ditolak `invalid_output`, tidak dipotong. Biaya panggilan tetap dicatat.
- Peminta job AI dihitung sebagai pembuat: tidak boleh menjadi reviewer independen
  atau approver draft tersebut. Draft AI klien nyata tetap minimal L2.

Trade-off: parafrasa yang benar bisa tertahan. Reviewer memperbaiki draft/tabel klaim
melalui versi baru; jangan melonggarkan gate untuk mengejar volume. H4 perlu rekonsiliasi
seluruh output dan evidence terversi sebelum klaim “validasi otomatis lengkap”.
Tidak ada perubahan schema database, provider nyata atau izin publish dalam perbaikan ini.
