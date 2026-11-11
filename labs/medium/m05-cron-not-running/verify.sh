#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"

shopt -s nullglob
files=()
for f in /etc/cron.d/*; do
    grep -Eq '^[[:space:]]*[^#[:space:]].*shopapp-backup' "$f" && files+=("$f")
done

if [[ ${#files[@]} -eq 0 ]]; then
    fail "no active cron entry for shopapp-backup in /etc/cron.d"
else
    for f in "${files[@]}"; do
        name=$(basename "$f")
        if [[ $name =~ ^[A-Za-z0-9_-]+$ ]]; then pass "$f has a valid name (cron will read it)"; else fail "$f: cron ignores files whose name has '.' or other chars"; fi
        mode=$(stat -c %a "$f"); owner=$(stat -c %U "$f")
        if [[ $owner == root ]] && (( (8#$mode & 8#022) == 0 )); then pass "$f is root-owned and not group/other writable ($mode)"; else fail "$f owner=$owner mode=$mode - cron rejects it (INSECURE MODE / WRONG FILE OWNER)"; fi
    done
fi

check "/usr/local/bin/shopapp-backup is executable" test -x /usr/local/bin/shopapp-backup

recent=$(find /srv/backups -name 'shopapp-*.tar.gz' -mmin -3 | head -1)
if [[ -n $recent ]]; then
    pass "fresh backup created by cron: $recent"
    check "backup archive is readable and contains config.ini" sh -c "tar -tzf '$recent' | grep -q config.ini"
else
    fail "no backup in /srv/backups from the last 3 minutes (after fixing, wait up to 60s for cron)"
fi
finish_verify
