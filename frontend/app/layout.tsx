import type { ReactNode } from "react";
import Link from "next/link";
import { Inter, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const heading = Plus_Jakarta_Sans({ subsets: ["latin"], weight: ["600", "700", "800"], variable: "--font-heading" });
const body = Inter({ subsets: ["latin"], variable: "--font-body" });

export const metadata = {
  title: "CLAU AI · Tim AI untuk Hospitality",
  description: "Tim agent AI CLAU untuk properti hospitality Indonesia. Agent menyiapkan draft, manusia yang memutuskan.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="id" className={`${heading.variable} ${body.variable}`}>
      <body>
        <header className="topbar">
          <div className="container topbar__inner">
            <Link href="/" className="logo">
              <span className="logo__mark">C</span> CLAU <span className="logo__ai">AI</span>
            </Link>
            <span className="topbar__note">Pratinjau platform</span>
          </div>
        </header>
        <main>{children}</main>
        <footer className="footer">
          <div className="container">
            Semua output agent adalah draft. Approval, publish, dan pengiriman ke tamu dilakukan manusia
            (core/AI-CONSTITUTION.md §4). Karakter adalah ilustrasi agent AI, bukan staf.
          </div>
        </footer>
      </body>
    </html>
  );
}
