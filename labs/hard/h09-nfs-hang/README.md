# H09 - Load 20, CPU idle, `df` hangs

**Level:** Hard · **Time:** 60 min · **Skills:** D-state processes, load average, NFS hard mounts, `/proc/PID/stack`/`wchan`, firewall, safe fstab options

## Ticket

> **INC-3009 · P1**
> tshoot-lab's load average keeps climbing (10, 15, 20 ...) but CPU is idle.
> `df -h` hangs and cannot be interrupted with Ctrl-C. An engineer's `ls /mnt` froze their shell.
> The nightly report export to the NAS (`nas01.lab.internal:/srv/nfs/reports` on `/mnt/reports`)
> has not produced files today.
> Change calendar: **SEC-410** "egress lockdown" was applied this morning.
>
> Restore the report export. Also make sure that the next NAS outage cannot hang the host's
> **boot**. Open a **new** terminal for your investigation - expect some commands to hang.

## Success criteria

- No processes stuck in state `D`
- `df -h` and `ls /mnt/reports` return within 5 seconds
- `/mnt/reports` is mounted, writable, and the report export works again
- The fstab entry is safe for boot (`_netdev` and `nofail`)

Check with `sudo ./labctl.sh check h09`.

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

### D-state / NFS hang - look without hanging yourself

```bash
ps -eo pid,stat,cmd | awk '$2 ~ /D/'           # 1. D = stuck in the kernel (waiting for IO)
sudo cat /proc/PID/stack | head -5             # 2. WHERE in the kernel it waits (look for nfs / sunrpc)
findmnt -t nfs,nfs4                            # 3. SAFE: reads the mount table only (df on a dead NFS would hang!)
timeout 5 stat -f /mnt/reports || echo hang    # 4. timeout = give up after 5 s so your shell does not freeze
nc -vz -w3 10.0.0.10 2049                      # 5. can we even reach the NFS port? (-z scan, -v verbose, -w3 3 s)
```

### findmnt / mount - what is mounted

```bash
mount | head                         # 1. old way: long list
findmnt                              # 2. tree of all mounts
findmnt /srv/shopdata                # 3. one mount: source, type, options (look for ro / rw)
findmnt -t nfs,nfs4                  # 4. -t = only these types
findmnt -no OPTIONS /srv/shopdata    # 5. -n no header, -o choose column -> script-friendly
```

### iptables - read the firewall

```bash
sudo iptables -L                              # 1. list rules (all chains)
sudo iptables -L INPUT                        # 2. one chain: INPUT = traffic TO this host; FORWARD = through; OUTPUT = from
sudo iptables -L INPUT -n                     # 3. -n = numbers, no DNS (much faster)
sudo iptables -L INPUT -n -v                  # 4. -v = packet/byte counters: does the number rise when you test? -> that rule hits
sudo iptables -L INPUT -n -v --line-numbers   # 5. rule numbers, so you can delete/insert by number
sudo iptables -S                              # 6. the same rules as commands (easy to copy, grep)
# change:  -D INPUT 1  (delete rule 1)   -I INPUT 1 <rule>  (insert at top)   -A  (append at end)
```

### fstab options for network mounts

```bash
grep reports /etc/fstab               # 1. look at the line
# _netdev  = wait for the network      nofail = do not drop to emergency mode if it is missing
# hard     = keep retrying   x-systemd.mount-timeout=30 = give up waiting after 30 s
sudo systemctl daemon-reload          # 2. systemd regenerates mount units from fstab
sudo mount -o remount /mnt/reports    # 3. apply new options without unmounting
```

## Hints

<details><summary>Hint 1 - what is load?</summary>

Linux load = runnable tasks **+ tasks in uninterruptible sleep (D)**.
`ps -eo pid,stat,wchan:32,cmd | awk '$2 ~ /D/'`. What are they waiting for?
`sudo cat /proc/<PID>/stack`.
</details>

<details><summary>Hint 2 - which mount?</summary>

`findmnt -t nfs,nfs4` (reads `/proc/self/mountinfo`, does not touch the server - safe).
Use `timeout 5 stat -f /mnt/reports` instead of a bare `ls` so your shell does not hang.
`dmesg -T | grep -i nfs` - "server not responding". Who is the server? `getent hosts nas01.lab.internal`.
</details>

<details><summary>Hint 3 - why can't we reach it?</summary>

`nc -vz -w3 nas01.lab.internal 2049`. `sudo iptables -L OUTPUT -n -v --line-numbers`.
After you fix the path, a hard mount recovers by itself (it can take a minute - TCP backoff).
Then look at the mount options in `/etc/fstab`.
</details>

## What you should learn

- High load + idle CPU = look for D-state tasks, not CPU hogs.
- A `hard` NFS mount blocks every process that touches it until the server is back - including `df`.
- `findmnt` is safe; `df`, `ls`, `stat` on a dead NFS mount are not. Use `timeout`.
- Firewall changes can cut storage paths. Check egress rules, not only ingress.
- `_netdev` + `nofail` (and maybe `x-systemd.automount`) stop a dead NAS from blocking boot.
- Last resort: `umount -f -l` (lazy, force) - processes may still get errors.

Solution: [SOLUTION.md](SOLUTION.md)
