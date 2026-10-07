import AgentCard from "../components/AgentCard";
import Carousel from "../components/Carousel";
import { PILLARS, getTeam } from "../lib/team";

const STEPS = [
  ["Kirim brief", "Ceritakan kebutuhan: caption, balasan review, kalender konten, atau laporan."],
  ["Agent menyiapkan draft", "Agent AI yang sesuai keahliannya menulis draft dengan gaya brand properti kamu."],
  ["Manusia mengecek", "Tim kamu mereview dan menyetujui. Draft penting dicek orang kedua."],
  ["Kamu yang publish", "Konten dipublish atau dikirim oleh manusia lewat aplikasi resmi, bukan oleh AI."],
];

export default function Home() {
  const team = getTeam();
  const active = team.filter((m) => m.status === "active");
  const pillars = Object.entries(PILLARS)
    .map(([n, name]) => ({ n: Number(n), name, members: team.filter((m) => m.pillar === Number(n)) }))
    .filter((p) => p.members.length > 0);

  return (
    <>
      <section className="hero">
        <div className="container">
          <p className="eyebrow">CLAU AI · Tim AI untuk hospitality Indonesia</p>
          <h1>
            Kenalan dengan tim AI <span className="accent">properti kamu</span>
          </h1>
          <p className="lead">
            {team.length} agent AI dengan keahlian masing-masing: dari caption dan review sampai laporan bulanan. Mereka
            menyiapkan draft. Kamu dan tim yang memutuskan.
          </p>
          <div className="stats">
            <span>
              <b>{active.length}</b> aktif
            </span>
            <span>
              <b>{team.length - active.length}</b> segera hadir
            </span>
            <span>
              <b>{pillars.length}</b> pilar
            </span>
          </div>
        </div>
        <div className="container container--wide">
          <Carousel label="Tim agent AI">
            {team.map((m) => (
              <AgentCard key={m.id} member={m} />
            ))}
          </Carousel>
        </div>
      </section>

      <section className="section">
        <div className="container">
          <h2>Cara kerja</h2>
          <ol className="steps">
            {STEPS.map(([title, body], i) => (
              <li key={title}>
                <span className="steps__n">{i + 1}</span>
                <h3>{title}</h3>
                <p>{body}</p>
              </li>
            ))}
          </ol>
        </div>
      </section>

      <section className="section section--muted">
        <div className="container">
          <h2>Tim per pilar</h2>
          {pillars.map((p) => (
            <div key={p.n} className="pillar">
              <h3 className="pillar__title">
                <span className="pillar__n">{p.n}</span> {p.name}
              </h3>
              <div className="grid">
                {p.members.map((m) => (
                  <AgentCard key={m.id} member={m} />
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    </>
  );
}
