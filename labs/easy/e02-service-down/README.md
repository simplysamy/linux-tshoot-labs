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

## Warm-up: build the commands up from simple

The solution uses long command lines. They are just short commands with one flag added at a time.
Practise each ladder on any Linux box first (all read-only). Every rung adds **one** thing to the
rung above - stop at the rung you understand, and read the next one only when you are ready.
The lab itself uses the last rung of each ladder.

### curl - talk to a web service

```bash
curl http://localhost/                                   # 1. fetch a page, print the body
curl -s http://localhost/                                # 2. -s = silent (no progress bar)
curl -s -o /dev/null http://localhost/                   # 3. -o /dev/null = throw the body away
curl -s -o /dev/null -w '%{http_code}\n' http://localhost/   # 4. -w = print only the HTTP status code
curl -v http://localhost/                                # 5. -v = verbose: shows connect, headers (debug)
curl -s -o /dev/null -w '%{http_code} %{time_total}s\n' --max-time 5 http://localhost/   # 6. + timing, + give up after 5 s
```

### ss - who is listening / connected?

```bash
ss                              # 1. all sockets (long)
ss -l                           # 2. -l = only listening sockets
ss -lt                          # 3. -t = TCP only
ss -ltn                         # 4. -n = numbers, no name lookup
ss -ltnp                        # 5. -p = which process owns each socket (needs sudo)
ss -ltnp 'sport = :80'          # 6. filter: only source (local) port 80
```

### systemctl + journalctl - service state and logs

```bash
systemctl status nginx                          # 1. state, last exit code, last log lines
systemctl is-active nginx                       # 2. one word: active / failed / inactive
journalctl -u nginx                             # 3. the whole log of one unit (-u = unit)
journalctl -u nginx -n 20                       # 4. only the last 20 lines
journalctl -u nginx -n 20 --no-pager            # 5. print straight to the terminal (no less)
journalctl -u nginx --since "10 min ago"        # 6. time window instead of line count
```

### nginx - test before you restart

```bash
nginx -t                                  # 1. check the config syntax, change nothing
sudo nginx -t                             # 2. needs root to read all files
sudo nginx -T                             # 3. -T = test AND print the full effective config
sudo nginx -T | grep -n listen            # 4. find one directive in it
sudo nginx -t && sudo systemctl reload nginx   # 5. && = reload only if the test passed
```

### grep - find text

```bash
grep error file                 # 1. lines containing 'error'
grep -i error file              # 2. -i = ignore case
grep -n error file              # 3. -n = show line numbers
grep -v debug file              # 4. -v = invert: lines WITHOUT 'debug'
grep -r error /etc/             # 5. -r = search all files below a directory
grep -E 'oom|killed' file       # 6. -E = extended regex: 'oom' OR 'killed'
dmesg | grep -i oom             # 7. most used form: filter another command's output
```

### sed - edit text from the command line

```bash
sed 's/old/new/' file           # 1. print file with the first 'old' on each line replaced (file unchanged)
sed 's/old/new/g' file          # 2. g = every match on the line
sed -n '3p' file                # 3. -n + p = print only line 3
sed '/old/d' file               # 4. d = delete lines that match (still only printed)
sed -i 's/old/new/' file        # 5. -i = edit the file IN PLACE (make a copy first: cp file file.bak)
sed -i 's#/a/b#/c/d#' file      # 6. any delimiter works: # avoids escaping / in paths
```

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
