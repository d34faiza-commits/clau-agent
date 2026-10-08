// Avatar "digital persona": siluet geometris tanpa wajah di atas gradien warna aksen agent.
// Bukan karakter kartun: tidak ada mata/ekspresi, satu bentuk yang sama untuk semua agent.
// Tanpa id SVG (gradien & sudut lewat CSS), jadi aman dipakai berkali-kali di satu halaman.
export default function Avatar({
  name,
  hue,
  size = "md",
  status,
}: {
  name: string;
  hue: string;
  size?: "sm" | "md" | "lg";
  status?: "active" | "planned";
}) {
  const av = (
    <span
      className={`av av--${size}`}
      role="img"
      aria-label={name}
      style={{ background: `linear-gradient(135deg, color-mix(in srgb, ${hue} 74%, #ffffff), ${hue})` }}
    >
      <svg viewBox="0 0 64 64" width="100%" height="100%" aria-hidden="true">
        <circle cx="52" cy="10" r="26" fill="#fff" opacity="0.08" />
        <path d="M-4 44 Q20 34 68 46" stroke="#fff" strokeOpacity="0.12" strokeWidth="1.5" fill="none" />
        <circle cx="32" cy="25" r="10.5" fill="#fff" opacity="0.94" />
        <path d="M12 66 C12 47 21 39.5 32 39.5 C43 39.5 52 47 52 66 Z" fill="#fff" opacity="0.94" />
      </svg>
    </span>
  );
  if (!status) return av;
  return (
    <span className="av-wrap">
      {av}
      <span className={`av-wrap__dot av-wrap__dot--${status}`} aria-hidden="true" />
    </span>
  );
}
