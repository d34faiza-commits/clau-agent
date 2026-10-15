#!/usr/bin/env bash
# Salinan backup VPS 2 di luar server: Backblaze B2, bucket privat dengan Object Lock (docs/deploy/vps-2-setup.md § I).
# Dipasang sebagai /usr/local/sbin/clau-vps2-offsite oleh vps2-setup.sh.
#
#   sudo clau-vps2-offsite setup          # sekali: isi key B2 (prompt tersembunyi), uji kirim + uji kunci hapus
#   sudo clau-vps2-offsite push FILE      # kirim backup + .hmac (dipanggil clau-vps2-backup)
#   sudo clau-vps2-offsite list           # daftar backup di B2: NAMA UKURAN
#   sudo clau-vps2-offsite pull NAMA DIR  # ambil backup + .hmac dari B2 ke DIR
#
# Key B2 disimpan di /etc/clau/offsite.env (600 root) dan diberikan ke rclone lewat environment, tidak pernah lewat
# argumen command line. File backup sudah terenkripsi (AES-256) sebelum dikirim: B2 tidak pernah melihat isinya.
# Object Lock di bucket membuat backup tidak bisa dihapus selama masa retensi, juga oleh orang yang menguasai server.
set -euo pipefail

CONF="${CLAU_OFFSITE_ENV:-/etc/clau/offsite.env}"
STAMP="${CLAU_OFFSITE_STAMP:-/srv/clau/.offsite-last}"
REMOTE=clauoff
PREFIX=vps2
NAME_RE='^clau-[0-9]{8}T[0-9]{6}Z(-[a-z0-9-]{1,32})?\.dump\.enc$'
RCLONE=(rclone -q --retries 3 --low-level-retries 10 --stats 0)

die() { echo "GAGAL: $*" >&2; exit 1; }
load() {
  [ -f "$CONF" ] || die "B2 belum disetel (sudo clau-vps2-offsite setup)"
  set -a; . "$CONF"; set +a
  [ -n "${CLAU_OFFSITE_BUCKET:-}" ] || die "CLAU_OFFSITE_BUCKET kosong di $CONF"
  dest="$REMOTE:$CLAU_OFFSITE_BUCKET/$PREFIX"
}
# --immutable: file yang sudah ada di B2 tidak pernah ditimpa (nama backup selalu baru).
send() { "${RCLONE[@]}" copyto --immutable "$1" "$dest/$(basename "$1")"; }

case "${1:-}" in
  push)
    file="${2:-}"
    [ -s "$file" ] && [ -s "$file.hmac" ] || die "backup atau .hmac tidak ada: $file"
    [[ "$(basename "$file")" =~ $NAME_RE ]] || die "nama backup tidak dikenal: $file"
    load
    send "$file"
    send "$file.hmac"
    printf '%s %s\n' "$(date +%s)" "$(basename "$file")" > "$STAMP"
    echo "salinan B2: $(basename "$file") → $CLAU_OFFSITE_BUCKET/$PREFIX/"
    ;;
  list)
    load
    "${RCLONE[@]}" lsf --files-only --format ps --separator ' ' "$dest" | awk -v re="$NAME_RE" '$1 ~ re'
    ;;
  pull)
    name="${2:-}" dir="${3:-}"
    [[ "$name" =~ $NAME_RE ]] || die "nama backup tidak valid: $name"
    [ -d "$dir" ] || die "folder tujuan tidak ada: $dir"
    load
    umask 077
    "${RCLONE[@]}" copyto "$dest/$name" "$dir/$name"
    "${RCLONE[@]}" copyto "$dest/$name.hmac" "$dir/$name.hmac"
    echo "diambil dari B2: $dir/$name"
    ;;
  setup)
    [ "$(id -u)" -eq 0 ] || [ -n "${CLAU_OFFSITE_ENV:-}" ] || die "jalankan dengan sudo"
    command -v rclone >/dev/null || die "rclone belum terpasang (jalankan ulang vps2-setup.sh)"
    echo "Isi dari Backblaze → Application Keys (simpan juga di password manager; key hanya tampil sekali)."
    read -rp "keyID: " key_id || key_id=""
    read -rsp "applicationKey (tidak tampil saat diketik/paste): " app_key || app_key=""; echo
    read -rp "Nama bucket: " bucket || bucket=""
    [[ "$key_id" =~ ^[A-Za-z0-9]{10,64}$ ]] || die "keyID tidak valid"
    [[ "$app_key" =~ ^[A-Za-z0-9+/=_-]{20,100}$ ]] || die "applicationKey tidak valid"
    [[ "$bucket" =~ ^[A-Za-z0-9-]{6,63}$ ]] || die "nama bucket tidak valid"
    umask 077
    tmp="$CONF.baru"
    {
      echo "# clau-vps2-offsite setup $(date -u +%FT%TZ). Jangan dibagikan. Backup key ini di password manager."
      printf 'RCLONE_CONFIG_%s_TYPE=%s\n' "${REMOTE^^}" "${CLAU_OFFSITE_TYPE:-b2}"
      printf 'RCLONE_CONFIG_%s_ACCOUNT=%s\n' "${REMOTE^^}" "$key_id"
      printf 'RCLONE_CONFIG_%s_KEY=%s\n' "${REMOTE^^}" "$app_key"
      printf 'CLAU_OFFSITE_BUCKET=%s\n' "$bucket"
    } > "$tmp"
    CONF="$tmp" load
    # Uji tulis dengan file kecil (bukan backup: server baru belum punya data yang benar).
    probe="$(mktemp)"
    trap 'rm -f "$probe"' EXIT
    echo "uji clau-vps2-offsite $(date -u +%FT%TZ)" > "$probe"
    probe_name="uji-kunci-$(date -u +%Y%m%dT%H%M%SZ).txt"
    "${RCLONE[@]}" copyto "$probe" "$dest/$probe_name" || { rm -f "$tmp"; die "tidak bisa menulis ke bucket $bucket (cek keyID, applicationKey, nama bucket, akses Read and Write)"; }
    mv "$tmp" "$CONF"
    chown root:root "$CONF" 2>/dev/null || true
    chmod 600 "$CONF"
    echo "OK  kirim ke B2 berhasil ($bucket/$PREFIX/)"
    # Object Lock: hapus permanen harus ditolak. Bila berhasil terhapus, bucket belum dikunci.
    "${RCLONE[@]}" deletefile --b2-hard-delete "$dest/$probe_name" >/dev/null 2>&1 || true
    if "${RCLONE[@]}" lsf "$dest/$probe_name" 2>/dev/null | grep -q .; then
      echo "OK  Object Lock aktif: file di B2 tidak bisa dihapus dari server ini"
    else
      echo "PERINGATAN: file uji bisa dihapus permanen. Aktifkan Object Lock + Default Retention di bucket (panduan § I)."
    fi
    echo "Selesai. Backup berikutnya (02/08/14/20 WITA) otomatis disalin ke B2. Cek: sudo clau-vps2-check"
    ;;
  *)
    sed -n '2,12p' "$0"; exit 2
    ;;
esac
