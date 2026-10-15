-- Ringkasan isi database CLAU dalam satu baris, untuk membandingkan database yang sedang dipakai dengan isi
-- backup sebelum memulihkan (scripts/db-restore.sh --verify, scripts/deploy/vps2-restore.sh). Hanya membaca.
-- Tabel yang belum ada di skema lama (backup dari versi sebelumnya) ditulis "-".
WITH n(label, tbl, ord) AS (
  VALUES ('user', 'users', 1), ('klien', 'clients', 2), ('request', 'requests', 3), ('draft', 'drafts', 4),
         ('fact sheet', 'fact_sheets', 5), ('audit', 'audit_log', 6)
)
SELECT string_agg(
         label || ' ' || CASE WHEN to_regclass('public.' || tbl) IS NULL THEN '-'
           ELSE (xpath('/row/c/text()', query_to_xml('SELECT count(*) AS c FROM public.' || tbl, false, true, '')))[1]::text END,
         ', ' ORDER BY ord)
       || ', aktivitas terakhir '
       || CASE WHEN to_regclass('public.audit_log') IS NULL THEN '-'
            ELSE coalesce((xpath('/row/t/text()', query_to_xml(
              $q$SELECT to_char(max(created_at) AT TIME ZONE 'Asia/Makassar', 'YYYY-MM-DD HH24:MI') || ' WITA' AS t FROM public.audit_log$q$,
              false, true, '')))[1]::text, '-') END
FROM n;
