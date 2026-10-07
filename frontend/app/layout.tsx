import type { ReactNode } from "react";
import { Inter } from "next/font/google";
import AppShell from "../components/AppShell";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata = {
  title: "CLAU · Bali AI Content Studio",
  description: "Platform konten AI untuk bisnis hospitality di Bali. Agent AI menyiapkan draft, manusia yang memutuskan.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="id" className={inter.variable}>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
