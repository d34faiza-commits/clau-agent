"""HMAC-SHA256 file backup (hex), kunci dari env CLAU_HMAC_KEY: passphrase tidak pernah jadi argumen proses
(argumen terbaca semua user lewat `ps`; environment hanya oleh pemilik proses). Sama dengan format lama
`openssl dgst -sha256 -hmac`, jadi .hmac lama tetap cocok.

    CLAU_HMAC_KEY=… python3 -I scripts/backup_hmac.py FILE
"""

import hashlib
import hmac
import os
import sys

mac = hmac.new(os.environ["CLAU_HMAC_KEY"].encode(), digestmod=hashlib.sha256)
with open(sys.argv[1], "rb") as f:
    for chunk in iter(lambda: f.read(1 << 20), b""):
        mac.update(chunk)
print(mac.hexdigest())
