// Format tanggal yang aman dipakai di server component (tanpa "use client").

const MONTH = {
  en: ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"],
  id: ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober", "November", "Desember"],
};

/** Bulan dan tahun dari tanggal ISO: "October 2026" / "Oktober 2026". */
export function monthYear(iso: string, lang: "en" | "id"): string {
  const [y, m] = iso.split("-").map(Number);
  return `${MONTH[lang][m - 1]} ${y}`;
}
