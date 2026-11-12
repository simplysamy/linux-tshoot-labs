# Per-command explanations for the easy labs' solution walkthroughs.
# One markdown table per lab: Command | What it does | Why we ran it here.
# Pipes (|) are only allowed inside `code` spans (the table parser splits on bare pipes).

CMDS = {
"e01": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `df -h /var/log/shopapp` | Reports used/free space of the **filesystem** that holds that path. `-h` = human units (M, G). | First question is *which volume is full*. Shows `/dev/loop0 100%` on its own mount, while `/` is healthy. |
| `journalctl -u shopapp --since "10 min ago"` | Reads the systemd journal for one unit (`-u`) over a time window. | Proves the symptom from the app's side: `Errno 28 No space left on device` = `ENOSPC`. |
| `... | tail` | Keeps only the last 10 lines. | Journal is long; the newest lines matter. |
| `du -xh --max-depth=1 /var/log/shopapp | sort -h` | `du` adds up file sizes per directory. `-x` = stay on this filesystem, `-h` = human sizes, `--max-depth=1` = one level only. `sort -h` sorts human numbers (10M < 1G). | `df` says *which volume*; `du` says *what is inside*. Biggest entry lands at the bottom. |
| `find /var/log/shopapp -xdev -type f -size +20M -exec ls -lh {} +` | Lists regular files bigger than 20 MB without crossing mount points, then runs `ls -lh` on all hits in one call (`{} +`). | Pinpoints the single culprit (`debug-trace.log`, 200 MB) with owner and size. |
| `tail -n 2 debug-trace.log` | Shows the last 2 lines of the file. | Look at *what* the file is before deleting - confirms it is debug spam, not the protected `app.log` audit log. |
| `lsof /var/log/shopapp/debug-trace.log` | Lists processes that have the file open. | No output = no open fd, so a plain `rm` really frees the blocks. If something held it, `rm` would only remove the name. |
| `rm debug-trace.log` | Unlinks the file; blocks are freed when no fd remains. | The actual fix. |
| `truncate -s 0 FILE` | Sets file size to 0 *in place* (same inode). | The alternative when a process still holds the file: space returns immediately and the writer keeps its fd. |
| `curl -s localhost/ && tail -n1 app.log` | `-s` = silent. Hits the app, then reads its newest log line. | Verify: the app answers **and** logging works again (new line appears). |
| `./labctl.sh check e01` | Lab's own checker script. | Confirms every success criterion (including "app.log untouched"). |
""",

"e02": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `curl -v http://localhost/` | HTTP client; `-v` prints the connect step. | `Connection refused` = kernel answered with RST = **nothing is listening**. Not a slow or broken app. |
| `ss -ltnp 'sport = :80'` | `ss` = socket statistics. `-l` listening, `-t` TCP, `-n` numeric (no DNS), `-p` show owning process. The filter `sport = :80` = source port 80. | Empty output confirms no process owns port 80. |
| `systemctl status nginx` | Shows unit state, last exit code and recent log lines. | `failed (Result: exit-code)` - nginx tried to start and died. |
| `journalctl -u nginx -n 20 --no-pager` | Last 20 journal lines for nginx; `--no-pager` prints straight to the terminal. | Gives the exact error and file:line (`invalid number of arguments ... :15`). |
| `nginx -t` | Parses the config and exits, without touching the running server. | Safe syntax check; use it before **every** reload/restart. |
| `grep -n timeout /etc/nginx/sites-available/shopapp` | Searches the file; `-n` prints line numbers. | The reported line is where the parser gave up - look at the line *before* it. Shows `proxy_read_timeout 30s` with no `;`. |
| `sed -i 's/proxy_read_timeout 30s$/proxy_read_timeout 30s;/' FILE` | In-place (`-i`) substitution. `$` anchors to end of line so only the broken line matches. | Adds the missing `;` and keeps the colleague's valid 30 s change instead of reverting it. |
| `nginx -t && systemctl restart nginx` | `&&` runs the second command only if the first succeeded. | Never restart onto an unchecked config; a bad config would turn a partial outage into a full one. |
| `curl -s -o /dev/null -w '%{http_code}\n' http://localhost/` | `-o /dev/null` discards the body, `-w` prints a format string - here the HTTP status. | One-line pass/fail check: expect `200`. |
""",

"e03": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `curl -s -o /dev/null -w '%{http_code}\n' localhost/` | Prints only the HTTP status code. | `502 Bad Gateway` = nginx (front) is up, the backend behind it is down. Tells you which layer to debug. |
| `systemctl status shopapp` | Unit state and exit info. | `activating (auto-restart)` + `status=2` = crash loop; the app starts and dies. |
| `journalctl -u shopapp -n 5 --no-pager` | Last 5 log lines for the unit. | `[Errno 13] Permission denied` on `config.ini` - the real error. |
| `systemctl show -p User -p Group shopapp` | Prints chosen properties of the unit in `key=value` form. | Learn **which account** the service runs as (`shopapp`) - permissions must be tested as that user, not as you/root. |
| `sudo -u shopapp cat /etc/shopapp/config.ini` | Runs a command as another user. | Reproduces the exact failure as the service user. Reading as root would always work and prove nothing. |
| `namei -l /etc/shopapp/config.ini` | Walks every component of a path and prints owner and mode of each. | Reading a file needs `x` on **every** directory plus `r` on the file. `namei` shows the exact broken link: dir `drwx------` and file `-rw-------`. |
| `chmod 0755 /etc/shopapp` | Sets directory mode (owner rwx, others r-x). | Directory holds no secrets; others need `x` to traverse it. |
| `chown root:shopapp config.ini` | Changes owner and group. | Gives group `shopapp` ownership so the service can read without making it world-readable. |
| `chmod 0640 config.ini` | owner rw, group r, others nothing. | Least privilege: service reads, outsiders cannot. |
| `systemctl restart shopapp` | Stop + start. | Pick up the fix now instead of waiting for the next auto-restart. |
| `curl -s localhost/health` | Calls the health endpoint. | Confirms the app is really serving again. |
""",

"e04": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `ping -c2 8.8.8.8` | Sends 2 ICMP echoes (`-c2`) to a raw IP. | Works = routing and internet are fine. Splits the problem: network vs name resolution. |
| `ping -c2 ubuntu.com` | Same, by name. | `Temporary failure in name resolution` while the IP works = **DNS** problem. |
| `ls -l /etc/resolv.conf` | Long listing incl. symlink target. | On Ubuntu it should be a symlink into `/run/systemd/resolve/`. A plain file means someone overwrote it. |
| `cat /etc/resolv.conf` | Prints the resolver list. | Shows `nameserver 10.255.255.53` - a dead server. |
| `dig ubuntu.com` | DNS query tool; uses the servers in resolv.conf. | `connection timed out; no servers could be reached` confirms that nameserver is dead. |
| `dig @127.0.0.53 ubuntu.com +short` | Queries a **specific** server (`@`); `+short` prints just the answer. | `127.0.0.53` is systemd-resolved's stub. It works, so the resolver service is healthy and only the pointer is wrong. |
| `resolvectl status` | Shows per-link DNS servers known to systemd-resolved. | Verify the real upstream DNS is configured. |
| `ln -sf /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf` | Creates a symlink; `-s` symbolic, `-f` replace existing. | Restores the standard setup: resolv.conf managed by systemd-resolved again. |
| `getent ahosts ubuntu.com` | Resolves via the **system resolver path** (nsswitch), same as apps do. | More realistic than `dig`, which bypasses `/etc/hosts` and nsswitch. |
| `apt update` | Refreshes package lists. | Real-world test that name resolution works for the original complaint. |
| `dig +short example.com` vs `getent hosts example.com` | `dig` asks DNS only; `getent` follows nsswitch order. | Two different answers = something earlier than DNS overrides it. This is how you find fault 2. |
| `grep -n example /etc/hosts` | Finds the line in the hosts file. | Shows the stale `203.0.113.77 example.com` entry. |
| `grep hosts /etc/nsswitch.conf` | Shows lookup order. | `hosts: files dns` - `files` (/etc/hosts) is consulted **before** DNS, so it wins. |
| `sed -i '/203\.0\.113\.77/d' /etc/hosts` | Deletes every line matching the pattern (`\.` = literal dot). | Removes only the stale entry. |
| `curl -sI https://example.com | head -1` | `-I` = HEAD request; `head -1` keeps the status line. | End-to-end proof. |
""",

"e05": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `systemctl status nginx --no-pager` | Unit state without paging. | Failed - need the reason. |
| `journalctl -u nginx -n 10 --no-pager` | Last 10 log lines. | `bind() to 0.0.0.0:80 failed (98: Address already in use)` - config is fine, the port is taken. |
| `ss -ltnp 'sport = :80'` | Listing of listeners on port 80 with process info. | Names the owner: `python3`, pid 2345. Needs `sudo` to show other users' processes. |
| `ps -fp 2345` | Full-format (`-f`) info for one PID (`-p`). | Shows parent, user and full command line - `python3 -m http.server 80` serving a legacy page. |
| `systemctl status 2345` | systemctl can resolve a **PID** to its unit. | Maps the stray process to `legacy-status.service` - the thing to manage, not the PID. |
| `kill 2345` (not used) | Sends SIGTERM to the PID. | Would fail here: `Restart=always` brings it back in 100 ms. Always find the supervisor. |
| `systemctl disable --now legacy-status` | `disable` removes boot-time start, `--now` also stops it immediately. | Frees port 80 and keeps it from returning at reboot. |
| `ss -ltnp 'sport = :80'` (again) | Re-checks the port. | Must be empty before starting nginx. |
| `systemctl start nginx` | Starts the unit. | Now it can bind. |
| `curl -s localhost/` | Fetches the page. | Confirm shopapp (not the legacy page) is answering. |
""",

"e06": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `ssh -i KEY -o StrictHostKeyChecking=no deploy@127.0.0.1 hostname` | SSH using a specific key (`-i`), skipping host-key prompt, runs `hostname` remotely. | Reproduces the failure: `Permission denied (publickey)`. |
| `ssh -v ... 2>&1 | grep -E 'Offering|Authentications'` | `-v` verbose client log; `2>&1` merges stderr into the pipe; `grep -E` filters with a regex (`a|b` = either). | Shows the client **did offer** the key and the server rejected it. The client never learns why - the reason is only in the **server** log. |
| `journalctl -u ssh -n 20 --no-pager` | Server-side log. | `Authentication refused: bad ownership or modes for directory /home/deploy` - the real reason. |
| `namei -l /home/deploy/.ssh/authorized_keys` | Owner and mode of every path component. | Shows home, `.ssh` and the file are all world-writable (`777`/`666`). sshd checks the whole chain (StrictModes). |
| `chmod 755 /home/deploy` | Removes group/other write on home. | Anyone able to write home could replace `.ssh` and add their own key. |
| `chmod 700 /home/deploy/.ssh` | Only owner can enter. | Standard secure mode for the SSH dir. |
| `chmod 600 .../authorized_keys` | Owner read/write only. | Standard secure mode for the key list. |
| `chown -R deploy:deploy /home/deploy/.ssh` | Recursively sets owner/group. | Ensures the user owns the key files (sshd also requires this). |
| `sshd -T | grep -i strictmodes` | `-T` dumps the effective server config. | Verify `strictmodes yes` - we fixed the permissions, we did **not** weaken the security check. |
""",

"e07": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `timedatectl` | Shows local time, UTC, timezone, NTP and sync state. | One command reveals both faults: timezone `America/Los_Angeles` and `NTP service: inactive`, `synchronized: no`. |
| `curl -sI https://www.google.com | grep -i ^date` | `-I` fetches headers only; `grep -i ^date` keeps the Date header. | Independent reference clock to see how far the local clock is off. |
| `timedatectl set-timezone Etc/UTC` | Changes timezone; updates the `/etc/localtime` symlink. | Servers log in UTC so logs from different hosts line up. |
| `ls -l /etc/localtime` | Shows the symlink target. | Verify it points to `/usr/share/zoneinfo/Etc/UTC`. |
| `timedatectl set-ntp true` | Enables network time sync service. | Fixes the clock drift permanently; a one-time manual `date -s` would drift again. |
| `systemctl status systemd-timesyncd` | State of the SNTP client. | Confirms the sync daemon runs (on Ubuntu 25.10+, chrony: `chronyc tracking`). |
| `timedatectl timesync-status` | Server, offset, poll interval. | Verify it actually talks to a time server. |
| `journalctl -u systemd-timesyncd -n 10` | Daemon logs. | See sync events or errors (UDP 123 blocked, etc.). |
| `tail -n1 /var/log/shopapp/app.log` | Newest log line. | Shows the app still logs the **old** timezone. |
| `systemctl restart shopapp` | Restarts the app. | The process read `TZ` once at startup; system changes do not reach running processes. |
""",

"e08": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `systemctl status shopapp-report` | Unit state and exit code. | `status=127` is the shell convention for **command not found**. |
| `journalctl -u shopapp-report -n 5 --no-pager` | Recent unit logs. | Names the missing command: `shopctl: command not found`. |
| `type shopctl` | Shows how the shell resolves a name (alias/builtin/file). | In *your* shell it exists: `/opt/shoptools/bin/shopctl` - so it works for you and fails for systemd. |
| `grep -r shoptools /etc/profile.d/` | Recursive text search. | Finds where PATH was extended: `/etc/profile.d/shoptools.sh`, read only by **login shells**. |
| `systemctl show-environment | grep ^PATH` | Prints the environment systemd gives services. | Shows the PATH without `/opt/shoptools/bin` - the root cause. |
| `sed -i 's#^\( *\)shopctl #\1/opt/shoptools/bin/shopctl #' SCRIPT` | In-place edit; `#` as delimiter so slashes need no escaping; `\1` keeps the indentation. | Fix a: use the absolute path. Explicit and independent of PATH. |
| `systemctl edit shopapp-report` + `Environment=PATH=...` | Opens a drop-in override file. | Fix b: give just this unit the PATH without touching the script. |
| `ln -s /opt/shoptools/bin/shopctl /usr/local/bin/shopctl` | Creates a symlink in a standard PATH directory. | Fix c: make the tool available everywhere. |
| `systemctl start shopapp-report` | Runs the oneshot job now. | Do not wait for the timer to test the fix. |
| `systemctl list-timers shopapp-report.timer` | Shows next/last run. | Confirm the scheduled trigger is intact. |
""",

"e09": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `systemctl is-active shopapp` | Prints whether it is **running now**. | `active` - looks fine, but that is only half the story. |
| `systemctl is-enabled shopapp` | Prints whether it **starts at boot**. | `static` = unit has no `[Install]` section, so it can never be enabled. Nothing pulls it in at boot. |
| `systemctl enable shopapp` | Creates the boot symlink from `[Install]`. | Fails with "no installation config" - confirms the missing section. |
| `systemctl cat shopapp` | Prints the unit file(s) exactly as systemd sees them, including drop-ins. | Shows the file ends after `[Service]`. |
| `sudoedit /etc/systemd/system/shopapp.service` | Edits a file as root, through your own editor, safely. | Add `[Install]` + `WantedBy=multi-user.target` ("start in normal multi-user boot"). |
| `systemctl daemon-reload` | Re-reads all unit files. | Required after any unit file change, otherwise systemd uses the old copy. |
| `systemctl enable shopapp` | Creates `multi-user.target.wants/shopapp.service` symlink. | The proper way - never hand-make the symlink; tooling would not track it. |
| `grep -L '^\[Install\]' /etc/systemd/system/*.service` | `-L` lists files that do **not** match. | Find other units with the same template breakage. |
| `systemctl list-dependencies multi-user.target | grep shopapp` | Shows what the boot target pulls in. | Proof that it now starts at boot. |
""",

"e10": r"""
| Command | What it does | Why we ran it here |
|---|---|---|
| `curl -si localhost/ | head -1` | `-i` includes response headers; `head -1` shows the status line. | `502 Bad Gateway` - proxy up, app down. |
| `systemctl status shopapp` | State and last exit. | Crash loop, `status=3`. |
| `journalctl -u shopapp -n 5 --no-pager` | Recent logs. | `Permission denied: '/var/log/shopapp/app.log'` - names the exact file. |
| `ls -l /var/log/shopapp/` | Owner, group, mode of each file. | `app.log` is `root:root 644`. Someone ran the app as root during testing, so root created the file. |
| `systemctl show -p User shopapp` | Which account the unit runs as. | `shopapp` - not root, so it cannot write a root-owned 644 file. |
| `sudo -u shopapp test -w FILE || echo "shopapp cannot write"` | `test -w` checks write permission as that user; `||` runs echo only if the test fails. | Quick yes/no proof of the permission problem. |
| `chown shopapp:shopapp /var/log/shopapp/app.log` | Gives the file to the service account. | Correct fix. `chmod 666` would let anyone forge log lines. |
| `systemctl restart shopapp` | Restart. | Skip the restart back-off wait. |
| `sudo -u shopapp /usr/bin/python3 /opt/shopapp/app.py` | Runs the app by hand **as the service user**. | Debug habit: never test as root - that is how this bug was created. |
| `systemd-run --pty -p User=shopapp CMD` | Runs a command in a transient unit with the same properties systemd would give it. | Reproduces the service environment (user, cgroup, limits) as closely as possible. |
""",
}
