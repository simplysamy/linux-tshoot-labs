#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

# --- The red herring: a legit, approved batch job at the lowest CPU priority.
cat > /usr/local/bin/batch-encoder <<'EOF'
#!/usr/bin/env python3
# Encodes product videos overnight. Approved to use idle CPU (nice 19).
x = 0
while True:
    x = (x * 7 + 3) % 1000003
EOF
chmod 0755 /usr/local/bin/batch-encoder
cat > /etc/systemd/system/batch-encoder.service <<'EOF'
[Unit]
Description=Product video batch encoder (approved, runs at idle CPU priority)

[Service]
User=shopapp
ExecStart=/usr/bin/python3 /usr/local/bin/batch-encoder
Nice=19
Restart=always

[Install]
WantedBy=multi-user.target
EOF

# --- The real culprit: a compliance "audit sync" that does tiny synchronous writes.
cat > /usr/local/bin/audit-sync <<'EOF'
#!/usr/bin/env bash
# Copies audit records to the local audit store. Every write is synced to disk.
end=$((SECONDS + 1800))
while (( SECONDS < end )); do
    dd if=/dev/zero of=/var/tmp/audit-sync.dat bs=4k count=2000 oflag=dsync conv=notrunc status=none
done
EOF
chmod 0755 /usr/local/bin/audit-sync
cat > /etc/systemd/system/audit-sync.service <<'EOF'
[Unit]
Description=Compliance audit record sync

[Service]
Type=simple
ExecStart=/usr/local/bin/audit-sync
EOF
cat > /etc/systemd/system/audit-sync.timer <<'EOF'
[Unit]
Description=Run audit-sync continuously (restart 20s after it stops)

[Timer]
OnActiveSec=1s
OnUnitInactiveSec=20s
AccuracySec=1s

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now batch-encoder >/dev/null 2>&1
systemctl enable --now audit-sync.timer >/dev/null 2>&1
sleep 5
