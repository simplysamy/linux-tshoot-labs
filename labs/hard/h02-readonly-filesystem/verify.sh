#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
M=/srv/shopdata

if ! findmnt -n "$M" >/dev/null; then
    fail "$M is not mounted"
    finish_verify
fi
opts=$(findmnt -no OPTIONS "$M")
[[ $opts =~ (^|,)rw(,|$) ]] && pass "$M is mounted read-write" || fail "$M is mounted with: $opts"

dev=$(findmnt -no SOURCE "$M")
state=$(dumpe2fs -h "$dev" 2>/dev/null | awk -F: '/^Filesystem state/{gsub(/^[ \t]+/,"",$2); print $2}')
if [[ $state == *error* ]]; then
    fail "filesystem state is '$state' - it was remounted rw without fsck"
else
    pass "filesystem state is '$state'"
fi

if [[ -r $M/catalog/products.db ]] && [[ $(sha256sum "$M/catalog/products.db" | awk '{print $1}') == $(cat "$LAB_STATE_DIR/h02-catalog.sha256" 2>/dev/null) ]]; then
    pass "catalog/products.db restored and matches the backup"
else
    fail "catalog/products.db is missing or not the backed-up version"
fi
owner=$(stat -c %U "$M/catalog/products.db" 2>/dev/null)
[[ $owner == shopapp ]] && pass "products.db owned by shopapp" || fail "products.db owner is '${owner:-?}', expected shopapp"

[[ $(http_code http://127.0.0.1/health) == 200 ]] && pass "/health returns 200" || fail "/health is not 200"
finish_verify
