# E03 - App won't start after "security hardening"

**Level:** Easy · **Time:** 20 min · **Skills:** Linux permissions, users/groups, path traversal

## Ticket

> **INC-1003 · P2**
> After the security team ran a hardening script last night, `shopapp` does not start.
> `curl localhost` returns **502 Bad Gateway**.
> The security team's goal: *other users on the box must not read the shopapp
> config.* Fix the app **without** undoing that goal (no `chmod 777`, no world-readable config).

## Success criteria

- shopapp is active and `/health` returns 200
- `shopapp` user can read but not write `config.ini`
- `config.ini` is not world-readable

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### curl - talk to a web service

```bash
curl http://localhost/                                   # 1. fetch a page, print the body
curl -s http://localhost/                                # 2. -s = silent (no progress bar)
curl -s -o /dev/null http://localhost/                   # 3. -o /dev/null = throw the body away
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/   # 4. -w = print only the HTTP status code
curl -v http://localhost/                                # 5. -v = verbose: shows connect, headers (debug)
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 5 http://localhost/   # 6. + timing, + give up after 5 s
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

## Hints

<details><summary>Hint 1 - 502 means what?</summary>

nginx is up but its backend (shopapp on :8080) is not answering. Look at the backend:
`systemctl status shopapp`, `journalctl -u shopapp -n 20`.
</details>

<details><summary>Hint 2 - which user?</summary>

Which user does the service run as? `systemctl show -p User shopapp` or look at
`systemctl cat shopapp`. Test as that user: `sudo -u shopapp cat /etc/shopapp/config.ini`.
</details>

<details><summary>Hint 3 - every directory counts</summary>

To open a file you need `x` on **every** directory on the path.
`namei -l /etc/shopapp/config.ini` shows owner and mode of each part.
</details>

## What you should learn

- 502 from a proxy -> the backend is the problem, not the proxy.
- Always test access *as the service user* (`sudo -u <user> ...`), not as root. Root ignores permissions.
- File access needs `r` on the file **and** `x` on every parent directory.
- Least privilege: give access through the **group** (`root:shopapp 0640`), not "other".

Solution: [SOLUTION.md](SOLUTION.md)
