# Separated MongoDB player collections

**2026-11-13 deployment update:** split storage is now live on authenticated local
MongoDB (`127.0.0.1:27017`, `ggserver`). With explicit user approval, the 7-account
SQLite backup was restored insert-only (983 inventory rows); all exported state
and identity aliases matched. Remote MongoDB was not modified. See
[deploy/mongodb/README.md](deploy/mongodb/README.md). The earlier pending notes
at the bottom are historical; there was no remote in-place split migration.

## Layout (storage version 2)

`users` retains canonical `_id`/UUID, device/UID aliases, `u_seq`, balances,
attendance, ban/network metadata, revision and **section references only**.
The old `contents` gameplay blob is removed when an account is converted.

| Collection | Content |
| --- | --- |
| `user_profiles` | Non-balance `userdata` profile fields |
| `user_unit`, `user_skill`, `user_music`, `user_guitar` | Owned inventory, one item per row |
| `user_costumes`, `user_prop`, `user_shop` | Costumes, props and shop inventory |
| `user_follower`, `user_follower_giftitem` | Followers and gift inventory |
| `user_follower_profile`, `user_follower_profile_reward`, `user_follower_quest` | Follower progress/rewards/quests |
| `user_areas`, `user_achievements`, `user_characters` | Areas, achievements and characters |
| `user_posts`, `user_messenger` | Mail/rewards and messenger state |
| `user_ap`, `user_ch_third_stage`, `user_chthird_stage` | Energy and chapter progress (both legacy spellings preserved) |
| `user_daily_mission`, `user_event_point`, `user_buff` | Missions, event points and buffs |
| `user_ad_level`, `user_ticketcollection`, `user_subscribe_list`, `user_tutorial` | Ads, tickets, subscriptions and tutorials |
| `user_state` | Remaining metadata and unknown fields, separated by field/key; never silently dropped |
| `counters` | Durable UID sequence (unchanged) |

Each child row contains `uuid`, `snapshot`, `field`, `position`, `data`, plus
`key` for map entries. Arrays are separate rows, maps are separate key rows;
scalars use one row. Empty maps/lists and nulls are preserved in the manifest.
Ownership/snapshot/field/position have a compound unique index. Child
collections are created as needed by writes, not by reads.

## Consistency and queries

All feature rows for a save are staged first. A revision-checked replacement of
`users` then publishes references to those rows atomically. A failed competing
save discards **only its own unpublished** rows and retries. Ambiguous publication
failures retain rows because the write might have succeeded. Readers follow the
captured manifest; missing rows fail visibly rather than resetting a player's data.
This works with standalone MongoDB and replica sets, without requiring transactions.

Child collections contain historical snapshots, not just current state. For a
current inventory query, use the user's `sections.<field>.snapshot` reference:

```javascript
const u = db.users.findOne({u_seq: 100001});
const ref = u.sections.user_music;
db.user_music.find({uuid: u._id, field: 'user_music', snapshot: ref.snapshot})
  .sort({position: 1});
```

Do not edit child rows directly while the server is running. Immutable history
keeps in-flight readers consistent and helps recovery, but increases storage.
No automatic history garbage collection is included in this release. Before
production use at scale, plan offline backup/GC while **all writers and readers
are stopped**. Explicit account deletion removes its current publication/rows;
older history remains until such offline cleanup. Retention is not secure erasure.

## Compatibility and explicit migration

Legacy `users.contents` accounts remain readable without migration on reads.
New accounts and accounts whose gameplay contents are saved use version 2;
mutation of a legacy account also converts it atomically. The game-facing API,
SQLite backend, account aliases, UID counter, numeric normalization and game
protocol do not change. This storage refactor does **not** fix APK error 20001.

Build first. The migration CLI defaults to a read-only dry run and refuses an
empty users collection, to catch selecting the wrong MongoDB target:

```bash
java -cp build/libs/ggserver-1.0.0-all.jar \
  emu.leman.ggserver.migration.SplitMongoUsers \
  --config resources/server-config.json --dry-run
```

For apply, stop every Java instance and any other database writer first. Take a
full MongoDB backup with your normal backup tooling. The tool additionally writes
an Extended-JSON backup of the original account documents to a **new**, private
directory before converting any legacy account:

```bash
java -cp build/libs/ggserver-1.0.0-all.jar \
  emu.leman.ggserver.migration.SplitMongoUsers \
  --config resources/server-config.json --apply --writers-stopped \
  --backup resources/data/migration-backups/mongo-split-UNIQUE_TIMESTAMP
```

It preserves identity/balances, checks each original document against the backup,
compares exports before/after conversion and skips already-separated accounts.
No collection is dropped. A failure can leave a partially converted database;
both formats remain supported and rerunning is safe after verifying the backup.
The account JSON backup alone is not a full backup of an already-separated DB:
back up all child collections as well. To roll back, stop all access and restore
the appropriate full backup; do not deploy an old one-document-only server against
converted accounts.

Live migration has **not** been applied. The current configured MongoDB endpoint
returned no `ggserver` database/accounts during inspection, unlike the earlier
7-account migration. Verify the correct endpoint/database/backup before cutover;
do not recreate identities or reimport stale SQLite over live accounts.
