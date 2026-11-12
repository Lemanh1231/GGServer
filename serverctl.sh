#!/usr/bin/env bash
# Manage only the Java process launched by this script. Never kill a port owner.
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/common.sh"
# These actions must also work on a fresh checkout without a built JAR.
usage() { echo "Usage: $0 {start|stop|restart|status|health|logs|build|test|paths}"; }
case "${1:-status}" in
    help|--help|-h) usage; exit 0 ;;
    test|tests) cd "$GG_PROJECT"; exec ./gradlew test --console=plain ;;
    build)
        # Do not replace classes/JARs underneath a live JVM (including Gradle run).
        for process in /proc/[0-9]*/cmdline; do
            [[ -r "$process" ]] || continue
            if grep -azqF -- "$GG_PROJECT/build/" "$process" &&
                    grep -azqE 'emu\.leman\.ggserver\.Main|ggserver-.*\.jar' "$process"; then
                echo 'Stop GGServer before building; live classes/JARs must not be replaced.' >&2
                exit 1
            fi
        done
        cd "$GG_PROJECT"; exec ./gradlew test fatJar installDist --console=plain ;;
    start|stop|restart|status|health|paths|log|logs) ;;
    *) usage >&2; exit 2 ;;
esac
CONFIG="${GG_CONFIG:-$GG_ROOT/server-config.json}"
CONFIG="$(realpath -m "$CONFIG")"
SCHEME=http
SERVER_ARGS=()
if [[ -f "$CONFIG" ]]; then
    require_jar
    settings="$("$JAVA" -cp "$GG_JAR" emu.leman.ggserver.cli.ConfigCli "$CONFIG")"
    mapfile -t config_values <<< "$settings"
    PORT="${GG_PORT_OVERRIDE:-${config_values[0]}}"
    SCHEME="${config_values[1]}"
    SERVER_ARGS=(--config "$CONFIG")
    [[ -z "$GG_PORT_OVERRIDE" ]] || SERVER_ARGS+=(--port "$PORT")
    [[ -z "${HOST:-}" ]] || SERVER_ARGS+=(--host "$HOST")
else
    PORT="${PORT:-8080}"
    SERVER_ARGS=(--root "$GG_ROOT" --host "${HOST:-127.0.0.1}" --port "$PORT")
fi
[[ "$PORT" =~ ^[0-9]+$ ]] && (( PORT >= 1 && PORT <= 65535 )) || { echo "Invalid PORT: $PORT" >&2; exit 1; }
HOST="${HOST:-127.0.0.1}"
LOG="${GG_LOG:-$GG_ROOT/logs/server.log}"
RUN_DIR="$GG_ROOT/.run"
PID_FILE="$RUN_DIR/server-$PORT.pid"
mkdir -p "$RUN_DIR"

# Linux /proc start-time defeats stale PID files/PID reuse. Exact jar argv
# checks prevent acting on arbitrary processes even with a forged/stale record.
start_time() {
    local stat
    [[ -r "/proc/$1/stat" ]] || return 1
    stat="$(cat "/proc/$1/stat")" || return 1
    stat="${stat##*) }"
    local -a fields
    read -r -a fields <<< "$stat"
    [[ "${fields[0]}" != Z ]] || return 1
    echo "${fields[19]}"
}
owned_process() {
    local saved_time actual_time arg previous="" found=0 root_found=0 port_found=0 config_found=0
    [[ -r "$PID_FILE" ]] || return 1
    read -r PID saved_time < "$PID_FILE" || return 1
    [[ "$PID" =~ ^[0-9]+$ && "$saved_time" =~ ^[0-9]+$ ]] || return 1
    actual_time="$(start_time "$PID")" || return 1
    [[ "$actual_time" == "$saved_time" ]] || return 1
    [[ -r "/proc/$PID/cmdline" ]] || return 1
    while IFS= read -r -d '' arg; do
        if [[ "$previous" == -jar && "$arg" == "$GG_JAR" ]]; then found=1; fi
        if [[ "$previous" == --root && "$arg" == "$GG_ROOT" ]]; then root_found=1; fi
        if [[ "$previous" == --port && "$arg" == "$PORT" ]]; then port_found=1; fi
        if [[ "$previous" == --config && "$arg" == "$CONFIG" ]]; then config_found=1; fi
        previous="$arg"
    done < "/proc/$PID/cmdline"
    (( found == 1 && (config_found == 1 || (root_found == 1 && port_found == 1)) ))
}
health() { curl --noproxy '*' --insecure --fail --silent --max-time 2 "$SCHEME://127.0.0.1:$PORT/health"; }
start() {
    require_jar
    if owned_process; then echo "RUNNING pid=$PID port=$PORT"; return; fi
    # A responding service is not ours. Never claim ownership or stop it.
    if health >/dev/null 2>&1; then echo "Port $PORT already serves another/unmanaged process; refusing to start." >&2; return 1; fi
    mkdir -p "$(dirname "$LOG")"
    cd "$GG_ROOT"
    nohup "$JAVA" -jar "$GG_JAR" "${SERVER_ARGS[@]}" </dev/null >>"$LOG" 2>&1 9>&- &
    local pid=$! stamp
    stamp="$(start_time "$pid")" || { echo "Server exited at startup; inspect $LOG" >&2; return 1; }
    printf '%s %s\n' "$pid" "$stamp" > "$PID_FILE"
    local attempt
    for attempt in {1..30}; do
        sleep 1
        if ! owned_process; then echo "START FAILED; inspect $LOG" >&2; tail -n 20 "$LOG"; return 1; fi
        if health >/dev/null 2>&1; then echo "STARTED pid=$PID port=$PORT log=$LOG"; return; fi
    done
    echo "Server still starting (pid=$PID) but /health did not become ready; inspect $LOG" >&2
    return 1
}
stop() {
    if ! owned_process; then echo "STOPPED (no managed Java process; other port owners are untouched)"; return; fi
    local pid="$PID" attempt
    kill -TERM "$pid"
    for attempt in {1..15}; do
        sleep 1
        if ! owned_process; then rm -f "$PID_FILE"; echo "STOPPED"; return; fi
    done
    # Reverify identity immediately before escalation; never look up a new port owner.
    if owned_process && [[ "$PID" == "$pid" ]]; then kill -KILL "$pid"; fi
    sleep 1
    if owned_process; then echo "Unable to stop managed pid=$PID" >&2; return 1; fi
    rm -f "$PID_FILE"
    echo "STOPPED"
}
status() {
    if owned_process; then
        echo "RUNNING pid=$PID port=$PORT log=$LOG"
        ps -p "$PID" -o %cpu,%mem,rss,etime --no-headers || true
        printf 'health: '
        health || printf '(unavailable)'
        echo
    else
        echo "STOPPED (no managed Java process; port $PORT may belong to another service)"
        if health >/dev/null 2>&1; then echo "UNMANAGED service responds on port $PORT; it will not be stopped/adopted."; fi
    fi
}

case "${1:-status}" in
    log|logs) mkdir -p "$(dirname "$LOG")"; touch "$LOG"; exec tail -n 80 -f "$LOG" ;;
    health) health; echo; exit ;;
    paths) printf 'Config: %s\nResources: %s\nJAR: %s\nConsole log: %s\nLocal health: %s://127.0.0.1:%s/health\n' "$CONFIG" "$GG_ROOT" "$GG_JAR" "$LOG" "$SCHEME" "$PORT"; exit 0 ;;
    start|stop|restart|status) ;;
    *) echo "Usage: $0 {start|stop|restart|status|log|test}" >&2; exit 2 ;;
esac
command -v flock >/dev/null || { echo 'flock is required (util-linux)' >&2; exit 1; }
exec 9>"$RUN_DIR/server-$PORT.lock"
flock -x 9
# Canonicalize the jar for stop/status even when it was moved/deleted after start.
if [[ -d "$(dirname "$GG_JAR")" ]]; then GG_JAR="$(cd "$(dirname "$GG_JAR")" && pwd -P)/$(basename "$GG_JAR")"; fi
case "${1:-status}" in
    start) start ;;
    stop) stop ;;
    restart) stop; start ;;
    status) status ;;
esac
