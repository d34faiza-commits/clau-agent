"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState, type ReactNode } from "react";
import Icon, { type IconName } from "./Icon";
import Logo from "./Logo";

const NAV: { group: string; items: { href: string; label: string; icon: IconName }[] }[] = [
  { group: "Ringkasan", items: [{ href: "/", label: "Dashboard", icon: "dashboard" }] },
  {
    group: "Workspace",
    items: [
      { href: "/clients", label: "Klien", icon: "users" },
      { href: "/projects", label: "Proyek", icon: "folder" },
      { href: "/content", label: "Konten", icon: "content" },
      { href: "/calendar", label: "Kalender", icon: "calendar" },
    ],
  },
  {
    group: "AI",
    items: [
      { href: "/agents", label: "Agent AI", icon: "bot" },
      { href: "/workflows", label: "Alur kerja", icon: "workflow" },
    ],
  },
  { group: "Bisnis", items: [{ href: "/reports", label: "Laporan", icon: "reports" }] },
  { group: "Sistem", items: [{ href: "/settings", label: "Pengaturan", icon: "settings" }] },
];

const TITLES: [string, string][] = NAV.flatMap((g) => g.items.map((i) => [i.href, i.label] as [string, string]));

function isActive(path: string, href: string) {
  return href === "/" ? path === "/" : path === href || path.startsWith(`${href}/`);
}

export default function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname() ?? "/";
  const [open, setOpen] = useState(false);
  useEffect(() => setOpen(false), [path]);
  const title = [...TITLES].reverse().find(([href]) => isActive(path, href))?.[1] ?? "CLAU";

  return (
    <div className="shell">
      <aside className={`sidebar${open ? " sidebar--open" : ""}`} aria-label="Navigasi utama">
        <div className="sidebar__brand">
          <Link href="/" aria-label="Dashboard">
            <Logo />
          </Link>
          <button type="button" className="icon-btn icon-btn--ghost sidebar__close" onClick={() => setOpen(false)} aria-label="Tutup menu">
            <Icon name="x" />
          </button>
        </div>
        <nav>
          {NAV.map((g) => (
            <div key={g.group} className="nav-group">
              <span className="nav-group__label">{g.group}</span>
              {g.items.map((i) => (
                <Link key={i.href} href={i.href} className={`nav-item${isActive(path, i.href) ? " nav-item--active" : ""}`} aria-current={isActive(path, i.href) ? "page" : undefined}>
                  <Icon name={i.icon} size={18} />
                  {i.label}
                </Link>
              ))}
            </div>
          ))}
        </nav>
        <div className="sidebar__foot">
          <Icon name="shield" size={16} />
          AI hanya menyiapkan draft. Manusia yang menyetujui dan mempublish.
        </div>
      </aside>
      {open && <button type="button" className="scrim" aria-label="Tutup menu" onClick={() => setOpen(false)} />}

      <div className="main">
        <header className="topbar">
          <button type="button" className="icon-btn icon-btn--ghost topbar__menu" onClick={() => setOpen(true)} aria-label="Buka menu">
            <Icon name="menu" />
          </button>
          <span className="topbar__title">{title}</span>
          <div className="topbar__search" title="Pencarian tersedia setelah backend tersambung">
            <Icon name="search" size={16} />
            <input type="search" placeholder="Cari klien, konten, agent…" aria-label="Cari" disabled />
          </div>
          <span className="workspace" title="Mode pratinjau dengan data simulasi">
            <span className="workspace__dot" />
            Pratinjau · Simulasi
          </span>
          <button type="button" className="icon-btn icon-btn--ghost" aria-label="Notifikasi (belum ada)" disabled>
            <Icon name="bell" size={18} />
          </button>
          <span className="avatar" title="Owner (pratinjau)">
            <Icon name="user" size={16} />
          </span>
        </header>
        <main className="content">{children}</main>
      </div>
    </div>
  );
}
