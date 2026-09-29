#!/usr/bin/env bash
# Chay tren MAY CHU (can docker CLI). Tat mot node giua chung vong do luu luong
# roi bat lai, ke ra so lieu cho Bang 3.2.
#   failover.sh <ten_node> <do_dai_vong_do_giay> <so_giay_sau_khi_tat_thi_bat_lai>
set -uo pipefail
# Git Bash (MSYS) doi duong dan bat dau bang dau / thanh duong dan Windows,
# lam hong tham so truyen vao docker compose exec.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

TARGET="${1:-web02}"
DUR="${2:-70}"
RESTART_AFTER="${3:-30}"
STAMP="$(date +%Y%m%d-%H%M%S)"
CSV_NAME="load-${TARGET}-${STAMP}.csv"

# Ten node -> dia chi trong mang backend, de loc access log cua LB.
case "$TARGET" in
    web01) TARGET_IP="172.20.0.11" ;;
    web02) TARGET_IP="172.20.0.12" ;;
    web03) TARGET_IP="172.20.0.13" ;;
    *)
        # Voi ten sai, moi phep do van chay het va in ra bang "0 loi, khong
        # gian doan": khong co node nao bi tat nen khong co gi de do.
        echo "LOI: ten node khong biet: $TARGET (web01|web02|web03)" >&2
        exit 1
        ;;
esac

mkdir -p results/failover

# Moc dong access log truoc khi mo vong do. Khong co moc nay thi lenh tach
# log o cuoi gom ca cac lan thu lai cua nhung vong do truoc, vi healthz.log
# cua lb01 chi bi xoa khi container khoi dong lai.
LOG_BEFORE="$(docker compose exec -T lb01 sh -c \
    'wc -l < /var/log/nginx/healthz.log 2>/dev/null || echo 0')"
LOG_BEFORE="${LOG_BEFORE//[!0-9]/}"; LOG_BEFORE="${LOG_BEFORE:-0}"

echo "[t=0s]   Mo vong do ${DUR}s, mot request cach nhau 0,2 s cong thoi gian dap ung, ghi vao results/failover/${CSV_NAME}"
docker compose exec -d client01 bash /scripts/loadloop.sh "$DUR" 0.2 "/results/failover/${CSV_NAME}"

sleep 5
echo "[t=5s]   Trang thai cluster truoc khi tat ${TARGET}:"
docker compose ps --format '{{.Name}}: {{.Status}}' | sed 's/^/           /'

sleep 5
echo "[t=10s]  docker compose stop ${TARGET}"
docker compose stop "$TARGET"

# Chung minh node that da dung lai. Lenh stop tra ve thanh cong van co the di
# qua mot container da o trang thai dung tu truoc, va khi do ca vong do chi la
# ba node dang phuc vu binh thuong duoc ghi ten la "failover".
for _ in 1 2 3 4 5; do
    STATE="$(docker compose ps --format '{{.Name}} {{.State}}' \
              | awk -v n="de07-${TARGET}" '$1 == n { print $2 }')"
    if [ "$STATE" = "exited" ] || [ "$STATE" = "created" ]; then break; fi
    sleep 1
done
if [ "$STATE" != "exited" ] && [ "$STATE" != "created" ]; then
    echo "LOI: ${TARGET} van o trang thai '$STATE' sau khi stop, khong phai mot vong failover" >&2
    docker compose start "$TARGET" >/dev/null 2>&1
    exit 1
fi
echo "           ${TARGET} da dung (${STATE})"

sleep "$RESTART_AFTER"
echo "[t=$((10 + RESTART_AFTER))s] docker compose start ${TARGET}"
docker compose start "$TARGET"

# Cho vong do ket thuc va ghi het du lieu.
WAIT=$(( DUR - 10 - RESTART_AFTER + 5 ))
[ "$WAIT" -lt 8 ] && WAIT=8
sleep "$WAIT"

echo ""
echo "== LOG cua load balancer trong khoang thoi gian dien ra su co =="
LOG_EXC="results/failover/retries-${TARGET}-${STAMP}.log"
docker compose logs --since "$(( DUR + 30 ))s" lb01 2>&1 \
    | grep -Ei 'upstream|timed out|refused|disabled' > "$LOG_EXC" || true
# Access log nam trong container va bi xoa khi khoi dong lai lb01 o phep do
# khac, nen luu rieng cac dong co hai dia chi upstream.
docker compose exec -T lb01 sh -c \
    "tail -n +$(( LOG_BEFORE + 1 )) /var/log/nginx/healthz.log \
     | grep 'upstream=${TARGET_IP}:80, '" \
    >> "$LOG_EXC" 2>/dev/null || true
N_ALL=$(( $(wc -l < "$LOG_EXC") ))
N_ACC=$(grep -c 'upstream=' "$LOG_EXC" || true)
echo "Da luu $N_ALL dong log vao $LOG_EXC ($N_ACC dong access log co hai dia chi upstream, $(( N_ALL - N_ACC )) dong error/warn cua nginx)"
grep -c 'upstream=' "$LOG_EXC" >/dev/null && \
    tail -6 "$LOG_EXC"

awk -f scripts/summarize.awk "results/failover/${CSV_NAME}" \
    | tee "results/failover/summary-${CSV_NAME%.csv}.txt"
