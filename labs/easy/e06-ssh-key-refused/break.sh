#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

K=$LAB_STATE_DIR/e06
backup_file /etc/ssh/sshd_config
mkdir -p "$K"; chmod 700 "$K"

id deploy >/dev/null 2>&1 || useradd -m -s /bin/bash deploy
[[ -f $K/deploy_key ]] || ssh-keygen -q -t ed25519 -N '' -C ci-pipeline -f "$K/deploy_key"
chmod 600 "$K/deploy_key"

install -d -m 700 -o deploy -g deploy /home/deploy/.ssh
install -m 600 -o deploy -g deploy "$K/deploy_key.pub" /home/deploy/.ssh/authorized_keys

# make sure sshd runs (socket-activated on Ubuntu 24.04)
systemctl start ssh.socket 2>/dev/null || true
systemctl start ssh 2>/dev/null || systemctl start sshd 2>/dev/null || true

# "fix permissions so the shared script works"
chmod 0777 /home/deploy /home/deploy/.ssh
chmod 0666 /home/deploy/.ssh/authorized_keys
