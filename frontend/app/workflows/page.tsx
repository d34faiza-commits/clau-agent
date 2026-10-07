import { Card, PageHeader } from "../../components/ui";

export const metadata = { title: "Alur kerja · CLAU" };

const FLOW: { title: string; body: string; who: "ai" | "human" }[] = [
  { title: "Brief & data klien", body: "Tim menulis kebutuhan. Fakta penting (harga, promo, fasilitas) dikonfirmasi owner.", who: "human" },
  { title: "Routing ke agent", body: "Permintaan diarahkan ke agent yang sesuai keahliannya. Tugas di luar batas dieskalasi ke owner.", who: "ai" },
  { title: "Draft oleh agent", body: "Agent menulis draft memakai Voice Card klien dan kartu persona agent.", who: "ai" },
  { title: "Cek otomatis", body: "Draft dicek terhadap aturan: frasa terlarang, klaim tanpa bukti, panjang, CTA.", who: "ai" },
  { title: "Review manusia", body: "Dicek sesuai level L1–L3. L2 dan L3 wajib orang kedua yang bukan pembuat brief.", who: "human" },
  { title: "Persetujuan", body: "Konten yang lolos review disetujui dan dijadwalkan.", who: "human" },
  { title: "Publish", body: "Tim mempublish lewat aplikasi resmi platform. AI tidak pernah publish sendiri.", who: "human" },
];

export default function Workflows() {
  return (
    <>
      <PageHeader title="Alur kerja" subtitle="Satu alur yang sama untuk setiap konten, dari brief sampai tayang." />
      <div className="grid-2">
        <Card title="Alur produksi konten" flush>
          <ol className="flow">
            {FLOW.map((f, i) => (
              <li key={f.title}>
                <span className={`flow__n flow__n--${f.who}`}>{i + 1}</span>
                <div>
                  <h3>{f.title}</h3>
                  <p>{f.body}</p>
                </div>
                <span className={`who who--${f.who}`}>{f.who === "ai" ? "AI" : "Manusia"}</span>
              </li>
            ))}
          </ol>
        </Card>
        <div className="stack">
          <Card title="Level persetujuan" flush>
            <dl className="facts">
              <dt>L1</dt>
              <dd>Dicek satu orang di tim</dd>
              <dt>L2</dt>
              <dd>Dicek orang kedua (bukan pembuat brief)</dd>
              <dt>L3</dt>
              <dd>Wajib persetujuan owner</dd>
            </dl>
          </Card>
          <Card title="Yang tidak dilakukan AI">
            <ul className="bullets">
              <li>Publish ke media sosial atau OTA</li>
              <li>Mengirim pesan langsung ke tamu</li>
              <li>Menyetujui hasil kerjanya sendiri</li>
              <li>Mengarang fakta yang belum dikonfirmasi</li>
            </ul>
          </Card>
        </div>
      </div>
    </>
  );
}
