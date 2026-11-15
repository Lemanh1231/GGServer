# Source update — 2026-11-16

## Current update

- Repair the stale `ResourceLoaderTest` contract, not the catalog: validate every
  table against numeric data, preserve exact historical-capture comparison except
  the three documented CH2/UI changes, assert cookie product 31 and reject bad
  manifest counts. No catalog/capture values or prices/rewards were changed.
- Restore the legitimate main/test Java `data` packages omitted by the previous
  publication's broad ignore rule, without allowing runtime player-data folders.
- Include the Encore regression/strict-ID, UTC+7/future-attendance, Star Pass
  purchase/storage optimization and shared manual Sale/50 CP projection fixes.
  These are combined source changes, not a Sale-only binary.
- Apply the requested OpenAI `security-threat-model` workflow, including owner
  confirmation of public game/private admin, evidence-grounded abuse paths and
  isolated security tests. See `GGServerJava-threat-model.md` for residual risks.
- Fix the newly reproduced direct guest-login alias substitution after explicit
  owner approval. Existing accounts require the exact stored device credential;
  UID/u_id/canonical lookup aliases cannot substitute for it. A migrated account
  with different canonical/device IDs still logs in using its real device.
  Regression failed on SQLite and Mongo memory before the fix, then passed.
- Preserve sanitized example configuration, portable layout test and existing
  resource defaults. Do not publish live posts/configuration, account data,
  captures/logs, backups, APKs or signing material.

## Current verification and limitations

- Before the new security cases: working source and sanitized publication each
  passed 370/370 tests; publication `test fatJar installDist` succeeded.
- Isolated security-focused checks passed 100/100 tests. Guest-login follow-up
  also passed its focused SQLite/Mongo, session, codec and HTTP transport tests.
- Final sanitized publication: **378 tests passed, 0 failures/errors/skips**;
  `test fatJar installDist` succeeded with JVM timezone UTC. Four parser cases and
  four SQLite/Mongo guest-identity cases are included in that total.
  Candidate SHA-256:
  `b403a0fe5fdaa05bc5e01fb9092755586b68b010ffa20ca89b09efd8d564fcd3`.
- `detect-secrets` scan found 32 candidates, manually reviewed as SHA-256 metadata,
  synthetic fixtures, UI localization text and example/test passwords. No private
  credential was identified in those candidates. File inventory checks also
  exclude runtime/private artifacts; this is not proof of a secret-free history
  or a full dependency-vulnerability audit.
- Source publication only: no candidate deployment, APK change, player-data reset,
  compensation or live exploit/load test. The guest credential secrecy, trusted
  proxy controls, parser resource budgets, capture retention and admin hardening
  still require review. Passing tests is not a security certification.

## Previous source update — 2026-11-15

- Synchronize Java gameplay fixes and regression tests for chapter progression,
  event/shop rules, offline currency, follower/Messenger access and mailbox rewards.
- Include current MongoDB deployment/backup examples and migration documentation.
- The experimental custom WSS/FCM/local-notification project is canceled; none of
  its transport, receiver or dependency code is included in this source update.
- Runtime configurations, player databases, captures, backups, APKs and signing
  credentials are excluded. Existing sanitized example configuration is retained.

### Historical verification and limitations

The local source suite before publication ran 285 tests: 284 passed and one
stale catalog parity test failed. That test contract is resolved in the current
update above; these historical counts are not the current validation result.

This is a source publication, not a server deployment. The running production
binary has historical differences from this repository; publishing does not
establish byte-for-byte equivalence or authorize replacing a live server build.
