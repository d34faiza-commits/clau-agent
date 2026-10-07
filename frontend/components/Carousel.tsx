"use client";

import { useRef, type ReactNode } from "react";

export default function Carousel({ children, label }: { children: ReactNode; label: string }) {
  const track = useRef<HTMLDivElement>(null);
  const scroll = (dir: 1 | -1) => {
    const el = track.current;
    if (el) el.scrollBy({ left: dir * el.clientWidth * 0.8, behavior: "smooth" });
  };
  return (
    <div className="carousel" role="region" aria-label={label}>
      <button type="button" className="carousel__btn carousel__btn--prev" onClick={() => scroll(-1)} aria-label="Sebelumnya">
        ←
      </button>
      <div className="carousel__track" ref={track}>
        {children}
      </div>
      <button type="button" className="carousel__btn carousel__btn--next" onClick={() => scroll(1)} aria-label="Berikutnya">
        →
      </button>
    </div>
  );
}
