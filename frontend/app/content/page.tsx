import { Suspense } from "react";
import ContentBoard from "../../components/ContentBoard";
import { SimNotice } from "../../components/ui";
import { getTeam } from "../../lib/team";

export const metadata = { title: "Konten · CLAU" };

export default function ContentPage() {
  const agents = Object.fromEntries(getTeam().map((m) => [m.id, m.name]));
  return (
    <Suspense>
      <ContentBoard agents={agents} />
      <div style={{ marginTop: 16 }}>
        <SimNotice />
      </div>
    </Suspense>
  );
}
