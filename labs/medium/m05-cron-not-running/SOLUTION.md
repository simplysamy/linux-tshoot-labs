# M05 - Solution

## 1. Does cron run it?

```bash
ls -l /srv/backups                        # empty
journalctl -u cron --since "10 min ago"   # no shopapp-backup lines at all
ls -l /etc/cron.d/
# -rw-rw-rw- 1 root root ... shopapp-backup.cron
```

Debian/Ubuntu cron uses `run-parts` naming rules for `/etc/cron.d`: names with a `.` are
**ignored** (so editor backups like `foo.bak` / `foo.dpkg-old` don't run). No error is logged.

## 2. Fault 1 - the name

```bash
sudo mv /etc/cron.d/shopapp-backup.cron /etc/cron.d/shopapp-backup
```

Wait one minute and read the log again:

```bash
journalctl -u cron --since "2 min ago"
# cron[650]: (*system*shopapp-backup) INSECURE MODE (group/other writable) (/etc/cron.d/shopapp-backup)
```

## 3. Fault 2 - the file mode

```bash
sudo chown root:root /etc/cron.d/shopapp-backup
sudo chmod 0644 /etc/cron.d/shopapp-backup
```

Next minute:

```bash
journalctl -u cron --since "2 min ago"
# CRON[7001]: (root) CMD (/usr/local/bin/shopapp-backup)
# CRON[7000]: (CRON) info (No MTA installed, discarding output)
ls /srv/backups      # still empty!
```

Cron runs it now, but the job fails and the output is thrown away (no mail server).

## 4. Fault 3 - run it like cron does

```bash
sudo /usr/local/bin/shopapp-backup
# sudo: /usr/local/bin/shopapp-backup: command not found      (or: Permission denied)
ls -l /usr/local/bin/shopapp-backup
# -rw-r--r-- ...           <-- no x bit
sudo chmod 0755 /usr/local/bin/shopapp-backup
sudo /usr/local/bin/shopapp-backup && ls -l /srv/backups
journalctl -t shopapp-backup -n 3
```

## 5. Verify the backup is usable

A backup you never restored is not a backup:

```bash
tar -tzvf /srv/backups/shopapp-*.tar.gz | head
```

## Root cause and prevention

| | |
|---|---|
| Root cause | Three deploy mistakes: `.cron` suffix (ignored), mode 0666 (rejected as insecure), script without `x` bit. Output was discarded, so nobody saw it |
| Prevent | Deploy cron jobs with config management/packages; capture output (`>> /var/log/... 2>&1` or `logger`); alert on "newest backup older than 26h"; consider systemd timers (logs in journal, `systemctl list-timers`) |
