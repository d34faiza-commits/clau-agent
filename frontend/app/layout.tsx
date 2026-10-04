import type { ReactNode } from "react";

export const metadata = {
  title: "CLAU AI Agents",
  description: "Platform agent CLAU AI untuk hospitality Indonesia (scaffold)",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="id">
      <body style={{ fontFamily: "system-ui, sans-serif", margin: "0 auto", maxWidth: 960, padding: 24 }}>
        {children}
      </body>
    </html>
  );
}
