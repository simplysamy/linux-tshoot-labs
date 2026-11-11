# E06 - SSH key login refused

**Level:** Easy · **Time:** 15 min · **Skills:** sshd logs, StrictModes, home/.ssh permissions

## Ticket

> **INC-1006 · P3 · CI pipeline red**
> The deploy job fails with `deploy@tshoot-lab: Permission denied (publickey).`
> The key has not changed. Yesterday someone "fixed permissions" in the `deploy`
> user's home directory so a shared script would work.
> Reproduce with:
> `sudo ssh -i /var/lib/tshoot/e06/deploy_key -o StrictHostKeyChecking=no deploy@127.0.0.1 hostname`
> Fix it without weakening the SSH server configuration.

## Success criteria

- Key login as `deploy` works with the given key
- `/home/deploy`, `~/.ssh` and `authorized_keys` have safe permissions
- `sshd_config` still enforces `StrictModes yes`

Check with `sudo ./labctl.sh check e06`.

## Hints

<details><summary>Hint 1 - the client tells you little</summary>

`ssh -v` shows the client side only: the key was offered and refused. The *reason* is
on the server: `journalctl -u ssh -n 30` (unit is `ssh` on Ubuntu, `sshd` elsewhere).
</details>

<details><summary>Hint 2 - what sshd checks</summary>

With `StrictModes yes` sshd refuses keys if the home directory, `~/.ssh` or
`authorized_keys` can be written by anyone other than the user.
`namei -l /home/deploy/.ssh/authorized_keys` shows every level at once.
</details>

<details><summary>Hint 3 - the right modes</summary>

Home: no group/other write (`755` or `750`). `~/.ssh`: `700`. `authorized_keys`: `600`.
All owned by `deploy`.
</details>

## What you should learn

- For SSH problems, the client error is generic - the server log has the real reason.
- `Authentication refused: bad ownership or modes` = permissions, not the key.
- `chmod 777` "to make it work" breaks security checks in other tools.
- Never fix this by setting `StrictModes no` - that removes a protection for every user.

Solution: [SOLUTION.md](SOLUTION.md)
