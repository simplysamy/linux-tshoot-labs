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
