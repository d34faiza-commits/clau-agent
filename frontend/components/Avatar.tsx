// Avatar "digital persona": siluet geometris tanpa wajah di atas gradien warna aksen agent.
// Bukan karakter kartun: tidak ada mata/ekspresi, satu bentuk yang sama untuk semua agent.
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
  const id = `av-${name.toLowerCase()}-${size}`;
  const svg = (
    <svg className={`av av--${size}`} viewBox="0 0 64 64" role="img" aria-label={name}>
      <defs>
        <linearGradient id={`${id}-bg`} x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor={hue} stopOpacity="0.75" />
          <stop offset="1" stopColor={hue} />
        </linearGradient>
        <clipPath id={`${id}-clip`}>
          <rect width="64" height="64" rx="18" />
        </clipPath>
      </defs>
      <g clipPath={`url(#${id}-clip)`}>
        <rect width="64" height="64" fill={`url(#${id}-bg)`} />
        <circle cx="52" cy="10" r="26" fill="#fff" opacity="0.08" />
        <path d="M-4 44 Q20 34 68 46" stroke="#fff" strokeOpacity="0.12" strokeWidth="1.5" fill="none" />
        <circle cx="32" cy="25" r="10.5" fill="#fff" opacity="0.94" />
        <path d="M12 66 C12 47 21 39.5 32 39.5 C43 39.5 52 47 52 66 Z" fill="#fff" opacity="0.94" />
      </g>
    </svg>
  );
  if (!status) return svg;
  return (
    <span className="av-wrap">
      {svg}
      <span className={`av-wrap__dot av-wrap__dot--${status}`} aria-hidden="true" />
    </span>
  );
}
