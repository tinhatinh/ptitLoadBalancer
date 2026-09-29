#!/usr/bin/env bash
# Phan phoi tai DONG THOI va dem node tu access log cua chinh load balancer.
# Phep do tuan tu bang curl khong phan biet duoc round robin voi least_conn,
# vi tai mot thoi diem khong co node nao giu qua mot ket noi.
#   dist_concurrent.sh <nhan> <so_request> <so_ket_noi>
set -uo pipefail

export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

LABEL="${1:-run}"
N="${2:-600}"
C="${3:-20}"
LB_IP="192.168.240.10"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="results/distribute/concurrent-${LABEL}-${STAMP}.txt"
mkdir -p results/distribute

lines_before="$(docker compose exec -T lb01 sh -c \
    'wc -l < /var/log/nginx/healthz.log 2>/dev/null || echo 0')"
# Lam sach nhu dist_matrix.sh: neu lenh exec loi thi bien nay khong ra so,
# va $(( "" + 1 )) = 1 nghia la tail ca file log, tinh luon moi luong truoc.
lines_before="${lines_before//[!0-9]/}"
[ -z "$lines_before" ] && lines_before=0

echo "ab -n ${N} -c ${C} https://${LB_IP}/healthz   (nhan: ${LABEL})"
docker compose exec -T client01 ab -n "$N" -c "$C" "https://${LB_IP}/healthz" \
    > "$OUT.raw" 2>&1

docker compose exec -T lb01 sh -c \
    "tail -n +$(( lines_before + 1 )) /var/log/nginx/healthz.log" > "$OUT.log"

{
    echo "nhan=${LABEL}  n=${N}  concurrency=${C}  stamp=${STAMP}"
    grep -E 'Complete requests|Failed requests|Requests per second|Non-2xx|Time per request|  50%|  95%|  99%' "$OUT.raw" \
        | sed 's/^ *//'
    echo ""
    echo "Phan phoi node theo access log cua load balancer:"
    awk '
        match($0, /upstream=[0-9.:, ]+/) {
            spec = substr($0, RSTART + 9, RLENGTH - 9)
            gsub(/[ ]/, "", spec)
            n = split(spec, parts, ",")
            last = parts[n]
            sub(/:80$/, "", last)
            hits[last]++
        }
        END {
            ip["172.20.0.11"] = "web01"; ip["172.20.0.12"] = "web02"; ip["172.20.0.13"] = "web03"
            for (k in hits) printf "  %-8s %d\n", (k in ip ? ip[k] : k), hits[k]
        }
    ' "$OUT.log" | sort
    echo ""
    echo "So request phai thu lai o node khac (upstream co hai dia chi):"
    grep -c 'upstream=[0-9.]*:80, ' "$OUT.log" || true
} | tee "$OUT"
