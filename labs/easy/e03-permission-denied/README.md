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
