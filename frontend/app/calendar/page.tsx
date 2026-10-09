import { PageHeader, SimNotice } from "../../components/ui";
import { CONTENT, SIM_DATE, STATUS, STATUS_ORDER, clientName } from "../../lib/demo";
import { monthYear } from "../../lib/format";
import { L } from "../../lib/i18n";

export const metadata = { title: "Calendar · CLAU" };

const DOW = [["Mon", "Sen"], ["Tue", "Sel"], ["Wed", "Rab"], ["Thu", "Kam"], ["Fri", "Jum"], ["Sat", "Sab"], ["Sun", "Min"]];

export default function CalendarPage() {
  const [y, m] = SIM_DATE.split("-").map(Number);
  const first = new Date(Date.UTC(y, m - 1, 1));
  const offset = (first.getUTCDay() + 6) % 7;
  const start = new Date(Date.UTC(y, m - 1, 1 - offset));
  const days = Array.from({ length: 42 }, (_, i) => {
    const d = new Date(start);
    d.setUTCDate(start.getUTCDate() + i);
    return d.toISOString().slice(0, 10);
  });

  return (
    <>
      <PageHeader title={<L en="Content calendar" id="Kalender konten" />} subtitle={<L en={`${monthYear(SIM_DATE, "en")} · publish dates for every client`} id={`${monthYear(SIM_DATE, "id")} · tanggal tayang semua klien`} />} />
      <SimNotice />
      <div className="legend">
        {STATUS_ORDER.map((s) => (
          <span key={s} className={`badge badge--${STATUS[s].tone}`}><L en={STATUS[s].en} id={STATUS[s].id} /></span>
        ))}
      </div>
      <section className="panel panel--flush">
        <div className="cal">
          {DOW.map(([en, id]) => (
            <div key={en} className="cal__dow"><L en={en} id={id} /></div>
          ))}
          {days.map((iso) => {
            const items = CONTENT.filter((c) => c.date === iso);
            const out = Number(iso.slice(5, 7)) !== m;
            return (
              <div key={iso} className={`cal__day${out ? " cal__day--out" : ""}${iso === SIM_DATE ? " cal__day--today" : ""}`}>
                <span className="cal__num">{Number(iso.slice(8))}</span>
                {items.map((c) => (
                  <span key={c.id} className={`cal__item cal__item--${STATUS[c.status].tone}`}>
                    {c.title}
                    <span className="sr-only">
                      {" · "}{clientName(c.client)} · <L en={STATUS[c.status].en} id={STATUS[c.status].id} />
                    </span>
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
