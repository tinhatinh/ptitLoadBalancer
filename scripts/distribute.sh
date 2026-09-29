#!/usr/bin/env bash
# Chay BEN TRONG container client01 de IP nguon la that.
#   distribute.sh <so_request> <ten_thuat_toan>
set -uo pipefail

N="${1:-300}"
ALG="${2:-default}"
LB_HOST="${LB_HOST:-192.168.240.10}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="/results/distribute"
mkdir -p "$OUT_DIR"

RAW="$OUT_DIR/raw-${ALG}-${STAMP}.txt"
SUM="$OUT_DIR/summary-${ALG}-${STAMP}.txt"
: > "$RAW"

echo "Gui $N request toi https://${LB_HOST}/healthz (thuat toan: ${ALG})"

for ((i = 1; i <= N; i++)); do
    curl -sk -m 10 -o /dev/null -D - "https://${LB_HOST}/healthz" \
        | tr -d '\r' \
        | awk -F': ' 'tolower($1) == "x-node" { print $2 }' >> "$RAW"
done

MISSING=$(( N - $(wc -l < "$RAW") ))

{
    echo "algorithm=${ALG}"
    echo "requests=${N}"
    echo "missing_node_header=${MISSING}"
    echo "distribution:"
    sort "$RAW" | uniq -c | sed 's/^ *//' | sort -t' ' -k2
} | tee "$SUM"
