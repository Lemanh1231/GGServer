#!/usr/bin/env bash
set -euo pipefail
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/common.sh"
require_jar
cd "$GG_ROOT"
exec "$JAVA" -cp "$GG_JAR" emu.leman.ggserver.cli.EventCli "$@"
