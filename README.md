# Guitar Girl private server emulator

Private/offline revival server for the EOS Android game **Guitar Girl**. It serves the recovered Thrift game API, NeonAPI responses, game data, and asset bundles for a patched client.

## Run

```bash
cd /home/leman/debug/GGServer/emulator
python3 run.py
```

The server listens on `0.0.0.0:8080`; stop it with `Ctrl-C`.

For Cloudflare Tunnel/Zero Trust, patch the APK to your HTTPS domain and run:

```bash
GG_PUBLIC_BASE="https://your-domain.example" python3 run.py --port 8080
```

## Android test

```bash
adb devices -l
adb -s <device> shell pm clear com.neowiz.game.guitargirl  # after each server-code change
adb -s <device> shell monkey -p com.neowiz.game.guitargirl 1
```

After clearing data, accept all Terms, choose **Agree and Play**, dismiss Google Play Games by tapping outside it, and grant requested app permissions.

## Gameplay behavior

- Login event is visible and claimable once per day.
- New users start with zero CP and Candy.
- Skill, music, and furniture upgrades persist correctly.
- Free Star Pass rewards use game data and are idempotent.
- Gold/Paid Star Pass stays locked; no paid-card entitlement is created.

Detailed fixes: [BUG.md](BUG.md). APK setup: [ANDROID_SETUP.md](ANDROID_SETUP.md). Protocol notes: [PROTOCOL.md](PROTOCOL.md).

## Git hygiene

`emulator/captures/` and `emulator/data/database.db*` are runtime-only and ignored by Git. They must not be committed or pushed.
