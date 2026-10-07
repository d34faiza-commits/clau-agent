import type { Scene as SceneName } from "../lib/team";

// Latar lanskap Nusantara (brand-guideline §6): flat, garis sederhana, maks 3 warna palet
// (tint Teal Laut, Terracotta, Pasir). Motif berbeda per agent, nada warna sama untuk semua.
const TEAL_1 = "#CCFBF1";
const TEAL_2 = "#99F6E4";
const TEAL_3 = "#5EEAD4";
const SUN = "#C2410C";

export default function Scene({ scene, uid, muted = false }: { scene: SceneName; uid: string; muted?: boolean }) {
  const id = `${uid}-bg`;
  return (
    <svg
      viewBox="0 0 300 360"
      preserveAspectRatio="xMidYMid slice"
      width="100%"
      height="100%"
      aria-hidden="true"
      style={muted ? { filter: "grayscale(1)", opacity: 0.75 } : undefined}
    >
      <defs>
        <linearGradient id={id} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#FAFAF9" />
          <stop offset="1" stopColor="#F0FDFA" />
        </linearGradient>
      </defs>
      <rect width="300" height="360" fill={`url(#${id})`} />
      {[60, 92, 124].map((y) => (
        <path key={y} d={`M-10 ${y} Q80 ${y - 18} 160 ${y - 4} T310 ${y - 10}`} stroke={TEAL_1} strokeWidth="1.2" fill="none" />
      ))}

      {scene === "sawah" && (
        <g>
          <circle cx="232" cy="96" r="14" fill={SUN} opacity=".9" />
          <path d="M0 214 Q90 186 170 206 T300 198 V360 H0 Z" fill={TEAL_1} />
          <path d="M0 250 Q100 224 180 246 T300 238 V360 H0 Z" fill={TEAL_2} />
          <path d="M0 290 Q110 266 190 288 T300 282 V360 H0 Z" fill={TEAL_3} opacity=".7" />
        </g>
      )}

      {scene === "bukit" && (
        <g>
          <circle cx="76" cy="100" r="14" fill={SUN} opacity=".9" />
          <path d="M0 230 Q70 170 150 220 Q220 166 300 210 V360 H0 Z" fill={TEAL_1} />
          <path d="M0 268 Q100 224 180 260 Q240 232 300 252 V360 H0 Z" fill={TEAL_2} />
          <g transform="translate(206 194)" fill={TEAL_3}>
            <rect x="2" y="16" width="34" height="22" />
            <path d="M-6 18 L19 -2 L44 18 Z" />
          </g>
        </g>
      )}

      {scene === "pantai" && (
        <g>
          <circle cx="226" cy="104" r="14" fill={SUN} opacity=".9" />
          <rect y="200" width="300" height="70" fill={TEAL_1} />
          <path d="M0 222 Q40 216 80 222 T160 222 T240 222 T320 222" stroke="#fff" strokeWidth="1.5" fill="none" />
          <path d="M0 244 Q40 238 80 244 T160 244 T240 244 T320 244" stroke="#fff" strokeWidth="1.5" fill="none" />
          <g transform="translate(40 196)" fill={TEAL_3}>
            <path d="M0 8 Q26 18 52 8 L46 15 Q26 21 6 15 Z" />
            <path d="M24 8 V-20 L40 5 Z" opacity=".8" />
          </g>
          <path d="M0 270 Q150 252 300 272 V360 H0 Z" fill={TEAL_2} />
        </g>
      )}

      {scene === "lobi" && (
        <g>
          <path d="M115 90 Q150 50 185 90 V200 H115 Z" fill={TEAL_1} />
          <path d="M150 66 V200 M115 140 H185" stroke="#fff" strokeWidth="3" />
          <rect x="40" y="208" width="26" height="28" rx="5" fill={SUN} opacity=".85" />
          <path d="M53 210 Q34 186 44 168 Q50 192 53 210 Q56 178 70 174 Q66 196 53 210" fill={TEAL_3} />
          <rect y="236" width="300" height="124" fill={TEAL_1} />
          <path d="M0 280 H300 M75 236 L45 360 M150 236 V360 M225 236 L255 360" stroke="#fff" strokeWidth="1.5" />
        </g>
      )}

      {scene === "malam" && (
        <g>
          <circle cx="230" cy="96" r="14" fill={SUN} opacity=".9" />
          {[
            [50, 60],
            [110, 104],
            [168, 52],
            [270, 150],
            [36, 150],
          ].map(([x, y]) => (
            <path key={`${x}-${y}`} d={`M${x} ${y - 4} V${y + 4} M${x - 4} ${y} H${x + 4}`} stroke={TEAL_3} strokeWidth="1.5" />
          ))}
          <path d="M0 240 Q80 190 160 230 Q230 196 300 222 V360 H0 Z" fill={TEAL_1} />
          <path d="M0 276 Q120 246 300 270 V360 H0 Z" fill={TEAL_2} />
          <path d="M40 300 L90 270 L130 284 L190 250 L250 262" stroke="#0F766E" strokeWidth="2" fill="none" opacity=".35" />
        </g>
      )}
    </svg>
  );
}
