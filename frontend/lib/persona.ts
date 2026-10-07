import { readFileSync } from "node:fs";
import path from "node:path";

// Kartu persona di agents/personas/ adalah sumber kebenaran; halaman agent membacanya saat build.
const PERSONAS = path.join(process.cwd(), "..", "agents", "personas");

export type PersonaFacts = {
  like: string;
  skills: string[];
  audience: string;
  escalation: string[];
};

function section(md: string, heading: RegExp): string {
  const lines = md.split("\n");
  const start = lines.findIndex((l) => heading.test(l));
  if (start < 0) return "";
  const rest = lines.slice(start + 1);
  const end = rest.findIndex((l) => l.startsWith("## "));
  return (end < 0 ? rest : rest.slice(0, end)).join("\n").trim();
}

function row(md: string, key: string): string {
  const m = md.match(new RegExp(`^\\|\\s*${key}\\s*\\|\\s*(.+?)\\s*\\|\\s*$`, "m"));
  return m ? m[1] : "";
}

function plain(s: string): string {
  return s.replace(/\[([^\]]+)\]\([^)]*\)/g, "$1").replace(/[`*]/g, "").trim();
}

export function getPersona(id: string): PersonaFacts {
  const md = readFileSync(path.join(PERSONAS, `${id}.md`), "utf-8");
  const escalation = section(md, /^## 5\./)
    .split("\n")
    .filter((l) => /^\s*(-|\d+\.)\s+/.test(l))
    .map((l) => plain(l.replace(/^\s*(-|\d+\.)\s+/, "")))
    .filter((l) => !l.includes("AI-CONSTITUTION"))
    .slice(0, 5);
  return {
    like: plain(row(md, "Seperti")),
    skills: plain(row(md, "Keahlian"))
      .split(/,\s*(?![^()]*\))/)
      .map((s) => s.trim())
      .filter(Boolean),
    audience: plain(section(md, /^## 2\./).split("\n")[0] ?? ""),
    escalation,
  };
}
