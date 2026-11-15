# Star Pass purchase performance

Source-only optimization, 2026-11-15. This is not a production deployment.

## Sale correctness follow-up

`StarPassShopRules` now shares the manual Sale policy between authoritative
purchase checks and the `getGameDataList` shop projection. Closing Sale disables
the 26 merchandise products (2001–2013, 3001–3013) in the projection and rejects
their RPC purchases, including a purchase after a previously successful preflight.
Opening Sale does not override a catalog-inactive product.

Season-three aliases 2003/3003 retain their existing effective 50 CP price. The
projection now reports 50 in `i_SellValue` and the four schema store-price strings,
using the same rule as deduction. The immutable catalog, other prices, titles and
descriptions are unchanged. Native popup/cache behavior still requires Android
verification; no forced account/APK data clearing is part of this fix.
No automatic schedule or expiry date has been introduced.

Sale-specific checks: 19 focused cases pass (15 SQLite/Mongo purchase cases and
4 policy cases), including malformed/missing configuration, immediate config
refresh, unchanged catalog and non-price fields. Actual candidate-JAR probes
verify 13 seasonal grants, closed-event denial without account mutation, all
26 inactive projections, and a Thrift roundtrip of the five season-three price
fields. These do not verify native Android rendering or invalidate its cache.
Candidate SHA-256 for this follow-up:
`f3e67ff8c6ad149c28f11cef08c1f7febd28d4fa73636f0bf062f7ec19b8c571`.
Evidence: `/tmp/opencode/star-pass-sale-fixed-jar-audit.json` and
`/tmp/opencode/star-pass-sale-final-focused.log`.
The earlier Sale follow-up had 368 tests with one stale catalog regression.
That regression is now repaired: the catalog/numeric sources correctly contain
4,066 rows; the historical capture differs only by the intentional cookie product,
Vietnamese received label and ad cooldown. Tests retain exact comparison of all
other data, per-table counts, explicit cookie contracts and malformed-count checks.
After repair, both working source and sanitized publication passed **370/370**
tests, with no errors/skips; JAR and publication installDist packaging succeeded.
Final sanitized publication including parser and guest-login security cases:
**378/378 passed**, no failures/errors/skips; `test fatJar installDist` succeeded
with JVM timezone UTC. Candidate SHA-256:
`b403a0fe5fdaa05bc5e01fb9092755586b68b010ffa20ca89b09efd8d564fcd3`.
See `RELEASE_NOTES.md` for publication provenance.

### Deployment acceptance checklist (not yet executed)

1. Review the combined candidate against deployed behavior, including earlier
   Encore/UTC+7/storage changes and the security threat model. The catalog
   regression has been resolved without changing catalog data or the capture.
2. Use a staging root/database and the actual candidate JAR. Exercise Sale open,
   closed, successful preflight followed by closure, insufficient funds, aliases,
   retry, save failure, and reopen on the deployment backend.
3. Obtain authorization for a maintenance deployment and a consistent backend
   backup. Preserve old binary, config, APK/signing material and all account data.
4. After deployment, verify health/version, client price display after normal
   metadata refresh, and purchase completion using an approved test account.
   Do not close the global Sale merely to test against real players.
5. Roll back only to a reviewed compatible binary if necessary; do not restore an
   old database over newer player progress. Remove the corresponding `loi.md`
   entry only once production verification is complete.

## Changes and invariants

- `EconomyData`: index the existing lifetime catalog snapshot by product ID and
  reward group; preserve first matching ID, group order, duplicates and strict
  reward validation. Each reward response remains a fresh mutable list/map.
- `EconomyModule.buyShop`: reuse the normalized shop for eligibility, ad history
  and receipts. Preserve ad-level normalization for non-ad purchases, native DTOs,
  ownership checks, prices (including 50 CP for 2003/3003), subscriptions and tickets.
- Star-card checks use one fresh event snapshot; operator switches are not cached.
- SQLite inventory saves reuse prepared statements and execute batches inside the
  existing transaction. Explicit empty sections still delete inventory; omitted
  sections remain untouched; the last duplicate item still wins.
- Account locking resolves only canonical identity instead of reconstructing all
  inventories twice per command. UUID/device/guest/sequence aliases still share
  the same lock. No identity cache or lock removal.
- Payment, inventory and receipts still commit together. No success is returned
  before save completion. Mongo snapshot/CAS publication is unchanged.

## Repeatable characterization

`StarPassPurchaseBenchmarkTest` uses the real public catalog, a synthetic account
with 236 inventory rows and populated shop history, isolated SQLite and an
in-process Mongo memory server. Each scenario warms up for 40 iterations, then
reports p50/p95 from 80 iterations. It measures `buyCheck` → `buyShop` →
`checkBuyShop` through the handler registry, including identity lookup, database
work and locking, **not HTTP, TLS, codec, network, Android callbacks or live Mongo**.
The fixture resets the synthetic account before each purchase, outside the timer.
Measurements are warm-path, single-request-at-a-time results, not cold startup or
multi-account load testing. The economy-wide monitor remains in place, so queueing
under production concurrency is not claimed to be eliminated.
Mongo published snapshot history is retained by design in both runs; the same
fixture and iteration count are used so this is not a cleanup/GC optimization.

Use a Gradle init script to redirect `layout.buildDirectory` outside `build/`:
the production JAR must not be overwritten during measurement. There are no
timing assertions: shared-host load, JVM warmup and Mongo memory behavior vary.
For before/after comparisons, use two separate source projects **and** separate
build directories. Do not replace `compileJava` sources in-place with a Gradle
init script: incremental outputs may otherwise be shared and invalidate the
baseline. Earlier exploratory timings are not the final comparison.

### Verified isolated-source comparison

Milliseconds, 80 measured samples per scenario after 40 warmups:

| Store | Product | buyShop p50 before → after | buyShop p95 before → after | Full workflow p50 before → after |
|---|---|---:|---:|---:|
| SQLite | 2003 merchandise | 17.648 → 11.207 | 32.221 → 15.021 | 22.124 → 14.682 |
| SQLite | 1003 star card | 17.109 → 10.422 | 19.148 → 15.266 | 21.678 → 13.190 |
| Mongo memory | 2003 merchandise | 204.627 → 141.558 | 286.187 → 190.536 | 474.188 → 272.683 |
| Mongo memory | 1003 star card | 199.538 → 136.050 | 271.495 → 188.479 | 448.152 → 264.846 |

`buyShop` median reduction is 36–39% on SQLite and 31–32% on Mongo memory
in this run. Complete workflow median reduction is 34–39% and 41–43%, respectively.
Logs: `/tmp/opencode/star-pass-verified-before.log`,
`/tmp/opencode/star-pass-verified-after.log`; aggregate comparison:
`/tmp/opencode/star-pass-benchmark-comparison.json`. Baseline source hashes and
bytecode were checked to confirm the old full-account identity load, unbatched
SQL and unindexed reward path; candidate bytecode confirms the optimized paths.

## Regression coverage

`StarPassPurchaseRegressionTest` covers merchandise aliases, card prices,
entitlements, unchanged Pass progress, preflight without persistence, reopen,
insufficient funds, event switches, malformed IDs/rewards, concurrent requests
using different account aliases, and SQLite save-failure rollback/retry.
`EconomyDataIndexTest` checks lookup ordering and response isolation.
`SqliteInventoryBatchTest` checks replacement/partial-save/duplicate semantics.
The 12 purchase/storage compatibility cases also pass against the isolated
pre-optimization source, confirming these tests preserve existing rules rather
than introducing a new price/reward policy.
An exact fixed-clock synthetic comparison of response DTOs and all purchase-owned
sections also matches the baseline for all 46 public shop products, including
1003/2003/3003, ad shop 3 and daily shop 10012 (only SHA-256 results retained).
Unavailable products compare rejection behavior, not a successful grant.

Historical optimization validation: 360 tests, 359 passed, one stale catalog
regression (now resolved as described above), no errors/skips. The 14 new
regression cases and 11 timezone cases also pass with the JVM timezone set to UTC.
An actual candidate-JAR probe confirms the 2003 purchase, 50 CP deduction,
canonical device alias and duplicate 3003 rejection without using source classes.

## Remaining verification

The candidate is not deployed. A separate recovery restarted the unchanged old
production JAR after its process disappeared; that cause remains unresolved.
The candidate also contains
earlier Encore and UTC+7 source changes, so deploying it requires a combined
review rather than treating it as an optimization-only binary. Live before/after
RPC timing and Android purchase completion still need verification after an
authorized deployment. Mongo memory timings must not be presented as live Mongo
latency or as proof that the user's full perceived delay has been resolved.
