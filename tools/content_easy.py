# Hand-written study content for the easy labs.
# mcq tuple: (question, [CORRECT option first, wrong, wrong, wrong], why-explanation)
# qa tuple : (question, model answer)   - option order is shuffled in the browser.

CONTENT = {
"e01": dict(
explain="""
**Mental model.** Two tools, two questions:

- `df` asks the **filesystem** how many blocks are used (superblock counters). It answers *which volume is full*.
- `du` / `find` **walk directory names** and add up file sizes. They answer *what is filling it*.

Here `/var/log/shopapp` is its own 256 MB volume, so `/` looked healthy while the log volume hit 100%.
The app kept serving pages (the web request does not depend on the log write) but every log write failed with `ENOSPC` (`Errno 28`) - which is why the *log* silently stopped growing.

**Why `-x` / `-xdev`?** Without it `du` and `find` cross into other mounted volumes, so you count (or delete!) data that is not on the full filesystem.

**Why look before you `rm`?** If a process still has the file open, `rm` removes only the *name*; the blocks stay allocated (that is lab M01). Here `lsof` printed nothing, so a plain `rm` was safe. If something *had* held it, `truncate -s 0` frees the blocks immediately.

**Why not the obvious file?** The ticket protects `app.log` (audit). The big file was a forgotten debug trace, found by size - not by guessing from the symptom.
""",
mcq=[
("Which command tells you WHICH filesystem is full?",
 ["df -h", "du -sh /", "lsof +L1", "ls -l /var/log"],
 "`df` reads per-filesystem usage. `du` shows what is inside a directory tree, not which volume is full."),
("Why do you add `-x` (du) or `-xdev` (find) when hunting for big files on a full volume?",
 ["It keeps the command on one filesystem, so other mounted volumes are not counted or touched",
  "It makes the command run faster by using extended attributes",
  "It excludes files owned by root",
  "It shows only files larger than 1 MB"],
 "`-x`/`-xdev` = do not cross mount points. Otherwise you may chase space (or delete files) on a different volume."),
("A running process still writes to a 200 MB log and you need the space back NOW without stopping it. What do you do?",
 ["truncate -s 0 the file", "rm the file", "mv the file to /tmp", "chmod 000 the file"],
 "`rm` only removes the name; the open fd keeps the blocks. Truncating in place frees them while the process keeps its fd."),
],
qa=[
("The ticket says 'do not delete app.log'. app.log is the file that stopped growing - so why is it NOT the file to clean up?",
 "app.log stopped growing only because the volume was full (ENOSPC). It is the victim, not the cause. The real consumer was debug-trace.log (200 MB), found with `du -xh --max-depth=1 | sort -h` and `find -size +20M`. Always find what fills the disk by measuring, not by assuming the file named in the symptom."),
("Name three prevention items for this incident.",
 "1) logrotate rule with `maxsize` for /var/log/shopapp/*.log. 2) Alert at 80% disk usage, not 100%. 3) Turn debug tracing off after use / time-box debug flags. (Bonus: monitor inode usage too.)"),
]),

"e02": dict(
explain="""
**Connection refused = nothing is listening.** The kernel answers a SYN to a closed port with a RST. So the first question is not "what is wrong with the app" but "is the service running?" - `ss -ltnp 'sport = :80'` and `systemctl status nginx`.

**Why the error points at the wrong line.** nginx directives end with `;`. With `proxy_read_timeout 30s` missing its `;`, the parser keeps reading and treats the next line as more arguments:

```
proxy_read_timeout 30s proxy_send_timeout 30s;   # one directive, 3 args -> "invalid number of arguments"
```

The error names the line where the parser *gave up*, which is often the line **after** the real mistake. Look at the end of the previous line.

**Config test before apply.** `nginx -t` parses the config without touching the running server. `reload` starts new workers with the new config and keeps the old ones if parsing fails; `restart` stops nginx first, so a bad config means an outage. Habit: `nginx -t && systemctl reload nginx`. The same pattern exists for `sshd -t`, `apachectl configtest`, `named-checkconf`.

Keep the colleague's valid change (30s timeout): fix the syntax, do not revert blindly.
""",
mcq=[
("`curl http://localhost/` returns 'Connection refused'. What is the best FIRST check?",
 ["Is nginx running / is anything listening on port 80? (systemctl status nginx, ss -ltnp)", "Clear the DNS cache", "Check the TLS certificate dates", "Increase proxy_read_timeout"],
 "Refused = RST from the kernel = no listener on that port."),
("nginx reports an error on line 15, but the typo is on line 14. Why?",
 ["A missing `;` makes the parser continue into the next line and only fail there", "nginx counts lines starting from 0", "The journal shows the wrong file", "nginx -t reports errors one line late by design in all cases"],
 "Without `;` the next line's text becomes extra arguments; the parser fails when it sees too many."),
("Why is `nginx -t && systemctl reload nginx` safer than `systemctl restart nginx`?",
 ["With a bad config the reload fails and the old workers keep serving; a restart would stop nginx first", "reload is faster because it skips DNS", "restart does not read the config file", "reload re-enables the unit at boot"],
 "Validate first; reload never drops the old working configuration if the new one is broken."),
],
qa=[
("Walk through the tools you use from symptom to root cause for this ticket, in order.",
 "curl -v (confirm 'Connection refused') -> ss -ltnp 'sport = :80' (nothing listens) -> systemctl status nginx (failed, exit-code) -> journalctl -u nginx -n 30 (emerg + file:line) -> nginx -t -> grep -n timeout on the file (see missing `;`) -> fix with sed/editor -> nginx -t && systemctl restart nginx -> curl returns 200."),
("The colleague only 'bumped a timeout'. What do you keep and what do you change?",
 "Keep the new timeout value (it is valid); only add the missing semicolon. Reverting the whole change would hide the real lesson and lose their intended tuning. Prevent with config in git + CI lint and always running nginx -t before applying."),
]),

"e03": dict(
explain="""
**502 = proxy fine, backend not.** nginx answered, so look at shopapp (`systemctl status`, `journalctl -u shopapp`). The log says `Permission denied` on the config.

**Permission rule you must know:** to open `/etc/shopapp/config.ini` a user needs `r` on the file **and** `x` (search) on **every directory** on the path. `namei -l <path>` prints owner and mode of each component - the broken one stands out.

**Test as the service user.** `root` ignores file permissions (DAC), so `sudo cat` "works" and proves nothing. Use `sudo -u shopapp cat ...`.

**Least privilege with groups:**

```
root:shopapp 0640 config.ini   # root rw, group shopapp r, others nothing
0755 /etc/shopapp              # directory itself holds no secret; the file does
```

The security goal (others cannot read the config) stays true; only the service user's group gets read access. Wrong fixes: `chmod 777`, `chmod 644` (world-readable = violates the goal), `User=root` (service gets too much power).
""",
mcq=[
("nginx returns 502 Bad Gateway. What does that tell you?",
 ["nginx is up, but its backend (shopapp) is not answering correctly", "nginx itself is down", "DNS is broken", "The client certificate is invalid"],
 "A 502 is generated by the proxy when the upstream fails. Start with the backend."),
("Why is `sudo cat /etc/shopapp/config.ini` NOT a valid test of whether shopapp can read it?",
 ["root bypasses file permission checks; you must test as the service user (sudo -u shopapp)", "sudo strips the file path", "cat cannot open .ini files", "sudo cat is always denied"],
 "DAC permission checks do not apply to root, so the test must run as the real service user."),
("Which result best meets 'shopapp can read the config, others cannot'?",
 ["chown root:shopapp config.ini; chmod 0640 config.ini (and make the directory traversable)", "chmod 777 config.ini", "chmod 644 config.ini", "Change the unit to User=root"],
 "Group read for the service group; no access for others. 777/644 are too open; root is excessive privilege."),
],
qa=[
("What does `namei -l /etc/shopapp/config.ini` show and why was it the key command?",
 "It prints owner, group and mode of every component of the path (/, etc, shopapp, config.ini). It revealed `drwx------ root` on the shopapp directory (no `x` for the shopapp user) and `-rw------- root` on the file (no `r`) - two separate problems that a single `ls -l` of the file would have hidden."),
("Why is `chmod 644 config.ini` the wrong fix even though the service then starts?",
 "It makes the config world-readable, which is exactly what the security team's hardening wanted to prevent. The correct fix grants read through the group (root:shopapp 0640) so the requirement and the service both work."),
]),

"e04": dict(
explain="""
**How a name becomes an IP for an application:**

1. glibc reads `/etc/nsswitch.conf`: `hosts: files dns`
2. `files` = `/etc/hosts` is checked **first**
3. `dns` = nameservers in `/etc/resolv.conf` (on Ubuntu normally the stub `127.0.0.53` of systemd-resolved)

**Split the problem.** `ping 8.8.8.8` works but `ping ubuntu.com` fails -> IP routing is fine, name resolution is broken.

**Two independent faults here:**

1. `/etc/resolv.conf` was turned from a symlink (to `/run/systemd/resolve/stub-resolv.conf`) into a plain file pointing at a dead server `10.255.255.53`.
2. A stale line in `/etc/hosts` pins `example.com` to `203.0.113.77`.

**Tool difference:** `dig` and `nslookup` talk to DNS only - they ignore `/etc/hosts`. `getent hosts` uses the same lookup path as real programs. After you fix DNS, `dig example.com` is right while `curl` still hits the stale IP - the "dig and curl disagree" trap.
""",
mcq=[
("`ping 8.8.8.8` works but `ping ubuntu.com` fails with 'Temporary failure in name resolution'. What is broken?",
 ["Name resolution (DNS / resolver config)", "Routing to the internet", "The default gateway", "The network cable"],
 "IP reachability is proven by the successful ping to an IP; only name -> IP resolution fails."),
("After fixing DNS, `dig example.com` shows the real IP but `curl https://example.com` still connects to a wrong IP. Why?",
 ["/etc/hosts is consulted before DNS (nsswitch: files dns) and has a stale entry; dig ignores /etc/hosts", "curl caches DNS answers for 24 hours", "dig uses IPv6 only", "systemd-resolved is stopped"],
 "Applications follow nsswitch order; `files` comes before `dns`. `dig` only queries DNS."),
("On a standard Ubuntu 22.04/24.04, what is /etc/resolv.conf normally?",
 ["A symlink to /run/systemd/resolve/stub-resolv.conf managed by systemd-resolved", "A plain file that admins edit by hand", "An empty file", "A symlink to /etc/hosts"],
 "Hand edits get lost or (as here) break resolution; manage DNS via netplan/systemd-resolved."),
],
qa=[
("Which command shows what applications really resolve, and why not use dig for that?",
 "`getent hosts <name>` (or `getent ahosts`) - it goes through nsswitch.conf (/etc/hosts, then DNS). dig/nslookup query DNS servers directly and bypass /etc/hosts, so they can disagree with what curl/apps see."),
("You fixed fault 1 and `apt update` works. Why are you not done, and how do you verify the whole ticket?",
 "The ticket also says the payment check to example.com fails. A second fault (stale /etc/hosts entry) remained. Verify with the real client: `getent hosts example.com` and `curl -sI https://example.com`, not just with one tool. Always re-test the original symptom, not only the first fix."),
]),

"e05": dict(
explain="""
**One listener per (address, port).** `bind()` fails with errno 98 `Address already in use` when another socket already listens there. nginx logged exactly that.

**Find the owner:** `sudo ss -ltnp 'sport = :80'` -> `python3 pid=2345`. **Map PID to unit:** `systemctl status 2345` (or `ps -o unit= -p 2345`) reads the process's cgroup and tells you `legacy-status.service`.

**Why `kill` is not a fix:** the unit has `Restart=always`, so systemd restarts it within 100 ms and it grabs port 80 again. And it is **enabled**, so it would also win the race after the next reboot.

| Command | Stops now | Stops at boot |
|---|---|---|
| `systemctl stop X` | yes | no |
| `systemctl disable X` | no | yes |
| `systemctl disable --now X` | yes | yes |

Order of fix: disable --now the squatter, confirm port 80 is free (`ss`), start nginx, `curl` the shop. Remove the retired unit only after asking its owner.
""",
mcq=[
("nginx fails with `bind() to 0.0.0.0:80 failed (98: Address already in use)`. What does it mean?",
 ["Another process already listens on port 80", "The firewall blocks port 80", "nginx lacks permission to use ports below 1024", "The port number is invalid"],
 "EADDRINUSE: the (address, port) is already bound by another socket."),
("Which command shows which process owns port 80?",
 ["sudo ss -ltnp 'sport = :80'", "systemctl list-timers", "df -h", "ip route"],
 "`ss -ltnp` lists listening TCP sockets with the owning process."),
("Why is `kill <PID>` not enough here?",
 ["The unit has Restart=always (and is enabled), so it comes back; use systemctl disable --now", "kill cannot stop python processes", "Port 80 can never be freed", "nginx must be reinstalled first"],
 "Fix the cause (the unit), not the symptom (the process)."),
],
qa=[
("Explain the difference between `stop`, `disable` and `disable --now`.",
 "stop ends the running process only (it returns at next boot if enabled). disable removes the boot symlink but leaves it running. disable --now does both: stops now and prevents starting at boot - what this ticket asks for."),
("After the fix, what two checks prove the shop is restored AND the problem will not return after a reboot?",
 "`ss -ltnp 'sport = :80'` shows nginx and `curl localhost/` returns 'shopapp is running'; `systemctl is-enabled legacy-status` says disabled while `systemctl is-enabled nginx` says enabled."),
]),

"e06": dict(
explain="""
**The client error is generic.** `Permission denied (publickey)` only says "the server did not accept any key". The reason lives in the **server** log: `journalctl -u ssh` (unit is `ssh` on Ubuntu, `sshd` elsewhere):

```
Authentication refused: bad ownership or modes for directory /home/deploy
```

**StrictModes yes** (default): sshd refuses to trust `authorized_keys` if the user's home directory, `~/.ssh` or the file can be written by anyone other than the user (or root). If they could be, any local user could append their own key and log in as `deploy`. So sshd rejects the setup instead of the key.

**Safe modes:**

| Path | Mode |
|---|---|
| `/home/deploy` | 755 (or 750) - no group/other write |
| `~/.ssh` | 700 |
| `~/.ssh/authorized_keys` | 600 |

All owned by `deploy`. `namei -l` shows every level at once.

**Wrong fixes:** `StrictModes no` (removes the protection for every user on the server) and leaving `777` "so the shared script works" - give that script a group-owned shared directory instead.
""",
mcq=[
("`ssh` says `Permission denied (publickey)`. Where do you find the real reason?",
 ["The server's auth log: journalctl -u ssh", "ssh -v on the client always prints the reason", "The client's ~/.ssh/known_hosts", "/var/log/dpkg.log"],
 "The server deliberately gives the client little detail; its log has `bad ownership or modes`."),
("Which permission set is safe for key login?",
 ["home 755, ~/.ssh 700, authorized_keys 600, all owned by the user", "home 777, ~/.ssh 777, authorized_keys 666", "home 700, ~/.ssh 755, authorized_keys 777", "everything owned by root with 600"],
 "No group/other write anywhere on the path; .ssh and the key file private."),
("A colleague suggests `StrictModes no` in sshd_config. Why is that bad?",
 ["It disables a safety check for every user on the host, not only deploy", "It breaks password logins", "It changes the SSH port", "It deletes authorized_keys"],
 "Fix the permissions, never weaken the server config."),
],
qa=[
("Why does sshd refuse a key when the home directory is world-writable?",
 "Anyone who can write the home dir or ~/.ssh can replace or add to authorized_keys, i.e. add their own public key and log in as that user (or swap .ssh for a symlink). sshd can't tell the file is trustworthy, so with StrictModes it ignores it."),
("A shared script needed access to /home/deploy, which is why someone ran chmod -R 777. What is a better design?",
 "Put the shared files in a group-owned directory (e.g. /srv/shared with a dedicated group and mode 2770/2750), or use ACLs - and keep the home at 755/750 with .ssh 700 and authorized_keys 600."),
]),

"e07": dict(
explain="""
**Two different things called "time":**

- the **clock** - the real instant (kept as UTC by the kernel; NTP corrects drift)
- the **timezone** - only how that instant is *displayed* (`/etc/localtime` -> a zoneinfo file)

`timedatectl` shows both plus "System clock synchronized" and "NTP service". Here: zone `America/Los_Angeles` (logs 8 h off) **and** NTP inactive (clock drifted by minutes).

**Fix:** `timedatectl set-timezone Etc/UTC` and `timedatectl set-ntp true` (systemd-timesyncd; chrony on newer Ubuntu). Synchronisation needs network access to an NTP server (UDP 123).

**Why the app still logged the old zone:** a process reads the timezone (the `TZ` / `/etc/localtime`) when it starts. Changing the system setting does not change running processes - **restart shopapp**. The same is true for environment variables and limits.

**Why servers use UTC:** one timeline for log correlation, no daylight-saving jumps. A drifting clock also breaks TLS validity checks, Kerberos (5 min skew), cron timing and token expiry.
""",
mcq=[
("Which single command shows local time, UTC time, timezone and NTP sync status?",
 ["timedatectl", "date +%s", "hwclock --debug", "uptime"],
 "`timedatectl` is the one place to look."),
("You set the timezone to UTC but shopapp still writes local-time timestamps. What is needed?",
 ["Restart shopapp - it read the timezone at startup", "Reboot the network", "Run logrotate", "Nothing, it updates after 24 hours"],
 "Timezone is read at process start; running processes keep the old value."),
("Which is NOT a typical consequence of a drifting system clock?",
 ["The disk fills up faster", "TLS certificate validation errors", "Kerberos authentication failures", "Log timestamps that cannot be correlated across servers"],
 "Clock drift affects anything time-based; it does not change disk consumption."),
],
qa=[
("Explain the difference between a wrong timezone and a wrong clock, and how you can tell them apart.",
 "A wrong timezone changes only the displayed local time; `date -u` (UTC) is still correct. A wrong clock means even UTC is off - compare `date -u` with a trusted source or see `System clock synchronized: no` / NTP inactive in timedatectl. This host had both."),
("Why do most server fleets run in UTC?",
 "One shared timeline makes log correlation and incident timelines simple, avoids daylight-saving ambiguity, and keeps tools (TLS, cron schedules, tokens) consistent. Convert to local time only at display."),
]),

"e08": dict(
explain="""
**Exit code 127 = command not found** (126 = found but not executable). systemd logged `shopctl: command not found` with status 127.

**Why it works in your shell:** an interactive **login shell** reads `/etc/profile`, `/etc/profile.d/*.sh` and `~/.bashrc`. The package upgrade moved `shopctl` to `/opt/shoptools/bin` and added that directory to PATH in `/etc/profile.d/shoptools.sh`. systemd (and cron) never read those files; their PATH is short and fixed: `/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin`. `sudo` has its own `secure_path`, `sudo -i` starts a login shell - same trap.

**Three valid fixes:**

| Fix | Good because | Watch out |
|---|---|---|
| Full path in the script | explicit, no hidden env | must edit script |
| `Environment=PATH=...` drop-in (`systemctl edit`) | no script change | must list the whole PATH |
| symlink into `/usr/local/bin` | works everywhere | one more thing to keep in sync |

**Method:** "works in my shell" means "my environment differs" - compare user, cwd, env, PATH. Test the job the way it runs: `systemctl start shopapp-report`.
""",
mcq=[
("A systemd service exits with status 127. What does that mean?",
 ["Command not found", "Permission denied on the executable", "Out of memory", "Segmentation fault"],
 "127 = not found; 126 = found but not executable."),
("Why does the script work in the developer's shell but not under systemd?",
 ["systemd does not read /etc/profile.d or ~/.bashrc, so its PATH lacks /opt/shoptools/bin", "systemd runs scripts as a different language", "The timer is disabled", "The script is not executable only for systemd"],
 "Only login shells source /etc/profile.d. Services get a minimal fixed PATH."),
("Which is a valid fix that needs no change to the script file?",
 ["A systemctl edit drop-in with Environment=PATH=/opt/shoptools/bin:...", "chmod 777 /opt/shoptools", "Reboot the host", "Run the job from your own interactive shell every 5 minutes"],
 "Set PATH for the unit; or use full paths, or a symlink."),
],
qa=[
("Compare the three fix options (full path, unit Environment=PATH, symlink). Which would you choose and why?",
 "Full path is the most explicit and robust for machine-run scripts. A drop-in PATH keeps the script untouched but you must repeat the full standard PATH. A symlink makes the tool available to everything but is hidden indirection. Any is acceptable if you can justify it; for scheduled jobs prefer explicit full paths."),
("Why does `sudo /usr/local/bin/shopapp-report` also fail, and why does `sudo -i` succeed?",
 "sudo resets PATH to its `secure_path` (no /opt/shoptools/bin), so the same 127 appears. `sudo -i` starts a login shell that sources /etc/profile.d, so PATH is extended - which hides the bug when you test that way."),
]),

"e09": dict(
explain="""
**Running is not enabled.** `is-active` asks "is it running now?"; `is-enabled` asks "will it start at boot?". Output `static` means the unit has **no `[Install]` section** - systemd has no instruction how to hook it into boot, so it only starts if another unit pulls it in (none does).

**What `enable` does:** reads `[Install] WantedBy=multi-user.target` and creates a symlink `/etc/systemd/system/multi-user.target.wants/shopapp.service -> ...`. At boot `multi-user.target` "wants" the service. No `[Install]` -> nothing to link -> `enable` explains this in its error message.

**Fix:**

```
[Install]
WantedBy=multi-user.target
```

then `systemctl daemon-reload` and `systemctl enable --now shopapp`. Do **not** create the symlink by hand: config management and `systemctl disable` would not know about it.

**Mindset:** after every fix ask "does this survive a reboot?" The 40-minute outage came from patch-reboot + a template rollout that removed `[Install]`. Prevent with `systemd-analyze verify` in CI and reboot tests.
""",
mcq=[
("`systemctl is-enabled shopapp` prints `static`. What does it mean?",
 ["The unit has no [Install] section, so it cannot be enabled for boot", "The unit is enabled and running", "The unit file is read-only", "The unit is masked"],
 "static = no installation config; it can't be enabled/disabled directly."),
("What does `systemctl enable` actually do?",
 ["Creates a symlink in <target>.wants/ based on WantedBy= in [Install]", "Starts the service immediately", "Edits /etc/fstab", "Sets the service's nice value"],
 "Enable = hook into boot via a symlink; start = run now."),
("You edited a unit file. What must you run before enable/start see the change?",
 ["systemctl daemon-reload", "ldconfig", "update-rc.d -f", "sysctl --system"],
 "systemd caches unit files; reload to re-read them."),
],
qa=[
("Explain `start` vs `enable`, and the one-liner that does both.",
 "start runs the unit now; enable makes it start at boot. `systemctl enable --now <unit>` does both."),
("The ticket mentions a 'template cleanup' rolled out to the host. How do you find out whether other services are affected?",
 "List units with no [Install] section: `grep -L '^\\[Install\\]' /etc/systemd/system/*.service`, then check `systemctl is-enabled` for each that should start at boot; run `systemd-analyze verify` on them and tell the template owner."),
]),

"e10": dict(
explain="""
**Chain of events:**

1. Engineer stopped the service and ran `app.py` **as root**
2. They moved the old log away, so root's run **created a new `app.log` owned by root (0644)**
3. They restarted the service, which runs as **`shopapp`**
4. shopapp cannot open the root-owned log -> prints `FATAL: cannot open log file ... Permission denied` -> exits with status 3
5. `Restart=` relaunches it -> crash loop -> nginx has no backend -> **502**

**Reading the symptoms:** `activating (auto-restart)` and a growing restart counter = a crash loop. `status=3` (exit code) plus the FATAL line in `journalctl` give the reason. `ls -l /var/log/shopapp` + `sudo -u shopapp test -w ...` prove it.

**Fix:** `chown shopapp:shopapp app.log`. Not `chmod 666` (anyone could forge log lines) and not `User=root`.

**Debug the right way:** `sudo -u shopapp /usr/bin/python3 /opt/shopapp/app.py` or `systemd-run --pty -p User=shopapp ...`. Better still, let systemd create log files with `LogsDirectory=` or tmpfiles.d so ownership is always right.
""",
mcq=[
("Why did shopapp crash-loop after the engineer's manual debug session?",
 ["Running app.py as root created a root-owned app.log that user shopapp cannot open", "Python was upgraded", "The disk was full", "nginx removed the upstream"],
 "Files created by root stay root-owned; the service user can't write them."),
("What is the correct fix?",
 ["chown shopapp:shopapp /var/log/shopapp/app.log, then restart", "chmod 666 app.log", "Change the unit to User=root", "Delete /var/log/shopapp entirely"],
 "Restore ownership to the service user; 666 and root are workarounds with side effects."),
("`systemctl status` shows `activating (auto-restart)` with a rising restart count. This indicates:",
 ["A crash loop: the process starts, exits, and systemd restarts it", "The service is healthy", "The service is masked", "The service is waiting for a timer"],
 "Read the exit status and journal to find why it exits."),
],
qa=[
("How should the engineer have debugged to avoid causing this?",
 "Run it as the service user: `sudo -u shopapp /usr/bin/python3 /opt/shopapp/app.py`, or reproduce systemd's environment with `systemd-run --pty -p User=shopapp ...`. Never run the service by hand as root in its real directories."),
("Why is `chmod 666 app.log` a bad fix?",
 "Any local user could write or forge log lines (breaking audit trust); it only hides the ownership mistake. The log should be owned by the service user with restrictive mode."),
]),
}
