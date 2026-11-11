#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

check "queue-dispatcher is active" systemctl is-active --quiet queue-dispatcher

tm=$(systemctl show -p TasksMax --value queue-dispatcher)
[[ $tm == 150 ]] && pass "TasksMax is still 150" || fail "TasksMax changed to $tm - fix the cause, keep the limit"

info "Watching the dispatcher for 10 seconds ..."
sleep 10
main=$(systemctl show -p MainPID --value queue-dispatcher)
z=$(ps -eo ppid=,stat= | awk -v p="$main" '$1==p && $2 ~ /^Z/' | wc -l)
[[ $z -lt 5 ]] && pass "$z zombie children" || fail "$z zombie children of PID $main"

tasks=$(systemctl show -p TasksCurrent --value queue-dispatcher)
[[ $tasks =~ ^[0-9]+$ && $tasks -lt 20 ]] && pass "tasks in unit: $tasks" || fail "tasks in unit: $tasks"

if journalctl -u queue-dispatcher --since "-10s" --no-pager -q | grep -q 'dispatched job'; then
    pass "jobs are being dispatched"
else
    fail "no 'dispatched job' log lines in the last 10s"
fi
if journalctl -u queue-dispatcher --since "-10s" --no-pager -q | grep -q 'fork failed'; then
    fail "fork failures in the last 10s"
fi
finish_verify
