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
