import Character from "./Character";
import type { Look, Uniform } from "../lib/team";

// Avatar agent: karakter (gaya v1, kepala & bahu) di atas latar lembut warna aksen agent.
// Tanpa look (mis. langkah sistem/manusia) jatuh ke siluet netral.
export default function Avatar({
  name,
  hue,
  look,
  uniform,
  image,
  size = "md",
  status,
}: {
  name: string;
  hue: string;
  look?: Look;
  uniform?: Uniform;
  image?: string;
  size?: "sm" | "md" | "lg" | "xl";
  status?: "active" | "planned";
}) {
  const av = (
    <span
      className={`av av--${size}${look || image ? " av--char" : ""}`}
      role="img"
      aria-label={name}
      style={{
        background: look || image
          ? `linear-gradient(160deg, color-mix(in srgb, ${hue} 12%, var(--color-surface)), color-mix(in srgb, ${hue} 30%, var(--color-surface)))`
          : `linear-gradient(135deg, color-mix(in srgb, ${hue} 74%, #ffffff), ${hue})`,
      }}
    >
      {image ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={image} alt="" className="av__img" loading="lazy" style={uniform?.muted ? { filter: `saturate(${1 - uniform.muted})` } : undefined} />
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
