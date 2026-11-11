# E10 - Solution

## 1. Confirm

```bash
curl -si localhost/ | head -1          # HTTP/1.1 502 Bad Gateway
systemctl status shopapp
# Active: activating (auto-restart) (Result: exit-code)
# Process: 4410 ExecStart=/usr/bin/python3 /opt/shopapp/app.py (code=exited, status=3)
```

## 2. Why does it exit?

```bash
journalctl -u shopapp -n 5 --no-pager
# python3[4410]: FATAL: cannot open log file /var/log/shopapp/app.log: [Errno 13] Permission denied: '/var/log/shopapp/app.log'
```

## 3. Check ownership

```bash
ls -l /var/log/shopapp/
# -rw-r--r-- 1 root    root       812 ... app.log        <- created by the root test run
# -rw-r--r-- 1 shopapp shopapp  48211 ... app.log.old
systemctl show -p User shopapp          # User=shopapp
sudo -u shopapp test -w /var/log/shopapp/app.log || echo "shopapp cannot write"
```

The engineer moved the old log away and started `app.py` as root. Python created a new
`app.log` owned by root with mode 644. The service runs as `shopapp` and cannot open it.

## 4. Fix

```bash
sudo chown shopapp:shopapp /var/log/shopapp/app.log
sudo systemctl restart shopapp     # or wait for the next auto-restart
```

Wrong fixes: `chmod 666 app.log` (anyone can forge log lines), `User=root` in the unit.

## 5. Verify

```bash
systemctl status shopapp --no-pager
curl -s localhost/health
sudo ./labctl.sh check e10
```

Next time, debug as the service user with the service's environment:

```bash
sudo -u shopapp /usr/bin/python3 /opt/shopapp/app.py
# or exactly like systemd would run it:
sudo systemd-run --pty -p User=shopapp /usr/bin/python3 /opt/shopapp/app.py
```

## Root cause and prevention

| | |
|---|---|
| Root cause | Manual run as root created a root-owned `app.log`; service user could not open it (exit 3) |
| Fix | `chown shopapp:shopapp app.log`, restart |
| Prevent | Debug with `sudo -u` / `systemd-run`; create log files from the unit (`LogsDirectory=`) or tmpfiles.d; alert on restart counts |
