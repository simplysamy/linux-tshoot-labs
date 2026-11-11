# E01 - Solution

## 1. Confirm the symptom

```bash
df -h /var/log/shopapp
# Filesystem  Size  Used Avail Use% Mounted on
# /dev/loop0  232M  232M     0 100% /var/log/shopapp
```

`/var/log/shopapp` is its own small volume, and it is full. Root (`/`) is fine,
so only this app is hit.

The journal shows the app failing to write:

```bash
journalctl -u shopapp --since "10 min ago" | tail
# --- Logging error ---
# OSError: [Errno 28] No space left on device
```

## 2. Find what is big

```bash
sudo du -xh --max-depth=1 /var/log/shopapp | sort -h
sudo find /var/log/shopapp -xdev -type f -size +20M -exec ls -lh {} +
# -rw-r--r-- 1 shopapp shopapp 200M ... /var/log/shopapp/debug-trace.log
```

## 3. Look before you delete

```bash
tail -n 2 /var/log/shopapp/debug-trace.log     # debug trace spam
sudo lsof /var/log/shopapp/debug-trace.log     # no output = nothing holds it open
```

## 4. Fix

No process holds the file open, so we can remove it:

```bash
sudo rm /var/log/shopapp/debug-trace.log
```

If a process *did* hold it open, empty it in place instead, so the space is freed now:

```bash
sudo truncate -s 0 /var/log/shopapp/debug-trace.log
```

Old rotated logs in `archive/` are another option, but only after you check how
long they must be kept.

## 5. Verify

```bash
df -h /var/log/shopapp
curl -s localhost/ && tail -n1 /var/log/shopapp/app.log
sudo ./labctl.sh check e01
```

## Root cause and prevention

| | |
|---|---|
| Root cause | A debug trace was left on and wrote to an unrotated file until the log volume filled |
| Fix | Removed the trace file, freed space |
| Prevent | Add a `logrotate` rule for `/var/log/shopapp/*.log` with `maxsize`; alert at 80% usage; turn off debug tracing after use |
