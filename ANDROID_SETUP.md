# Run Guitar Girl on BlueStacks (no root) via APK patch

BlueStacks on macOS isn't rooted, so we can't edit `hosts` or install a system CA. Instead we
**patch the APK** to point the game's hardcoded server URLs at your Mac over plain HTTP (no TLS,
so no CA needed), then re-sign and install the split APKs.

## What the patch does

Inside `base_assets.apk`'s `global-metadata.dat`, these string literals are rewritten in place
(same byte size, CRC fixed — see `patcher/patch_metadata.py`):

| Original | Becomes |
|----------|---------|
| `https://game.gtgl.pmang.cloud` (+ dev/dq/review) | `http://<your-ip>:8080` |
| `https://dl.gtgl.pmang.cloud` (+ variants) | `http://<your-ip>:8080` |
| `https://global.neonapi.com/api` (+ variants) | `http://<your-ip>:8080/api` |

No anti-tamper / metadata-integrity / signature check runs in the game (verified by
disassembly — CodeStage AntiCheat is linked but never invoked), so a re-signed, patched APK runs.

## Two redirect modes

| Mode | Target | TLS / cert | When |
|------|--------|-----------|------|
| **LAN HTTP** | `http://<your-ip>:8080` | none | quick local test on the same network |
| **External HTTPS** | `https://your.domain` | **real cert (Let's Encrypt / Cloudflare)** → no CA install needed | play from anywhere; cleanest for no-root |

The patcher supports **any URL length and either scheme** — it grows the metadata string heap when a
URL is longer than the original (so long external domains work). Pick the mode and pass it to `build.sh`:

```bash
./build.sh                                   # LAN: auto http://<en0-ip>:8080
./build.sh http://192.168.1.50:8080          # explicit LAN
./build.sh https://gg.example.com            # external HTTPS (recommended)
```

### External HTTPS with a real cert = no CA needed
Because the client validates TLS against the system trust store, a **real certificate** for your
domain just works on non-rooted BlueStacks. Easiest setups:
- **Cloudflare Tunnel:** `cloudflared tunnel --url http://localhost:8080` (or a named tunnel mapped to
  `gg.example.com`). Run the server as HTTP and tell it the public URL:
  ```bash
  GG_PUBLIC_BASE="https://gg.example.com" python3 emulator/run.py --port 8080
  ```
- **VPS + Caddy/nginx** terminating TLS and proxying to the Python server (set `GG_PUBLIC_BASE` the same way).
- **Python direct HTTPS** with a real cert: `python3 run.py --https --port 443 --cert /path/fullchain+key.pem`.

`GG_PUBLIC_BASE` must equal the URL you patched, so `init` advertises the right `game_url`/`cdn_url`.

## Steps

### 0. Prereqs (already installed in this project)
- Python 3, a JDK (`brew install openjdk`), `adb` (`brew install android-platform-tools`),
  `patcher/uber-apk-signer.jar` (bundled).

### 1. Build patched + signed APKs (auto-detects your LAN IP)
```bash
cd patcher
./build.sh                 # or: ./build.sh 192.168.1.50 8080
```
Output: `out/patched-apks/{com.neowiz.game.guitargirl,config.arm64_v8a,base_assets}.apk`,
all signed with one fresh key (required for split installs).

> Budget note: the replacement URL must be ≤ the shortest original host (`dl.gtgl.pmang.cloud` = 27
> chars). `http://192.168.1.50:8080` (24) fits. If your IP is long, use port 80 (`./build.sh <ip> 80`,
> run the server with `--port 80`) — the CDN host is also re-advertised by the init response anyway.

### 2. Start the emulator server (same machine, same port)
```bash
cd emulator
python3 run.py --port 8080            # binds 0.0.0.0:8080
```
Allow inbound 8080 in the macOS firewall; BlueStacks must be able to reach your Mac's LAN IP.

### 3. Install on BlueStacks
Enable **ADB** in BlueStacks Settings → Advanced, then:
```bash
adb connect 127.0.0.1:5555            # BlueStacks adb port (check settings)
adb uninstall com.neowiz.game.guitargirl
adb install-multiple out/patched-apks/com.neowiz.game.guitargirl.apk \
                     out/patched-apks/config.arm64_v8a.apk \
                     out/patched-apks/base_assets.apk
```

### 4. Launch
Open Guitar Girl. The server log should show:
```
Request -> main.initReturn        (routing/init)
userJoin / userLogin -> ...
getServerTime / getUpdateTime / defaultSettingList
getGameDataList -> static (296612 B)
CDN /AssetBundles/Android/...
```
Every request is also written to `emulator/captures/` (decoded) for debugging.

## Troubleshooting

- **No requests reach the server** → the patch IP/port doesn't match where the server runs, or
  firewall/network blocks it. Re-run `build.sh` with the correct IP; confirm `python3 run.py` is on
  that IP:port.
- **`INSTALL_FAILED_UPDATE_INCOMPATIBLE`** → uninstall the original first (different signing key).
- **`INSTALL_FAILED_INVALID_APK` / signature mismatch** → all 3 splits must be signed with the same
  key; re-run `build.sh` (it does this).
- **Game stuck after a screen** → an unimplemented command returned empty data. Find it in
  `emulator/captures/` (the request is decoded) and implement its payload in
  `emulator/server/handlers.py` (the dispatcher wraps it in the right envelope automatically).
- **`UNRESOLVED` in the log** → a command we didn't map; the raw fields are captured — share that file.

## Alternative (rooted device/emulator)
If you do have root, skip the APK patch: redirect `*.gtgl.pmang.cloud` + `*.neonapi.com` via
`/system/etc/hosts` to your server and run it on the matching ports (or keep HTTP and patch only the
scheme). The APK-patch route above is required specifically because BlueStacks/macOS has no root.
