#!/usr/bin/env bash
# Shared helpers for all lab scripts. Source this file; do not execute it.

LAB_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LAB_STATE_DIR=/var/lib/tshoot
LAB_MARKER=/etc/tshoot-lab
BACKUP_DIR="$LAB_STATE_DIR/backup"

FAILED=0

red()    { printf '\e[31m%s\e[0m\n' "$*"; }
green()  { printf '\e[32m%s\e[0m\n' "$*"; }
yellow() { printf '\e[33m%s\e[0m\n' "$*"; }
info()   { printf '\e[36m[*]\e[0m %s\n' "$*"; }

pass() { printf '\e[32m[PASS]\e[0m %s\n' "$*"; }
fail() { printf '\e[31m[FAIL]\e[0m %s\n' "$*"; FAILED=1; }
warn() { printf '\e[33m[WARN]\e[0m %s\n' "$*"; }

require_root() {
    if [[ $EUID -ne 0 ]]; then
        red "This must run as root. Use: sudo $0 $*"
        exit 1
    fi
}

# Break scripts damage the system on purpose. Never let them run on a real host.
require_lab_host() {
    if [[ ! -f $LAB_MARKER && "${TSHOOT_FORCE:-0}" != 1 ]]; then
        red "Refusing to run: $LAB_MARKER not found."
        red "These labs BREAK the machine on purpose. Run them only in the disposable lab VM."
        red "(setup/install-base.sh creates the marker.)"
        exit 1
    fi
}

# Run a check: check "description" command args...
check() {
    local desc=$1; shift
    if "$@" >/dev/null 2>&1; then pass "$desc"; else fail "$desc"; fi
}

http_code() {
    curl -s -o /dev/null -w '%{http_code}' --max-time "${2:-5}" "$1" 2>/dev/null || true
}

finish_verify() {
    echo
    if [[ $FAILED -eq 0 ]]; then
        green "=== ALL CHECKS PASSED - incident resolved. Now write your incident notes (templates/incident-notes.md). ==="
        exit 0
    else
        red "=== NOT RESOLVED YET - keep digging. ==="
        exit 1
    fi
}

backup_file() {
    local f=$1
    mkdir -p "$BACKUP_DIR"
    [[ -e $f ]] && cp -a "$f" "$BACKUP_DIR/$(echo "$f" | tr '/' '_')"
}

# Restore the golden baseline (app, nginx, mounts, permissions). Idempotent.
restore_baseline() {
    SKIP_PACKAGES=1 bash "$LAB_ROOT/setup/install-base.sh"
}
