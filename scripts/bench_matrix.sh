#!/usr/bin/env bash
# Ma tran do benchmark: ba thuat toan x ba tang phan hoi x hai che do
# keep-alive, moi o chay N luong doc lap co mot luong lam nong may.
#   bench_matrix.sh [so_luong] [so_request] [so_ket_noi]
set -uo pipefail

export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'
command -v docker >/dev/null ||
    export PATH="$PATH:/c/Program Files/Docker/Docker/resources/bin"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

# Mac dinh 20 luong: bao cao va cac bang doi chieu du dinh so luong nay.
# Chay it hon thi analyze_bench.py in canh bao "CHI CO n/20 LUONG".
REPS="${1:-20}"
N="${2:-5000}"
C="${3:-20}"
LB_IP="192.168.240.10"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="results/bench/matrix-${STAMP}.csv"
mkdir -p results/bench

echo "algorithm,endpoint,keepalive,rep,rps,p50,p95,p99,p100,failed,non2xx" > "$OUT"

run_one() {
    local alg="$1" ep="$2" ka="$3" rep="$4" extra="$5"
    local raw code
    # ab -k co the treo khi ket noi keep-alive khong dong het tren WSL2,
    # nen moi luong phai co han ngat; mot luong treo khong ket dic ma tran.
    raw="$(timeout 240 docker compose exec -T client01 ab $extra -n "$N" -c "$C" -q \
            "https://${LB_IP}/${ep}" 2>&1)"
    code=$?
    local rps p50 p95 p99 p100 failed non2xx
    # "Requests per second:" co BA tu truoc con so nen gia tri nam o $4,
    # khac voi "Complete requests:" va "Failed requests:" chi co hai tu.
    rps="$(printf '%s\n'    "$raw" | awk '/Requests per second:/{print $4}')"
    p50="$(printf '%s\n'    "$raw" | awk '/^  50%/{print $2}')"
    p95="$(printf '%s\n'    "$raw" | awk '/^  95%/{print $2}')"
    p99="$(printf '%s\n'    "$raw" | awk '/^  99%/{print $2}')"
    p100="$(printf '%s\n'   "$raw" | awk '/^ ?100%/{print $2}')"
    failed="$(printf '%s\n' "$raw" | awk '/Failed requests:/{print $3}')"
    non2xx="$(printf '%s\n' "$raw" | awk '/Non-2xx responses:/{print $3}')"
    if [ -z "$rps" ]; then
        echo "  LOI: $alg/$ep/$ka luong $rep (exit $code) khong tra ve so lieu" >&2
        echo "$alg,$ep,$ka,$rep,,,,,,," >> "$OUT"
        # Han ngat chi giết tiến trình docker trên máy chủ; ab trong container
        # van song và tranh CPU voi cac luong tiep theo.
        if [ "$code" = "124" ]; then
            timeout 20 docker compose exec -T client01 pkill ab >/dev/null 2>&1
            sleep 2
        fi
        return 1
    fi
    echo "$alg,$ep,$ka,$rep,$rps,${p50:-},${p95:-},${p99:-},${p100:-},${failed:-0},${non2xx:-0}" >> "$OUT"
    printf '  %-12s %-12s %-10s rep %2d  rps=%8s  P99=%4s  P100=%5s\n' \
        "$alg" "$ep" "$ka" "$rep" "$rps" "${p99:-?}" "${p100:-?}"
}

set_algorithm() {
    local directive="$1"
    LB_ALGO_DIRECTIVE="$directive" docker compose up -d --force-recreate \
        --no-deps lb01 > /dev/null 2>&1
    sleep 5
}

for spec in "round_robin|# round_robin: khong khai bao directive" \
            "least_conn|least_conn;" \
            "ip_hash|ip_hash;"; do
    alg="${spec%%|*}"
    directive="${spec#*|}"
    echo ""
    echo "############## ${alg} ##############"
    set_algorithm "$directive"

    for ep in lb-only healthz dbping.php; do
        for ka in cold keepalive; do
            extra=""; [ "$ka" = "keepalive" ] && extra="-k"
            echo "  nong may: $ep/$ka"
            run_one "$alg" "$ep" "$ka" 0 "$extra" >/dev/null 2>&1
            for ((i = 1; i <= REPS; i++)); do
                run_one "$alg" "$ep" "$ka" "$i" "$extra"
                sleep 1
            done
        done
    done
done

set_algorithm "least_conn;"
echo ""
echo "Da ghi $OUT  ($(( $(wc -l < "$OUT") - 1)) mau)"
