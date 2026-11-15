#!/usr/bin/env bash
# Full authenticated local database dump; no credentials in argv or logs.
set -euo pipefail
umask 077
container=ggserver-local-mongodb-1
root=/var/backups/ggserver/mongodb
mkdir -p "$root"
chmod 700 "$root"
directory="$(mktemp -d "$root/$(date -u +%Y%m%dT%H%M%SZ)-XXXXXX")"
archive="$directory/ggserver.archive.gz"
if ! docker exec "$container" mongodump --config=/run/secrets/backup_config \
    --host=127.0.0.1 --username=gg_local_admin --authenticationDatabase=admin \
    --db=ggserver --archive --gzip > "$archive.partial" 2> "$directory/dump.log"; then
    echo "MongoDB backup failed; private partial/log retained at $directory" >&2
    exit 1
fi
test -s "$archive.partial"
mv "$archive.partial" "$archive"
sha256sum "$archive" > "$archive.sha256"
echo "MongoDB backup saved: $archive"
