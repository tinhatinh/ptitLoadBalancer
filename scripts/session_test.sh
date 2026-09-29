#!/usr/bin/env bash
# Do kha nang giu phien khi node da phuc vu dang nhap bi tat.
#   session_test.sh redis      => ky vong van con dang nhap
#   session_test.sh file       => ky vong bi day ve trang dang nhap
set -uo pipefail
# Git Bash (MSYS) doi duong dan bat dau bang dau / thanh duong dan Windows,
# lam hong tham so truyen vao docker compose exec.
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

MODE="${1:-redis}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="results/session/session-${MODE}-${STAMP}.txt"
mkdir -p results/session

echo "=============================================================="
echo " Che do luu session: SESSION_STORE=${MODE}"
echo "=============================================================="

# Phuong an luu session trong file bat buoc nguoi dung dinh kem voi mot node,
# neu khong thi mat phien ngay tu luc dang nhap vi CSRF token nam o node khac.
# Do vay phuong an file chay voi ip hash, con phuong an redis chay voi
# least_conn tu do. So sanh van cong bang: tat ca node khac node giu phien.
if [ "$MODE" = "file" ]; then
    ALGO='ip_hash;'
else
    ALGO='least_conn;'
fi
echo " Thuat toan load balancer: ${ALGO}"

# Hai lenh nay truoc day nuot het loi. Chung that bai thi cum van chay cau hinh
# cu, con file ket qua thi ghi ten thuat toan khong he duoc ap vao - phep do
# "mat phien" khi do la do tren dinh kem ip_hash that.
if ! LB_ALGO_DIRECTIVE="$ALGO" docker compose up -d --force-recreate --no-deps lb01 >/dev/null 2>&1; then
    echo "LOI: khong dat duoc thuat toan $ALGO len load balancer" >&2; exit 1
fi
if ! SESSION_STORE="$MODE" docker compose up -d web01 web02 web03 >/dev/null 2>&1; then
    echo "LOI: khong khoi dong lai duoc ba node voi SESSION_STORE=$MODE" >&2; exit 1
fi
echo -n "Cho cum san sang "
for _ in $(seq 1 30); do
    code="$(docker compose exec -T client01 curl -sk -m 3 -o /dev/null -w '%{http_code}'              "https://${LB_IP:-192.168.240.10}/healthz" 2>/dev/null || true)"
    if [ "$code" = "200" ]; then echo " -> OK"; break; fi
    echo -n "."; sleep 2
done
[ "$code" = "200" ] || { echo " -> KHONG DAT" >&2; exit 1; }

{
    echo "# session_test mode=${MODE} stamp=${STAMP}"
    echo "# load_balancer_algorithm=${ALGO}"
    echo ""
    echo "## Buoc 1. Dang nhap"
} | tee "$OUT"

LOGIN="$(docker compose exec -T client01 bash /scripts/session_client.sh login | tee -a "$OUT")"
NODE="$(printf '%s\n' "$LOGIN" | awk -F= '/^login_node=/{print $2}')"

if [ -z "$NODE" ] || [ "$NODE" = "none" ]; then
    echo "LOI: khong xac dinh duoc node phuc vu dang nhap, dung test." | tee -a "$OUT"
    exit 1
fi

echo "" | tee -a "$OUT"
echo "## Buoc 2. Tat dung node vua phuc vu dang nhap: ${NODE}" | tee -a "$OUT"
docker compose stop "$NODE" 2>&1 | tee -a "$OUT"
sleep 3

echo "" | tee -a "$OUT"
echo "## Buoc 3. Goi lai /member.php 10 lan bang cookie cu" | tee -a "$OUT"
docker compose exec -T client01 bash /scripts/session_client.sh probe 10 | tee -a "$OUT"

echo "" | tee -a "$OUT"
echo "## Buoc 4. Bat lai ${NODE}" | tee -a "$OUT"
docker compose start "$NODE" 2>&1 | tee -a "$OUT"

# Khong de lai load balancer o che do ip_hash cung nhu node o che do luu
# session trong file: bat ky phep do nao chay sau ma khong tu dat hai tham so
# nay se do nham ca mot cau hinh khong con ton tai. Mot luong chay nam lai sau
# lenh nay da keo toan bo 126000 request ve dung mot node.
echo "" | tee -a "$OUT"
echo "## Buoc 5. Tra cum ve cau hinh mac dinh (redis + least_conn)" | tee -a "$OUT"
LB_ALGO_DIRECTIVE="least_conn;" docker compose up -d --force-recreate \
    --no-deps lb01 >/dev/null 2>&1
SESSION_STORE=redis docker compose up -d --force-recreate \
    web01 web02 web03 >/dev/null 2>&1
sleep 8

echo ""
echo "Da luu ket qua vao ${OUT}"
