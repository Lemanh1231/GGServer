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

# Load .env if present (allows local configuration without committing to git)
[ -f "$HERE/../.env" ] && set -a && . "$HERE/../.env" && set +a
[ -f "$HERE/.env" ] && set -a && . "$HERE/.env" && set +a

DEFAULT_APK_DIR="$HERE/../orig_apk"
APK_DIR="${GG_APK_DIR:-$DEFAULT_APK_DIR}"
OUT="${GG_OUT:-$HERE/../out/patched-apks}"

# Check that the original APK directory exists and has files
if [ ! -d "$APK_DIR" ] || [ -z "$(ls -A "$APK_DIR" 2>/dev/null)" ]; then
  echo "=========================================================================="
  echo "LỖI: Không tìm thấy file APK gốc trong: $APK_DIR"
  echo "Hướng dẫn cho người dùng mới:"
  echo "1. Tải bản Guitar Girl v8.0.0 (XAPK hoặc Split APKs từ APKPure)."
  echo "2. Đặt 3 file APK vào thư mục orig_apk/:"
  echo "   - base_assets.apk"
  echo "   - com.neowiz.game.guitargirl.apk"
  echo "   - config.arm64_v8a.apk"
  echo "   (Hoặc đặt biến môi trường: export GG_APK_DIR=/path/to/apks)"
  echo "=========================================================================="
  exit 1
fi

ARG="$1"
if [ -n "$ARG" ]; then
  if [[ "$ARG" == http://* || "$ARG" == https://* ]]; then
    TARGET="$ARG"
  else
    TARGET="http://$ARG"
  fi
elif [ -n "$GG_PUBLIC_BASE" ]; then
  TARGET="$GG_PUBLIC_BASE"
else
  # Auto-detect local LAN IP or fallback to localhost:8080
  LOCAL_IP="$(ip route get 1.1.1.1 2>/dev/null | awk '{print $7; exit}')"
  [ -z "$LOCAL_IP" ] && LOCAL_IP="$(ipconfig getifaddr en0 2>/dev/null)"
  [ -z "$LOCAL_IP" ] && LOCAL_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
  [ -z "$LOCAL_IP" ] && LOCAL_IP="localhost"
  TARGET="http://${LOCAL_IP}:8080"
fi
TARGET="${TARGET%/}"

if command -v brew >/dev/null 2>&1; then
  export PATH="$(brew --prefix)/opt/openjdk/bin:$PATH"
fi
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
