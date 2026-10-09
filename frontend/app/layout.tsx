import type { ReactNode } from "react";
import { Inter } from "next/font/google";
import AppShell from "../components/AppShell";
import { LangProvider } from "../lib/i18n";
import { THEME_SCRIPT } from "../lib/theme";
import { getTeam } from "../lib/team";
import "./globals.css";

const inter = Inter({ subsets: ["latin"], variable: "--font-inter" });

export const metadata = {
  title: "CLAU AI",
  description: "Your AI marketing team for hospitality. AI agents prepare drafts; your team approves and publishes.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  const active = getTeam().filter((m) => m.status === "active").length;
  return (
    <html lang="en" className={inter.variable} data-theme="light" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: THEME_SCRIPT }} />
      </head>
      <body>
        <LangProvider>
          <AppShell activeAgents={active}>{children}</AppShell>
        </LangProvider>
      </body>
    </html>
  );
}
