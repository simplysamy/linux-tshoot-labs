# E06 - Solution

## 1. Reproduce

```bash
sudo ssh -i /var/lib/tshoot/e06/deploy_key -o StrictHostKeyChecking=no deploy@127.0.0.1 hostname
# deploy@127.0.0.1: Permission denied (publickey).
sudo ssh -v -i /var/lib/tshoot/e06/deploy_key deploy@127.0.0.1 2>&1 | grep -E 'Offering|Authentications'
# debug1: Offering public key: /var/lib/tshoot/e06/deploy_key ED25519 ...
# debug1: Authentications that can continue: publickey
```

The client offered the key; the server said no. The client does not know why.

## 2. Read the server log

```bash
journalctl -u ssh -n 20 --no-pager
# sshd[2211]: Authentication refused: bad ownership or modes for directory /home/deploy
```

## 3. Check every level of the path

```bash
namei -l /home/deploy/.ssh/authorized_keys
# drwxr-xr-x root   root   /
# drwxr-xr-x root   root   home
# drwxrwxrwx deploy deploy deploy          <- world-writable home
# drwxrwxrwx deploy deploy .ssh            <- world-writable .ssh
# -rw-rw-rw- deploy deploy authorized_keys <- anyone can add a key!
```

Why sshd cares: if anyone can write to your home or `.ssh`, anyone can add their own key
and log in as you. sshd refuses rather than trust that file.

## 4. Fix

```bash
sudo chmod 755 /home/deploy          # or 750
sudo chmod 700 /home/deploy/.ssh
sudo chmod 600 /home/deploy/.ssh/authorized_keys
sudo chown -R deploy:deploy /home/deploy/.ssh
```

The shared script that needed access should get a group or a shared directory, not a 777 home.

## 5. Verify

```bash
sudo ssh -i /var/lib/tshoot/e06/deploy_key -o StrictHostKeyChecking=no deploy@127.0.0.1 hostname
sudo sshd -T | grep -i strictmodes      # strictmodes yes
sudo ./labctl.sh check e06
```

## Root cause and prevention

| | |
|---|---|
| Root cause | `chmod -R 777` on `/home/deploy`; sshd `StrictModes` rejected the key |
| Fix | Home 755, `.ssh` 700, `authorized_keys` 600 |
| Prevent | Manage users/keys with config management; shared files go in a group-owned dir; monitor "Authentication refused" in auth logs |
