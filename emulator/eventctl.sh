#!/usr/bin/env bash
# Event Control CLI wrapper for Guitar Girl Server
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$DIR/eventctl.py" "$@"
