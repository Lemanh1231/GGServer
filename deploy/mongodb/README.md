# Local MongoDB deployment

Deployed 2026-11-13 with the user's approval to restore the 7-account SQLite
backup from 2026-11-12. Later remote progress is not recoverable from that backup.

- Compose: `compose.yaml`, project `ggserver-local`.
- MongoDB 8.0 image pinned by digest; restart policy `unless-stopped`.
- Host listener **127.0.0.1:27017 only**, authenticated; no public MongoDB port.
- Database `ggserver`; application user `ggserver_app` has `readWrite` only there.
- Named durable volume `ggserver-local_mongo_data`. Never use `down -v` or remove
  this volume to repair connectivity.
- Separate root/application credentials under `/etc/ggserver/mongodb/`, host
  directory mode 0700. Secret files are readable by the container's MongoDB user
  through read-only mounts. Credentials are not committed or shown in commands.
- Java connection lives in the private `resources/server-config.json`; launcher
  environment `GG_MONGO_URI`/`GG_MONGO_DATABASE` overrides must not point elsewhere.

## Restore verification

Imported **7 accounts / 983 SQL inventory rows**, insert-only into the new local
database. All full reconstructed account exports (including balances/inventory)
and UUID/device/UID aliases matched the source backup after numeric normalization.
Source SQLite SHA-256 remained
`ca1f3ba13373b54b39ba2a1e58757596c2f753188cc7031565755be8ee3e9ee1`.
All seven accounts use the split collection layout (31 collections initially,
zero `users.contents` blobs). Read-only native admin confirmed seven users.

Original JAR/config, pre-cutover full MongoDB archive and previous published APKs
are preserved in `/var/backups/ggserver/20261113-local-cutover/` (root-only).
Remote MongoDB was not modified, dropped or merged. Original SQLite is unchanged.

## Operations

From repository root:

```bash
docker compose -f GGServerJava/deploy/mongodb/compose.yaml ps
docker compose -f GGServerJava/deploy/mongodb/compose.yaml up -d --wait
./run.sh status
bash GGServerJava/deploy/mongodb/backup.sh
systemctl status ggserver-mongo-backup.timer
```

Daily timer runs around 04:15 in the host timezone. Backups, logs and SHA-256 files
are private under `/var/backups/ggserver/mongodb/`; no automatic deletion/retention
policy is applied. Monitor disk use (split snapshots are also retained). MongoDB
is standalone: stop Java/all writers for a consistent manual backup or restore;
the daily online dump is best-effort and not a cross-collection snapshot.
The cutover archive was made before Java connected and is consistent.

For recovery, first stop Java and back up the current database. Prefer restoring
to a fresh database/volume and verifying full account exports before switching;
never blindly drop the live database. A version-2 split database needs **all**
child collections, not just `users`. Application-only credentials cannot restore
admin users; preserve `/etc/ggserver/mongodb/` separately and securely.

The timer service uses this host's absolute repository path; adjust it if moving
the checkout. Docker starts the MongoDB container after host reboot; the existing
Java lifecycle remains controlled separately by `run.sh`.
