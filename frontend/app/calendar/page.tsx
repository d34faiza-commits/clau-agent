import { PageHeader, SimNotice } from "../../components/ui";
import { CONTENT, SIM_DATE, STATUS, STATUS_ORDER, clientName } from "../../lib/demo";

export const metadata = { title: "Kalender · CLAU" };

const DOW = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"];

export default function CalendarPage() {
  const [y, m] = SIM_DATE.split("-").map(Number);
  const first = new Date(Date.UTC(y, m - 1, 1));
  const offset = (first.getUTCDay() + 6) % 7; // Senin = 0
  const start = new Date(Date.UTC(y, m - 1, 1 - offset));
  const days = Array.from({ length: 42 }, (_, i) => {
    const d = new Date(start);
    d.setUTCDate(start.getUTCDate() + i);
    return d.toISOString().slice(0, 10);
  });

  return (
    <>
      <PageHeader title="Kalender konten" subtitle="Oktober 2026 · tanggal tayang per konten" />
      <SimNotice />
      <div className="legend" style={{ marginBottom: 12 }}>
        {STATUS_ORDER.map((s) => (
          <span key={s} className={`badge badge--${STATUS[s].tone}`}>
            {STATUS[s].label}
          </span>
        ))}
      </div>
      <section className="panel panel--flush">
        <div className="cal">
          {DOW.map((d) => (
            <div key={d} className="cal__dow">
              {d}
            </div>
          ))}
          {days.map((iso) => {
            const items = CONTENT.filter((c) => c.date === iso);
            const out = Number(iso.slice(5, 7)) !== m;
            return (
              <div key={iso} className={`cal__day${out ? " cal__day--out" : ""}${iso === SIM_DATE ? " cal__day--today" : ""}`}>
                <span className="cal__num">{Number(iso.slice(8))}</span>
                {items.map((c) => (
                  <span
                    key={c.id}
                    className={`cal__item cal__item--${STATUS[c.status].tone}`}
                    title={`${c.title} · ${clientName(c.client)} · ${STATUS[c.status].label}`}
                  >
                    {c.title}
                  </span>
                ))}
              </div>
            );
          })}
        </div>
      </section>
    </>
  );
}
