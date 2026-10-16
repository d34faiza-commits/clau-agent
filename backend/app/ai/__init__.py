"""AI menulis draft (Tahap 2, kontrak core 0.9.0, AI-BOUNDARY 1.4.0 § Data ke Provider AI).

Alur: endpoint membuat job di antrean (`ai_jobs`) → worker (`python -m app.ai.worker`, container terpisah, satu-satunya
pemegang API key) mengambil job → prompt dari aturan + fakta klien yang dikonfirmasi + request yang disamarkan →
provider → AI fact-check → draft agent + klaim + QA otomatis → review & approval manusia. Tidak ada publish.
"""
