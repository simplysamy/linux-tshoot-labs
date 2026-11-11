# Linux Troubleshooting Lab

Hands-on break/fix labs for junior engineers. Each lab breaks a disposable Linux VM the way
production systems really break. You get a ticket, you find the root cause with real tools,
you fix it, and an automatic checker tells you if you are done.

- **30 labs** in 3 levels: 10 easy, 10 medium, 10 hard
- **[COMMAND_GUIDE.md](COMMAND_GUIDE.md)** - every command used in the labs, explained: what it does,
  the flags that matter, and how to read the output
- **[templates/incident-notes.md](templates/incident-notes.md)** - fill one in for every lab

> **Warning:** the labs delete files, fill disks, corrupt a filesystem, change the clock,
> push the VM into swap and change firewall rules and kernel settings **on purpose**. Run them only in the lab VM. The scripts refuse to run on a host
> without the `/etc/tshoot-lab` marker that the setup script creates.

---

## The system you will support

Every lab uses the same small "production" stack, so you learn the system the way you would at work:

```
 client --> nginx :80 --> shopapp :8080 (python, systemd unit, runs as user "shopapp")
                              |-- config : /etc/shopapp/config.ini
                              |-- logs   : /var/log/shopapp   (own 256 MB volume)
                              `-- data   : /srv/shopdata      (own 128 MB volume)
```

- `curl localhost/` -> `shopapp is running`
- `curl localhost/health` -> `OK` (the app writes a heartbeat file to the data volume)
- Unit file: `systemctl cat shopapp` · logs: `journalctl -u shopapp`, `/var/log/shopapp/app.log`

---

## Setup

### Option A - Vagrant (recommended)

Needs [Vagrant](https://developer.hashicorp.com/vagrant) + VirtualBox (or Hyper-V).

```bash
vagrant up
vagrant ssh
cd /lab
sudo ./labctl.sh list
```

Broke the VM beyond repair? `vagrant destroy -f && vagrant up`. That is the point of a lab VM.

### Option B - any throwaway Ubuntu 22.04 / 24.04 VM

```bash
# copy this folder to the VM, then:
sudo bash setup/install-base.sh
```

Windows users: keep LF line endings (the `.gitattributes` file does that for git checkouts).
If you see `$'\r': command not found`, run `sed -i 's/\r$//' $(find . -name '*.sh')`.

---

## How to run a lab

```bash
sudo ./labctl.sh list            # all labs
sudo ./labctl.sh start e01       # breaks the system and prints the ticket
#   ... investigate and fix ...
sudo ./labctl.sh check e01       # automatic checker: PASS / FAIL per item
sudo ./labctl.sh reset e01       # undo everything, back to a healthy baseline
./labctl.sh ticket e01           # print the ticket again
```

Rules for students:

1. **Don't read `break.sh` or `SOLUTION.md` first.** In production nobody tells you what broke.
2. Use the hints in the lab `README.md` one at a time, only after ~10 minutes stuck.
3. Write incident notes while you work (template above). The notes are the real deliverable.
4. After you pass, read `SOLUTION.md` anyway - compare your path with the senior path.
5. Only one lab active at a time. Always `reset` before the next one.

---

## Lab catalogue

### Easy - one fault, one layer

| Lab | Scenario | You practice |
|-----|----------|--------------|
| [e01-disk-full](labs/easy/e01-disk-full) | Log volume 100% full | `df`, `du`, `find -size`, safe cleanup |
| [e02-service-down](labs/easy/e02-service-down) | nginx down after a "small" config change | `systemctl`, `journalctl`, `nginx -t` |
| [e03-permission-denied](labs/easy/e03-permission-denied) | App won't start after hardening | `namei -l`, `sudo -u`, `chmod`/`chown`, least privilege |
| [e04-dns-resolution](labs/easy/e04-dns-resolution) | "Internet is down" | `dig`, `getent`, `resolv.conf`, `/etc/hosts`, nsswitch |
| [e05-port-conflict](labs/easy/e05-port-conflict) | Wrong page on port 80 | `ss -ltnp`, `lsof -i`, PID -> systemd unit |
| [e06-ssh-key-refused](labs/easy/e06-ssh-key-refused) | CI can't SSH in with its key | `ssh -v`, sshd log, `StrictModes`, `~/.ssh` modes |
| [e07-clock-timezone](labs/easy/e07-clock-timezone) | Log times hours off, NTP alert | `timedatectl`, NTP sync, restart to apply |
| [e08-command-not-found](labs/easy/e08-command-not-found) | "Works when I run it" | exit 127, systemd PATH vs login shell |
| [e09-service-not-enabled](labs/easy/e09-service-not-enabled) | Down after every reboot | `is-enabled`, `[Install]`, `enable --now` |
| [e10-log-owned-by-root](labs/easy/e10-log-owned-by-root) | 502 after a debugging session | crash loop, exit codes, `chown`, `sudo -u` |

### Medium - the obvious fix doesn't work, or there are 2-3 faults

| Lab | Scenario | You practice |
|-----|----------|--------------|
| [m01-deleted-open-file](labs/medium/m01-deleted-open-file) | Deleted a file, disk still full | `lsof +L1`, `/proc/PID/fd`, inodes |
| [m02-inode-exhaustion](labs/medium/m02-inode-exhaustion) | "No space left" on an empty disk | `df -i`, `du --inodes`, `find -mmin -delete` |
| [m03-high-cpu-respawn](labs/medium/m03-high-cpu-respawn) | CPU hog comes back after kill | `top`, `ps`, `pstree -ps`, cron |
| [m04-oom-crashloop](labs/medium/m04-oom-crashloop) | Service restarts every few seconds | OOM killer, cgroup `MemoryMax`, kernel log |
| [m05-cron-not-running](labs/medium/m05-cron-not-running) | Backups silently stopped | cron rules, cron log, run-as-cron |
| [m06-swap-storm](labs/medium/m06-swap-storm) | Everything slow, CPU idle | `vmstat si/so`, `VmSwap`, worker sizing, `sysctl.d` |
| [m07-zombie-processes](labs/medium/m07-zombie-processes) | Hundreds of `<defunct>`, fork fails | process states, reaping, `TasksMax` |
| [m08-logrotate-broken](labs/medium/m08-logrotate-broken) | Logs never rotate | `logrotate -d/-f`, `su`, `copytruncate`, `lsof +L1` |
| [m09-tls-cert-expired](labs/medium/m09-tls-cert-expired) | Certificate warning after a renewal | `openssl s_client/x509/pkey`, key match, key perms |
| [m10-listen-address](labs/medium/m10-listen-address) | Works on the box, down from outside | refused vs timeout, `ss -ltn`, INPUT rules, netns |

### Hard - several stacked faults, evidence needed, red herrings

| Lab | Scenario | You practice |
|-----|----------|--------------|
| [h01-fd-exhaustion](labs/hard/h01-fd-exhaustion) | App hangs after some traffic | `/proc/PID/limits`, fd leak, `strace`, drop-ins |
| [h02-readonly-filesystem](labs/hard/h02-readonly-filesystem) | "Read-only file system" | kernel log, `fuser`, `umount`, `e2fsck`, restore |
| [h03-network-path](labs/hard/h03-network-path) | Service unreachable across networks | `ip route`, `ip_forward`, `iptables -nv`, `tcpdump`, netns |
| [h04-perf-red-herring](labs/hard/h04-perf-red-herring) | "Server slow", wrong suspect | `vmstat`, `iostat -x`, `pidstat -d`, USE method, timers |
| [h05-boot-dependency](labs/hard/h05-boot-dependency) | App not back after reboot | mount units, fstab, `217/USER`, dependency chains |
| [h06-ephemeral-port-exhaustion](labs/hard/h06-ephemeral-port-exhaustion) | "Cannot assign requested address" | TIME_WAIT, port range, keep-alive, sysctl myths |
| [h07-mtu-blackhole](labs/hard/h07-mtu-blackhole) | Small requests OK, downloads hang | MTU, PMTUD, ICMP, `ping -M do`, MSS clamping |
| [h08-conntrack-table-full](labs/hard/h08-conntrack-table-full) | Random connect timeouts | `dmesg`, conntrack, connection leaks |
| [h09-nfs-hang](labs/hard/h09-nfs-hang) | Load 20, CPU idle, `df` hangs | D state, `/proc/PID/stack`, NFS options, egress firewall |
| [h10-cpu-throttling](labs/hard/h10-cpu-throttling) | Slow app on an idle host | cgroup `cpu.max`/`cpu.stat`, slices, drop-ins |

Suggested path:

1. Easy E01-E10 (any order; E01 before M01, E03 before E10)
2. Medium: M01, M02, M08 (disk/logs) -> M03, M04, M06, M07 (processes/memory) -> M05, M09, M10
3. Hard: H01, H02, H05 (one host) -> H04, H10 (performance) -> H03, H06, H07, H08 (network) -> H09

Labs that need internet access in the VM: E04 (DNS), E07 (only for the final NTP sync - not required to pass).

---

## How a senior SRE troubleshoots

Tools change; the method doesn't. Use it in every lab.

### 1. Confirm the symptom yourself
Tickets are often wrong. Reproduce it: `curl -v`, `systemctl status`, `df -h`. Write down the exact error.

### 2. Define scope and ask "what changed?"
One host or all? One service or all? Since when? Most incidents follow a change: deploy,
config edit, reboot, cron job, "hardening", "cleanup", load test. Check
`journalctl --since`, `last reboot`, `ls -lt /etc | head`, package logs (`/var/log/apt/history.log`).

### 3. Work from the outside in, layer by layer
Client -> DNS -> network -> port/listener -> proxy -> service -> app -> OS resources (CPU, memory, disk, fds) -> kernel/hardware.
Find the **first** layer that is broken. Error messages usually name it:

| Message | Likely layer |
|---------|--------------|
| `Connection refused` | nothing listening on that port (service down / wrong port) |
| `Connection timed out` | packets dropped: firewall, routing, host down |
| `Name or service not known` / `Temporary failure in name resolution` | DNS |
| `502 Bad Gateway` | proxy is up, backend down or refusing |
| `504 Gateway Timeout` | backend up but not answering in time (hung, overloaded) |
| `Permission denied` (EACCES) | file mode / owner / directory `x` bit / SELinux-AppArmor |
| `No space left on device` (ENOSPC) | blocks **or** inodes full |
| `Too many open files` (EMFILE) | per-process fd limit |
| `Read-only file system` (EROFS) | fs remounted ro (often after errors) or mounted ro |
| `Address already in use` (EADDRINUSE) | another process owns the port |
| `Cannot assign requested address` (EADDRNOTAVAIL) | out of local (ephemeral) ports for outgoing connections |
| `Resource temporarily unavailable` (EAGAIN) on fork | task/PID limit (`TasksMax`, zombies) |
| `certificate has expired` / `verify failed` | TLS: wrong/expired cert, missing CA, wrong name |
| exit code `127` | command not found (PATH) |

### 4. USE method for performance
For every resource - CPU, memory, disk, network: **U**tilisation, **S**aturation, **E**rrors.
Don't stop at the first busy thing you see (lab H04).

### 5. One hypothesis, one test, one change at a time
Write the hypothesis, the command that tests it, and the result. Change one thing, then re-test.
Several changes at once = you don't know what fixed it (or what broke something new).

### 6. Preserve evidence before you "fix"
A restart destroys the state you need (open fds, memory, stuck threads). Capture first:
`ps`, `ls /proc/PID/fd`, `ss`, logs. Then restart if you must (lab H01).

### 7. Fix the cause, not only the symptom
Killing a process that cron restarts, deleting files that a disabled cleanup job should delete,
raising a limit to hide a leak - these come back. Ask "why?" until you hit a process problem.

### 8. Verify, persist, document
Verify from the user's view (`curl`), make it survive a reboot (fstab, `systemctl enable`,
`sysctl.d`, firewall persistence), and write the incident notes with prevention items.

### Safety rules in production
- Look before destructive commands: `ls` before `rm`, `find ... -print | wc -l` before `-delete`, `pgrep -af` before `pkill -f`.
- Prefer `reload` over `restart`; run the config test first (`nginx -t`, `sshd -t`).
- Never `chmod 777`, never run the service as root to "fix" permissions.
- Never `fsck` a mounted filesystem. Never just remount a broken fs `rw`.
- Tell people what you are doing (incident channel) before you do it.

---

## Repo layout

```
labctl.sh                 lab controller (list/start/check/reset/ticket)
COMMAND_GUIDE.md          command reference with explanations
setup/install-base.sh     builds and restores the healthy baseline (idempotent)
setup/files/              shopapp code, config, unit, nginx site
lib/common.sh             shared helpers (safety checks, PASS/FAIL output)
labs/<level>/<id>/
    README.md             ticket, success criteria, hints, learning points
    SOLUTION.md           senior engineer walkthrough + root cause table
    break.sh              breaks the system (don't read before solving!)
    verify.sh             automatic checker
    cleanup.sh            undo + restore baseline
templates/incident-notes.md
```

## Instructor notes

- Pair juniors: one drives the keyboard, one keeps the incident notes. Swap each lab.
- After each lab, run a 10-minute review: "What was your first command? Why? What would you check first next time?"
- Hard labs work well as timed game days (45-60 min) with a senior acting as incident commander.
- Add your own lab: copy a lab folder, write `break.sh`/`verify.sh`/`cleanup.sh`, and end `cleanup.sh` with `restore_baseline`.
