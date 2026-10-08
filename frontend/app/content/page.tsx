import { Suspense } from "react";
import ContentBoard from "../../components/ContentBoard";
import { SimNotice } from "../../components/ui";
import { monthlyRun } from "../../lib/run";
import { getTeam } from "../../lib/team";

export const metadata = { title: "Content · CLAU" };

export default function ContentPage() {
  const agents = Object.fromEntries(getTeam().map((m) => [m.id, { name: m.name, hue: m.hue, look: m.look, uniform: m.uniform, image: m.image }]));
  return (
    <Suspense>
      <SimNotice />
      <ContentBoard agents={agents} steps={monthlyRun()} />
    </Suspense>
  );
}
