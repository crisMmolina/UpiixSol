#!/usr/bin/env bash
# Daily backup (UPS-015): Postgres dump (custom format) + uploaded media, with rotation.
#   deploy/backup.sh                    # run from the repo root on the server
#   cron: 30 3 * * * cd /opt/upiixsol && deploy/backup.sh >> /var/log/upiixsol-backup.log 2>&1
# Env: BACKUP_DIR (default ~/upiixsol-backups, outside the git clone), KEEP_DAYS (default 14). Restore: docs/runbook.md §Restore.
set -euo pipefail

cd "$(dirname -- "$0")/.."
umask 077  # dumps contain personal data (emails, boletas): owner-only dir and files
backup_dir=${BACKUP_DIR:-$HOME/upiixsol-backups}
keep_days=${KEEP_DAYS:-14}
stamp=$(date -u +%Y%m%dT%H%M%SZ)
mkdir -p "$backup_dir"

db_file="$backup_dir/db-$stamp.dump"
media_file="$backup_dir/media-$stamp.tar.gz"
trap 'rm -f "$db_file.partial" "$media_file.partial"' EXIT  # a failed run leaves nothing behind

# pg_dump runs inside the db container, so the password never leaves it. Write to a .partial name first:
# a failed dump never looks like a valid backup and is never rotated in.
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --format=custom --no-owner' \
  > "$db_file.partial"
mv "$db_file.partial" "$db_file"

docker compose exec -T api tar -C /data -czf - media > "$media_file.partial"
mv "$media_file.partial" "$media_file"

# Rotation: only our own finished files, older than KEEP_DAYS.
find "$backup_dir" -maxdepth 1 -type f \( -name 'db-*.dump' -o -name 'media-*.tar.gz' \) \
  -mtime +"$keep_days" -print -delete

printf 'BACKUP_OK %s %s (%s, %s)\n' "$db_file" "$media_file" \
  "$(du -h "$db_file" | cut -f1)" "$(du -h "$media_file" | cut -f1)"
