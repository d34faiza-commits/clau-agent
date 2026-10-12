# SUBMODULE.md — Koneksi Antar Repo CLAU AI

Panduan Git submodule untuk tiga repo CLAU AI. File ini identik di `clau-ai-marketing` dan `clau-ai-agents`. Kalau mengubahnya, ubah di keduanya.

## 1. Topologi

```text
clau-ai-marketing
├── core/      → clau-ai-core     (branch main)
└── agents/    → clau-ai-agents   (branch main)
    └── core/  → clau-ai-core     (pin milik clau-ai-agents)

clau-ai-agents
└── core/      → clau-ai-core     (branch main)

clau-ai-core   (tidak punya submodule)
```

| Repo | Submodule | Kegunaan |
|---|---|---|
| clau-ai-marketing | `core/` | Constitution, boundary, workflow umum, orchestrator |
| clau-ai-marketing | `agents/` | Registry agent dan kode platform yang menjalankan skill Pilar 1 (referensi & validasi silang) |
| clau-ai-agents | `core/` | Aturan induk; router di `core/orchestrator/router.md` dites terhadap `agents/registry.json` |

Prinsip yang perlu diingat:

- **Submodule = pin ke satu commit**, bukan salinan yang ikut berubah otomatis. Repo induk menyimpan hash commit submodule; isi file tetap di repo aslinya.
- **Edit di repo asal**, bukan di folder submodule. Perubahan di `core/` atau `agents/` di dalam repo lain tidak ikut ke repo aslinya dan akan tertimpa saat sync.
- Semua repo **private**: akun atau token yang meng-clone harus punya akses ke ketiga repo.
- `agents/core/` mengikuti pin milik clau-ai-agents. Script sync dan workflow mengecek pin core sama di semua tempat (`scripts/check-core-pins.sh`).

## 2. Clone Pertama Kali

```bash
git clone --recurse-submodules https://github.com/d34faiza-commits/clau-ai-marketing.git

# Kalau sudah ter-clone tanpa submodule (folder core/ atau agents/ kosong):
git submodule update --init --recursive
```

## 3. Cara Update Submodule

Cara paling aman adalah memakai script. Script ini menjalankan validator sebelum commit dan membuat satu commit per submodule, sesuai `core/AI-BOUNDARY.md` §Multi-Repo & Submodule:

```bash
scripts/sync-submodules.sh              # sync ke terbaru + validasi + commit + push
scripts/sync-submodules.sh --dry-run    # lihat perubahan saja, tanpa commit
scripts/sync-submodules.sh --no-push    # commit lokal, push sendiri nanti
```

Manual (kalau perlu kontrol penuh), contoh untuk `core`:

```bash
git submodule update --remote core      # ambil commit terbaru branch main di clau-ai-core
git -C core log --oneline -5            # cek apa yang berubah
python3 scripts/validate.py --require-submodules   # (marketing) atau: cd backend && pytest (agents)
git add core
git commit -m "chore(core): bump core to $(git -C core rev-parse --short HEAD)"
git push
```

Untuk mengunci submodule ke commit tertentu (rollback):

```bash
git -C core checkout <hash>
git add core && git commit -m "chore(core): pin core to <hash>"
```

## 4. Cara Sync

"Sync" punya dua arti yang sering tertukar:

| Perintah | Fungsi | Kapan |
|---|---|---|
| `git submodule update --init --recursive` | Samakan isi folder submodule dengan **pin** yang tercatat di repo induk | Setelah `git pull`, ganti branch, atau clone |
| `git submodule update --remote <path>` | Majukan submodule ke commit **terbaru** branch-nya (pin berubah, perlu commit) | Saat mau mengambil perubahan baru dari repo asal |
| `git submodule sync --recursive` | Salin URL dari `.gitmodules` ke `.git/config` | Setelah URL submodule di `.gitmodules` berubah |

Supaya `git pull` otomatis ikut menyamakan submodule:

```bash
git config submodule.recurse true
```

## 5. Otomasi GitHub Actions

| Workflow | Repo | Trigger | Fungsi |
|---|---|---|---|
| `notify-downstream.yml` | core, agents | Push ke `main` | Kirim `repository_dispatch` (`submodule-updated`) ke repo konsumen: core → agents & marketing; agents → marketing |
| `sync-submodules.yml` | marketing, agents | Harian 06.17 WITA, manual, `submodule-updated` | Jalankan `scripts/sync-submodules.sh --pr-branch bot/sync-submodules`: majukan pin, validasi, commit `chore(<path>): bump …`, push ke branch `bot/sync-submodules`, lalu buka PR ke `main` (workflow menunggu semua check PR; merge hanya bila hijau, merah = PR dibiarkan terbuka dan job gagal) |
| `cross-repo-validate.yml` | marketing, agents | Push, PR, manual, `submodule-updated` | Checkout semua submodule, lalu validator core, validator repo dengan `--require-submodules`, test backend agents terhadap router core, dan cek pin core |
| `validate.yml` / `ci.yml` | semua | Push, PR | Validasi tanpa submodule (tidak butuh token); referensi ke submodule dilewati |

Kalau validasi gagal, sync **tidak** commit dan workflow merah. Pin lama tetap dipakai sampai masalahnya diperbaiki di repo asal.

### Setup GitHub Actions (sekali saja)

`GITHUB_TOKEN` bawaan Actions hanya bisa mengakses repo tempat workflow berjalan, jadi tidak bisa meng-clone submodule private atau memicu repo lain. Karena itu dibutuhkan satu token:

1. GitHub → **Settings → Developer settings → Personal access tokens → Fine-grained tokens → Generate new token**.
2. **Repository access:** *Only select repositories* → `clau-ai-core`, `clau-ai-marketing`, `clau-ai-agents`.
3. **Permissions → Repository permissions → Contents: Read and write** dan **Pull requests: Read and write** (bot membuka PR sync karena `main` terproteksi). Metadata (read) otomatis ikut.
   Aktifkan juga **Settings → General → Allow auto-merge** di clau-ai-marketing dan clau-ai-agents agar PR sync ter-merge lewat auto-merge bila proteksi `main` dipaksa server. Tanpa itu, workflow tetap menunggu CI hijau sebelum merge.
4. Expiration: pilih tanggal, lalu catat tanggal perpanjangannya.
5. Simpan token sebagai secret **`SUBMODULE_TOKEN`** di **ketiga** repo: repo → **Settings → Secrets and variables → Actions → New repository secret**.

Selama secret belum ada, workflow `sync-submodules`, `cross-repo-validate`, dan `notify-downstream` tetap hijau tapi dilewati, dengan notice "SUBMODULE_TOKEN belum diset".

**RISK:** token ini bisa menulis ke ketiga repo. Jangan simpan token di file, jangan bagikan, dan cabut (revoke) kalau bocor. Commit dari bot tercatat atas nama `github-actions[bot]`.

## 6. Troubleshooting

| Gejala | Penyebab | Solusi |
|---|---|---|
| Folder `core/` atau `agents/` kosong | Clone tanpa `--recurse-submodules` | `git submodule update --init --recursive` |
| `git status` menampilkan `modified: core (new commits)` | Isi submodule maju tapi pin belum di-commit, atau pin di-pull tapi folder belum disamakan | Mau dipakai: `git add core && git commit`. Mau dibatalkan: `git submodule update --init --recursive` |
| `fatal: repository not found` / `Authentication failed` saat clone submodule | Akun/token tidak punya akses ke repo private submodule | Pastikan akses ke ketiga repo; di Actions cek secret `SUBMODULE_TOKEN` dan scope repo-nya |
| `HEAD detached at …` di dalam submodule | Normal: submodule di-checkout ke commit pin | Mau mengedit? Jangan di sini. Edit di repo asal. Kalau terlanjur: `git -C core switch main` lalu pindahkan perubahan ke clone repo asal |
| `fatal: reference is not a tree: <hash>` | Pin menunjuk commit yang belum di-push di repo asal | Push dulu repo asal (urutan: core → agents → marketing), lalu `git submodule update --init --recursive` |
| `working tree tidak bersih` dari `sync-submodules.sh` | Ada perubahan lokal | Commit atau `git stash`, lalu jalankan ulang |
| Warning "pin clau-ai-core berbeda antar submodule" | `agents/core` tertinggal dari `core/` (atau sebaliknya) | Sync clau-ai-agents dulu, lalu sync marketing. Otomatis lewat `notify-downstream` bila token ada |
| Workflow sync merah setelah perubahan di core | Perubahan core membuat validator/test di repo ini gagal | Baca log step validasi. Perbaiki di repo yang tepat (core atau repo ini), lalu jalankan workflow ulang (**Actions → Sync Submodules → Run workflow**) |
| URL submodule berubah (repo di-rename/pindah) | `.git/config` masih memakai URL lama | Edit `.gitmodules`, lalu `git submodule sync --recursive && git submodule update --init --recursive` |
| `git pull` tidak ikut memperbarui submodule | Default Git | `git config submodule.recurse true`, atau jalankan `git submodule update --init --recursive` setelah pull |
