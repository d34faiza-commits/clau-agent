import AgentCard from "../components/AgentCard";
import Carousel from "../components/Carousel";
import Character from "../components/Character";
import { PILLARS, UNIFORM, getTeam } from "../lib/team";
import { readdirSync, readFileSync } from "node:fs";
import path from "node:path";

const STEPS = [
  ["Kirim brief", "Tim kamu menulis kebutuhan: caption, balasan review, kalender konten, atau laporan."],
  ["Agent menyiapkan draft", "Agent dengan keahlian yang sesuai menulis draft memakai Voice Card properti kamu."],
  ["Manusia memeriksa", "Draft dicek sesuai level L1–L3. Fakta penting dikonfirmasi owner."],
  ["Manusia mempublish", "Konten tayang atau terkirim lewat aplikasi resmi, oleh tim kamu, bukan oleh AI."],
];

const GOVERNANCE = [
  ["Draft, bukan keputusan", "Agent tidak bisa publish, mengirim pesan ke tamu, atau menyetujui pekerjaannya sendiri."],
  ["Persetujuan berlapis", "Setiap agent punya level minimum L1–L3. Konten sensitif wajib naik ke level persetujuan yang lebih tinggi."],
  ["Batas tertulis", "Setiap agent punya kartu persona: gaya bahasa, hal yang dihindari, dan kapan wajib berhenti."],
  ["Diuji sebelum dipakai", "Kualitas tiap agent diukur dengan kasus uji dan rubrik penilaian manusia."],
];

function countEvalCases(): number {
  const dir = path.join(process.cwd(), "..", "agents", "evals", "cases");
  return readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .reduce((n, f) => n + JSON.parse(readFileSync(path.join(dir, f), "utf-8")).cases.length, 0);
}

export default function Home() {
  const team = getTeam();
  const active = team.filter((m) => m.status === "active");
  const pillars = Object.entries(PILLARS)
    .map(([n, name]) => ({ n: Number(n), name, members: team.filter((m) => m.pillar === Number(n)) }))
    .filter((p) => p.members.length > 0);
  const lead = team.slice(0, 3);
  // Pilar dengan 1 agent digabung dalam satu baris agar grid tetap penuh dan rapi.
  const big = pillars.filter((p) => p.members.length > 1);
  const small = pillars.filter((p) => p.members.length === 1);
  const groups = [
    ...big.map((p) => ({
      n: String(p.n).padStart(2, "0"),
      title: p.name,
      members: p.members,
      status: p.members.every((m) => m.status === "active") ? "berjalan" : "bertahap",
    })),
    {
      n: small.map((p) => String(p.n).padStart(2, "0")).join(" · "),
      title: small.map((p) => p.name.split(" & ")[0]).join(", "),
      members: small.flatMap((p) => p.members),
      status: `${small.flatMap((p) => p.members).filter((m) => m.status === "active").length} aktif`,
    },
  ].filter((g) => g.members.length > 0);

  return (
    <>
      <section className="hero">
        <div className="container hero__grid">
          <div>
            <p className="eyebrow">Studio konten AI untuk hospitality Indonesia</p>
            <h1>
              Tim AI yang menyiapkan. <span className="accent">Tim kamu yang memutuskan.</span>
            </h1>
            <p className="lead">
              {team.length} agent AI dengan keahlian berbeda, dari caption dan balasan review sampai laporan bulanan.
              Setiap draft melewati persetujuan manusia sebelum tayang.
            </p>
            <dl className="kpis">
              <div>
                <dt>Agent aktif</dt>
                <dd>{active.length}</dd>
              </div>
              <div>
                <dt>Pilar layanan</dt>
                <dd>{pillars.length}</dd>
              </div>
              <div>
                <dt>Kasus uji kualitas</dt>
                <dd>{countEvalCases()}</dd>
              </div>
            </dl>
          </div>
          <div className="hero__visual" aria-hidden="true">
            {lead.map((m, i) => (
              <div key={m.id} className={`hero__char hero__char--${i}`}>
                <Character look={m.look} uniform={UNIFORM[m.status]} uid={`hero-${m.id}`} />
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="section" id="tim">
        <div className="container">
          <Carousel title="Kenalan dengan tim" intro="Klik kartu untuk melihat keahlian, batas kerja, dan level persetujuan tiap agent.">
            {team.map((m) => (
              <AgentCard key={m.id} member={m} />
            ))}
          </Carousel>
        </div>
      </section>

      <section className="section section--alt" id="cara-kerja">
        <div className="container">
          <div className="section-head">
            <div>
              <h2>Cara kerja</h2>
              <p className="section-intro">Empat langkah yang sama untuk setiap konten.</p>
            </div>
          </div>
          <ol className="steps">
            {STEPS.map(([title, body], i) => (
              <li key={title}>
                <span className="steps__n">{String(i + 1).padStart(2, "0")}</span>
                <h3>{title}</h3>
                <p>{body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="section" id="pilar">
        <div className="container">
          <div className="section-head">
            <div>
              <h2>Tim per pilar</h2>
              <p className="section-intro">Pilar Marketing & Content dan Analytics sudah berjalan. Pilar lain disiapkan bertahap.</p>
            </div>
          </div>
          {groups.map((g) => (
            <div key={g.title} className="pillar">
              <div className="pillar__head">
                <span className="pillar__n">{g.n}</span>
                <h3>{g.title}</h3>
                <span className="pillar__count">
                  {g.members.length} agent · {g.status}
                </span>
              </div>
              <div className="grid">
                {g.members.map((m) => (
                  <AgentCard key={m.id} member={m} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="section section--dark" id="tata-kelola">
        <div className="container">
          <div className="section-head">
            <div>
              <h2>Tata kelola</h2>
              <p className="section-intro">AI membantu bekerja lebih cepat. Tanggung jawab tetap di tangan manusia.</p>
            </div>
          </div>
          <ul className="gov">
            {GOVERNANCE.map(([title, body]) => (
              <li key={title}>
                <h3>{title}</h3>
                <p>{body}</p>
              </li>
            ))}
          </ul>
        </div>
      </section>
    </>
  );
}
