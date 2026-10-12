"""Koneksi aplikasi ke database (role aplikasi, tanpa hak DDL).

URL dibaca dari CLAU_DATABASE_URL. Backend tetap bisa jalan tanpa database (endpoint registry read-only
tidak memakainya); endpoint yang butuh database memanggil get_engine() dan gagal jelas bila belum diatur.
"""

from __future__ import annotations

import os
from functools import lru_cache

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import sessionmaker


@lru_cache(maxsize=1)
def get_engine() -> Engine:
    url = os.environ.get("CLAU_DATABASE_URL", "")
    if not url:
        raise RuntimeError("CLAU_DATABASE_URL belum diatur (lihat .env.example)")
    # pool_pre_ping: koneksi putus (restart Postgres) diganti otomatis, bukan error ke pengguna.
    return create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)


def session_factory() -> sessionmaker:
    return sessionmaker(bind=get_engine(), expire_on_commit=False)
