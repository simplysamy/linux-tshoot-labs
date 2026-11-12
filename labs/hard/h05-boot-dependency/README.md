# H05 - App does not come back after a maintenance reboot

**Level:** Hard · **Time:** 45 min · **Skills:** systemd dependencies, mount units, fstab, drop-ins, exit codes

## Ticket

> **INC-3005 · P1 · Customer facing**
> Last night's maintenance window had two changes: a storage "naming cleanup" and
> security ticket SEC-117 ("service account naming standard"). After the reboot,
> shopapp did not come back. nginx shows **502**.
> The change owners are asleep. Restore service, and make sure it survives the **next** reboot.

(The lab simulates the reboot of the app stack - you don't need to reboot the VM.
The checker simulates it again.)

## Success criteria

- `/srv/shopdata` mounts from fstab, shopapp starts automatically, `/health` 200
- shopapp does not run as root
- Survives a simulated reboot

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

### fstab / mount - boot-time mounts

```bash
cat /etc/fstab                                  # 1. what mounts at boot: source, mountpoint, type, options, dump, pass
grep shopdata /etc/fstab                        # 2. one line
ls -l /var/lib/tshoot/*.img                     # 3. does the source file/device really exist?
blkid                                           # 4. UUIDs/labels of real disks (compare with fstab)
sudo mount -a                                   # 5. try every fstab line now (errors show here, not at 3am boot)
findmnt /srv/shopdata                           # 6. confirm
getent passwd shopapp                           # 7. does this user exist? (no output = no)
```

### systemctl show / cat - ask systemd for facts

```bash
systemctl cat nginx                              # 1. the unit file(s) systemd really uses, incl. drop-ins
systemctl show nginx                             # 2. every property (long)
systemctl show -p User nginx                     # 3. -p = just one property
systemctl show -p User -p MainPID nginx          # 4. several
systemctl show -p MainPID --value nginx          # 5. --value = print only the value (for scripts)
```

## Hints

<details><summary>Hint 1 - what failed?</summary>

`systemctl --failed`. `systemctl status shopapp` - read `Dependency failed` carefully.
`systemctl list-dependencies shopapp` shows what it needs (look for red / failed).
</details>

<details><summary>Hint 2 - the mount</summary>

Mounts from `/etc/fstab` become units: `/srv/shopdata` -> `srv-shopdata.mount`
(`systemd-escape -p --suffix=mount /srv/shopdata`). `systemctl status srv-shopdata.mount`,
`journalctl -b -u srv-shopdata.mount`. Compare fstab with what exists on disk.
After editing fstab: `systemctl daemon-reload`.
</details>

<details><summary>Hint 3 - after the mount works</summary>

The app fails differently now. `systemctl status shopapp` shows `status=217/USER`.
What does 217 mean? `systemctl cat shopapp` shows every drop-in. `getent passwd shop-app`.
</details>

## What you should learn

- systemd failures chain: a failed mount -> `Dependency failed` on every unit that needs it.
  Fix the **first** failure in the chain.
- fstab entries are converted into `.mount` units by a generator - `daemon-reload` after edits.
- systemd exit codes like `217/USER`, `203/EXEC`, `200/CHDIR` describe *setup* failures before the app ran. App logs will be empty.
- Partially applied changes (config changed, user never created) are a classic maintenance-window failure.
- "Fixed" is not done until it survives a reboot.

Solution: [SOLUTION.md](SOLUTION.md)
