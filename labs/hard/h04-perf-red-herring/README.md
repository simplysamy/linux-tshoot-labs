# H04 - "The server is slow" (and the obvious suspect is innocent)

**Level:** Hard · **Time:** 45 min · **Skills:** USE method, CPU vs. IO wait, per-process IO, systemd timers

## Ticket

> **INC-3004 · P2**
> Everything on the box feels slow: shell commands lag, `apt` and file writes crawl,
> shopapp latency is up. The junior on shift says: *"top shows `batch-encoder` at 100% CPU.
> I'll kill it."* - **Stop. Don't kill anything yet.**
> `batch-encoder` is an approved job that is *supposed* to use idle CPU.
> Find the real bottleneck with evidence, fix it, and keep `batch-encoder` running.

## Success criteria

- `batch-encoder` still running at nice 19
- The real cause stopped **or** limited so it cannot hurt the box, and it won't come back unconstrained
- You can explain with numbers why batch-encoder was *not* the cause

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

### free / vmstat - memory and swap

```bash
free                    # 1. memory in KB
free -m                 # 2. in MB; read the 'available' column, not 'free'
vmstat                  # 3. one summary line since boot
vmstat 1 5              # 4. a line per second, 5 times (ignore the first line)
# columns: r=runnable b=blocked si/so=swap in/out wa=CPU waiting for disk. si/so > 0 for long = swapping.
```

### iostat / pidstat - disk activity

```bash
iostat                          # 1. summary since boot
iostat -x 1 3                   # 2. -x = extended (utilisation, latency), every 1 s, 3 times
iostat -xz 1 3                  # 3. -z = hide idle devices
sudo pidstat -d 1 5             # 4. -d = disk IO per PROCESS, every 1 s, 5 times
ps -eo pid,stat,wchan:22,cmd | awk '$2 ~ /D/'   # 5. D = uninterruptible sleep = waiting for IO
# %util near 100 and high await = the disk is the bottleneck.
```

### systemctl + journalctl - service state and logs

```bash
systemctl status nginx                          # 1. state, last exit code, last log lines
systemctl is-active nginx                       # 2. one word: active / failed / inactive
journalctl -u nginx                             # 3. the whole log of one unit (-u = unit)
journalctl -u nginx -n 20                       # 4. only the last 20 lines
journalctl -u nginx -n 20 --no-pager            # 5. print straight to the terminal (no less)
journalctl -u nginx --since "10 min ago"        # 6. time window instead of line count
```

## Hints

<details><summary>Hint 1 - look at all resources, not only CPU</summary>

USE method: for each resource (CPU, memory, disk, network) check **U**tilisation,
**S**aturation, **E**rrors. Start with `vmstat 1 5` - read `r`, `b`, `us`, `sy`, `id`, `wa`.
In `top`, the header line `%Cpu(s)` has `ni` and `wa` - what do they mean?
</details>

<details><summary>Hint 2 - which disk, which process?</summary>

`iostat -xz 1 3` - look at `w/s`, `w_await`, `%util`.
`sudo pidstat -d 1 5` or `sudo iotop -o` shows IO per process.
`ps -eo pid,stat,wchan:20,cmd | awk '$2 ~ /D/'` shows tasks blocked on IO.
</details>

<details><summary>Hint 3 - it comes back</summary>

`systemctl status <PID>` shows the unit. Look for a `TriggeredBy:` line.
`systemctl list-timers --all`. Stopping the service is not enough if a timer restarts it.
Options: stop + disable the timer, or keep it but give it a low IO priority
(`sudo systemctl edit audit-sync.service` -> `IOSchedulingClass=idle` / `IOWeight=` / `IOWriteBandwidthMax=`).
</details>

## What you should learn

- High CPU from a **niced** process is mostly harmless: the scheduler gives CPU to normal tasks first. `ni` in top.
- `wa` (iowait) high + processes in `D` state + disk `%util` high = **IO bottleneck**.
- Small synchronous writes (`O_DSYNC`, `fsync`) can saturate a disk at low MB/s.
- Evidence before action. Killing the obvious suspect would have hurt the business and fixed nothing.
- systemd timers restart work just like cron. `TriggeredBy:` tells you.

Solution: [SOLUTION.md](SOLUTION.md)
