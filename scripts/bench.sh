#!/usr/bin/env bash
# Do thong qua va p95 bang ab, so sanh luc 3 node con song voi luc mat 1 node.
#   bench.sh <ten_file_ket_qua> <so_request> <so_ket_noi_dong_thoi>
set -uo pipefail
# Git Bash (MSYS) doi duong dan bat dau bang dau / thanh duong dan Windows,
# lam hong tham so truyen vao docker compose exec.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

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
    awk '
        /Complete requests:/      { printf "  So request hoan thanh      : %s\n", $3 }
        /Failed requests:/        { printf "  Request that bai           : %s\n", $3 }
        /Requests per second:/    { printf "  Thong qua (req/s)          : %s\n", $4 }
        /Time per request.*mean/  { printf "  Thoi gian moi request      : %s ms\n", $4 }
        /50%/                     { printf "  P50                        : %s ms\n", $2 }
        /95%/                     { printf "  P95                        : %s ms\n", $2 }
        /99%/                     { printf "  P99                        : %s ms\n", $2 }
        /Maximum length of keepalive/ { next }
    ' "$OUT"
} | tee -a "$OUT"
