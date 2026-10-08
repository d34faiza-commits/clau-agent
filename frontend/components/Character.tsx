"use client";

import { useId } from "react";
import type { Look, Prop, Uniform } from "../lib/team";

// Karakter chibi orisinal CLAU: seragam hospitality + badge "AI" di dada (penanda jujur bahwa ini agent AI).
// Efek "3D" dibuat dengan gradien radial dan kilap, tanpa file gambar.

function shade(hex: string, amount: number): string {
  const n = parseInt(hex.slice(1), 16);
  const ch = [(n >> 16) & 255, (n >> 8) & 255, n & 255].map((c) =>
    Math.round(amount >= 0 ? c + (255 - c) * amount : c * (1 + amount)),
  );
  return `#${ch.map((c) => c.toString(16).padStart(2, "0")).join("")}`;
}

function PropShape({ prop }: { prop: Prop }) {
  switch (prop) {
    case "pen":
      return (
        <g transform="rotate(24 198 194)">
          <rect x="192" y="160" width="12" height="52" rx="4" fill="#C2410C" />
          <rect x="192" y="160" width="12" height="10" rx="4" fill="#FED7AA" />
          <path d="M192 210 L198 224 L204 210 Z" fill="#292524" />
          <rect x="195" y="166" width="3" height="40" rx="1.5" fill="#fff" opacity=".45" />
        </g>
      );
    case "clapper":
      return (
        <g transform="rotate(-10 198 196)">
          <rect x="176" y="186" width="46" height="32" rx="4" fill="#292524" />
          <g transform="rotate(-14 176 186)">
            <rect x="176" y="174" width="46" height="11" rx="2" fill="#F5F5F4" />
            {[0, 1, 2, 3].map((i) => (
              <path key={i} d={`M${180 + i * 11} 174 l7 0 l-5 11 l-7 0 Z`} fill="#292524" />
            ))}
          </g>
          <rect x="182" y="194" width="22" height="3" rx="1.5" fill="#A8A29E" />
          <rect x="182" y="202" width="30" height="3" rx="1.5" fill="#A8A29E" />
        </g>
      );
    case "phone":
      return (
        <g transform="rotate(8 198 196)">
          <rect x="184" y="168" width="30" height="52" rx="7" fill="#1C1917" />
          <rect x="187.5" y="174" width="23" height="38" rx="3" fill="#CCFBF1" />
          <circle cx="199" cy="186" r="6" fill="#0F766E" />
          <rect x="191" y="196" width="16" height="3" rx="1.5" fill="#0F766E" />
          <rect x="191" y="202" width="11" height="3" rx="1.5" fill="#5EEAD4" />
        </g>
      );
    case "tablet":
      return (
        <g transform="rotate(-6 198 196)">
          <rect x="172" y="172" width="52" height="40" rx="6" fill="#292524" />
          <rect x="176" y="176" width="44" height="32" rx="3" fill="#F0FDFA" />
          <path d="M188 196 L198 186 L208 196 V204 H188 Z" fill="#14B8A6" />
          <rect x="195" y="198" width="6" height="6" fill="#F0FDFA" />
        </g>
      );
    case "calendar":
      return (
        <g transform="rotate(-6 198 196)">
          <rect x="174" y="174" width="48" height="42" rx="6" fill="#fff" stroke="#E7E5E4" strokeWidth="2" />
          <rect x="174" y="174" width="48" height="12" rx="6" fill="#C2410C" />
          <rect x="182" y="170" width="4" height="9" rx="2" fill="#57534E" />
          <rect x="210" y="170" width="4" height="9" rx="2" fill="#57534E" />
          {[0, 1, 2, 3].flatMap((c) =>
            [0, 1].map((r) => (
              <rect
                key={`${c}-${r}`}
                x={180 + c * 10}
                y={192 + r * 10}
                width="6"
                height="6"
                rx="1.5"
                fill={c === 2 && r === 0 ? "#14B8A6" : "#D6D3D1"}
              />
            )),
          )}
        </g>
      );
    case "megaphone":
      return (
        <g transform="rotate(-18 198 196)">
          <path d="M180 190 L216 172 V218 L180 202 Z" fill="#fff" stroke="#E7E5E4" strokeWidth="2" />
          <rect x="172" y="188" width="10" height="16" rx="3" fill="#C2410C" />
          <ellipse cx="216" cy="195" rx="5" ry="23" fill="#FED7AA" />
          <path d="M186 202 L190 214 H196 L194 204" fill="#C2410C" />
        </g>
      );
    case "globe":
      return (
        <g>
          <circle cx="198" cy="192" r="22" fill="#14B8A6" />
          <path d="M184 182 q8 -6 14 0 q4 6 -4 10 q-6 4 -2 10 q-8 2 -10 -8 Z" fill="#CCFBF1" />
          <path d="M204 196 q8 -4 12 2 q-2 10 -10 10 q-4 -6 -2 -12 Z" fill="#CCFBF1" />
          <ellipse cx="198" cy="192" rx="9" ry="22" fill="none" stroke="#fff" strokeWidth="1.5" opacity=".7" />
          <path d="M176 192 H220" stroke="#fff" strokeWidth="1.5" opacity=".7" />
          <ellipse cx="190" cy="180" rx="7" ry="4" fill="#fff" opacity=".45" />
        </g>
      );
    case "chart":
      return (
        <g transform="rotate(-6 198 196)">
          <rect x="172" y="172" width="52" height="42" rx="6" fill="#fff" stroke="#E7E5E4" strokeWidth="2" />
          <rect x="180" y="196" width="8" height="12" rx="2" fill="#C2410C" />
          <rect x="192" y="188" width="8" height="20" rx="2" fill="#0F766E" />
          <rect x="204" y="180" width="8" height="28" rx="2" fill="#14B8A6" />
          <path d="M180 190 L196 182 L208 174" stroke="#292524" strokeWidth="2" fill="none" strokeLinecap="round" />
        </g>
      );
    case "keycard":
      return (
        <g transform="rotate(-14 198 196)">
          <rect x="178" y="178" width="40" height="28" rx="5" fill="#C2410C" />
          <rect x="178" y="184" width="40" height="6" fill="#7C2D12" />
          <rect x="184" y="196" width="14" height="4" rx="2" fill="#fff" opacity=".8" />
          <circle cx="210" cy="198" r="4" fill="#fff" opacity=".8" />
        </g>
      );
    case "bell":
      return (
        <g>
          <rect x="174" y="208" width="48" height="7" rx="3" fill="#78716C" />
          <path d="M178 208 Q198 168 218 208 Z" fill="#C2410C" />
          <circle cx="198" cy="183" r="4" fill="#78716C" />
          <ellipse cx="190" cy="196" rx="5" ry="8" fill="#fff" opacity=".45" />
        </g>
      );
    case "clipboard":
      return (
        <g transform="rotate(-6 198 196)">
          <rect x="174" y="168" width="46" height="54" rx="6" fill="#78716C" />
          <rect x="179" y="176" width="36" height="42" rx="3" fill="#fff" />
          <rect x="188" y="164" width="18" height="10" rx="3" fill="#57534E" />
          {[0, 1, 2].map((i) => (
            <g key={i}>
              <path
                d={`M183 ${186 + i * 10} l3 3 l5 -6`}
                stroke="#0F766E"
                strokeWidth="2"
                fill="none"
                strokeLinecap="round"
              />
              <rect x="194" y={185 + i * 10} width="16" height="3" rx="1.5" fill="#D6D3D1" />
            </g>
          ))}
        </g>
      );
    case "speech":
      return (
        <g>
          <rect x="170" y="166" width="54" height="36" rx="12" fill="#fff" stroke="#E7E5E4" strokeWidth="2" />
          <path d="M184 200 L180 212 L194 201 Z" fill="#fff" />
          {[0, 1, 2].map((i) => (
            <circle key={i} cx={185 + i * 12} cy="184" r="4" fill="#14B8A6" />
          ))}
        </g>
      );
  }
}

export default function Character({
  look,
  uniform,
  crop = "full",
}: {
  look: Look;
  uniform: Uniform;
  /** "bust" = kepala & bahu untuk avatar kecil; "full" = seluruh badan. */
  crop?: "full" | "bust";
}) {
  // useId: id gradien unik per instance, jadi karakter yang sama boleh tampil berkali-kali.
  const uid = useId().replace(/[^a-zA-Z0-9_-]/g, "");
  const id = (s: string) => `c${uid}-${s}`;
  const url = (s: string) => `url(#${id(s)})`;
  const hijab = look.hairStyle === "hijab";
  const a = look.attire;
  const skirt = a.kind !== "batik";
  const topFill = a.kind === "kebaya" || a.kind === "kutubaru" ? url("lace") : a.kind === "batik" ? url("cloth") : url("outfit");
  const skinDark = shade(look.skin, -0.18);

  const backHair: Record<string, string | null> = {
    bob: "M48 150 C40 70 80 38 120 38 C160 38 200 70 192 150 Q186 166 170 160 L170 128 L70 128 L70 160 Q54 166 48 150 Z",
    long: "M46 204 C34 70 80 34 120 34 C160 34 206 70 194 204 Q180 216 166 204 L166 128 L74 128 L74 204 Q60 216 46 204 Z",
  };

  const frontHair: Record<string, string> = {
    short:
      "M56 112 C52 58 88 40 120 40 C156 40 190 58 184 112 C180 96 174 86 166 80 C150 90 128 92 110 86 C96 92 76 90 64 84 C60 92 57 102 56 112 Z",
    swoop:
      "M56 114 C50 56 92 38 124 40 C162 42 192 64 184 112 C178 94 170 84 160 78 C140 98 104 96 76 72 C68 86 60 98 56 114 Z",
    bob: "M56 112 C54 60 90 42 120 42 C150 42 186 60 184 112 C178 98 174 90 168 84 Q120 98 72 84 C66 90 60 100 56 112 Z",
    bun: "M58 110 C54 60 90 44 120 44 C150 44 186 60 182 110 C176 92 160 80 138 76 C122 86 92 88 70 84 C64 92 60 100 58 110 Z",
    long: "M56 116 C52 58 88 40 120 40 C152 40 188 58 184 116 C178 92 160 74 126 66 C110 82 82 90 58 100 Z",
    curly: "M60 104 C60 66 88 48 120 48 C152 48 180 66 180 104 C168 88 150 80 120 80 C90 80 72 88 60 104 Z",
  };

  return (
    <svg
      viewBox={crop === "bust" ? "26 18 188 188" : "0 0 240 300"}
      width="100%"
      height="100%"
      aria-hidden="true"
      preserveAspectRatio="xMidYMid meet"
      style={uniform.muted ? { filter: `saturate(${1 - uniform.muted})` } : undefined}
    >
      <defs>
        <radialGradient id={id("skin")} cx="38%" cy="32%" r="78%">
          <stop offset="0" stopColor={shade(look.skin, 0.22)} />
          <stop offset=".6" stopColor={look.skin} />
          <stop offset="1" stopColor={skinDark} />
        </radialGradient>
        <radialGradient id={id("hair")} cx="35%" cy="25%" r="85%">
          <stop offset="0" stopColor={shade(look.hair, 0.28)} />
          <stop offset=".55" stopColor={look.hair} />
          <stop offset="1" stopColor={shade(look.hair, -0.35)} />
        </radialGradient>
        <linearGradient id={id("outfit")} x1="0" y1="0" x2=".3" y2="1">
          <stop offset="0" stopColor={shade(a.main, 0.25)} />
          <stop offset=".6" stopColor={a.main} />
          <stop offset="1" stopColor={shade(a.main, -0.18)} />
        </linearGradient>
        {/* kebaya: brokat halus */}
        <pattern id={id("lace")} width="10" height="10" patternUnits="userSpaceOnUse">
          <rect width="10" height="10" fill={a.main} />
          <circle cx="5" cy="5" r="1.6" fill="none" stroke={shade(a.main, -0.22)} strokeWidth=".8" />
          <circle cx="0" cy="0" r="1" fill={shade(a.main, -0.15)} />
          <circle cx="10" cy="10" r="1" fill={shade(a.main, -0.15)} />
        </pattern>
        {/* kain batik: motif geometris umum (ceplok sederhana) */}
        <pattern id={id("cloth")} width="14" height="14" patternUnits="userSpaceOnUse">
          <rect width="14" height="14" fill={a.cloth} />
          <path d="M7 2 L12 7 L7 12 L2 7 Z" fill="none" stroke={a.motif} strokeWidth="1" opacity=".75" />
          <circle cx="7" cy="7" r="1.4" fill={a.motif} opacity=".8" />
          <circle cx="0" cy="0" r="1.2" fill={a.motif} opacity=".6" />
          <circle cx="14" cy="14" r="1.2" fill={a.motif} opacity=".6" />
        </pattern>
        <linearGradient id={id("shade")} x1="0" y1="0" x2="1" y2="0">
          <stop offset="0" stopColor="#000" stopOpacity="0" />
          <stop offset="1" stopColor="#000" stopOpacity=".18" />
        </linearGradient>
        <linearGradient id={id("pants")} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#57534E" />
          <stop offset="1" stopColor="#292524" />
        </linearGradient>
      </defs>

      <ellipse cx="120" cy="286" rx="62" ry="9" fill="#000" opacity=".18" />

      {look.hairStyle === "bun" && <circle cx="120" cy="38" r="21" fill={url("hair")} />}
      {backHair[look.hairStyle] && <path d={backHair[look.hairStyle] as string} fill={url("hair")} />}

      {/* bawahan: kain batik (kamen/jarik) atau celana */}
      {skirt ? (
        <>
          <ellipse cx="104" cy="277" rx="15" ry="7" fill="#1C1917" />
          <ellipse cx="136" cy="277" rx="15" ry="7" fill="#1C1917" />
          <path d="M82 230 L158 230 L163 270 Q120 279 77 270 Z" fill={url("cloth")} />
          <path d="M82 230 L158 230 L163 270 Q120 279 77 270 Z" fill={url("shade")} />
          <path d="M136 232 L146 272" stroke={shade(a.cloth, -0.3)} strokeWidth="2" opacity=".7" />
        </>
      ) : (
        <>
          <rect x="96" y="244" width="20" height="30" rx="8" fill={url("pants")} />
          <rect x="124" y="244" width="20" height="30" rx="8" fill={url("pants")} />
          <ellipse cx="104" cy="276" rx="16" ry="8" fill="#1C1917" />
          <ellipse cx="136" cy="276" rx="16" ry="8" fill="#1C1917" />
          <ellipse cx="100" cy="273" rx="6" ry="2.5" fill="#fff" opacity=".25" />
          <ellipse cx="132" cy="273" rx="6" ry="2.5" fill="#fff" opacity=".25" />
        </>
      )}

      {/* atasan: busana adat hospitality */}
      <path d="M80 182 Q80 166 98 164 L142 164 Q160 166 160 182 L165 238 Q165 252 150 252 L90 252 Q75 252 75 238 Z" fill={topFill} />
      <path d="M80 182 Q80 166 98 164 L142 164 Q160 166 160 182 L165 238 Q165 252 150 252 L90 252 Q75 252 75 238 Z" fill={url("shade")} />
      {a.kind === "kebaya" && (
        <>
          <path d="M104 164 L120 198 L136 164 Z" fill={shade(a.accent, -0.1)} />
          <path d="M104 164 L120 198 L136 164" fill="none" stroke={shade(a.main, -0.25)} strokeWidth="2" />
          <path d="M84 170 L100 164 L163 234 L152 246 Z" fill={a.accent} />
          <path d="M100 164 L163 234" stroke="#fff" strokeOpacity=".3" strokeWidth="2" />
        </>
      )}
      {a.kind === "kutubaru" && (
        <>
          <path d="M106 164 L120 180 L134 164 Z" fill={shade(a.accent, -0.1)} />
          <rect x="111" y="176" width="18" height="62" rx="2" fill={a.accent} />
          {[188, 204, 220].map((y) => (
            <circle key={y} cx="120" cy={y} r="3" fill="#E0B341" stroke="#9A7B1F" strokeWidth="1" />
          ))}
          <path d="M80 236 L160 236" stroke={shade(a.main, -0.3)} strokeWidth="3" />
        </>
      )}
      {a.kind === "batik" && (
        <>
          <path d="M102 164 L120 178 L112 186 L96 170 Z" fill={a.main} />
          <path d="M138 164 L120 178 L128 186 L144 170 Z" fill={a.main} />
          <path d="M120 180 L120 250" stroke={shade(a.cloth, -0.35)} strokeWidth="2" />
          {[196, 214, 232].map((y) => (
            <circle key={y} cx="120" cy={y} r="2.2" fill={a.motif} />
          ))}
        </>
      )}
      {a.kind === "udeng" && (
        <>
          <path d="M102 164 L120 178 L112 186 L96 170 Z" fill="#fff" stroke="#CBD5E1" strokeWidth="1" />
          <path d="M138 164 L120 178 L128 186 L144 170 Z" fill="#fff" stroke="#CBD5E1" strokeWidth="1" />
          <path d="M120 180 L120 226" stroke="#CBD5E1" strokeWidth="1.5" />
          {[196, 212].map((y) => (
            <circle key={y} cx="120" cy={y} r="2" fill="#94A3B8" />
          ))}
          <path d="M77 222 L163 222 L165 244 L75 244 Z" fill={a.accent} />
          <path d="M77 222 L163 222" stroke="#fff" strokeOpacity=".35" strokeWidth="2" />
        </>
      )}
      {a.kind === "beskap" && (
        <>
          <path d="M104 162 L136 162 L134 172 L106 172 Z" fill={shade(a.main, -0.25)} />
          <path d="M106 172 L140 250" stroke={shade(a.main, -0.35)} strokeWidth="2.5" />
          {[184, 202, 220, 238].map((y, i) => (
            <circle key={y} cx={111 + i * 7.6} cy={y} r="2.6" fill={a.accent} />
          ))}
        </>
      )}
      <circle cx="96" cy="206" r="10.5" fill="#fff" stroke={uniform.trim} strokeWidth="2.5" />
      <text x="96" y="210" textAnchor="middle" fontSize="10" fontWeight="800" fill={uniform.trim} fontFamily="system-ui, sans-serif">
        AI
      </text>

      {/* lengan kiri */}
      <rect x="64" y="174" width="20" height="56" rx="10" fill={a.kind === "udeng" ? "#F1F5F9" : topFill} transform="rotate(14 74 178)" />
      <circle cx="64" cy="234" r="9.5" fill={url("skin")} />

      {/* leher */}
      <rect x="110" y="152" width="20" height="16" rx="6" fill={skinDark} />

      {hijab ? (
        <>
          <path
            d="M40 140 C36 62 80 32 120 32 C160 32 204 62 200 140 C204 178 184 198 160 202 L80 202 C56 198 36 178 40 140 Z"
            fill={url("hair")}
          />
          <ellipse cx="120" cy="120" rx="54" ry="52" fill={url("skin")} />
          <path d="M66 104 Q120 56 174 104 Q120 76 66 104 Z" fill={shade(look.hair, -0.2)} />
          <ellipse cx="72" cy="78" rx="16" ry="9" fill="#fff" opacity=".2" transform="rotate(-30 72 78)" />
        </>
      ) : (
        <>
          <circle cx="57" cy="120" r="10" fill={url("skin")} />
          <circle cx="183" cy="120" r="10" fill={url("skin")} />
          <ellipse cx="120" cy="108" rx="64" ry="60" fill={url("skin")} />
        </>
      )}

      {/* wajah */}
      <path d="M90 101 q8 -5 16 0" stroke={hijab ? "#2B211C" : look.hair} strokeWidth="3.5" fill="none" strokeLinecap="round" />
      <path d="M134 101 q8 -5 16 0" stroke={hijab ? "#2B211C" : look.hair} strokeWidth="3.5" fill="none" strokeLinecap="round" />
      {[98, 142].map((x) => (
        <g key={x}>
          <ellipse cx={x} cy="120" rx="9.5" ry="11.5" fill="#1C1917" />
          <ellipse cx={x} cy="123" rx="6" ry="7" fill="#5A3A26" />
          <circle cx={x + 3} cy="115" r="3.4" fill="#fff" />
          <circle cx={x - 3} cy="126" r="1.6" fill="#fff" />
        </g>
      ))}
      <ellipse cx="82" cy="137" rx="9" ry="5" fill="#F43F5E" opacity=".2" />
      <ellipse cx="158" cy="137" rx="9" ry="5" fill="#F43F5E" opacity=".2" />
      <ellipse cx="120" cy="132" rx="2.6" ry="1.8" fill={shade(look.skin, -0.3)} />
      <path d="M109 140 Q120 153 131 140 Q120 145 109 140 Z" fill="#9A3412" />

      {!hijab && <path d={frontHair[look.hairStyle]} fill={url("hair")} />}
      {look.hairStyle === "curly" &&
        [-172, -150, -128, -106, -84, -62, -40, -18].map((deg) => {
          const r = (deg * Math.PI) / 180;
          return <circle key={deg} cx={120 + 60 * Math.cos(r)} cy={104 + 56 * Math.sin(r)} r="17" fill={url("hair")} />;
        })}
      {!hijab && <ellipse cx="94" cy="62" rx="20" ry="8" fill="#fff" opacity=".18" transform="rotate(-22 94 62)" />}

      {/* aksesori kepala */}
      {look.headwear === "glasses" && (
        <g stroke="#292524" strokeWidth="3" fill="#fff" fillOpacity=".12">
          <circle cx="98" cy="120" r="16" />
          <circle cx="142" cy="120" r="16" />
          <path d="M114 118 q6 -4 12 0" fill="none" />
        </g>
      )}
      {look.headwear === "headset" && (
        <g>
          <path d="M54 112 C50 34 190 34 186 112" stroke="#292524" strokeWidth="7" fill="none" strokeLinecap="round" />
          <rect x="44" y="104" width="16" height="28" rx="7" fill="#292524" />
          <rect x="180" y="104" width="16" height="28" rx="7" fill="#292524" />
          <path d="M52 130 Q60 152 88 150" stroke="#292524" strokeWidth="3.5" fill="none" strokeLinecap="round" />
          <circle cx="90" cy="150" r="5" fill="#14B8A6" />
        </g>
      )}
      {look.headwear === "beret" && (
        <g transform="rotate(-10 110 52)">
          <ellipse cx="112" cy="54" rx="58" ry="20" fill={uniform.trim} />
          <ellipse cx="100" cy="47" rx="22" ry="6" fill="#fff" opacity=".2" />
          <circle cx="112" cy="34" r="5" fill={uniform.trim} />
        </g>
      )}
      {look.headwear === "cap" && (
        <g>
          <path d="M56 86 C58 34 182 34 184 86 Z" fill={url("outfit")} />
          <path d="M150 82 Q204 78 210 94 Q172 98 150 90 Z" fill={uniform.trim} />
          <rect x="56" y="80" width="128" height="8" rx="4" fill={uniform.trim} />
          <circle cx="120" cy="40" r="4" fill={uniform.trim} />
          <ellipse cx="96" cy="56" rx="16" ry="6" fill="#fff" opacity=".22" transform="rotate(-18 96 56)" />
        </g>
      )}

      {look.headwear === "udeng" && (
        <g>
          <path d="M54 96 Q120 58 186 96 L184 80 Q120 40 56 80 Z" fill={url("cloth")} />
          <path d="M54 96 Q120 58 186 96" stroke={shade(a.cloth, -0.35)} strokeWidth="2" fill="none" />
          <path d="M108 66 L120 34 L132 66 Z" fill={url("cloth")} stroke={shade(a.cloth, -0.35)} strokeWidth="1.5" />
          <ellipse cx="182" cy="86" rx="8" ry="10" fill={url("cloth")} />
        </g>
      )}
      {look.headwear === "blangkon" && (
        <g>
          <path d="M54 98 C52 36 188 36 186 98 Q120 80 54 98 Z" fill={url("cloth")} />
          <path d="M54 98 Q120 80 186 98" stroke={shade(a.cloth, -0.4)} strokeWidth="3" fill="none" />
          <path d="M70 70 Q120 50 170 70" stroke={a.motif} strokeOpacity=".5" strokeWidth="1.5" fill="none" />
        </g>
      )}

      {/* lengan kanan memegang alat kerja */}
      <rect x="156" y="174" width="20" height="50" rx="10" fill={a.kind === "udeng" ? "#F1F5F9" : topFill} transform="rotate(-35 166 178)" />
      <PropShape prop={look.prop} />
      <circle cx="192" cy="216" r="9.5" fill={url("skin")} />
    </svg>
  );
}
