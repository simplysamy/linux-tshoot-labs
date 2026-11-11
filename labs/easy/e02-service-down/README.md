# E02 - Website down after a config change

**Level:** Easy · **Time:** 15 min · **Skills:** systemd, journal, config validation

## Ticket

> **INC-1002 · P1 · Customer facing**
> `curl http://localhost/` returns **Connection refused**.
> A colleague says: "I only bumped an nginx timeout and restarted it. Nothing else."
> Bring the site back. Keep the colleague's change if it is valid.

## Success criteria

- `nginx -t` passes, nginx is active and enabled
- `http://localhost/` returns 200

## Hints

<details><summary>Hint 1 - is it running?</summary>

`systemctl status nginx` - look at the `Active:` line and the last log lines.
</details>

<details><summary>Hint 2 - why did it fail?</summary>

`journalctl -u nginx -n 30 --no-pager` and `sudo nginx -t`. The error names a
file and a line number.
</details>

<details><summary>Hint 3 - read the line before</summary>

Parser errors often point at the line *after* the real mistake. Check the end of
the line before it.
</details>

## What you should learn

- Connection refused = nothing is listening on that port. Check the service first.
- `systemctl status` -> `journalctl -u` -> the tool's own config test (`nginx -t`,
  `sshd -t`, `apachectl configtest`, `named-checkconf`).
- Always run the config test **before** you restart. `nginx -t && systemctl reload nginx`.
- `reload` keeps the old workers if the new config is bad; `restart` stops nginx first.

Solution: [SOLUTION.md](SOLUTION.md)
