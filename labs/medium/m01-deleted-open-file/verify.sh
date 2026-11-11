#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
L=/var/log/shopapp

use=$(df --output=pcent "$L" | tail -1 | tr -dc '0-9')
[[ $use -lt 50 ]] && pass "$L usage is ${use}% (< 50%)" || fail "$L usage is ${use}% (needs < 50%)"

deleted=$(lsof -nP +L1 2>/dev/null | awk -v m="$L" '$0 ~ m && /shipper-spool/' | wc -l)
[[ $deleted -eq 0 ]] && pass "no process holds a deleted spool file" || fail "a process still holds a deleted file on $L"

check "log-shipper service is still running (do not break log shipping!)" systemctl is-active --quiet log-shipper
finish_verify
