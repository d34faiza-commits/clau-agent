"use client";

import { useEffect, useState } from "react";
import { api, type Me } from "../lib/auth";
import { useL } from "../lib/i18n";
import Icon from "./Icon";

// Tanpa backend (VPS 1, pratinjau SIMULASI): tetap ikon pratinjau seperti sebelumnya.
// Dengan backend: nama pengguna → /account, atau tombol Masuk bila belum login.
export default function UserMenu() {
  const tr = useL();
  const [state, setState] = useState<{ kind: "preview" } | { kind: "signed-out" } | { kind: "user"; me: Me }>({ kind: "preview" });

  useEffect(() => {
    api<Me>("auth/me").then((r) => {
      if (r.ok) setState({ kind: "user", me: r.data });
      else if (r.status === 401) setState({ kind: "signed-out" });
    });
  }, []);

  if (state.kind === "signed-out")
    return (
      <a className="btn btn--secondary btn--sm" href="/login">
        {tr("Sign in", "Masuk")}
      </a>
    );
  if (state.kind === "user")
    return (
      <a className="avatar-user" href="/account" title={`${state.me.user.display_name} · ${tr("Account", "Akun")}`} aria-label={tr("Account", "Akun")}>
        <Icon name="user" size={16} />
      </a>
    );
  return (
    <span className="avatar-user" title={tr("Owner (preview)", "Owner (pratinjau)")}>
      <Icon name="user" size={16} />
    </span>
  );
}
