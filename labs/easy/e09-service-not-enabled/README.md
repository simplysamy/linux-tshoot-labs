# E09 - Down after every reboot

**Level:** Easy · **Time:** 10 min · **Skills:** systemctl enable, unit `[Install]` section, boot targets

## Ticket

> **INC-1009 · P2 (post-incident action)**
> After last night's patch reboot the shop was down for 40 minutes until on-call ran
> `systemctl start shopapp`. It is running now.
> Make sure shopapp starts **by itself** after the next reboot.
> Note: last week a "unit file template cleanup" was rolled out to this host.

## Success criteria

- `shopapp` is enabled for boot (`multi-user.target`)
- The unit file itself declares how it is enabled (so `enable`/`disable` keep working)
- shopapp is running and healthy

Check with `sudo ./labctl.sh check e09`.

## Hints

<details><summary>Hint 1 - running is not enabled</summary>

`systemctl is-active shopapp` vs `systemctl is-enabled shopapp`. They answer different questions.
</details>

<details><summary>Hint 2 - read the error</summary>

Try `sudo systemctl enable shopapp`. Read the whole message. Then `systemctl cat shopapp`.
</details>

<details><summary>Hint 3 - what enable does</summary>

`enable` creates a symlink in `/etc/systemd/system/<target>.wants/` based on the
`WantedBy=` line in the `[Install]` section. No `[Install]` = nothing to link.
</details>

## What you should learn

- `start` = now. `enable` = at boot. You usually want both: `systemctl enable --now`.
- `enable` needs `[Install] WantedBy=...` in the unit.
- After any fix, ask "will this survive a reboot?"

Solution: [SOLUTION.md](SOLUTION.md)
