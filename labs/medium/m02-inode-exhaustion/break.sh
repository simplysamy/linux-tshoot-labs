#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

# The session cleanup cron was "temporarily" disabled during a migration.
cat > /etc/cron.d/shopapp-session-cleanup <<'EOF'
# Remove shopapp sessions older than 1 day.
# DISABLED during storage migration - re-enable afterwards!  (ticket MIG-311)
#17 * * * * shopapp find /srv/shopdata/sessions -type f -name 'sess_*' -mmin +1440 -delete
EOF
chmod 0644 /etc/cron.d/shopapp-session-cleanup

# Months of session files pile up until the filesystem runs out of inodes.
python3 - <<'EOF'
import os, time
d = "/srv/shopdata/sessions"
now = time.time()
# live sessions (last few hours) - these must survive the cleanup
for i in range(40):
    p = f"{d}/sess_live_{i:04d}"
    with open(p, "w") as fh:
        fh.write("user=customer cart=active\n")
    t = now - 600 * i
    os.utime(p, (t, t))
i = 0
while True:
    p = f"{d}/sess_{i:06d}"
    try:
        with open(p, "w") as fh:
            fh.write("user=guest cart=empty\n")
    except OSError:
        break
    t = now - 86400 * (2 + i % 60)
    os.utime(p, (t, t))
    i += 1
EOF
chown -R shopapp:shopapp /srv/shopdata/sessions
sync
