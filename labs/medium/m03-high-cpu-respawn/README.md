# M03 - High CPU that keeps coming back

**Level:** Medium · **Time:** 25 min · **Skills:** load average, top/ps, process trees, cron

## Ticket

> **INC-2003 · P2**
> Server is slow, load average is high, CPU is pinned at 100%.
> The night shift "killed the process" twice. Each time the CPU went back to
> 100% about a minute later. Find what it is, why it comes back, and stop it for good.
> The search team owns the job - leave a note for them, do not delete their script.

## Success criteria

- The CPU hog is not running
- Nothing will start it again
- shopapp still healthy

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### uptime / top - CPU

```bash
uptime                  # 1. load average: 1, 5, 15 min. Compare to the CPU count:
nproc                   # 2. number of CPUs. load 2.0 on 2 CPUs = fully busy
top                     # 3. live view. P = sort by CPU, M = by memory, 1 = per-CPU, q = quit
top -bn1 | head -5      # 4. -b = batch (plain text), -n1 = one snapshot -> good for logs and pipes
# CPU line: us=user sy=kernel ni=niced id=idle wa=waiting for disk
```

### ps / pgrep / pstree - look at processes

```bash
ps                                         # 1. only your shell
ps -ef                                     # 2. every process, full format (PID, PPID, command)
ps -fp 1234                                # 3. just one PID
ps -eo pid,ppid,user,%cpu,%mem,cmd         # 4. -o = choose your own columns
ps -eo pid,%cpu,cmd --sort=-%cpu | head    # 5. sort by CPU, highest first (- = descending), top 10
pgrep -af nginx                            # 6. find PIDs by name (-a = show full command, -f = match whole command line)
pstree -ps 1234                            # 7. parent chain of one PID: who started it?
```

### grep - find text

```bash
grep error file                 # 1. lines containing 'error'
grep -i error file              # 2. -i = ignore case
grep -n error file              # 3. -n = show line numbers
grep -v debug file              # 4. -v = invert: lines WITHOUT 'debug'
grep -r error /etc/             # 5. -r = search all files below a directory
grep -E 'oom|killed' file       # 6. -E = extended regex: 'oom' OR 'killed'
dmesg | grep -i oom             # 7. most used form: filter another command's output
```

### cron - is my job running?

```bash
ls -l /etc/cron.d/                              # 1. system cron files: names, owner, mode
cat /etc/cron.d/NAME                            # 2. format: min hour day month weekday USER command
journalctl -u cron --since "10 min ago"         # 3. every run, and every complaint
systemctl list-timers                           # 4. the systemd equivalent
sudo /path/to/script                            # 5. run the job by hand to see its real error
```

## Hints

<details><summary>Hint 1 - who is using CPU?</summary>

`uptime` (load vs. CPU count from `nproc`), then `top` (press `P` to sort by CPU, `1` for per-CPU),
or `ps -eo pid,ppid,user,ni,%cpu,etime,cmd --sort=-%cpu | head`.
</details>

<details><summary>Hint 2 - who started it?</summary>

Look at the parent PID chain: `pstree -ps <PID>`. What is at the top?
`systemctl status <PID>` also shows the unit (cgroup) it belongs to.
</details>

<details><summary>Hint 3 - where is it scheduled?</summary>

`grep -r reindex /etc/cron* /var/spool/cron 2>/dev/null` and `systemctl list-timers`.
`journalctl -u cron --since "10 min ago"` shows every cron run.
</details>

## What you should learn

- Load average = runnable (+ uninterruptible) tasks. Compare it to `nproc`.
- Killing a PID is not a fix if a scheduler (cron, systemd timer, supervisor, k8s) restarts it.
- `pstree -ps` and `systemctl status <PID>` answer "who started this?".
- Disable (comment out) and leave a note instead of deleting other teams' work.

Solution: [SOLUTION.md](SOLUTION.md)
