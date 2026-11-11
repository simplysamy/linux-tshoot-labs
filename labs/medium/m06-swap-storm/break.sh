#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

S=$LAB_STATE_DIR
sysctl -n vm.swappiness > "$S/m06-swappiness.orig"

# make sure there is some swap to thrash
if [[ -z $(swapon --noheadings --show) ]]; then
    fallocate -l 1G "$S/m06-swapfile"
    chmod 600 "$S/m06-swapfile"
    mkswap -q "$S/m06-swapfile" >/dev/null
    swapon "$S/m06-swapfile"
fi

cat > /etc/sysctl.d/60-batch-tuning.conf <<'EOF'
# CHG-552 batch performance tuning
# swap more eagerly so the batch gets more page cache
vm.swappiness = 100
EOF
sysctl -q -p /etc/sysctl.d/60-batch-tuning.conf

# enough 200 MB workers to need ~25% more than the memory available right now
avail_mb=$(awk '/MemAvailable/{print int($2/1024)}' /proc/meminfo)
workers=$(( (avail_mb * 125 / 100 + 199) / 200 ))
cat > /etc/report-builder.conf <<EOF
# report-builder - nightly reporting batch
workers = $workers            # CHG-552: was 2
worker_mb = 200
EOF

cat > /usr/local/bin/report-builder <<'EOF'
#!/usr/bin/env python3
"""report-builder: each worker keeps an in-memory working set and keeps touching it."""
import multiprocessing, os, time

conf = {}
for line in open("/etc/report-builder.conf"):
    line = line.split("#")[0].strip()
    if "=" in line:
        k, v = line.split("=", 1)
        conf[k.strip()] = v.strip()
workers, mb = int(conf.get("workers", 2)), int(conf.get("worker_mb", 200))

def work(n):
    buf = bytearray(mb * 1024 * 1024)
    size = len(buf)
    while True:
        for i in range(0, size, 4096):
            buf[i] = (buf[i] + 1) & 0xFF
        time.sleep(0.2)

if __name__ == "__main__":
    print(f"report-builder: {workers} workers x {mb} MB", flush=True)
    procs = [multiprocessing.Process(target=work, args=(n,)) for n in range(workers)]
    for p in procs:
        p.start()
    for p in procs:
        p.join()
EOF
chmod 0755 /usr/local/bin/report-builder

cat > /etc/systemd/system/report-builder.service <<'EOF'
[Unit]
Description=Nightly report builder (batch)

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/report-builder
Restart=always
RestartSec=5
OOMScoreAdjust=500

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now report-builder >/dev/null 2>&1
info "Waiting 30s for memory pressure to build ..."
sleep 30
