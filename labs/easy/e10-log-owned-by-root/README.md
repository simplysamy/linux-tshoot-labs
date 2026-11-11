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
