# Backend (FastAPI scaffold)

API read-only di atas registry agent dan router statis. **Tidak ada** endpoint yang publish konten, mengirim pesan ke tamu, atau mengubah sistem client (`core/AI-CONSTITUTION.md` §4). Kontrak: `core/shared/api-contracts.md`.

## Jalankan

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload          # http://127.0.0.1:8000/docs
pytest                                  # test API + konsistensi registry ↔ core router
```

## Endpoint

| Method & path | Fungsi |
|---|---|
| `GET /health` | Status service |
| `GET /agents` | Daftar agent dari `../agents/registry.json` + forbidden actions |
| `POST /route` | `{"intent": "caption"}` → agent, pilar, skill, repo, approval minimum, status |

## Belum Ada (Planned)

Database (lihat `core/shared/database-schema.md`), autentikasi, pemanggilan AI model, endpoint requests/drafts/qa-records/approvals.
