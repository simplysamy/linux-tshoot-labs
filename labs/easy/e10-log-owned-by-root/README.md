# E10 - 502 after a debugging session

**Level:** Easy · **Time:** 15 min · **Skills:** reading crash loops, exit codes, file ownership, running things as the right user

## Ticket

> **INC-1010 · P2**
> The shop returns `502 Bad Gateway` since this morning.
> Yesterday evening an engineer was debugging shopapp. Their note in the ticket:
> *"stopped the service, ran app.py by hand as root to see the error, moved the old log away,
> started the service again - looked fine."*
> Bring the shop back. The service must keep running as user `shopapp`.

## Success criteria

- shopapp is active and stays up; `/health` returns 200
- shopapp still runs as user `shopapp`
- Log files belong to `shopapp`

Check with `sudo ./labctl.sh check e10`.

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### ls / namei / id - read permissions

```bash
ls                                  # 1. names only
ls -l /etc/hostname                 # 2. -l = long: mode, owner, group, size, date
ls -ld /etc                         # 3. -d = the directory itself, not its content
namei -l /etc/hostname              # 4. mode + owner of EVERY directory on the way (a path needs x on each)
id                                  # 5. who am I: uid, gid, groups
sudo -u www-data cat /etc/hostname  # 6. run a command AS another user = test what the service can do
# mode  rwxr-x---  = owner rwx (7), group r-x (5), others --- (0)  ->  chmod 750
```

### chmod / chown - change permissions and owner

```bash
chmod 644 file          # 1. numbers: r=4 w=2 x=1, add up per owner/group/others -> rw-r--r--
chmod 600 file          # 2. owner only: rw-------
chmod u+x file          # 3. symbolic: u=owner g=group o=others, +/- add/remove a bit
chown alice file        # 4. change owner
chown alice:staff file  # 5. owner and group
chown -R alice:staff dir/   # 6. -R = recursive (whole tree - double-check the path first!)
```

### systemd-run / sudo -u - run it like the service does

```bash
sudo -u shopapp COMMAND                         # 1. as the service user
sudo systemd-run --pty -p User=shopapp COMMAND  # 2. through systemd: same environment as a service
sudo systemctl start shopapp-report             # 3. start the real unit, then read its status/journal
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

<details><summary>Hint 1 - 502 means...</summary>

nginx is up, the backend is not. `systemctl status shopapp` - is it running,
restarting, failed? Look at the exit `status=`.
</details>

<details><summary>Hint 2 - why does it exit?</summary>

`journalctl -u shopapp -n 20`. The app prints a FATAL line before it exits.
</details>

<details><summary>Hint 3 - who owns it</summary>

`ls -l /var/log/shopapp/`. Which user runs the service (`systemctl show -p User shopapp`)?
Can that user write the file? Test: `sudo -u shopapp test -w /var/log/shopapp/app.log && echo ok`.
</details>

## What you should learn

- 502 from a proxy = look at the backend service first.
- A crash loop shows up as `activating (auto-restart)` and a growing restart counter.
- Running a service by hand as root leaves root-owned files that the real service user
  cannot write. Use `sudo -u <serviceuser>` when you debug.
- The fix is `chown` back to the service user - not running the service as root.

Solution: [SOLUTION.md](SOLUTION.md)
