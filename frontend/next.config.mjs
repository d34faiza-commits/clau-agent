import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const dev = process.env.NODE_ENV !== "production";

// Content Security Policy (docs/security.md § 2). Next.js menyisipkan script inline (data RSC + skrip tema)
// yang isinya berbeda per halaman, jadi script-src butuh 'unsafe-inline'; yang tetap dikunci: tidak ada
// script/style/gambar/koneksi dari domain lain, tidak bisa di-embed (clickjacking), tidak ada plugin,
// <base> dan form tidak bisa diarahkan ke luar. 'unsafe-eval' hanya untuk `next dev` (hot reload).
const csp = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${dev ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data: blob:",
  "font-src 'self'",
  `connect-src 'self'${dev ? " ws:" : ""}`,
  "media-src 'self'",
  "object-src 'none'",
  "frame-src 'none'",
  "worker-src 'self'",
  "manifest-src 'self'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
].join("; ");

const securityHeaders = [
  { key: "Content-Security-Policy", value: csp },
  { key: "X-Content-Type-Options", value: "nosniff" },
  { key: "X-Frame-Options", value: "DENY" },
  { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
  { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=(), usb=(), serial=(), hid=(), magnetometer=(), gyroscope=(), accelerometer=(), browsing-topics=()" },
  { key: "Cross-Origin-Opener-Policy", value: "same-origin" },
  { key: "Cross-Origin-Resource-Policy", value: "same-origin" },
  { key: "X-DNS-Prefetch-Control", value: "off" },
  { key: "X-Permitted-Cross-Domain-Policies", value: "none" },
  // HSTS sengaja tidak di sini: dipasang di Nginx setelah HTTPS aktif (docs/deploy/vps-1-setup.md, Bagian 10).
];

/** @type {import('next').NextConfig} */
const nextConfig = {
  // The page imports ../agents/registry.json (repo root), so Turbopack's root is the repo root.
  turbopack: { root: path.join(here, "..") },
  // Jangan umumkan teknologi server.
  poweredByHeader: false,
  // next/image tidak dipakai: matikan optimizer agar endpoint /_next/image tidak bisa disalahgunakan
  // (resize gambar berulang untuk membebani server, atau fetch URL luar).
  images: { unoptimized: true },
  async headers() {
    return [{ source: "/:path*", headers: securityHeaders }];
  },
};

export default nextConfig;
