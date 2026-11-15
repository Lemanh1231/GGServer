# Current source fixes and verification limits

Updated 2026-11-16. This branch contains source, not a production deployment.

## Fixed in source, awaiting deployment verification

- Session validation uses fresh identity-only repository reads on SQLite/Mongo,
  retaining alias/device/placeholder checks without cross-request identity caching.
- Protected RPCs reject missing/undecodable messages before handler execution;
  no-body bootstrap remains compatible and credentials are not sniffed as messages.
- Both advertisement rewards enforce the catalog active flag and named daily-limit/
  cooldown rules. Cookie reward remains 25 AP; payment/reward/save semantics remain atomic.
- Public profile reads honor the target UID without changing update identity or
  nesting requester/target account locks.
- New skill/unit acquisition checks catalog unlock requirements. Skill projection
  preserves previously earned levels/timers; upgrade prices and max levels are unchanged.
- Native patcher rejects unsupported/truncated patch sites instead of silently
  emitting partially applied patches; known already-patched inputs are idempotent.

## Validation

- Publication checkout validation: 419 tests passed across 53 suites, zero
  failures/errors/skips, JVM UTC; `test fatJar` succeeded on 2026-11-16.
- Publication JAR exactly matches the validated candidate, SHA256
  `90c15a78d2532c2e810e8165f8b3b34604a79c424de6af1af9404b2ec33fd2a8`.
  Its 104 application classes match; no private/runtime artifacts are included.
- The five synthetic native guard tests also passed in the publication checkout.
- Host tests: 27 passed (5 native guards, 17 skill policy, 5 gateway/release tests).
  Only the native guard test and its patcher are included here; the other suites
  belong to the existing local Android experimental toolchain.
- Full inventory: 134 wire routes, 65 handler routes, 69 fallback routes. This is
  not a claim that all 134 routes have end-to-end native gameplay coverage.

## Still requires verification

- Android UI/ART/device behavior and the two exact-base ARM64 experimental suites:
  the required original APK is unavailable. No APK is included or rebuilt here.
- Production deployment, proxy/header trust, origin isolation, secrets/TLS/rate
  limits and unexplained historical process exits require operational verification.
- Legacy namespace collisions/schema-only routes require native contracts; no
  speculative routing rewrite or gameplay implementation was introduced.
- Notification work remains canceled. No database cleanup, account reset,
  compensation, live purchase/claim or automatic deployment is authorized by publication.

The old root BUG.md was removed from the working repository as requested; it was
not present on this Java-only branch. No archival copy is added. See
[RPC_LOGIC_AUDIT.md](RPC_LOGIC_AUDIT.md) and
[BUG_DISPOSITION.md](BUG_DISPOSITION.md) for disposition and regression detail.
