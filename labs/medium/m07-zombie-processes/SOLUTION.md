# M07 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. Confirm

```bash
journalctl -u queue-dispatcher -n 5 --no-pager
# queue-dispatcher[6100]: ERROR fork failed: [Errno 11] Resource temporarily unavailable
ps -eo stat | grep -c '^Z'          # ~149
ps -eo pid,ppid,stat,cmd                              # 1. all processes with state
ps -eo pid,ppid,stat,cmd | awk '$3 ~ /Z/'             # 2. awk: keep rows whose 3rd column contains Z
ps -eo pid,ppid,stat,cmd | awk '$3 ~ /Z/' | head -3   # 3. first three
#  6230  6100 Z    [python3] <defunct>
#  6231  6100 Z    [python3] <defunct>
```

All zombies have the same parent: PID 6100.

## 2. Why `kill -9` does nothing

A zombie has already exited. Its memory is gone; only the process-table entry (PID, exit
status) remains until the parent calls `wait()`. You cannot kill something that is dead.

## 3. Why fork fails

```bash
systemctl status queue-dispatcher | grep Tasks
#      Tasks: 150 (limit: 150)
systemctl show -p TasksMax queue-dispatcher     # TasksMax=150
```

Every zombie still holds a PID inside the service's cgroup. 150 of them = the limit is
reached, and the next `fork()` fails with `EAGAIN` (errno 11).

## 4. Why the parent doesn't reap

```bash
pstree -p 6100 | head -3
systemctl cat queue-dispatcher | grep ExecStart
cat /etc/queue-dispatcher.conf
# [dispatcher]
# ; set to false while debugging INC-2190 (child exit codes) - revert after!
# reap_children = false
```

The parent was told not to collect its children's exit status.

## 5. Fix

```bash
sudo sed -i 's/^reap_children *=.*/reap_children = true/' /etc/queue-dispatcher.conf
sudo systemctl restart queue-dispatcher
```

Restarting the parent alone already clears the zombies (systemd stops the cgroup;
orphans are re-parented and reaped). But without the config fix they come back in ~30 seconds.

## 6. Verify

```bash
ps -eo stat | grep -c '^Z'                  # 0 (or a few for a moment)
journalctl -u queue-dispatcher -n 3 --no-pager   # dispatched job N
sudo ./labctl.sh check m07
```

## Root cause and prevention

| | |
|---|---|
| Root cause | Debug setting `reap_children = false` left on; zombies filled the unit's `TasksMax` |
| Fix | Reaping enabled, service restarted |
| Prevent | Expiring debug flags / review; alert on zombie count and on `Tasks` near `TasksMax` |
