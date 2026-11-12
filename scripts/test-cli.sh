#!/usr/bin/env bash
# End-to-end shell lifecycle/safety tests. Uses an isolated root, never emulator data.
set -euo pipefail
PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d /tmp/opencode/ggjava-cli-test.XXXXXX)"
export GG_ROOT="$TEST_ROOT"
export GG_JAR="$PROJECT/build/libs/ggserver-1.0.0-all.jar"
export GG_LOG="$TEST_ROOT/server.log"
export GG_NO_ADB=1
export PORT="${GG_TEST_PORT:-18793}"
export GG_ADMIN_PASSWORD="cli-test-password"
unrelated=""
cleanup() {
    "$PROJECT/serverctl.sh" stop >/dev/null 2>&1 || true
    if [[ -n "$unrelated" ]]; then kill "$unrelated" 2>/dev/null || true; fi
    # Keep isolated files available for failure diagnosis; no recursive deletion.
}
trap cleanup EXIT
[[ -f "$GG_JAR" ]] || { echo 'Build first: ./gradlew fatJar' >&2; exit 1; }
cp -R "$PROJECT/resources/schema" "$TEST_ROOT/schema"

# A stale PID file referencing a live unrelated process must never authorize kill.
sleep 300 &
unrelated=$!
mkdir -p "$TEST_ROOT/.run"
stat="$(cat "/proc/$unrelated/stat")"
stat="${stat##*) }"
read -r -a fields <<< "$stat"
printf '%s %s\n' "$unrelated" "${fields[19]}" > "$TEST_ROOT/.run/server-$PORT.pid"
"$PROJECT/serverctl.sh" stop
kill -0 "$unrelated"
[[ "$("$PROJECT/serverctl.sh" status)" == *STOPPED* ]]

"$PROJECT/eventctl.sh" enable all
"$PROJECT/eventctl.sh" season 8
"$PROJECT/eventctl.sh" enable cherry
[[ "$("$PROJECT/eventctl.sh" list)" == *'season 8'* ]]
"$PROJECT/serverctl.sh" start
[[ "$("$PROJECT/serverctl.sh" status)" == *RUNNING* ]]
[[ "$("$PROJECT/serverctl.sh" start)" == *RUNNING* ]]
"$PROJECT/send-notification.sh" --title 'CLI smoke' --memo 'Native broadcast' --cp 1 --candy 1.5 --like 2 --cookie 1 --guitar 1 --costume 1 --music 1
"$PROJECT/eventctl.sh" sendmail 'Mail smoke' 'Native mail' 1 2.5 3
"$PROJECT/serverctl.sh" restart
[[ "$("$PROJECT/serverctl.sh" status)" == *RUNNING* ]]
"$PROJECT/serverctl.sh" stop
[[ "$("$PROJECT/serverctl.sh" status)" == *STOPPED* ]]
kill -0 "$unrelated"
echo "PASS: native CLI + lifecycle + unrelated-process safety (isolated root $TEST_ROOT)"
