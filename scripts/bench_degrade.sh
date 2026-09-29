#!/usr/bin/env bash
# Do muc suy giam hieu nang khi mat mot node, voi cung tham so va cung cach
# tong hop nhu ma tran: mot kich thuoc 3 node va mot kich thuoc 2 node, moi
# che do keep-alive chay 20 luong doc lap sau mot luong lam nong may.
#
# Kich thuoc 2 node phai CHUNG MINH duoc node bi tat thuc su khong phuc vu
# request nao: dem theo IP trong access log cua chinh load balancer, ghi ra
# file degrade-nodes song song. Khong co dem nay thi "hai node" chi la mot
# cai nhan.
#   bench_degrade.sh [so_luong] [so_request] [so_ket_noi]
set -uo pipefail

export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'
command -v docker >/dev/null ||
    export PATH="$PATH:/c/Program Files/Docker/Docker/resources/bin"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REPS="${1:-20}"
N="${2:-3000}"
C="${3:-20}"
LB_IP="192.168.240.10"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="results/bench/degrade-${STAMP}.csv"
NODES="results/bench/degrade-nodes-${STAMP}.csv"
mkdir -p results/bench

echo "state,keepalive,rep,rps,p50,p95,p99,p100,failed,non2xx" > "$OUT"
echo "state,web01,web02,web03,retries,lines" > "$NODES"

log_lines() {
    docker compose exec -T lb01 sh -c \
        'wc -l < /var/log/nginx/healthz.log 2>/dev/null || echo 0' \
        | tr -dc '0-9'
}

count_nodes() {  # $1 = state, $2 = so dong bat dau
    local state="$1" before="$2"
    docker compose exec -T lb01 sh -c \
        "tail -n +$(( before + 1 )) /var/log/nginx/healthz.log" \
    | awk -v state="$state" '
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
            tot++
        }
        END { printf "%s,%d,%d,%d,%d,%d\n", state, w1 + 0, w2 + 0, w3 + 0, retry + 0, tot }
    ' >> "$NODES"
}

restore() { docker compose start web03 >/dev/null 2>&1; }
trap restore EXIT

set_algorithm() {
    LB_ALGO_DIRECTIVE="$1" docker compose up -d --force-recreate \
        --no-deps lb01 > /dev/null 2>&1
    sleep 5
}

# Thuat toan phai duoc dat trong chinh lenh nay, khong thua ke trang thai cua
# lan chay truoc. Mot luong chay nam lai sau session_test.sh (de ip_hash) da
# keo toan bo 126000 request ve dung mot node ma khong bao loi nao.
set_algorithm "least_conn;"
docker compose cp lb01:/etc/nginx/conf.d/default.conf \
    "results/bench/rendered-degrade-${STAMP}.conf" 2>/dev/null
grep -A5 'upstream web_cluster' "results/bench/rendered-degrade-${STAMP}.conf" \
    | sed 's/^/  upstream: /'

run_one() {
    local state="$1" ka="$2" rep="$3" extra="$4" raw code
    raw="$(timeout 240 docker compose exec -T client01 ab $extra -n "$N" -c "$C" -q \
            "https://${LB_IP}/healthz" 2>&1)"
    code=$?
    local rps p50 p95 p99 p100 failed non2xx
    rps="$(printf '%s\n'    "$raw" | awk '/Requests per second:/{print $4}')"
    p50="$(printf '%s\n'    "$raw" | awk '/^  50%/{print $2}')"
    p95="$(printf '%s\n'    "$raw" | awk '/^  95%/{print $2}')"
    p99="$(printf '%s\n'    "$raw" | awk '/^  99%/{print $2}')"
    p100="$(printf '%s\n'   "$raw" | awk '/^ ?100%/{print $2}')"
    failed="$(printf '%s\n' "$raw" | awk '/Failed requests:/{print $3}')"
    non2xx="$(printf '%s\n' "$raw" | awk '/Non-2xx responses:/{print $3}')"
    if [ -z "$rps" ]; then
        echo "  LOI: $state/$ka luong $rep (exit $code)" >&2
        echo "$state,$ka,$rep,,,,,,," >> "$OUT"
        [ "$code" = "124" ] && timeout 20 docker compose exec -T client01 pkill ab >/dev/null 2>&1
        return 1
    fi
    echo "$state,$ka,$rep,$rps,${p50:-},${p95:-},${p99:-},${p100:-},${failed:-0},${non2xx:-0}" >> "$OUT"
    printf '  %-8s %-10s rep %2d  rps=%8s  P99=%4s  P100=%5s\n' \
        "$state" "$ka" "$rep" "$rps" "${p99:-?}" "${p100:-?}"
}

for spec in "3-node|" "2-node|web03"; do
    state="${spec%%|*}"
    victim="${spec#*|}"
    echo ""
    echo "############## ${state} ##############"
    if [ -n "$victim" ]; then
        docker compose stop "$victim" >/dev/null 2>&1
        echo "  da tat $victim; cho het chu ky fail_timeout de node bi loai khoi danh sach"
        sleep 15
    fi
    BEFORE="$(log_lines)"; BEFORE="${BEFORE:-0}"
    for ka in cold keepalive; do
        extra=""; [ "$ka" = "keepalive" ] && extra="-k"
        echo "  lam nong may: $state/$ka"
        run_one "$state" "$ka" 0 "$extra" >/dev/null 2>&1
        for ((i = 1; i <= REPS; i++)); do
            run_one "$state" "$ka" "$i" "$extra"
            sleep 1
        done
    done
    count_nodes "$state" "$BEFORE"
    echo "  node phuc vu trong kich thuoc $state: $(tail -1 "$NODES")"
done

restore
trap - EXIT
sleep 5
echo ""
echo "Da ghi $OUT ($(( $(wc -l < "$OUT") - 1)) luong) va $NODES"
