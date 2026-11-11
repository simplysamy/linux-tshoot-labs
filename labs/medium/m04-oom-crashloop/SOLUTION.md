# M04 - Solution

## 1. How does it die?

```bash
systemctl status cache-warmer --no-pager
# Active: activating (auto-restart) (Result: oom-kill)
systemctl show -p NRestarts cache-warmer    # NRestarts=7 and climbing
journalctl -u cache-warmer -n 20 --no-pager
# cache-warmer starting, max_mb=0 (UNLIMITED)
# cache size 150 MB
# cache-warmer.service: A process of this unit has been killed by the OOM killer.
# cache-warmer.service: Failed with result 'oom-kill'.
```

## 2. Kernel view

```bash
journalctl -k --since "5 min ago" | grep -iE 'oom|killed process'
# Memory cgroup out of memory: Killed process 5120 (python3) total-vm:..., anon-rss:163000kB ...
#   oom-kill:constraint=CONSTRAINT_MEMCG ... task_memcg=/system.slice/cache-warmer.service
free -m             # host has lots of free RAM -> this is a cgroup limit, not the host
systemctl show -p MemoryMax cache-warmer    # 167772160 (160M)
```

`CONSTRAINT_MEMCG` = the unit hit **its own** limit.

## 3. Why does it grow?

```bash
watch -n1 'systemctl show -p MemoryCurrent cache-warmer'    # grows ~20 MB/s, straight line
cat /etc/cache-warmer.conf
# Changed for load test LT-88: 0 = unlimited.  (was: 64)
# max_mb = 0
```

The load test set the cache to unlimited and nobody changed it back.

## 4. Fix the config, keep the limit

```bash
sudo sed -i 's/^max_mb = 0/max_mb = 64/' /etc/cache-warmer.conf
sudo systemctl restart cache-warmer
sleep 15
systemctl show -p NRestarts -p MemoryCurrent cache-warmer   # memory flat at ~70-80 MB
```

Wrong fix: raising or removing `MemoryMax`. With an unbounded cache it only delays
the kill - and without a limit the *global* OOM killer may kill something important instead.

## Root cause and prevention

| | |
|---|---|
| Root cause | Load-test config `max_mb = 0` (unbounded cache) left in place; process grows to the 160M cgroup limit and is OOM-killed, systemd restarts it |
| Prevent | Revert test config with a checklist/ticket; validate config (reject 0); alert on `NRestarts` and on oom-kill events |
