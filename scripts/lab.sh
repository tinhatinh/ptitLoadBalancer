#!/usr/bin/env bash
# Dieu dong toan bo lab de 07. Chay tu Git Bash tren may chu.
#   ./scripts/lab.sh up | ps | down | logs [dich_vu]
#   ./scripts/lab.sh dist [so_request]        phan phoi tuan tu
#   ./scripts/lab.sh dist-all
#   ./scripts/lab.sh dist-c | dist-all-c      phan phoi dong thoi mot luong
#   ./scripts/lab.sh dist-skew [luong] [req] [cong]   do lech 20 luong (muc 3.2.2)
#   ./scripts/lab.sh failover [ten_node]
#   ./scripts/lab.sh session [redis|file]
#   ./scripts/lab.sh sec                      bang kiem 19 hang muc
#   ./scripts/lab.sh bench-matrix [luong] [req] [cong]   18 o thong qua (muc 3.5.1)
#   ./scripts/lab.sh bench-degrade [luong] [req] [cong]  3 node vs 2 node (muc 3.5.4)
#   ./scripts/lab.sh report [matrix|skew|degrade|all]    in lai so trong bang
#   ./scripts/lab.sh all
set -uo pipefail
# Git Bash khong luon tim thay docker.exe trong PATH.
command -v docker >/dev/null ||
    export PATH="$PATH:/c/Program Files/Docker/Docker/resources/bin"
# Git Bash (MSYS) doi duong dan bat dau bang dau / thanh duong dan Windows,
# lam hong tham so truyen vao docker compose exec.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

LB_IP="${LB_IP:-192.168.240.10}"
export LB_IP

wait_ready() {
    echo -n "Cho load balancer san sang "
    for _ in $(seq 1 40); do
        code="$(docker compose exec -T client01 curl -sk -m 3 -o /dev/null -w '%{http_code}' \
                 "https://${LB_IP}/healthz" 2>/dev/null || true)"
        if [ "$code" = "200" ]; then echo " -> OK"; return 0; fi
        echo -n "."
        sleep 2
    done
    echo " -> KHONG DAT"
    return 1
}

# /healthz chi xac nhan nginx va php-fpm song, khong cham den MariaDB. Lenh
# nay cho den khi duoc noi "co" lenh that, de mot lan khoi dong lanh khong
# bi do nham nhanh cua nhanh phuc hoi khi DB chua kip.
wait_db() {
    echo -n "Cho ung dung noi duoc MariaDB "
    for _ in $(seq 1 40); do
        body="$(docker compose exec -T client01 curl -sk -m 3 \
                "https://${LB_IP}/dbping.php" 2>/dev/null || true)"
        if printf '%s' "$body" | grep -q '"ok":1'; then echo " -> OK"; return 0; fi
        echo -n "."
        sleep 2
    done
    echo " -> KHONG DAT"
    return 1
}

cmd="${1:-help}"
shift || true

case "$cmd" in
up)
    bash scripts/gen_certs.sh
    docker compose --profile tools build
    docker compose --profile tools up -d
    sleep 6
    docker compose --profile tools up -d --no-deps client01
    wait_ready
    wait_db
    docker compose ps
    ;;

down)
    docker compose --profile tools down -v
    ;;

ps)
    docker compose ps --format '{{.Name}}\t{{.Status}}\t{{.Ports}}'
    ;;

logs)
    docker compose logs --tail 60 "${1:-lb01}"
    ;;

shell)
    docker compose exec "${1:-client01}" sh
    ;;

dist)
    N="${1:-300}"
    ALG="${LB_ALGO_DIRECTIVE:-least_conn;}"
    docker compose exec -T client01 bash /scripts/distribute.sh "$N" "${ALG%%;*}"
    ;;

dist-all)
    # Round robin khong co directive trong nginx. Thay de gia tri rong (de
    # compose coi la khong dat va dung gia tri mac dinh), dung mot dong comment
    # de file nginx sinh ra tu doc duoc thuat toan dang chay.
    RR_DIRECTIVE="# round_robin: khong khai bao directive thuat toan"
    for spec in "round_robin|${RR_DIRECTIVE}" "least_conn|least_conn;" "ip_hash|ip_hash;"; do
        name="${spec%%|*}"
        directive="${spec#*|}"
        echo ""
        echo "############## THUAT TOAN: ${name} ##############"
        LB_ALGO_DIRECTIVE="$directive" docker compose up -d --force-recreate --no-deps lb01 >/dev/null
        wait_ready || exit 1
        # Luu lai khoi upstream thuc te ma nginx dang dung, de bang so lieu
        # kiem chung duoc la thuat toan da doi qua that.
        docker compose cp lb01:/etc/nginx/conf.d/default.conf \
            "results/distribute/rendered-${name}.conf" 2>/dev/null
        docker compose exec -T client01 bash /scripts/distribute.sh 300 "$name"
        sleep 12
    done
    LB_ALGO_DIRECTIVE="least_conn;" docker compose up -d --force-recreate --no-deps lb01 >/dev/null
    ;;

dist-c)
    bash scripts/dist_concurrent.sh "${LB_ALGO_DIRECTIVE:-least_conn}" "${1:-600}" "${2:-20}"
    ;;

dist-all-c)
    RR_DIRECTIVE="# round_robin: khong khai bao directive thuat toan"
    for spec in "round_robin|${RR_DIRECTIVE}" "least_conn|least_conn;" "ip_hash|ip_hash;"; do
        name="${spec%%|*}"
        directive="${spec#*|}"
        echo ""
        echo "############## THUAT TOAN: ${name} (tai dong thoi) ##############"
        LB_ALGO_DIRECTIVE="$directive" docker compose up -d --force-recreate --no-deps lb01 >/dev/null
        wait_ready || exit 1
        docker compose cp lb01:/etc/nginx/conf.d/default.conf \
            "results/distribute/rendered-${name}.conf" 2>/dev/null
        bash scripts/dist_concurrent.sh "$name" 600 20
        sleep 12
    done
    LB_ALGO_DIRECTIVE="least_conn;" docker compose up -d --force-recreate --no-deps lb01 >/dev/null
    ;;

failover)
    bash scripts/failover.sh "${1:-web02}" 70 30
    ;;

session)
    bash scripts/session_test.sh "${1:-redis}"
    ;;

sec)
    bash scripts/sec_check.sh
    ;;

bench)
    echo "=== 3 node ==="
    bash scripts/bench.sh 3-node 1500 30
    echo ""
    echo "=== Tat web03, con 2 node ==="
    docker compose stop web03
    sleep 14
    bash scripts/bench.sh 2-node 1500 30
    docker compose start web03
    ;;

# Ba lenh duoi nay la cac phep do that cua muc 3.2.2 va 3.5 trong bao cao.
# Moi lenh tu dat thuat toan va tu lam nong may, chay trong khoang 5-45 phut.
dist-skew)
    bash scripts/dist_matrix.sh "${2:-20}" "${3:-600}" "${4:-20}"
    ;;

bench-matrix)
    bash scripts/bench_matrix.sh "${2:-20}" "${3:-3000}" "${4:-20}"
    ;;

bench-degrade)
    bash scripts/bench_degrade.sh "${2:-20}" "${3:-3000}" "${4:-20}"
    ;;

report)
    # In lai dung cac con so nam trong bang bao cao, doc tu results/.
    python REPORT/analyze_bench.py "${2:-all}"
    ;;

all)
    $0 up
    $0 dist-all
    $0 dist-all-c
    $0 dist-skew
    $0 failover web02
    $0 session redis
    $0 session file
    $0 sec
    $0 bench-matrix
    $0 bench-degrade
    echo ""
    echo "Toan bo ket qua nam trong thu muc results/"
    python REPORT/analyze_bench.py
    ;;

*)
    awk 'NR>1 && /^#/{sub(/^# ?/,""); print; next} NR>1 && !/^#/{exit}' "$0"
    ;;
esac
