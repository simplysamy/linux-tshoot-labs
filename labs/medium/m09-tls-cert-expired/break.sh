#!/usr/bin/env bash
set -euo pipefail
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
require_root; require_lab_host

CA=$LAB_STATE_DIR/m09-ca
D=/etc/ssl/shopapp
NAME=shop.lab.internal
rm -rf "$CA"; mkdir -p "$CA/new" "$D"
touch "$CA/index.txt"; echo 1000 > "$CA/serial"

cat > "$CA/ca.cnf" <<EOF
[ ca ]
default_ca = lab
[ lab ]
dir            = $CA
database       = \$dir/index.txt
new_certs_dir  = \$dir/new
serial         = \$dir/serial
default_md     = sha256
policy         = pol
copy_extensions = copy
unique_subject = no
[ pol ]
commonName = supplied
EOF

# lab CA ("public CA")
openssl req -x509 -newkey rsa:2048 -nodes -keyout "$CA/ca.key" -out "$CA/ca.crt" \
    -days 3650 -subj "/CN=Tshoot Lab Root CA" 2>/dev/null

issue() {   # key csr crt startdate enddate
    openssl req -new -key "$1" -subj "/CN=$NAME" -addext "subjectAltName=DNS:$NAME" -out "$2" 2>/dev/null
    openssl ca -batch -config "$CA/ca.cnf" -cert "$CA/ca.crt" -keyfile "$CA/ca.key" -notext \
        -in "$2" -out "$3" -startdate "$4" -enddate "$5" >/dev/null 2>&1
}

# last year's cert - expired 3 days ago
openssl genrsa -out "$D/shop-2025.key" 2048 2>/dev/null
issue "$D/shop-2025.key" "$CA/old.csr" "$D/shop-2025.crt" \
    "$(date -u -d '-368 days' +%Y%m%d%H%M%SZ)" "$(date -u -d '-3 days' +%Y%m%d%H%M%SZ)"

# the renewal: right key under a confusing name, plus a leftover key from a first CSR attempt
openssl genrsa -out "$D/shop-2026-renewal.key" 2048 2>/dev/null
issue "$D/shop-2026-renewal.key" "$CA/new.csr" "$D/shop-2026.crt" \
    "$(date -u -d '-7 days' +%Y%m%d%H%M%SZ)" "$(date -u -d '+358 days' +%Y%m%d%H%M%SZ)"
openssl genrsa -out "$D/shop-2026.key" 2048 2>/dev/null

cp "$CA/ca.crt" "$D/lab-ca.crt"
chown root:root "$D"/*
chmod 0644 "$D"/*.crt
chmod 0600 "$D/shop-2025.key" "$D/shop-2026.key"
chmod 0644 "$D/shop-2026-renewal.key"          # copied with the wrong mode

cat > /etc/nginx/sites-available/shopapp-tls <<EOF
server {
    listen 443 ssl;
    listen [::]:443 ssl;
    server_name $NAME;

    ssl_certificate     $D/shop-2025.crt;
    ssl_certificate_key $D/shop-2025.key;

    access_log /var/log/nginx/shopapp.access.log;
    error_log  /var/log/nginx/shopapp.error.log;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host \$host;
        proxy_read_timeout 10s;
    }
}
EOF
ln -sf /etc/nginx/sites-available/shopapp-tls /etc/nginx/sites-enabled/shopapp-tls
nginx -t >/dev/null 2>&1
systemctl reload nginx
