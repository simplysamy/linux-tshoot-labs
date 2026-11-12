# E07 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. Look at the clock

```bash
timedatectl
#                Local time: Tue 2026-11-10 02:51:10 PST
#            Universal time: Tue 2026-11-10 10:51:10 UTC
#                 Time zone: America/Los_Angeles (PST, -0800)
# System clock synchronized: no
#               NTP service: inactive
```

Two problems:

1. **Timezone** is `America/Los_Angeles`, not UTC. The logs show local time, 8 hours off.
2. **NTP is inactive**, and the clock is wrong by several minutes (compare with another
   host or `curl -sI https://www.google.com | grep -i ^date` if you have internet).

## 2. Fix the timezone

```bash
sudo timedatectl set-timezone Etc/UTC
ls -l /etc/localtime      # -> /usr/share/zoneinfo/Etc/UTC
```

## 3. Turn time sync back on

```bash
sudo timedatectl set-ntp true
systemctl status systemd-timesyncd     # (Ubuntu 25.10+: chrony -> `chronyc tracking`)
timedatectl timesync-status            # server, offset, poll interval
journalctl -u systemd-timesyncd -n 10
```

`System clock synchronized: yes` appears once a server answers (needs network to NTP, UDP 123).

## 4. The app still logs the old timezone

```bash
curl -s localhost/ >/dev/null; tail -n1 /var/log/shopapp/app.log
# still 02:5x - the process read TZ at startup
sudo systemctl restart shopapp
curl -s localhost/ >/dev/null; tail -n1 /var/log/shopapp/app.log
# now 10:5x = UTC
```

## 5. Verify

```bash
sudo ./labctl.sh check e07
```

## Root cause and prevention

| | |
|---|---|
| Root cause | Image customisation set a local timezone and disabled NTP; clock drifted |
| Fix | Timezone UTC, NTP enabled, app restarted |
| Prevent | Set timezone + NTP in the base image / config management; alert on `timedatectl show -p NTPSynchronized` = no |
