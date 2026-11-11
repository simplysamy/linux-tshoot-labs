# H01 - Solution

## 1. Confirm and capture evidence **before** restarting

A restart destroys the evidence. Look first.

```bash
curl -s -o /dev/null -w '%{http_code}\n' --max-time 15 localhost/   # 504
PID=$(systemctl show -p MainPID --value shopapp); echo $PID
top -p $PID                          # high CPU while hung
sudo ls /proc/$PID/fd | wc -l        # 64
grep 'open files' /proc/$PID/limits
# Max open files            64                   64                   files
journalctl -u shopapp --since "15 min ago" | grep -i errno | tail -3
# OSError: [Errno 24] Too many open files: '/srv/shopdata/trace.log'
```

The process reached its fd limit. Why the high CPU? The listening socket is
"ready" but `accept()` fails with EMFILE, so the event loop spins.

## 2. What are the fds?

```bash
sudo ls -l /proc/$PID/fd | awk '{print $NF}' | sort | uniq -c | sort -rn | head
#  56 /srv/shopdata/trace.log         <-- same file opened 56 times = leak
sudo strace -f -p $PID -e trace=openat,close -o /tmp/st.txt &   # watch one request
curl -s --max-time 2 localhost:8080/ ; sudo kill %1
grep trace.log /tmp/st.txt          # openat ... trace.log ... and no close()
```

Each request opens `trace.log` and never closes it.

## 3. Why only since yesterday? Two changes

```bash
grep -n trace /etc/shopapp/config.ini
# 11:; enabled for INC-1999 debugging - turn off after!
# 12:trace_requests = true
systemctl cat shopapp
# # /etc/systemd/system/shopapp.service
# ...
# # /etc/systemd/system/shopapp.service.d/10-limits.conf
# # copied from legacy container template (tpl-v1)
# [Service]
# LimitNOFILE=64
```

- The leak (trace on) was added yesterday.
- The tiny limit (64) has existed for weeks; it made the leak fail in minutes instead of days.

## 4. Fix both

```bash
# stop the leak
sudo sed -i 's/^trace_requests = true.*/trace_requests = false/' /etc/shopapp/config.ini
# remove the bad limit (default for services is 1024 soft / 524288 hard)
sudo rm /etc/systemd/system/shopapp.service.d/10-limits.conf
sudo systemctl daemon-reload
sudo systemctl restart shopapp
PID=$(systemctl show -p MainPID --value shopapp)
grep 'open files' /proc/$PID/limits
for i in $(seq 300); do curl -s -o /dev/null localhost:8080/; done
sudo ls /proc/$PID/fd | wc -l       # small and stable
```

(If you need a custom limit, set e.g. `LimitNOFILE=65536` in a drop-in - via
`sudo systemctl edit shopapp` - never edit `/lib/systemd/system` files.)

## 5. Report the bug

The trace code never closes its file handle. Tell the developers: use
`with open(...)` or one shared handle.

## Root cause and prevention

| | |
|---|---|
| Root cause | Debug tracing leaks 1 fd per request; a legacy drop-in limited the service to 64 fds |
| Contributing | Restarts were used as a fix and destroyed evidence; "temporary" debug flag left on |
| Prevent | Monitor `process_open_fds / process_max_fds`; review drop-ins (`systemd-delta`); time-box debug flags |
