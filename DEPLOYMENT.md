# Java production routing & control center

## Current hotfix: provider identity normalization (2026-11-13)

This section supersedes the earlier APK checksum below. Native Java and the
same-key **IdentityFix** APK are deployed/published together. The historical phone
DTO sent the patched PlayGame placeholder in `uuid`, despite a valid known stored
device. The guest adapter now checks device/game aliases before returning a
normalized encoded DTO and session. Because the wire user DTO has no UUID field,
protected calls still carrying the exact placeholder are normalized only after
validating an issued session, exact stored device, and every supplied game UID.
No shared placeholder alias is created; real mismatched UUIDs remain rejected.
Auth 401/403 no longer triggers gateway domain failover. Adapter capture now adds
safe `identity_check` reason categories without credentials. See
[verification/PROVIDER_ID_FIX.md](verification/PROVIDER_ID_FIX.md).

Download: `https://kotori.click/download/Guitar_Girl_v8.0.0_Java_8181_IdentityFix.apk`.
All existing Java/SessionFix/PrimaryFirst/Universal/NoGooglePlay aliases serve the
same new bytes, 480,706,770 bytes; SHA-256
`96e9b996dd3b26cc5841e245d6b4005ba940d55223ee1e74007c35fbed0f97c4`.
V2/v3 signature, original certificate, zipalign and unchanged manifest verified.
Every request still tries kotori.click first, with the same ordered HTTPS backups.

Verification: 189 Java tests, 4 gateway tests; 50 strict differential scenarios
plus 128 full-feature calls / 60 commands / zero failures. Gateway/native Java
placeholder login/relogin/protected load succeeded in disposable storage with
mandatory sessions. Four public domains passed routing, APK HEAD/range, and
malformed adapter rejection checks. Android gameplay still needs a phone retry.

Java stopped before JAR replacement and MongoDB full backup; restarted on 8181,
PID at deployment 3171152. No live account recreation or gameplay login was used
for smoke checks. Previous JAR/config/APKs preserved privately under
`/var/backups/ggserver/20261113-provider-fix/`. Consistent stopped-writer database
archive: `/var/backups/ggserver/mongodb/20261112T192540Z-jtOJFi/` (UTC timestamp).

## Current deployment: local MongoDB + primary-first APK (2026-11-13)

**This section supersedes the pending/blocked status below.** The user approved
hosting MongoDB locally and restoring the known 7-account backup, acknowledging
that progress after the backup is unavailable. Local authenticated MongoDB is
healthy at `127.0.0.1:27017`, database `ggserver`, with a dedicated durable Docker
volume. Full reconstructed exports and UUID/device/UID alias checks matched all
7 restored accounts / 983 SQL inventory rows. All accounts use split collections.
See [deploy/mongodb/README.md](deploy/mongodb/README.md) for secrets, backups and
operation. Remote MongoDB and source SQLite were not changed.

Java was stopped through its managed launcher before the verified staged JAR was
installed and restarted on 8181 (PID at cutover: 3128322). Native opaque guest
session adapter, catalog rules and split storage are now deployed. Admin sees
seven accounts; four-domain routing checks passed; malformed adapter requests
on all domains receive no session. No real player login was simulated against
production to manufacture a device-success result.

The signed primary-first APK is now published:
`https://kotori.click/download/Guitar_Girl_v8.0.0_Java_8181_PrimaryFirst.apk`.
Java_8181, SessionFix, Universal and NoGooglePlay links serve identical bytes.
Size 480,706,770; SHA-256
`fffc6fcb3563b1c85b48c0fd23042f82fdc5337b50cccbd0553be27c0dfc9b91`.
All four domains passed APK HEAD/range checks. Same certificate, zipalign and
v2/v3 signatures verified. Every request retries `kotori.click` first; ordered
backups are only used on upstream failures. Device gameplay remains unverified;
update in place, never uninstall or clear guest data.

Pre-cutover JAR/config/full local MongoDB archive and previous APKs are preserved
in `/var/backups/ggserver/20261113-local-cutover/`. Daily private MongoDB backups
are scheduled with `ggserver-mongo-backup.timer`; online standalone dumps are not
atomic across collections, so stop writers for consistent recovery snapshots.

## Pending primary-first APK (2026-11-13)

User-confirmed routing policy: **each request** tries `https://kotori.click`
first, then `https://kotorin.click`, `https://kotorin.dev`, and
`https://kotorin.me`, all on 443. Successful fallback is diagnostic state only;
legacy persisted active-domain selection is ignored. No load balancing/sticky
backup selection. DNS/TCP/TLS errors, HTTP 5xx/408/429 trigger fallback; ordinary
authentication failures do not. If primary stays down, every request incurs its
timeout again. CDN responses already streamed to the client cannot safely restart
midstream, and retrying a POST after a lost response is not exactly-once delivery.

This build includes the opaque login bridge below and uses the existing signing
key. APK staging/signature verification does not authorize replacing the running
Java JAR or migrating an unidentified MongoDB database. Public publication must
wait for the matching native endpoint and the correct player database/backup.
Primary-first gateway regression tests cover backup order, retrying primary after
fallback, primary recovery, all-domain failure, unchanged request bodies, and no
fallback on HTTP 401.

Staged APK: `/tmp/opencode/gg-primary-first-apk-20261113/Guitar_Girl_v8.0.0_Universal.apk`
(480,706,770 bytes), SHA-256
`fffc6fcb3563b1c85b48c0fd23042f82fdc5337b50cccbd0553be27c0dfc9b91`.
Zipalign and v2/v3 signatures verified against the existing certificate
`63260d7f7ee0669e1473deab29aa39fcd3ad132e052a23670663898d8968a763`;
manifest matches the published SessionFix. Embedded DEX matches rebuilt source
output and contains the opaque adapter path plus primary-first policy strings.
Four gateway regressions passed; disposable gateway → Java login/relogin/load
returned code 0 with mandatory sessions. No Android device verification or public
publication. Build/verify logs: `/tmp/opencode/gg-primary-first-apk-build.log`,
`/tmp/opencode/gg-primary-first-apk-verify.log`; staged metadata: `release-staged.json`
beside the APK. Existing download aliases/APKs remain unchanged.

## Pending login/catalog repair (not deployed)

The 21:26 device capture established that the failing `userLogin` credential was
opaque (37 characters, one pipe field), so the published pipe-only SessionFix did
not request a fresh SDK session. The source now supports an opaque-token exchange
at `/api/accounts/v3/global/game-session`. Java decodes the existing login/join
DTO, checks the stored device and all supplied account aliases, rejects bans and
issues an ordinary server session. Protected RPC validation remains enabled.
This is **device-based guest authentication**, like the existing `device_cd`
endpoint, not cryptographic verification of Play Games/PmangPlus credentials.

Daily mission definitions now use the existing named server catalog (IDs, active
flags, conditions and aggregate completion). Mission/achievement rewards resolve
named fields, including the noncontiguous higher achievement reward fields.
See [verification/LOGIN_CATALOG_RESULTS.md](verification/LOGIN_CATALOG_RESULTS.md)
for isolated tests and limitations.

**Neither this Java endpoint nor the opaque-token bridge is deployed/published.**
The currently published SessionFix APK is 480,706,770 bytes, SHA-256
`b421b1a214c85fedf2a3e8610b2ab2fbf091794ca617a1af85f9f56ac1e6e076`.
Older APK checksums below are historical. Device success is not yet verified.
Deploying this source also deploys the pending MongoDB split described below;
confirm the correct player database and backups before replacing the running JAR.
The new bridge requires an in-place, same-key APK update together with Java;
never uninstall, clear guest data, reopen Python gameplay, or fabricate accounts
to work around the missing database.

## Pending storage refactor: separate MongoDB collections

The Mongo repository source now separates player features from `users.contents`;
see [MONGO_COLLECTIONS.md](MONGO_COLLECTIONS.md) for schema, consistency,
retention, migration and backup instructions. 182 Java tests passed and a real
MongoDB disposable-database smoke confirmed separate inventory rows, legacy
conversion/export parity, alias lookup and currency spending. The test database
was removed after verification; no player database was migrated.

**Not deployed:** the source was built into `/tmp/opencode/gg-mongo-split-build`
without replacing the running server JAR or restarting Java. Inspection of the
currently configured MongoDB target returned no `ggserver` database/accounts.
This differs from the earlier 7-account migration and blocks live conversion
until the correct target/backup is confirmed. Do not reimport stale SQLite,
generate replacement identities, or treat an empty dry run as successful migration.

## Current release: old/new APK split (2026-11-12)

### Session refresh hotfix

#### Device follow-up / safe route diagnostics

Retired Python bootstrap now defaults to `http://127.0.0.1:28765`, including
requests arriving directly at a shared domain without gateway headers. This
restores the APK gateway so its release marker can choose Java versus retirement;
it does not itself authorize gameplay. Public checks passed on all four domains.

`/var/log/nginx/gg-release.log` records game-path routing, release marker,
upstream, status, and loopback-proxy header, not bodies, credentials, or queries.
The 21:12 +0700 device retry was unmarked and reached Python. After loopback
recovery, the 21:19 retry reached Java for time/login with the release marker,
but `userLogin` still received 401 and no fresh SDK login was seen. This confirms
routing recovery, **not** successful device session refresh. The user confirmed
installing SessionFix on a physical Android phone. Cached direct routing and
installed-version ambiguity must not be treated as proven root causes.

Rejected Java sessions now include `session_diagnostics` in the existing capture:
presence, length, pipe-field count, encoded-pipe flag and normalized form type
only. No token value/hash or app/device identity is added. This is diagnostic
only: session validation remains unchanged. A fresh device retry is required to
capture the shape and determine whether framing/form parsing prevents refresh.

The first Java APK reached Java correctly but retained the cached Python SDK
token. Device traffic completed bootstrap then repeatedly received 401 on
`userLogin` (reported client error 20001). `SessionTokenBridge` now obtains a fresh
server-issued token via `/api/accounts/v3/global/login` before game login/join,
using the cached SDK device/app identity. It replaces only the access-token form
field and keeps the mapping in process memory for subsequent calls. It never
imports a caller token into server sessions, disables account checks, logs tokens,
or clears device preferences. Missing/unrecognized token framing is still rejected
normally by Java. Both multipart and urlencoded forms have regression tests.

The actual gateway → SDK login → Java userLogin flow passed with response code 0
against disposable SQLite, without writing live MongoDB. Android device validation
is still required. See `../out/java-8181-release.json` for the current APK checksum;
the first-build hash below is historical after this hotfix.

The APK has now been **rebuilt and published** as `java-8181-v1`:

- Download: `https://kotori.click/download/Guitar_Girl_v8.0.0_Java_8181.apk`
  (same file also published at the historical NoGooglePlay/Universal links).
- 480,702,674 bytes; SHA-256:
  `ff08521e2438f170060c4101020a2a8c323006f2fa9f714b1d011f53bfcd043c`.
- Same package and signing key/certificate as the old APK; v2/v3 signature and
  zipalign verified. Install/update in place; do not uninstall or clear guest data.
- Gateway still uses the same four HTTPS domains on **443**, with local loopback
  port 28765. It adds `X-GG-Client-Release: java-8181-v1` on every upstream request.
  This is a deployment selector, **not authentication**.
- `/etc/nginx/conf.d/zz-gg-client-release.conf` maps that exact marker to Java
  **8181**; missing/other markers route game/CDN/SDK paths to retired Python
  **8080**. `/admin`, `/download`, `/health` always remain on Java.
- Python permits only bootstrap/SDK/UI assets then returns native Thrift error
  900 with the download notice for login/gameplay. No player database imports or
  writes; see `../emulator/RETIRED.md`.
- Java public bootstrap no longer rejects cached/expired SDK tokens, allowing
  the client to reach fresh authentication. This grants no session identity and
  performs no account-IP updates. Protected calls still reject invalid tokens.
- Root `run.sh` controls Java only. Retired Python has a separate recorded PID
  and no automatic reboot service.

Verification: `python3 verification/release_routing.py` probes both markers on
all four domains without creating accounts. Legacy login gets 900/update notice;
new invalid-token probe gets 401 (proves Java, not successful gameplay).
Gateway JVM test confirms header injection from the actual gateway source.
Android ART/device login and the legacy popup still require a device check.

Backup before this cutover: `resources/data/deployment-backups/20261112T113823Z/`
contains previous Nginx config and preserved old published APKs. APK build and
verification logs: `/tmp/opencode/gg-java-8181-apk-build.log`. Release metadata:
`../out/java-8181-release.json`. Build staged with `--no-export` before publication.

**The sections below describe the initial domain cutover; where they differ,
this current-release section takes precedence.**

## Public endpoints

All four existing APK domains now route Guitar Girl to the **same Java instance**
at `127.0.0.1:8181`:

- `https://kotori.click`
- `https://kotorin.click`
- `https://kotorin.dev`
- `https://kotorin.me`

Each supports `/health`, `/admin`, `/download`, `/download/apk`, game RPC,
NeonAPI authentication and `/AssetBundles/`. TLS verification passed for the four
bare domains. Do not assume every `www` alias is covered by this certificate.

The active shared Nginx site is `/etc/nginx/sites-available/kotori.click`, enabled
by a symlink in `sites-enabled/`. Only its six Guitar Girl upstreams changed
from `8080` to `8181`. The static homepage and unrelated applications are retained.
This host uses Nginx, not Cloudflare Tunnel. Validate before every reload:

```bash
/usr/sbin/nginx -t
/usr/sbin/nginx -s reload
```

Changing Java's port also requires updating these upstreams; `run.sh` deliberately
does not rewrite system Nginx config. Failover domains share one host/database;
they are not four independent backend servers. No automatic boot service was added.

## Root launcher (JDK 21, Bash, curl, flock, Linux /proc)

From the repository root:

```bash
./run.sh               # New terminal menu; noninteractive invocation shows status
./run.sh status
./run.sh logs          # Ctrl+C returns from the menu's log view
./run.sh web           # 16 HTTPS HEAD checks, nonzero exit if any fail
./run.sh paths         # Safe config/JAR/log paths; no secrets
./run.sh stop
./run.sh build         # Java test + fatJar + installDist; refuses a live build
./run.sh start
./run.sh restart
```

The menu delegates lifecycle to `serverctl.sh`. PID + Linux start-time + exact
JAR/config argv checks protect unrelated processes and stale PID reuse. A
manually launched server is reported as **UNMANAGED**, not adopted or killed.
Build/test failure is reported without auto-resetting data. Check the output
before starting after a failed build. Stop before building to avoid replacing
classes/JARs underneath an active JVM.

Runtime config: `resources/server-config.json`; MongoDB remains the live backend.
Console: `resources/logs/server.log`; rolling application log:
`resources/logs/latest.log`. Explicit caller environment overrides win over `.env`;
the launcher never reads `emulator/.env`. Old Python lifecycle/dashboard/reset
actions are no longer called by root `run.sh`.

## APK publication

The existing published APK already contains the four HTTPS domains in
`classes5.dex`, with loopback gateway `127.0.0.1:28765`. **No APK rebuild or signing
key change is needed to switch Python → Java with these same domains.** Existing
installations can connect immediately; do not uninstall or clear guest data.

`out/Guitar_Girl_v8.0.0_NoGooglePlay.apk` and the `Universal` alternative are
currently identical (480,702,674 bytes / 458.43 MiB). Java serves HEAD and single
byte ranges (206) for download resumption. Verified existing APK:

- SHA-256: `04453d87381297cb8540fd14937159903fb3010f97d1589ca05bfca7fec990f7`
- Signature schemes v2/v3 and zipalign: verified.
- Signing certificate SHA-256:
  `63260d7f7ee0669e1473deab29aa39fcd3ad132e052a23670663898d8968a763`

The download page identifies this as a custom private-server APK, not an official
Google Play release. Signature/account compatibility must be checked before
replacing an installation. Android device gameplay was not exercised in this
deployment; public protocol smoke checks are not a substitute for a device test.

## Deployment checks (2026-11-12)

- All four domains: TLS verified; health/admin/download/APK HEAD 200.
- Admin rejects unauthenticated user queries (401); authenticated login and users
  listing work on each domain, showing the 7 migrated accounts. No account edits.
- Read-only `getGameDataList`: valid Base64/BZip2/Thrift, error code 0, 39 tables
  on every domain. APK range `bytes=0-15`: 206, 16 bytes, ZIP signature present.
- Disposable lifecycle tests cover start/idempotence/restart/stop, unmanaged
  listener protection, forged PID protection, help without a JAR and non-TTY menu.

Backup before routing/launcher changes:
`resources/data/deployment-backups/20261112T105833Z/` contains the old Nginx site
and old root launcher. Migration backups are separate and untouched. To roll
back, review the backup first: the old upstream `8080` needs a running Python
backend and will otherwise return 502. Never restore it blindly.
