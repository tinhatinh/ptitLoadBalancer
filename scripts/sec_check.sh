#!/usr/bin/env bash
# Kiem tra an toan cua cum may chu web. In ra bang PASS/FAIL cho muc 3.6.
# Toan bo phep goi dat tu client01 (192.168.240.20) de IP nguon la that.
set -uo pipefail
# Git Bash (MSYS) doi duong dan bat dau bang dau / thanh duong dan Windows,
# lam hong tham so truyen vao docker compose exec.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

LB_IP="192.168.240.10"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="results/security/seccheck-${STAMP}.txt"
TMP="$(mktemp -d)"
mkdir -p results/security

PASS=0; FAIL=0; SKIP=0; WARN=0

cli_sh() { docker compose exec -T client01 sh -c "$1" 2>&1; }
web_sh() { local s="$1"; shift; docker compose exec -T "$s" sh -c "$1" 2>&1; }

check() {
    local name="$1" expect="$2" actual="$3" note="$4"
    if [ "$actual" = "SKIP" ]; then
        printf '  [SKIP] %-46s %s\n' "$name" "$note"; SKIP=$(( SKIP + 1 ))
    elif [ "$actual" = "$expect" ]; then
        printf '  [PASS] %-46s %s\n' "$name" "$note"; PASS=$(( PASS + 1 ))
    else
        printf '  [FAIL] %-46s mong doi [%s] nhan duoc [%s]\n' "$name" "$expect" "$actual"
        FAIL=$(( FAIL + 1 ))
    fi
}

# Lay toan bo response header cua /healthz ve file de parse o may chu,
# tranh long ba tang dau nhay giua bash va sh trong container.
cli_sh "curl -sk -m 10 -D - -o /dev/null https://${LB_IP}/healthz" | tr -d '\r' > "$TMP/h.txt"
cli_sh "curl -sk -m 10 -D - -o /dev/null https://${LB_IP}/login.php" | tr -d '\r' > "$TMP/login.txt"

field() { awk -F': ' -v k="$2" 'tolower($1)==k {sub(/\r$/,""); print $2; exit}' "$1"; }
count_hdr() { grep -ci "$2" "$1" || true; }

run_all() {
echo "=================================================================="
echo " KIEM TRA AN TOAN WEB SERVER CLUSTER    ${STAMP}"
echo " Load balancer ${LB_IP} | may do client01 192.168.240.20"
echo "=================================================================="

check "An phien ban trong header Server" "nginx" \
    "$(field "$TMP/h.txt" server)" \
    "server_tokens off tai load balancer"

check "Khong ro X-Powered-By cua PHP" "0" \
    "$(count_hdr "$TMP/h.txt" 'x-powered-by')" \
    "proxy_hide_header o LB"

check "Co header Strict-Transport-Security" "1" \
    "$(count_hdr "$TMP/h.txt" 'strict-transport-security')" "max-age 31536000"

check "Co header X-Content-Type-Options" "1" \
    "$(count_hdr "$TMP/h.txt" 'x-content-type-options')" "nosniff"

check "Co header Content-Security-Policy" "1" \
    "$(count_hdr "$TMP/h.txt" 'content-security-policy')" "default-src self"

check "Cong 80 chuyen cuong buc sang HTTPS" "301" \
    "$(cli_sh "curl -s -o /dev/null -w '%{http_code}' http://${LB_IP}/index.php")" \
    "HTTP chi dung de redirect"

cli_sh "printf 'Q\n' | openssl s_client -connect ${LB_IP}:443 2>/dev/null" \
    > "$TMP/tls.txt"
PROTO="$(grep -o 'TLSv1[./][0-9]' "$TMP/tls.txt" | tail -1)"
case "$PROTO" in
    TLSv1.2|TLSv1.3) check "Thuong luong duoc TLS 1.2 tro len" "ok" "ok" "ket qua ${PROTO}" ;;
    "")              check "Thuong luong duoc TLS 1.2 tro len" "ok" "SKIP" "khong doc duoc Protocol" ;;
    *)               check "Thuong luong duoc TLS 1.2 tro len" "TLS 1.2+" "FAIL" "ket qua ${PROTO}" ;;
esac

CK="$(field "$TMP/login.txt" set-cookie)"
check "Cookie phien mang co ky HttpOnly" "1" "$(printf '%s' "$CK" | grep -ci httponly)" "cookie_httponly"
check "Cookie phien mang co ky Secure"   "1" "$(printf '%s' "$CK" | grep -ci secure)"  "chi gui di qua HTTPS"
check "Cookie phien mang co SameSite"    "1" "$(printf '%s' "$CK" | grep -ci 'samesite')" "SameSite=Lax"

check "Khong goi truc tiep duoc thu vien rieng" "403" \
    "$(cli_sh "curl -sk -o /dev/null -w '%{http_code}' https://${LB_IP}/lib/bootstrap.php")" \
    "location ^~ /lib/"

BODY="$(cli_sh "curl -sk https://${LB_IP}/healthz")"
if printf '%s' "$BODY" | grep -Eiq 'php|version|/var/|uid=|pwd=|document_root'; then
    check "Healthz khong lo thong tin he thong" "sach" "FAIL" "body: ${BODY}"
else
    check "Healthz khong lo thong tin he thong" "sach" "sach" "body: ${BODY}"
fi

# ab moi giu duoc nhieu ket noi mo dong thoi de vuot qua nguong 5 req/s.
# Goi tuan tu bang curl khong du nhanh vi moi lan khoi dong tien trinh mat
# hon mot chuc mili giay.
#
# Dem 429 trong log cua chinh location tham do, khong dem "Non-2xx" cua ab:
# Goi sang http:// (cang 80) thi moi request nhan 301 chuyen huong, ma 301
# cung la Non-2xx, nen phep do do luon "thanh cong" cho du gioi han tan suat
# co tat hay khong. Day chinh la lloi da lam o luong chay dau.
PROBE_BEFORE="$(docker compose exec -T lb01 sh -c \
    'wc -l < /var/log/nginx/probe.log 2>/dev/null || echo 0')"
PROBE_BEFORE="${PROBE_BEFORE//[!0-9]/}"; PROBE_BEFORE="${PROBE_BEFORE:-0}"
cli_sh "ab -n 200 -c 20 -q https://${LB_IP}/ratelimit-probe > /dev/null 2>&1"
N429="$(docker compose exec -T lb01 sh -c \
    "tail -n +$(( PROBE_BEFORE + 1 )) /var/log/nginx/probe.log" \
    | grep -c 'status=429')"
if [ "${N429:-0}" -gt 100 ]; then
    check "Rate limit chan request gui qua nhanh" "chan" "chan" \
        "${N429}/200 nhan 429 (burst=5)"
else
    check "Rate limit chan request gui qua nhanh" "chan" "khong chan" \
        "chi ${N429:-0}/200 nhan 429"
fi

check "Thu muc config cua ung dung bi node chan" "403" \
    "$(cli_sh "curl -sk -m 4 -o /dev/null -w '%{http_code}' https://${LB_IP}/config.php")" \
    "location = /config.php"

check "Node web khong goi duoc tu mang phia ngoai" "000" \
    "$(cli_sh "curl -s -m 4 -o /dev/null -w '%{http_code}' http://172.20.0.12/healthz")" \
    "mang backend internal"

check "Node tu choi container khong phai load balancer" "403" \
    "$(web_sh web03 "curl -s -m 4 -o /dev/null -w '%{http_code}' http://172.20.0.12/healthz")" \
    "allow 172.20.0.10 o node, truoc day tra 200"

check "Node web khong co duong ra Internet" "000" \
    "$(web_sh web03 "curl -s -m 5 -o /dev/null -w '%{http_code}' http://1.1.1.1/")" \
    "khong tai duoc package"

# Node khong con cho goi thang, nen dieu can kiem tra lai la chieu nguoc
# lai: sau khi chan, node co van ghi dung IP khach hang vao log khong.
# That bai o day khong lam hong dich vu ma lam mat kha nang truy vet, nen
# no la mot hang muc kiem tra dung nghia chu khong phai ghi nhan.
CLI_IP="192.168.240.20"
cli_sh "curl -sk -o /dev/null https://${LB_IP}/index.php" > /dev/null 2>&1
SEEN="khong"
for s in web01 web02 web03; do
    if web_sh "$s" "tail -n 20 /var/log/nginx/access.log" \
        | grep -q "client=\"${CLI_IP}\""; then
        SEEN="co"
    fi
done
check "Node ghi dung dia chi khach hang sau can bang tai" "co" "$SEEN" \
    "client=${CLI_IP} trong node_trace"

# Yeu cau thu tu cua muc 2.1: moi node phai tra ve cung mot noi dung. Trang
# chu co in nhan ten node nen hash khong the giong nhau nguyen van; xoa nhan
# do truoc khi so sanh thi phep do moi noi dung can noi.
HASHES="$(for s in web01 web02 web03; do
              web_sh "$s" "curl -s http://127.0.0.1/index.php | sed 's/web0[1-9]/NODE/g' | sha256sum | cut -c1-12"
          done | tr -d '\r' | sort -u | wc -l)"
check "Moi node tra ve cung mot noi dung" "1" "$HASHES" \
    "ba node chi ra $HASHES hash"

echo "------------------------------------------------------------------"
printf "  TONG KET:  PASS=%d   FAIL=%d   SKIP=%d   GHI_NHAN=%d\n" \
    "$PASS" "$FAIL" "$SKIP" "$WARN"
echo "=================================================================="
}

run_all | tee "$OUT"
rm -rf "$TMP"
echo ""
echo "Da luu vao ${OUT}"
