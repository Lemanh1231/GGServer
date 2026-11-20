# Security and private runtime files

## Java4Shell (CVE-2026-114938)

Use a vendor-confirmed patched JDK 21. Ubuntu 24.04 fixes this issue in
`21.0.13.1+2-1~24.04.1`; see https://ubuntu.com/security/CVE-2026-114938.
Check the running JVM with `jcmd <pid> VM.version`, not only `java -version`:
upgrading packages does not update an already running JVM.

`deploy/systemd/20-base64-intrinsic-mitigation.conf` provides an optional
defense-in-depth service drop-in. Merge any existing `JAVA_TOOL_OPTIONS`, test
startup/protocol compatibility, then reload systemd and restart the owning
service. Verify `UseBASE64Intrinsics = false` with `jcmd <pid> VM.flags -all`.
This mitigation is not a substitute for the vendor patch. The game decodes
Base64 before session validation; authentication is not a decoder boundary.

This branch intentionally excludes production configuration, account data, logs,
wire captures, backups, APKs, signing keys, certificates and credentials.
The example configuration contains no production connection information.

Before deploying:

1. Set independent, strong `GG_ADMIN_PASSWORD` and `GG_SECRET_KEY`. The legacy
   admin fallback `admin123` is unsafe; never rely on it. Restrict admin routes.
2. Keep `sessions.required: true`. Device-guest identity is not external-provider
   cryptographic authentication; a device identifier must be treated as private.
3. Bind Java to loopback behind a TLS reverse proxy. Use authenticated MongoDB,
   an application-scoped user, and a loopback/private-network-only listener.
4. Keep private config/env files and secret directories permission-restricted.
   Never place credentials in screenshots, shell history, Git URLs or log output.
5. Treat `data/`, captures, mail/posts and full database backups as private player
   information. Back up all MongoDB collections. On standalone MongoDB, stop all
   writers for a consistent cross-collection backup.
6. Review `git diff --cached` and run a secret scanner before each push. Ignore
   rules do not affect already tracked files and cannot detect hard-coded secrets.
7. If any credential is published, revoke/rotate it immediately; removing the
   current file does not remove its earlier copies from Git history.

Please do not post live account identifiers, access tokens or secrets in public
issues. Provide redacted reproduction steps and synthetic fixtures instead.

## Source security review — 2026-11-16

See `GGServerJava-threat-model.md` for the scoped threat model, owner-confirmed
public-game/private-admin context, tests and remaining conditional risks.
The direct guest-login alias substitution is fixed in source: an existing
account requires its actual stored device credential, not a UID/canonical alias.
This is not external-provider verification and does not protect a leaked real
device credential. Deploy only after a separate authorized review.

Enforce request/rate/concurrency/time limits and capture rotation; strip and set
forwarding headers at a trusted proxy and block direct origin access. Java-side
body/depth limits alone do not bound aggregate resource usage. Private admin
exposure and strong secrets remain required; the legacy token/logout/cookie
behavior is not redesigned by this release.
