# H02 - Solution

> Long commands below are built up short-first (`# 1.`, `# 2.` ...). Each rung adds one flag;
> the last rung is what the lab uses. The README **Warm-up** explains every flag from scratch.

## 1. Confirm

```bash
curl -s localhost/health                     # ERROR: [Errno 30] Read-only file system
findmnt /srv/shopdata
# TARGET        SOURCE     FSTYPE OPTIONS
# /srv/shopdata /dev/loop1 ext4   ro,relatime,errors=remount-ro
touch /srv/shopdata/x                        # Read-only file system
```

## 2. Why? Ask the kernel

```bash
journalctl -k --since "1 hour ago" | grep -iE 'ext4|remount'
# EXT4-fs error (device loop1): ext4_lookup:1855: inode #13: comm cat: deleted inode referenced: 14
# EXT4-fs (loop1): Remounting filesystem read-only
sudo dumpe2fs -h /dev/loop1                                   # 1. filesystem header
sudo dumpe2fs -h /dev/loop1 2>/dev/null                       # 2. hide the version banner (stderr)
sudo dumpe2fs -h /dev/loop1 2>/dev/null | grep -iE 'state|error'   # 3. only state / error lines
# Filesystem state:         clean with errors
# FS Error count:           1
# Last error function:      ext4_lookup
```

A directory entry (`products.db` in the catalog dir, inode 13) points to inode 14,
which is wiped. That is on-disk corruption.

## 3. Stop writers and unmount

```bash
cd /                                         # don't block the unmount yourself
sudo fuser -vm /srv/shopdata                 # who uses it?
sudo systemctl stop shopapp
sudo umount /srv/shopdata
# if "target is busy": fuser -vm again, stop that process. Avoid `umount -l` here.
```

## 4. Repair

The volume is a loop file; the image path is in `/etc/fstab`:

```bash
grep shopdata /etc/fstab
sudo e2fsck -f /var/lib/tshoot/shopdata.img        # interactive: answer y
#   Entry 'products.db' in /catalog (13) has deleted/unused inode 14.  Clear<y>? yes
#   ***** FILE SYSTEM WAS MODIFIED *****
sudo e2fsck -f /var/lib/tshoot/shopdata.img        # second run must be clean
sudo dumpe2fs -h /var/lib/tshoot/shopdata.img 2>/dev/null | grep state   # clean
```

(On a real disk you run `e2fsck -f /dev/sdb1`. Use `-n` first for a read-only dry run if you are unsure.)

## 5. Mount, check data, restore

```bash
sudo mount /srv/shopdata
findmnt -no OPTIONS /srv/shopdata            # rw,...
ls -l /srv/shopdata/catalog/                 # products.db is gone (fsck removed the broken entry)
ls -l /srv/shopdata/lost+found/
ls -l /srv/backups/catalog/
sudo cp /srv/backups/catalog/products.db.<date> /srv/shopdata/catalog/products.db
sudo chown shopapp:shopapp /srv/shopdata/catalog/products.db
head -3 /srv/shopdata/catalog/products.db
sudo systemctl start shopapp
curl -s localhost/health                     # OK
```

## 6. Wrong fix (and why)

`sudo mount -o remount,rw /srv/shopdata` - works at first, but the filesystem still has
the error flag, the broken entry is still there, and the next access can flip it to ro again
or spread the damage. The checker detects it (`state: clean with errors`).

## Root cause and prevention

| | |
|---|---|
| Root cause | Storage glitch corrupted an inode; ext4 detected it and remounted ro (`errors=remount-ro`) |
| Fix | Stop app -> unmount -> e2fsck -> mount -> restore lost file from backup -> start app |
| Prevent | Alert on `EXT4-fs error` in kernel log and on ro mounts; test restores regularly; investigate storage layer (SMART, hypervisor logs) |
