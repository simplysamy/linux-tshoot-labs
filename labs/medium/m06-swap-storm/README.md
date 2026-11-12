# M06 - Everything is slow, CPU is idle

**Level:** Medium · **Time:** 30 min · **Skills:** memory pressure, swap, `vmstat si/so`, RSS vs. swap per process, sysctl persistence

## Ticket

> **INC-2006 · P2**
> Since the change window for **CHG-552 "batch performance tuning"** the host is very
> sluggish: SSH takes seconds to echo keys, the shop is slow, load average is high.
> `top` shows the CPUs mostly idle. Nobody sees a CPU hog.
> `report-builder.service` (the nightly batch) must keep running - just not like this.

## Success criteria

- The host stops swapping (no steady swap-in/swap-out)
- `report-builder` keeps running with a sane memory footprint (≤ 50% of RAM)
- The swappiness "tuning" from CHG-552 is undone at runtime **and** on disk

Check with `sudo ./labctl.sh check m06`.

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

### sysctl - read and change kernel settings

```bash
sysctl vm.swappiness                    # 1. read one setting
sysctl -a | grep swappiness             # 2. list all, filter (when you do not know the exact name)
sudo sysctl -w vm.swappiness=60         # 3. -w = set NOW (lost at reboot)
cat /etc/sysctl.d/*.conf                # 4. where permanent values live
sudo sysctl --system                    # 5. re-read all files; the LAST file wins on a conflict
```

### grep VmSwap - who is swapped out?

```bash
grep VmSwap /proc/self/status                         # 1. swap used by one process
grep VmSwap /proc/[0-9]*/status 2>/dev/null           # 2. all processes (glob); hide errors of processes that vanished
grep VmSwap /proc/[0-9]*/status 2>/dev/null | sort -k2 -n | tail -3   # 3. sort by column 2, biggest last
```

## Hints

<details><summary>Hint 1 - CPU idle, load high</summary>

Load counts tasks waiting for CPU **and** tasks waiting in the kernel (I/O, page faults).
`vmstat 1 10` - look at the `si`/`so` (swap in/out) columns and `wa`. `free -m`.
</details>

<details><summary>Hint 2 - who uses the memory?</summary>

`ps -eo pid,user,rss,vsz,cmd --sort=-rss | head`. Swap per process:
`grep VmSwap /proc/*/status | sort -k2 -n | tail`. Add up all workers of the same program.
</details>

<details><summary>Hint 3 - what did CHG-552 change?</summary>

Look at recently changed files: `ls -lt /etc /etc/sysctl.d | head`.
`sysctl vm.swappiness`, and read the report-builder config. Two settings were changed.
</details>

## What you should learn

- Swap thrashing looks like "slow everything, CPU idle". `si`/`so` > 0 every second is the signal.
- `free` "used" is not the story: check **available** and swap activity.
- Size worker pools to RAM: workers × memory per worker must fit with headroom.
- `vm.swappiness` changes *when* the kernel swaps; it does not create memory.
- A runtime `sysctl -w` is lost at reboot; a file in `/etc/sysctl.d/` comes back at boot.

Solution: [SOLUTION.md](SOLUTION.md)
