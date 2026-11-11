# E05 - Wrong page on port 80

**Level:** Easy · **Time:** 15 min · **Skills:** listening sockets, process to service mapping

## Ticket

> **INC-1005 · P1 · Customer facing**
> Customers see an old page *"Maintenance status: ALL GREEN (legacy page, 2021)"*
> instead of the shop. Someone ran `systemctl start nginx` and it failed.
> Restore the shop and make sure this does not come back after a reboot.

## Success criteria

- nginx owns port 80 and serves shopapp
- The thing that took port 80 is stopped **and** will not start at boot

## Hints

<details><summary>Hint 1 - why won't nginx start?</summary>

`journalctl -u nginx -n 20` - look for `bind() ... failed (98: Address already in use)`.
</details>

<details><summary>Hint 2 - who has the port?</summary>

`sudo ss -ltnp 'sport = :80'` or `sudo lsof -i :80` gives you the PID.
</details>

<details><summary>Hint 3 - PID to service</summary>

`systemctl status <PID>` tells you which systemd unit owns that process.
Killing the PID is not enough if the unit has `Restart=always`.
</details>

## What you should learn

- `Address already in use` = another socket holds the port. `ss -ltnp` finds the owner.
- `systemctl status <PID>` maps any PID to its unit (or `ps -o unit= -p <PID>`).
- `kill` treats the symptom; `systemctl disable --now` fixes the cause.

Solution: [SOLUTION.md](SOLUTION.md)
