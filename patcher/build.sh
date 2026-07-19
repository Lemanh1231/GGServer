#!/usr/bin/env bash
# Patch + re-sign the split APKs to redirect Guitar Girl to a server you control.
#
# Usage:
#   ./build.sh                                   # LAN: auto-detect en0 IP -> http://<ip>:8080
#   ./build.sh http://192.168.1.50:8080          # explicit LAN HTTP base
#   ./build.sh https://gg.example.com            # external domain over HTTPS (real cert -> no CA needed)
#   ./build.sh https://gg.example.com:8443        # external HTTPS on a custom port
#
# Any URL length is supported (the patcher grows the metadata heap when needed).
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
APK_DIR="${GG_APK_DIR:-/Users/furiri/Downloads/Guitar+Girl_8.0.0_APKPure}"
OUT="${GG_OUT:-$HERE/../out/patched-apks}"

ARG="$1"
if [ -z "$ARG" ]; then
  IP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
  [ -z "$IP" ] && { echo "Could not detect LAN IP; pass a base URL: ./build.sh http://192.168.1.50:8080"; exit 1; }
  TARGET="http://$IP:8080"
elif [[ "$ARG" == http://* || "$ARG" == https://* ]]; then
  TARGET="$ARG"
else
  # bare host[:port] -> assume http
  TARGET="http://$ARG"
fi
TARGET="${TARGET%/}"

export PATH="$(brew --prefix)/opt/openjdk/bin:$PATH"
echo "Target base URL: $TARGET"
echo "APK dir:         $APK_DIR"
echo "Output:          $OUT"
python3 "$HERE/patch_apk.py" --apk-dir "$APK_DIR" --target "$TARGET" --out "$OUT"

# how the server should be reached
SCHEME="${TARGET%%://*}"
cat <<EOF

================ NEXT STEPS ================
1) Run the emulator server and advertise the SAME base URL:
EOF
if [ "$SCHEME" = "https" ]; then
cat <<EOF
   - External HTTPS: terminate TLS at your domain (Cloudflare Tunnel / nginx / Caddy) and forward to
     the Python server (HTTP). Tell the server its public URL so init returns https://:
       cd "$HERE/../emulator" && GG_PUBLIC_BASE="$TARGET" python3 run.py --port 8080
   - Or let Python serve HTTPS directly with a real cert for your domain:
       cd "$HERE/../emulator" && GG_PUBLIC_BASE="$TARGET" python3 run.py --https --port ${TARGET##*:} --cert /path/fullchain+key.pem
EOF
else
cat <<EOF
       cd "$HERE/../emulator" && GG_PUBLIC_BASE="$TARGET" python3 run.py --port ${TARGET##*:}
EOF
fi
cat <<EOF
2) Install on BlueStacks (uninstall any existing copy first):
     adb connect 127.0.0.1:5555
     adb uninstall com.neowiz.game.guitargirl
     adb install-multiple "$OUT/com.neowiz.game.guitargirl.apk" "$OUT/config.arm64_v8a.apk" "$OUT/base_assets.apk"
3) Launch Guitar Girl. Watch the server log + emulator/captures/.
===========================================
EOF
