# SQLite → MongoDB account migration

`emu.leman.ggserver.migration.SqliteToMongo` is an explicit, insert-only migration
for the Python emulator's **actual `emulator/data/database.db`**. It does not use
the Python server, initialize the source through `StateStore`, replace SQLite
files, delete accounts, or automatically change the configured backend.

## Before migrating

1. Stop both the Python and Java servers and any other database writers. Keep
   them stopped through validation, import, and verification.
2. Back up the original SQLite database **together with any `-wal` file**. Keep
   this backup and the original after migration. Back up an existing MongoDB
   destination separately as well. Do not delete sidecars to make a migration run.
3. Choose MongoDB explicitly in the configuration used for migration and Java
   startup. For example, in `resources/server-config.json`:

   ```json
   {
     "folders": { "data": "java-data" },
     "database": {
       "backend": "mongo",
       "uri": "mongodb://127.0.0.1:27017",
       "name": "ggserver"
     }
   }
   ```

   MongoDB connection credentials may be supplied using `GG_MONGO_URI`, and
   `GG_MONGO_DATABASE` overrides the database name. The program does not print
   the connection URI. The backend must still be selected explicitly in config.
   Relative configured folder paths resolve according to `ServerConfig`, not
   relative to the source database. The source path is independent of
   `folders.data`; no SQLite database is initialized there for a Mongo migration.

4. Build the runnable dependency-inclusive JAR (`./gradlew fatJar`). Run these
   commands from `GGServerJava`, adjusting the JAR filename if the version changes.

## Validate first

```sh
java -cp build/libs/ggserver-1.0.0-all.jar \
  emu.leman.ggserver.migration.SqliteToMongo \
  --config resources/server-config.json \
  --source ../emulator/data/database.db \
  --dry-run
```

Omitting both `--dry-run` and `--apply` also means dry-run. Dry-run validates all
source accounts, inventory JSON and identities, checks SQLite integrity, and
checks all destination account collisions. It imports **no accounts**. Opening
the configured MongoDB `StateStore` may create its normal indexes and initialize
or reconcile the sequence counter; this is not a read-only MongoDB inspection.

The program reads original SQLite files as ordinary input streams only. It
copies the main database and any WAL/journal to a private temporary directory,
then queries that copy using read-only JDBC and `query_only`. Committed WAL
records are included. The original main database, WAL, SHM and journal are
SHA-256 hashed before and after migration; original sidecars are never created,
checkpointed or removed by this tool. If source contents change during the
snapshot or preflight, the migration fails before importing accounts. A change
during import is reported as failure/partial, never successful completion.

## Apply

```sh
java -cp build/libs/ggserver-1.0.0-all.jar \
  emu.leman.ggserver.migration.SqliteToMongo \
  --config resources/server-config.json \
  --source ../emulator/data/database.db \
  --apply
```

`--dry-run` and `--apply` are mutually exclusive. There is no `--replace` option.
By default, **any** destination collision aborts the entire preflight before an
account is imported, including a collision discovered on the final source
account. Collision detection covers canonical UUID, device UUID, `u_id`, numeric
sequence and cross-field/guest identifier aliases. Duplicate source identities,
missing identities, invalid JSON, unknown inventory types and orphan inventory
rows also fail validation instead of silently discarding or changing data.

To deliberately skip already occupied identities, pass `--skip-existing` on
both the validation and apply commands. This skips the **whole source account**;
it does not merge inventories or overwrite destination data. Review the reported
collision UUIDs. A collision can belong to a different account: skipping it is
not proof that the existing account contains the desired source data.

Each account is imported atomically, including its full inventories, currencies,
ban and connection metadata. Source SQL identity and currency columns take
precedence over stale `user_contents_json`. Arbitrary user JSON, exact GP/reset
fields, `created_at`, inventory `extra_json`, and JSON-only starter inventories
are retained. For each inventory type, separated SQL rows supersede the JSON
inventory only when that type has separated rows. New account sequences advance
past the greatest imported sequence; sequences are not renumbered.

## Reports, failures and recovery

The final standard-output line is a JSON report containing:

- `status`: `validated`, `complete`, `failed`, or `partial`;
- `mode`, source path, `sourceAccounts`, `inventoryRows`, `eligible`, `skipped`
  and acknowledged `imported` account counts;
- `collisions` when destination preflight ran;
- `sourceSha256Before`, `sourceSha256After`, and `sourceUnchanged`;
- `error` on failure. The command also exits unsuccessfully on a failure.

Only `complete` with `sourceUnchanged: true` is successful apply completion.
There is no all-accounts transaction: a network or database failure can leave
earlier accounts imported. `partial` is not success and does not trigger deletion
or rollback of those accounts. `imported` counts acknowledged completed calls;
a network failure can have an uncertain last-write outcome. Keep the report,
inspect destination accounts, and rerun dry-run. After verification, an explicit
`--skip-existing --apply` can resume the remaining accounts. Never blindly
delete existing destination data to resolve a failure.

After applying, verify representative accounts by UUID, device and guest ID,
currencies, bans and inventories; check that the next created sequence exceeds
the migrated maximum. Start Java with the same MongoDB configuration only after
verification. Retain the original SQLite files and backups. Migration does not
transfer live sessions: clients must establish new sessions after cutover.

## Tests

`SqliteToMongoTest` covers dry-run, authoritative SQL fields, all account metadata,
inventory extras and JSON-only starters, preflight collisions, explicit skips,
corrupt input, committed WAL records, byte-for-byte original-file preservation,
concurrent source changes and partial-failure reporting. Its embedded MongoDB
wire-protocol integration test exercises the real `StateStore` import, reopen,
configured folders and sequence advancement without requiring an external server.

```sh
./gradlew test --tests emu.leman.ggserver.migration.SqliteToMongoTest
```
