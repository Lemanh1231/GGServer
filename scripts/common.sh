#!/usr/bin/env bash
# Shared environment for native Java tools. Source only; never load emulator/.env.
GG_PROJECT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# Explicit caller settings take precedence over .env defaults.
declare -A gg_overrides=()
for gg_key in GG_ROOT GG_CONFIG PORT HOST GG_LOG GG_JAR JAVA JAVA_HOME GG_PUBLIC_BASE GG_ADMIN_PASSWORD GG_SECRET_KEY GG_CERT_PASSWORD GG_ADMIN_URL GG_NO_ADB GG_MONGO_URI GG_MONGO_DATABASE; do
    if [[ -v "$gg_key" ]]; then gg_overrides["$gg_key"]="${!gg_key}"; fi
done
if [[ -f "$GG_PROJECT/../.env" ]]; then set -a; source "$GG_PROJECT/../.env"; set +a; fi
if [[ -f "$GG_PROJECT/.env" ]]; then set -a; source "$GG_PROJECT/.env"; set +a; fi
if [[ -f "$GG_PROJECT/resources/.env" ]]; then set -a; source "$GG_PROJECT/resources/.env"; set +a; fi
for gg_key in "${!gg_overrides[@]}"; do export "$gg_key=${gg_overrides[$gg_key]}"; done
GG_PORT_OVERRIDE="${gg_overrides[PORT]:-}"
GG_HOST_OVERRIDE="${gg_overrides[HOST]:-}"
unset gg_overrides gg_key
export GG_ROOT="${GG_ROOT:-$GG_PROJECT/resources}"
if [[ -f "$GG_ROOT/resources/server-config.json" ]]; then GG_ROOT="$GG_ROOT/resources"; fi
GG_ROOT="$(cd "$GG_ROOT" && pwd -P)" || return 1
if [[ -f "$GG_ROOT/server/state.py" ]]; then
    echo "Refusing to operate on Python emulator data: $GG_ROOT" >&2
    return 1
fi
export GG_ROOT
if [[ -f "${GG_CONFIG:-$GG_ROOT/server-config.json}" ]]; then
    [[ -n "$GG_PORT_OVERRIDE" ]] || unset PORT
    [[ -n "$GG_HOST_OVERRIDE" ]] || unset HOST
fi
GG_JAR="${GG_JAR:-$GG_PROJECT/build/libs/ggserver-1.0.0-all.jar}"
JAVA="${JAVA:-${JAVA_HOME:+$JAVA_HOME/bin/}java}"

require_jar() {
    if [[ ! -f "$GG_JAR" ]]; then
        echo "Missing $GG_JAR; build first: cd '$GG_PROJECT' && ./gradlew fatJar" >&2
        return 1
    fi
    GG_JAR="$(cd "$(dirname "$GG_JAR")" && pwd -P)/$(basename "$GG_JAR")"
}
