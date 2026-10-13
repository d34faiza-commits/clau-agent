// Penjaga halaman (Next.js 16 "proxy", dulu middleware). Hanya aktif bila CLAU_AUTH_ENABLED=1 (docker compose /
// VPS 2). VPS 1 (pratinjau data SIMULASI tanpa backend) tidak mengaturnya, jadi tetap bisa dibuka seperti sekarang.
// Ini hanya pengalihan kenyamanan: keamanan sesungguhnya ada di backend (setiap endpoint mengecek sesi & peran).
import { NextResponse, type NextRequest } from "next/server";

// Nama cookie sesi: __Host- (produksi) atau tanpa Secure bila backend CLAU_ENV=development (Safari di localhost).
const SESSION_COOKIES = ["__Host-clau_session", "clau_session_dev"];

function isPublic(pathname: string) {
  return pathname === "/login" || pathname.startsWith("/api/") || pathname.startsWith("/_next/") || /\.(webp|png|svg|ico|txt)$/.test(pathname);
}

export function proxy(request: NextRequest) {
  if (process.env.CLAU_AUTH_ENABLED !== "1") return NextResponse.next();
  const { pathname, search } = request.nextUrl;
  if (isPublic(pathname) || SESSION_COOKIES.some((c) => request.cookies.has(c))) return NextResponse.next();
  const url = request.nextUrl.clone();
  url.pathname = "/login";
  url.search = `?next=${encodeURIComponent(pathname + search)}`;
  return NextResponse.redirect(url);
}

export const config = { matcher: ["/((?!_next/static|_next/image).*)"] };
