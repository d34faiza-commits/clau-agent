import Link from "next/link";
import { Empty } from "../components/ui";

export default function NotFound() {
  return (
    <section className="panel">
      <Empty icon="inbox" title="Halaman tidak ditemukan" body="Alamat ini tidak ada atau sudah dipindahkan." action={<Link href="/" className="btn btn--secondary">Kembali ke dashboard</Link>} />
    </section>
  );
}
