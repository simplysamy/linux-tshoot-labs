# E08 - Solution

## 1. What does systemd say?

```bash
systemctl status shopapp-report
#   Process: 3120 ExecStart=/usr/local/bin/shopapp-report (code=exited, status=127)
journalctl -u shopapp-report -n 5 --no-pager
# shopapp-report[3120]: /usr/local/bin/shopapp-report: line 6: shopctl: command not found
```

Exit code 127 = command not found.

## 2. Why does it work in a shell?

```bash
type shopctl
# shopctl is /opt/shoptools/bin/shopctl
grep -r shoptools /etc/profile.d/
# /etc/profile.d/shoptools.sh:export PATH="$PATH:/opt/shoptools/bin"
systemctl show-environment | grep ^PATH
# PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

The upgrade moved `shopctl` to `/opt/shoptools/bin` and added it to PATH in
`/etc/profile.d/`. Only **login shells** read that file. systemd (and cron) do not.

Note: `sudo /usr/local/bin/shopapp-report` also fails - sudo uses its own `secure_path`.
`sudo -i` works because it starts a login shell. Same trap.

## 3. Fix (pick one)

**a) Full path in the script** (simplest, explicit):
```bash
sudo sed -i 's#^\( *\)shopctl #\1/opt/shoptools/bin/shopctl #' /usr/local/bin/shopapp-report
```

**b) Set PATH for the unit** (no script change):
```bash
sudo systemctl edit shopapp-report
# [Service]
# Environment=PATH=/opt/shoptools/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
```

**c) Link into a standard directory**:
```bash
sudo ln -s /opt/shoptools/bin/shopctl /usr/local/bin/shopctl
```

## 4. Verify

```bash
sudo systemctl start shopapp-report
systemctl status shopapp-report --no-pager    # status=0/SUCCESS
cat /srv/backups/shop-report.txt
systemctl list-timers shopapp-report.timer
sudo ./labctl.sh check e08
```

## Root cause and prevention

| | |
|---|---|
| Root cause | Package upgrade moved `shopctl` out of the default PATH; only login shells got the new PATH |
| Fix | Full path / unit `Environment=PATH` / symlink |
| Prevent | Test scheduled jobs the way they run: `systemd-run --wait -p ... ` or `systemctl start`; alert when a report gets stale; use full paths in scripts |
