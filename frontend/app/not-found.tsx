import Link from "next/link";
import { Empty } from "../components/ui";
import { L } from "../lib/i18n";

export const metadata = { title: "Not found · CLAU" };

export default function NotFound() {
  return (
    <section className="panel">
      <Empty heading="h1" icon="inbox" title={<L en="Page not found" id="Halaman tidak ditemukan" />} body={<L en="This address does not exist or has moved." id="Alamat ini tidak ada atau sudah dipindahkan." />} action={<Link href="/" className="btn btn--secondary"><L en="Back to dashboard" id="Kembali ke dashboard" /></Link>} />
    </section>
  );
}
