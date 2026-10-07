"use client";

import { useRef, type ReactNode } from "react";

export default function Carousel({ children, title, intro }: { children: ReactNode; title: string; intro: string }) {
  const track = useRef<HTMLDivElement>(null);
  const scroll = (dir: 1 | -1) => {
    const el = track.current;
    if (el) el.scrollBy({ left: dir * el.clientWidth * 0.75, behavior: "smooth" });
  };
  return (
    <div className="carousel" role="region" aria-label={title}>
      <div className="section-head">
        <div>
          <h2>{title}</h2>
          <p className="section-intro">{intro}</p>
        </div>
        <div className="carousel__nav">
          <button type="button" className="icon-btn" onClick={() => scroll(-1)} aria-label="Sebelumnya">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M15 18l-6-6 6-6" />
            </svg>
          </button>
          <button type="button" className="icon-btn" onClick={() => scroll(1)} aria-label="Berikutnya">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M9 18l6-6-6-6" />
            </svg>
          </button>
        </div>
      </div>
      <div className="carousel__track" ref={track}>
        {children}
      </div>
    </div>
  );
}
