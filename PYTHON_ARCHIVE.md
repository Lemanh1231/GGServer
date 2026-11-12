# Final Python server archive

This `main` branch preserves the final legacy Python server and APK patcher source.
The live deployment has moved to native Java on port 8181; Java source lives on
the separate `java-server` branch. Do not treat this branch as the live deployment.

Included: Python handlers, protocol/schema/catalog resources, regression test
sources and patcher changes. Tests are historical and may require disposable
local fixtures; never run legacy tests against production accounts or databases.

Excluded: player SQLite databases, captures, private runtime data, passwords,
tokens, signing keys and APK binaries. A private VPS backup is retained separately
before removing the local Python runtime.

The legacy `--retired` endpoint previously ran on port 8080 to tell old clients
to update. It is no longer a gameplay server. The Python process and its local
`emulator/` directory are removed after this archive is successfully published;
Nginx retains an HTTP 410 update notice for the retired route. Published APKs,
signing material, Java resources and MongoDB player data must be preserved.

The historical root launcher on this archived branch targets Python. The local
VPS launcher has already been migrated to Java and is deliberately not replaced
by this archive commit.
