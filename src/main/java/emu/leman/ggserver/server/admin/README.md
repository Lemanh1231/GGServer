# Native admin HTTP/API

`new AdminServer(services).handle(exchange)` consumes `/admin` and `/admin/**` and returns
`false` without responding for unrelated paths. It performs no startup cleanup or migration.
All reads and writes use the supplied native `Services` root, never the Python database.

## Original routes covered

| Method | Path | Behavior |
| --- | --- | --- |
| GET, HEAD | `/admin`, `/admin/` | Original bilingual login/dashboard HTML |
| POST | `/admin/api/login` | Password login; 30-day signed HTTP-only cookie and token |
| POST | `/admin/api/logout`, `/admin/logout` | Clear admin cookie |
| GET, HEAD | `/admin/api/events` | Live event config and all 13 season descriptions |
| POST | `/admin/api/events` | Native normalized config save; optional broadcast notification |
| GET, HEAD | `/admin/api/users` | SQL-backed player listing with inventory-aware pass/chapter status |
| POST | `/admin/api/send_post` | Individual or server-wide localized mail, optional CP/candy/AP rewards |
| POST | `/admin/api/user/ban` | Ban/unban by UUID/device identity or sequence |
| POST | `/admin/api/user/delete` | Full account deletion by identity or sequence |
| POST | `/admin/api/users/cleanup_tests` | Explicit authenticated test-user deletion |
| POST | `/admin/api/user/event_settings` | Gold pass grant/revoke, points/steps, attendance progress/rewards, chapter-2 unlock, currencies, ban, notification mail |

Unknown admin routes return JSON **404**, unsupported methods **405**. Malformed management
payloads return **400**, unexpected storage failures **500**. No unsupported route receives
a fabricated success response.

## Compatibility notes and remaining limitations

- There are **no unimplemented original admin routes**. Original admin APIs live in
  `emulator/server/app.py`, not in the HTML module itself.
- `/admin/api/send_post` additionally accepts validated explicit `items` for the native notification
  CLI (including Like and inventory rewards). Mail allocation, persistence and delivery delegate to
  the shared native `SocialPosts.sendPost`, rather than maintaining a second mailbox implementation.
- The original Python `app.py` and admin UI have **no SSE route, EventSource client, or SSE
  publisher**. Live mail visibility comes from the game's normal mailbox/event polling. The CLI's
  earlier SSE-delivery description was an assumption, not an original feature; no SSE extension is
  added by this port.
- Authentication deliberately preserves the original `GG_ADMIN_PASSWORD` default (`admin123`),
  Bearer-password compatibility, `GG_SECRET_KEY` / `data/admin_secret.key` HMAC-SHA256 tokens,
  cookie attributes, and logout's cookie-clearing semantics. Set a strong password and use TLS
  at the deployment boundary. Logout does not revoke an already-issued Bearer token, matching Python.
- Live-event announcement mail currently has specific Vietnamese and English text; other language
  fields fall back to Vietnamese. Python had individually translated live-event announcements in
  all twelve languages. Arbitrary mail still accepts and preserves all twelve supplied translations.
- Attendance grant-all decodes the native captured `gamedata/getEventRewardList.b64` with the
  schema. Missing/undecodable reward captures and unsupported reward type/ID combinations return
  **400 before saving progress**, rather than pretending grants succeeded. Supported original reward
  types are goods, music, costume, prop, follower, unit, guitar, and follower gifts.
- A follower granted by an attendance reward is persisted, but this admin implementation does not
  itself run the legacy messenger-room healing/synchronization routine. The native follower handlers
  can synchronize their own views on subsequent requests.
- Global event saving relies on native `EventManager`/game-data hot-reload behavior; it does not call
  a Python cache invalidator. HTTP game/download/CDN routes outside `/admin` remain the parent's
  responsibility, including the dashboard's existing download and CLI-reference links.
- Player read/modify/save operations and individual mail delivery use `registry.withAccountLock`;
  broadcast delivery uses `registry.withExclusiveLock` to exclude all account handlers while the
  shared `SocialPosts` takes its state monitor. Broadcast delivery is not a single all-users transaction; disk or process failure can
  leave partial eager delivery, with persisted broadcasts available for normal mailbox reconciliation.

The HTML files are exact extracted source strings, not redesigned pages. Gradle must include
`src/main/java/**/server/admin/*.html` as package-relative resources in the JAR; `AdminServer` also supports
source-tree execution as a development fallback.
