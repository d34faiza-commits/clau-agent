import type { Scene as SceneName } from "../lib/team";

// Latar lanskap Nusantara per pilar (brand-guideline §6: sawah, bukit, laut, perahu; tanpa motif sakral).
export default function Scene({ scene, uid }: { scene: SceneName; uid: string }) {
  const id = (s: string) => `${uid}-${s}`;
  const sky: Record<SceneName, [string, string]> = {
    sawah: ["#FEF3C7", "#FFF7ED"],
    bukit: ["#CCFBF1", "#F0FDFA"],
    pantai: ["#BFDBFE", "#EFF6FF"],
    lobi: ["#F5F5F4", "#E7E5E4"],
    malam: ["#1E1B4B", "#3730A3"],
  };
  const [top, bottom] = sky[scene];

  return (
    <svg viewBox="0 0 300 360" preserveAspectRatio="xMidYMid slice" width="100%" height="100%" aria-hidden="true">
      <defs>
        <linearGradient id={id("sky")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor={top} />
          <stop offset="1" stopColor={bottom} />
        </linearGradient>
      </defs>
      <rect width="300" height="360" fill={`url(#${id("sky")})`} />

      {scene === "sawah" && (
        <g>
          <circle cx="226" cy="78" r="30" fill="#FBBF24" opacity=".85" />
          <path d="M0 170 Q80 130 160 160 T300 150 V360 H0 Z" fill="#99F6E4" />
          <path d="M0 210 Q90 175 170 205 T300 195 V360 H0 Z" fill="#5EEAD4" />
          <path d="M0 255 Q100 222 180 250 T300 240 V360 H0 Z" fill="#2DD4BF" />
          <path d="M0 300 Q110 270 190 296 T300 288 V360 H0 Z" fill="#14B8A6" />
          {[188, 232, 278].map((y) => (
            <path key={y} d={`M0 ${y} Q100 ${y - 30} 180 ${y - 4} T300 ${y - 12}`} stroke="#F0FDFA" strokeWidth="1.5" fill="none" opacity=".6" />
          ))}
        </g>
      )}

      {scene === "bukit" && (
        <g>
          <circle cx="70" cy="70" r="24" fill="#FDE68A" opacity=".9" />
          <path d="M0 190 Q70 120 150 180 Q220 110 300 170 V360 H0 Z" fill="#99F6E4" />
          <path d="M0 240 Q90 180 170 230 Q240 190 300 220 V360 H0 Z" fill="#2DD4BF" />
          <g transform="translate(196 176)">
            <rect x="0" y="16" width="44" height="28" fill="#FFF7ED" />
            <path d="M-8 18 L22 -6 L52 18 Z" fill="#C2410C" />
            <rect x="17" y="28" width="10" height="16" fill="#9A3412" />
          </g>
          <path d="M0 290 Q120 250 300 280 V360 H0 Z" fill="#0F766E" />
        </g>
      )}

      {scene === "pantai" && (
        <g>
          <circle cx="232" cy="74" r="26" fill="#FDE68A" />
          <rect y="170" width="300" height="80" fill="#60A5FA" />
          <path d="M0 196 Q40 190 80 196 T160 196 T240 196 T320 196" stroke="#EFF6FF" strokeWidth="2" fill="none" opacity=".7" />
          <path d="M0 222 Q40 216 80 222 T160 222 T240 222 T320 222" stroke="#EFF6FF" strokeWidth="2" fill="none" opacity=".5" />
          <g transform="translate(46 168)">
            <path d="M0 10 Q30 22 60 10 L54 18 Q30 26 6 18 Z" fill="#C2410C" />
            <path d="M28 10 V-26 L48 6 Z" fill="#FFF7ED" />
            <path d="M-6 16 Q30 30 66 16" stroke="#9A3412" strokeWidth="2" fill="none" />
          </g>
          <path d="M0 250 Q150 230 300 252 V360 H0 Z" fill="#FDE68A" />
          <path d="M0 300 Q150 284 300 302 V360 H0 Z" fill="#FCD34D" opacity=".7" />
        </g>
      )}

      {scene === "lobi" && (
        <g>
          <path d="M110 40 h80 v120 h-80 Z" fill="#CCFBF1" />
          <path d="M110 70 Q150 20 190 70" fill="#CCFBF1" />
          <path d="M150 40 V160 M110 100 H190" stroke="#fff" strokeWidth="4" />
          <rect x="102" y="158" width="96" height="6" rx="3" fill="#D6D3D1" />
          <g transform="translate(40 150)">
            <rect x="0" y="40" width="34" height="34" rx="6" fill="#C2410C" />
            <path d="M17 42 Q-10 10 6 -10 Q14 20 17 42 Q22 0 40 -6 Q34 24 17 42" fill="#14B8A6" />
          </g>
          <rect y="236" width="300" height="124" fill="#D6D3D1" />
          {[0, 1, 2, 3, 4].map((i) => (
            <path key={i} d={`M${i * 75} 236 L${i * 75 - 40} 360`} stroke="#E7E5E4" strokeWidth="2" />
          ))}
          <path d="M0 280 H300" stroke="#E7E5E4" strokeWidth="2" />
        </g>
      )}

      {scene === "malam" && (
        <g>
          {[
            [40, 40],
            [90, 80],
            [150, 30],
            [200, 90],
            [260, 50],
            [120, 120],
            [30, 130],
            [280, 140],
          ].map(([x, y]) => (
            <circle key={`${x}-${y}`} cx={x} cy={y} r="1.8" fill="#FDE68A" />
          ))}
          <circle cx="236" cy="76" r="22" fill="#FEF3C7" />
          <circle cx="246" cy="70" r="20" fill="#1E1B4B" opacity=".9" />
          <path d="M0 220 Q80 160 160 210 Q230 170 300 200 V360 H0 Z" fill="#134E4A" />
          <path d="M0 270 Q120 230 300 262 V360 H0 Z" fill="#042F2E" />
        </g>
      )}
    </svg>
  );
}
