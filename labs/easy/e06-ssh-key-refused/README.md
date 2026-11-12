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

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### ssh - log in and debug

```bash
ssh user@host                                   # 1. log in
ssh user@host hostname                          # 2. run ONE command and exit
ssh -i ~/.ssh/key user@host hostname            # 3. -i = use this private key
ssh -o StrictHostKeyChecking=no user@host hostname   # 4. -o = set an option (here: skip the host-key question; lab only!)
ssh -v -i ~/.ssh/key user@host 2>&1 | grep -E 'Offering|Authentications'   # 5. -v = debug; filter the useful lines
# The client rarely knows why it was refused - read the SERVER log: journalctl -u ssh -n 20
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
