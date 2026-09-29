#!/usr/bin/env bash
# Do do lech phan phối voi NHIEU luong, khong phai mot luong.
# Moi luong dem node tu access log cua chinh load balancer, ghi mot dong CSV
# de tong hop duoc mean, do lech chuan va khoang tin cay.
#   dist_matrix.sh [so_luong] [so_request] [so_ket_noi]
set -uo pipefail

export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'
command -v docker >/dev/null ||
    export PATH="$PATH:/c/Program Files/Docker/Docker/resources/bin"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

REPS="${1:-20}"
N="${2:-600}"
C="${3:-20}"
LB_IP="192.168.240.10"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="results/distribute/skew-${STAMP}.csv"
LOG="$(mktemp)"
RAW="$(mktemp)"
mkdir -p results/distribute

echo "algorithm,rep,w1,w2,w3,unaccounted,retries,failed,rps" > "$OUT"

set_algorithm() {
    LB_ALGO_DIRECTIVE="$1" docker compose up -d --force-recreate \
        --no-deps lb01 > /dev/null 2>&1
    sleep 5
}

count_run() {  # $1 = algorithm, $2 = rep (0 la luong lam nong may)
    local alg="$1" rep="$2" before rps failed counts
    before="$(docker compose exec -T lb01 sh -c \
        'wc -l < /var/log/nginx/healthz.log 2>/dev/null || echo 0')"
    before="${before//[!0-9]/}"
    [ -z "$before" ] && before=0

    timeout 240 docker compose exec -T client01 ab -n "$N" -c "$C" -q \
        "https://${LB_IP}/healthz" > "$RAW" 2>&1
    code=$?
    # Han ngat chi giết tien trình docker tren may chu; ab trong container van
    # song va tiep tuc gui request vao luong ke tiep, lam hoai hai cot w1..w3.
    if [ "$code" = "124" ]; then
        timeout 20 docker compose exec -T client01 pkill ab >/dev/null 2>&1
        sleep 2
    fi

    docker compose exec -T lb01 sh -c \
        "tail -n +$(( before + 1 )) /var/log/nginx/healthz.log" > "$LOG"

    rps="$(awk '/Requests per second:/{print $4}' "$RAW")"
    failed="$(awk '/Failed requests:/{print $3}' "$RAW")"
    counts="$(awk '
        match($0, /upstream=[0-9.:, ]+/) {
            spec = substr($0, RSTART + 9, RLENGTH - 9)
            gsub(/[ ]/, "", spec)
            k = split(spec, parts, ",")
            if (k > 1) retry++
            last = parts[k]
            sub(/:80$/, "", last)
            if      (last == "172.20.0.11") w1++
            else if (last == "172.20.0.12") w2++
            else if (last == "172.20.0.13") w3++
            else other++
        }
        END { printf "%d,%d,%d,%d,%d", w1 + 0, w2 + 0, w3 + 0, other + 0, retry + 0 }
    ' "$LOG")"

    if [ -z "$rps" ] || [ -z "$counts" ] || [ "$counts" = "0,0,0,0,0" ]; then
        # awk END luon in ra nam so, ke ca khi log trong (do moc duoi lon hon
        # so dong hien tai sau khi log bi xoa). Mot dong toan 0 se bi tinh
        # vao trung binh nhu that nen phai bao loi, khong ghi.
        echo "  LOI: $alg luong $rep khong do duoc (rps='${rps}' counts='${counts}')" >&2
        echo "$alg,$rep,,,,,,," >> "$OUT"
        return 1
    fi
    echo "$alg,$rep,$counts,${failed:-0},$rps" >> "$OUT"
    printf '  %-12s rep %2d  %s\n' "$alg" "$rep" "${counts//,/\ }"
}

for spec in "round_robin|# round_robin: khong khai bao directive" \
            "least_conn|least_conn;" \
            "ip_hash|ip_hash;"; do
    alg="${spec%%|*}"
    directive="${spec#*|}"
    echo ""
    echo "############## ${alg} ##############"
    set_algorithm "$directive"
    echo "  lam nong may"
    count_run "$alg" 0 > /dev/null 2>&1
    for ((i = 1; i <= REPS; i++)); do
        count_run "$alg" "$i"
        sleep 1
    done
done

set_algorithm "least_conn;"
rm -f "$LOG" "$RAW"
echo ""
echo "Da ghi $OUT  ($(( $(wc -l < "$OUT") - 1)) luong)"
