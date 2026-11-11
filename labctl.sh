#!/usr/bin/env bash
# Lab controller.
#   sudo ./labctl.sh list
#   sudo ./labctl.sh start  e01      # break the system, print the ticket
#   sudo ./labctl.sh check  e01      # did you fix it?
#   sudo ./labctl.sh reset  e01      # undo the lab, restore baseline
#   sudo ./labctl.sh status          # which lab is active
#        ./labctl.sh ticket e01      # re-print the ticket
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/common.sh
source "$ROOT/lib/common.sh"
ACTIVE="$LAB_STATE_DIR/active-lab"

usage() { sed -n '2,9p' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

resolve() {
    local id=$1 matches=()
    shopt -s nullglob
    matches=("$ROOT"/labs/*/"$id"*/)
    shopt -u nullglob
    [[ ${#matches[@]} -eq 1 ]] || { red "Unknown or ambiguous lab id: $id (try: ./labctl.sh list)"; exit 1; }
    echo "${matches[0]%/}"
}

print_ticket() {
    # print the "Ticket" section of the lab README
    awk '/^## Ticket/{p=1;next} /^## /{p=0} p' "$1/README.md"
}

cmd=${1:-}; id=${2:-}
case $cmd in
    list)
        for level in easy medium hard; do
            yellow "== ${level^^} =="
            for d in "$ROOT"/labs/$level/*/; do
                d=${d%/}
                printf '  %-28s %s\n' "$(basename "$d")" "$(head -1 "$d/README.md" | sed 's/^# //')"
            done
        done
        ;;
    start)
        [[ -n $id ]] || usage
        require_root; require_lab_host
        dir=$(resolve "$id")
        if [[ -f $ACTIVE && $(cat "$ACTIVE") != "$(basename "$dir")" ]]; then
            red "Lab $(cat "$ACTIVE") is still active. Reset it first: sudo ./labctl.sh reset $(cat "$ACTIVE")"
            exit 1
        fi
        info "Breaking the system for $(basename "$dir") ..."
        bash "$dir/break.sh"
        basename "$dir" > "$ACTIVE"
        echo; yellow "================ INCIDENT TICKET ================"
        print_ticket "$dir"
        yellow "================================================="
        info "Check your fix: sudo ./labctl.sh check $id    Give up/undo: sudo ./labctl.sh reset $id"
        ;;
    check)
        [[ -n $id ]] || usage
        require_root
        dir=$(resolve "$id")
        bash "$dir/verify.sh"
        ;;
    reset)
        [[ -n $id ]] || usage
        require_root; require_lab_host
        dir=$(resolve "$id")
        info "Resetting $(basename "$dir") ..."
        bash "$dir/cleanup.sh"
        rm -f "$ACTIVE"
        green "Reset done."
        ;;
    status)
        if [[ -f $ACTIVE ]]; then echo "Active lab: $(cat "$ACTIVE")"; else echo "No active lab."; fi
        ;;
    ticket)
        [[ -n $id ]] || usage
        print_ticket "$(resolve "$id")"
        ;;
    *) usage ;;
esac
