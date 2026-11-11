#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

cat > /etc/queue-dispatcher.conf <<'EOF'
[dispatcher]
jobs_per_second = 5
; set to false while debugging INC-2190 (child exit codes) - revert after!
reap_children = false
EOF

cat > /usr/local/bin/queue-dispatcher <<'EOF'
#!/usr/bin/env python3
"""queue-dispatcher: forks one short-lived worker per job."""
import configparser, os, signal, sys, time

cfg = configparser.ConfigParser()
cfg.read("/etc/queue-dispatcher.conf")
rate = cfg.getfloat("dispatcher", "jobs_per_second", fallback=5)
reap = cfg.getboolean("dispatcher", "reap_children", fallback=True)

def reaper(signum, frame):
    while True:
        try:
            pid, _ = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return
        if pid == 0:
            return

if reap:
    signal.signal(signal.SIGCHLD, reaper)
print(f"queue-dispatcher started rate={rate}/s reap_children={reap}", flush=True)

job = 0
last_err = 0
while True:
    job += 1
    try:
        pid = os.fork()
    except OSError as exc:
        if time.time() - last_err > 5:
            print(f"ERROR fork failed: {exc}", flush=True)
            last_err = time.time()
        time.sleep(1)
        continue
    if pid == 0:
        time.sleep(0.05)          # "process the job"
        os._exit(0)
    if job % 25 == 0:
        print(f"dispatched job {job}", flush=True)
    time.sleep(1 / rate)
EOF
chmod 0755 /usr/local/bin/queue-dispatcher

cat > /etc/systemd/system/queue-dispatcher.service <<'EOF'
[Unit]
Description=Job queue dispatcher

[Service]
ExecStart=/usr/bin/python3 /usr/local/bin/queue-dispatcher
Restart=always
RestartSec=3
TasksMax=150

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl enable --now queue-dispatcher >/dev/null 2>&1
info "Waiting 35s for zombies to pile up ..."
sleep 35
