#!/usr/bin/env bash
# Chay BEN TRONG client01. Ghi lai tung request kem timestamp de do duoc
# thoi gian gian doan khi mot node bi tat.
#   loadloop.sh <giay> <chu_ky_giua_hai_request> <duong_dan_file>
set -uo pipefail

DURATION="${1:-60}"
INTERVAL="${2:-0.2}"
OUT="${3:-/results/failover/load.csv}"
LB_HOST="${LB_HOST:-192.168.240.10}"

mkdir -p "$(dirname "$OUT")"
HDR="$(mktemp)"

echo "unix_ms,http_code,node,time_total" > "$OUT"

END=$(( $(date +%s) + DURATION ))
SEQ=0

while [ "$(date +%s)" -lt "$END" ]; do
    SEQ=$(( SEQ + 1 ))
    RAW_MS="$(date +%s%3N)"
    CODE="$(curl -sk -m 8 -o /dev/null -D "$HDR" -w '%{http_code} %{time_total}' \
            "https://${LB_HOST}/healthz" 2>/dev/null)"
    # curl -w van in ra ma 000 va thoi gian da tiep khi het han, do loi ket
    # noi. Ghi de thanh "000 0" se xoa het thoi gian cham chinh trong luc
    # node chet, khiem khuyet nen bang tong hop khong con tinh trang.
    [ -z "$CODE" ] && CODE="000 0"
    STATUS="${CODE%% *}"
    ELAPSED="${CODE##* }"
    NODE="$(tr -d '\r' < "$HDR" | awk -F': ' 'tolower($1) == "x-node" { print $2 }')"

    echo "${RAW_MS},${STATUS},${NODE:-none},${ELAPSED}" >> "$OUT"
    sleep "$INTERVAL"
done

rm -f "$HDR"
echo "Da ghi ${SEQ} mau vao ${OUT}"
