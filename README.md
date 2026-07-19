# Guitar Girl — Private Server Emulator + APK Redirect

Offline/private server for **Guitar Girl** (`com.neowiz.game.guitargirl`) v8.0.0, a Neowiz game
that reached **End of Service**. The client's protocol was reverse-engineered from the Unity IL2CPP
binary; the backend is reimplemented in Python so the game runs again, and the APK is patched to
redirect to it (no root / BlueStacks-friendly).

> Preservation / educational project for a defunct (EOS) game, for a client you own.
> Backend logic & game-data tables are based on the excellent
> **[KhoalaS/guitar-girl-offline](https://github.com/KhoalaS/guitar-girl-offline)** (Go) reference,
> reimplemented here in Python with a no-root APK-patch redirect.

## Quick start (BlueStacks, no root)

```bash
# 1) patch + re-sign the split APKs to point at this machine (auto-detects LAN IP)
cd patcher && ./build.sh

# 2) run the emulator server
cd ../emulator && python3 run.py --port 8080

# 3) install on BlueStacks + launch  (details in ANDROID_SETUP.md)
adb install-multiple out/patched-apks/*.apk
```

Full redirect/install guide: **[ANDROID_SETUP.md](ANDROID_SETUP.md)**.
Protocol deep-dive: **[PROTOCOL.md](PROTOCOL.md)**.

## Protocol (recovered)

Every request/response is one **Apache Thrift** struct, transformed as:
```
wire = Base64( BZip2( Thrift-TBinaryProtocol( struct ) ) )
```
- Sent as a Unity **WWWForm** POST to `/{category}/{call}/en/`; fields: `call` (command),
  `tapsonic_data` (the base64 message), `access_token` (unvalidated), `current_time`.
- Response envelope `BaseGameResponse` = `{1 error, 2 server_time, 3 category, 4 call, 5 data, 6 maintenance}`;
  `error.code == 0` = success, `maintenance` empty = playable.
- Boot: `Request`(init) → `{game_url, cdn_url}` → `userJoin`/`userLogin` → `getGameDataList` (39 tables) → play.
- No encryption or request signing anywhere.

## What's implemented

- **Codec** (`emulator/codec/`): Base64 + BZip2 + Thrift TBinaryProtocol; byte-compatible with the
  client and the reference (validated on real captured payloads).
- **698 DTO schemas** (`emulator/schema/schema.json`) extracted from the binary & cross-checked
  against the reference models (3932/3944 fields matched; 2 fixed).
- **Server** (`emulator/server/`): game RPC, NeonAPI auth (JSON), CDN, capture logging. Commands
  ported from the reference: `Request`/init, `getServerTime`, `getUpdateTime`, `defaultSettingList`,
  `userJoin`, `userLogin` (full seeded contents), `userSave`, `userLoad`, `setSubscribe`,
  `buyVarietyStore`, `buyCheck`; static blobs for `getGameDataList`, `getEventRewardList`,
  `getVarietyStore`, `getPostTime`; generic success envelope for all other commands.
- **APK patcher** (`patcher/`): rewrites the server-URL literals in `global-metadata.dat` in place
  (STORED entry, size-preserving + CRC fix), re-signs all splits with one key (`uber-apk-signer`).

## Layout

```
PROTOCOL.md / ANDROID_SETUP.md   protocol analysis / redirect+install guide
emulator/
  run.py            entry (HTTP/HTTPS)         test_e2e.py   full boot-chain self-test
  codec/            base64+bzip2+thrift        schema/       schema.json, commands.json
  server/           app, dispatch, handlers, auth, multipart, state
  gamedata/         getGameDataList.b64 + 3 static blobs (+ game_data.json)
  cdn_files/        Unity asset bundles served over the CDN
  static/           eula.html ;  captures/  data/   (runtime)
patcher/
  build.sh          one-command patch+sign     patch_apk.py / patch_metadata.py
  uber-apk-signer.jar
work/               RE tooling: Il2CppDumper output, metadata parser, capstone disassembler
ref/                the KhoalaS/guitar-girl-offline reference (git clone)
out/patched-apks/   generated signed APKs
```

## Extending coverage

Run the game, read the decoded request in `emulator/captures/`, look up its payload DTO in
`emulator/schema/schema.json`, and add a handler in `emulator/server/handlers.py`:
```python
@cmd('someCommand')
def h(req, player, ctx):
    return { ...fields of someCommandRetDataInfo... }, OK
```
The dispatcher resolves `someCommandReturn` and wraps it automatically.

## Credits
- Protocol/data reference: [KhoalaS/guitar-girl-offline](https://github.com/KhoalaS/guitar-girl-offline).
- Symbolication: [Il2CppDumper](https://github.com/Perfare/Il2CppDumper). Signing: uber-apk-signer.
