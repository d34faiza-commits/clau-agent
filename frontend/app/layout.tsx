import type { ReactNode } from "react";
import Link from "next/link";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import Logo from "../components/Logo";
import "./globals.css";

const heading = Plus_Jakarta_Sans({ subsets: ["latin"], weight: ["600", "700", "800"], variable: "--font-heading" });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });

export const metadata = {
  title: "CLAU Content Studio · Tim AI",
  description: "Studio konten AI untuk hospitality Indonesia. Agent AI menyiapkan draft, manusia yang memutuskan.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="id" className={`${heading.variable} ${body.variable}`}>
      <body>
        <header className="topbar">
          <div className="container topbar__inner">
            <Link href="/" aria-label="CLAU Content Studio, beranda">
              <Logo />
            </Link>
            <nav className="topbar__nav" aria-label="Utama">
              <Link href="/#tim">Tim AI</Link>
              <Link href="/#cara-kerja">Cara kerja</Link>
              <Link href="/#tata-kelola">Tata kelola</Link>
            </nav>
            <span className="badge-preview">Pratinjau</span>
          </div>
        </header>
        <main>{children}</main>
        <footer className="footer">
          <div className="container footer__inner">
            <div>
              <Logo />
              <p className="footer__tag">Konten jujur, tamu datang.</p>
            </div>
            <p className="footer__note">
              Semua output agent adalah draft. Persetujuan, publish, dan pengiriman ke tamu dilakukan manusia. Karakter
              adalah ilustrasi agent AI, bukan staf.
            </p>
          </div>
        </footer>
      </body>
    </html>
  );
}
