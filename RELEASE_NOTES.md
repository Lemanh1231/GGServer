# Source update — 2026-11-15

- Synchronize Java gameplay fixes and regression tests for chapter progression,
  event/shop rules, offline currency, follower/Messenger access and mailbox rewards.
- Include current MongoDB deployment/backup examples and migration documentation.
- The experimental custom WSS/FCM/local-notification project is canceled; none of
  its transport, receiver or dependency code is included in this source update.
- Runtime configurations, player databases, captures, backups, APKs and signing
  credentials are excluded. Existing sanitized example configuration is retained.

## Verification and limitations

The local source suite before publication ran 285 tests: 284 passed and one
pre-existing catalog parity test failed (`ResourceLoaderTest`, expected 4065 rows,
actual 4066). No assertion or catalog data was changed to conceal this mismatch.

This is a source publication, not a server deployment. The running production
binary has historical differences from this repository; publishing does not
establish byte-for-byte equivalence or authorize replacing a live server build.
