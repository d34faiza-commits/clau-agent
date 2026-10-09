import Character from "./Character";
import type { Look, Uniform } from "../lib/team";

// Avatar agent: figur 3D (kepala & bahu, `public/agents/<id>.webp`) bila ada; agent konsep memakai
// karakter SVG (gaya v1). Tanpa look (mis. langkah sistem/manusia) jatuh ke siluet netral.
export default function Avatar({
  name,
  hue,
  look,
  uniform,
  image,
  size = "md",
  status,
  decorative,
}: {
  name: string;
  hue: string;
  look?: Look;
  uniform?: Uniform;
  image?: string;
  size?: "sm" | "md" | "lg" | "xl";
  status?: "active" | "planned";
  /** true bila nama agent sudah tertulis di sebelahnya, supaya pembaca layar tidak membacanya dua kali. */
  decorative?: boolean;
}) {
  const av = (
    <span
      className={`av av--${size}${look || image ? " av--char" : ""}`}
      {...(decorative ? { "aria-hidden": true } : { role: "img", "aria-label": name })}
      style={{
        // Crop 3D memakai latar mint yang menyatu di file webp; warna tile sama agar tepinya tidak terlihat.
        background: image
          ? "#DDF4EE"
          : look
          ? `linear-gradient(160deg, color-mix(in srgb, ${hue} 12%, var(--color-surface)), color-mix(in srgb, ${hue} 30%, var(--color-surface)))`
          : `linear-gradient(135deg, color-mix(in srgb, ${hue} 74%, #ffffff), ${hue})`,
      }}
    >
      {image ? (
        <img src={image} alt="" width={256} height={256} loading="lazy" decoding="async" />
      ) : look && uniform ? (
        <Character look={look} uniform={uniform} crop="bust" />
      ) : (
        <svg viewBox="0 0 64 64" width="100%" height="100%" aria-hidden="true">
          <circle cx="32" cy="25" r="10.5" fill="#fff" opacity="0.94" />
          <path d="M12 66 C12 47 21 39.5 32 39.5 C43 39.5 52 47 52 66 Z" fill="#fff" opacity="0.94" />
        </svg>
      )}
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
