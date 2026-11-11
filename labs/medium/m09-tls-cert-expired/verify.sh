#!/usr/bin/env bash
source "$(dirname "${BASH_SOURCE[0]}")/../../../lib/common.sh"
NAME=shop.lab.internal
CACRT=$LAB_STATE_DIR/m09-ca/ca.crt     # the original CA (students can't swap it)

check "nginx -t passes" nginx -t

body=$(curl -s --max-time 5 --resolve "$NAME:443:127.0.0.1" --cacert "$CACRT" "https://$NAME/" 2>/dev/null)
[[ $body == *"shopapp is running"* ]] && pass "https://$NAME/ verifies and answers" \
    || fail "https://$NAME/ fails TLS verification (curl -v ... to see why)"

served=$(echo | openssl s_client -connect 127.0.0.1:443 -servername "$NAME" 2>/dev/null | openssl x509 2>/dev/null)
if [[ -n $served ]] && openssl x509 -noout -checkend 2592000 <<<"$served" >/dev/null; then
    pass "served certificate valid for > 30 days ($(openssl x509 -noout -enddate <<<"$served"))"
else
    fail "served certificate expires within 30 days or could not be read"
fi

keys=$(nginx -T 2>/dev/null | awk '$1=="ssl_certificate_key"{gsub(/;/,"",$2); print $2}' | sort -u)
[[ -n $keys ]] || fail "no ssl_certificate_key in nginx config"
for k in $keys; do
    m=$(stat -c %a "$k" 2>/dev/null); o=$(stat -c %U "$k" 2>/dev/null)
    if [[ $o == root ]] && (( (8#${m:-777} & 8#007) == 0 )); then
        pass "key $k is $m $o"
    else
        fail "key $k is $m $o - private keys must not be readable by others"
    fi
done

[[ $(http_code http://127.0.0.1/) == 200 ]] && pass "http://localhost/ still 200" || fail "plain HTTP on :80 broken"
finish_verify
