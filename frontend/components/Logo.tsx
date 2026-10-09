// Logo konsep 2 "Terasering" (CLAU-AI-CONTENT/design/brand/logo-concept.md). Belum final: menunggu vektor desainer.
export function LogoMark({ size = 28 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 32 32" aria-hidden="true">
      <rect width="32" height="32" rx="8" fill="var(--color-primary)" />
      <path d="M7 10.5 Q14 9.2 20 10.5" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" fill="none" />
      <path d="M10 16 Q17 14.7 23 16" stroke="#fff" strokeWidth="3.2" strokeLinecap="round" fill="none" />
      <path d="M13 21.5 Q20 20.2 26 21.5" stroke="var(--color-primary-light)" strokeWidth="3.2" strokeLinecap="round" fill="none" />
    </svg>
  );
}

export default function Logo() {
  return (
    <span className="logo">
      <LogoMark />
      <span className="logo__text">
        <span className="logo__name">CLAU AI</span>
        <span className="logo__desc">Content Studio</span>
      </span>
    </span>
  );
}
