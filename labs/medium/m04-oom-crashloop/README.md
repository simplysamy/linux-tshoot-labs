# M04 - Service keeps restarting (OOM killer)

**Level:** Medium · **Time:** 25 min · **Skills:** memory, cgroups, OOM killer, kernel log, systemd

## Ticket

> **INC-2004 · P3**
> `cache-warmer.service` restarts every few seconds. Product pages are slow because the cache
> is always cold. Nobody changed the code. There was a load test (LT-88) last week.
> Find why it dies and stabilise it. Do **not** remove the memory limit - it protects the host.

## Success criteria

- cache-warmer stays up (no restarts for 20s)
- The memory limit on the unit is still in place
- The real cause is fixed

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### systemctl + journalctl - service state and logs

```bash
systemctl status nginx                          # 1. state, last exit code, last log lines
systemctl is-active nginx                       # 2. one word: active / failed / inactive
journalctl -u nginx                             # 3. the whole log of one unit (-u = unit)
journalctl -u nginx -n 20                       # 4. only the last 20 lines
journalctl -u nginx -n 20 --no-pager            # 5. print straight to the terminal (no less)
journalctl -u nginx --since "10 min ago"        # 6. time window instead of line count
```

### systemctl show / cat - ask systemd for facts

```bash
systemctl cat nginx                              # 1. the unit file(s) systemd really uses, incl. drop-ins
systemctl show nginx                             # 2. every property (long)
systemctl show -p User nginx                     # 3. -p = just one property
systemctl show -p User -p MainPID nginx          # 4. several
systemctl show -p MainPID --value nginx          # 5. --value = print only the value (for scripts)
```

### dmesg / journalctl -k - the kernel's messages

```bash
dmesg                           # 1. kernel ring buffer (needs sudo on some systems)
dmesg -T                        # 2. -T = readable timestamps
sudo dmesg -T | tail -5         # 3. only the newest lines
journalctl -k --since "1 hour ago"    # 4. kernel log from the journal, time window
journalctl -k | grep -iE 'oom|ext4'   # 5. filter for what you suspect
```

### free / vmstat - memory and swap

```bash
free                    # 1. memory in KB
free -m                 # 2. in MB; read the 'available' column, not 'free'
vmstat                  # 3. one summary line since boot
vmstat 1 5              # 4. a line per second, 5 times (ignore the first line)
# columns: r=runnable b=blocked si/so=swap in/out wa=CPU waiting for disk. si/so > 0 for long = swapping.
```

### sed - edit text from the command line

```bash
sed 's/old/new/' file           # 1. print file with the first 'old' on each line replaced (file unchanged)
sed 's/old/new/g' file          # 2. g = every match on the line
sed -n '3p' file                # 3. -n + p = print only line 3
sed '/old/d' file               # 4. d = delete lines that match (still only printed)
sed -i 's/old/new/' file        # 5. -i = edit the file IN PLACE (make a copy first: cp file file.bak)
sed -i 's#/a/b#/c/d#' file      # 6. any delimiter works: # avoids escaping / in paths
```

### watch - repeat a command

```bash
systemctl show -p MemoryCurrent cache-warmer                        # 1. one reading
watch -n1 'systemctl show -p MemoryCurrent cache-warmer'            # 2. every second; Ctrl-C to stop
# a straight line going up = a leak; flat = healthy
```

## Hints

<details><summary>Hint 1 - how does it die?</summary>

`systemctl status cache-warmer` - look at `Main PID`, the restart counter and
`Result:`. `journalctl -u cache-warmer -n 30`.
</details>

<details><summary>Hint 2 - who killed it?</summary>

The kernel logs every OOM kill: `journalctl -k | grep -i -E 'oom|killed process'`
(or `sudo dmesg -T | grep -i oom`). Is it a *global* OOM or a *cgroup* (memcg) OOM?
</details>

<details><summary>Hint 3 - why does it grow?</summary>

Watch it grow: `watch -n1 'systemctl show -p MemoryCurrent cache-warmer'` or
`ps -o pid,rss,cmd -C python3`. The program prints its config at start - read the log and `/etc/cache-warmer.conf`.
</details>

## What you should learn

- `Result: oom-kill` and `Killed process ... (oom-kill / memcg)` in the kernel log.
- cgroup limits (`MemoryMax=`) produce OOM kills even when `free -m` shows plenty of RAM.
- RSS growing in a straight line = leak or unbounded cache. Find the bound, don't raise the limit blindly.
- "Nobody changed the code" - but config changes are changes too.

Solution: [SOLUTION.md](SOLUTION.md)
