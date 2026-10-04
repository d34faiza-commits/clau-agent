import registry from "../../agents/registry.json";

type Agent = {
  id: string;
  pillar: number;
  status: string;
  intents: string[];
  skill: string | null;
  prompt: string | null;
  template: string | null;
  approval_min: string;
};

const PILLARS: Record<number, string> = {
  1: "Marketing & Content",
  2: "Sales & Reservations",
  3: "Guest Experience & Reputation",
  4: "Operations",
  5: "Analytics & Insights",
};

export default function Home() {
  const agents = registry.agents as Agent[];
  return (
    <main>
      <h1>CLAU AI Agents</h1>
      <p>
        Scaffold platform. Agent hanya menyiapkan draft. Publish, kirim ke tamu, dan approval tetap dilakukan manusia
        (<code>core/AI-CONSTITUTION.md</code> §4).
      </p>
      <table style={{ borderCollapse: "collapse", width: "100%" }}>
        <thead>
          <tr>
            {["Agent", "Pilar", "Intent", "Artefak", "Approval min", "Status"].map((h) => (
              <th key={h} style={{ textAlign: "left", borderBottom: "1px solid #ccc", padding: 6 }}>
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {agents.map((a) => (
            <tr key={a.id}>
              <td style={{ padding: 6 }}>{a.id}</td>
              <td style={{ padding: 6 }}>
                {a.pillar} · {PILLARS[a.pillar]}
              </td>
              <td style={{ padding: 6 }}>{a.intents.join(", ")}</td>
              <td style={{ padding: 6 }}>{a.skill ?? a.prompt ?? a.template ?? "—"}</td>
              <td style={{ padding: 6 }}>{a.approval_min}</td>
              <td style={{ padding: 6 }}>{a.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </main>
  );
}
