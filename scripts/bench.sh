#!/usr/bin/env bash
# Do thong qua va p95 bang ab, so sanh luc 3 node con song voi luc mat 1 node.
#   bench.sh <ten_file_ket_qua> <so_request> <so_ket_noi_dong_thoi>
set -uo pipefail
# Git Bash (MSYS) doi duong dan bat dau bang dau / thanh duong dan Windows,
# lam hong tham so truyen vao docker compose exec.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

LABEL="${1:-baseline}"
N="${2:-1500}"
C="${3:-30}"
LB="${LB_IP:-192.168.240.10}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="results/bench/${LABEL}-${STAMP}.txt"
mkdir -p results/bench

# Khong dung -k: ab 2.3 dung keepalive voi nginx 1.27 qua WSL2 bi nghet
# socket (apr_pollset_poll 70007) o do dong 50 ket noi.
echo "ab -n ${N} -c ${C} https://${LB}/healthz   (nhan: ${LABEL})"

docker compose exec -T client01 ab -n "$N" -c "$C" "https://${LB}/healthz" > "$OUT" 2>&1

{
    echo ""
    echo "===== TOM TAT ${LABEL} ====="
    if ! grep -q 'Complete requests:' "$OUT"; then
        # ab fail voi tham so sai (vi du -c lon hon -n) thi van de lai mot
        # tep chay duoc, khong co dong nao khop. In canh bao thay vi im lang.
        echo "  LOI: khong doc duoc ket qua ab, xem $OUT"
        head -3 "$OUT" | sed 's/^/  /'
    else
        awk '
            /Complete requests:/      { printf "  So request hoan thanh      : %s\n", $3 }
            /Failed requests:/        { printf "  Request that bai           : %s\n", $3 }
            /Requests per second:/    { printf "  Thong qua (req/s)          : %s\n", $4 }
            # ab in hai dong "Time per request": mot dong (mean) va mot dong
            # (mean, across all concurrent requests). Bo qua dau cau cuoi thi
            # in ra ca hai, ma dong thu hai nho hon bang so ket noi song.
            /Time per request:.*\(mean\)$/ { printf "  Thoi gian moi request      : %s ms\n", $4 }
            /served within a certain time/ { pct = 1; next }
            pct && /^ +50%/           { printf "  P50                        : %s ms\n", $2 }
            pct && /^ +95%/           { printf "  P95                        : %s ms\n", $2 }
            pct && /^ +99%/           { printf "  P99                        : %s ms\n", $2 }
            pct && /^ *100%/          { printf "  P100                       : %s ms\n", $2 }
        ' "$OUT"
    fi
} | tee -a "$OUT"
