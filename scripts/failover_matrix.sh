#!/usr/bin/env bash
# Lai phep do failover nhieu lan de so mau cham co khoang tin cay.
# Mot vong failover truoc day chi chay mot lan, nen "chin mau cham" la mot
# quan sat don le: khong biet chay lai thi con chin hay khong. O day giu
# nguyen kich thuoc vong do (70 s, tat o giay 10, bat lai o giay 40) va lap
# lai N lan, moi lan giu lai bo file ket qua cua no.
#   failover_matrix.sh [so_luong] [giay] [bat_lai_sau_giay]
set -uo pipefail

export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'
command -v docker >/dev/null ||
    export PATH="$PATH:/c/Program Files/Docker/Docker/resources/bin"

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

REPS="${1:-12}"
DUR="${2:-70}"
RESTART_AFTER="${3:-30}"
STAMP="$(date +%Y%m%d-%H%M%S)"
OUT="results/failover/repeat-${STAMP}.csv"
KEEP="results/failover/repeat-${STAMP}"
mkdir -p results/failover "$KEEP"

echo "rep,samples,errors,slow,avg_ms,max_ms,w1,w2,w3,retry_lines" > "$OUT"

for ((i = 1; i <= REPS; i++)); do
    echo "--- luong $i/$REPS ---"
    T0="$(date +%s)"
    bash scripts/failover.sh web02 "$DUR" "$RESTART_AFTER" \
        > "$KEEP/run-$i.out" 2>&1

    SUM="$(ls -t results/failover/summary-load-web02-*.txt 2>/dev/null | head -1)"
    LOG="$(ls -t results/failover/retries-web02-*.log 2>/dev/null | head -1)"
    CSV="$(ls -t results/failover/load-*.csv 2>/dev/null | head -1)"
    if [ -z "$SUM" ]; then
        echo "  LOI: luong $i khong co bang tong hop" >&2
        # Dong phai du 10 cot nhu tieu de, neu khong DictReader day cac gia
        # tri tiep theo sang cot thua va luong do bi loai im lang.
        echo "$i,,,,,,,,," >> "$OUT"
        continue
    fi
    # `ls -t` lay file MOI NHAT, khong phai file cua luong nay. Neu
    # failover.sh ket thuc som ma khong sinh ra bang tong hop thi ba dong
    # duoi day lay lai tro cua luong truoc do va bang 12 vong co mot dong
    # trung. Do lan da xay ra voi luong 10.
    if [ "$(stat -c %Y "$SUM" 2>/dev/null || echo 0)" -lt "$T0" ]; then
        echo "  LOI: luong $i lay lai tong hop cua luong tru ($SUM)" >&2
        echo "$i,,,,,,,,," >> "$OUT"
        continue
    fi
    cp "$SUM" "$KEEP/summary-$i.txt"
    [ -n "$LOG" ] && cp "$LOG" "$KEEP/retries-$i.log"
    [ -n "$CSV" ] && cp "$CSV" "$KEEP/load-$i.csv"

    ROW="$(awk -v rep="$i" -v logf="$KEEP/retries-$i.log" '
        /^Tong so mau/                    { s = $NF }
        /^So mau co HTTP != 200/          { e = $NF }
        /^Mau phai chiu/                  { s1 = $NF }
        /^Thoi gian dap ung trung binh/   { a = $(NF-1) }
        /^Thoi gian dap ung lon nhat/     { m = $(NF-1) }
        /^  web01/                        { w1 = $NF }
        /^  web02/                        { w2 = $NF }
        /^  web03/                        { w3 = $NF }
        END {
            printf "%s,%s,%s,%s,%.1f,%.1f,%s,%s,%s,", rep, s, e, s1, a * 1000, m * 1000, w1, w2, w3
        }
    ' "$KEEP/summary-$i.txt")"

    NRET=0
    [ -f "$KEEP/retries-$i.log" ] && \
        NRET=$(grep -c 'upstream=[^ ]*172\.20\.0\.12:80,' "$KEEP/retries-$i.log" || true)
    echo "$ROW$NRET" >> "$OUT"
    tail -1 "$OUT" | sed 's/^/  /'
    sleep 3
done

# Giu lai vong cuoi o thu muc goc de bieu do va vi du log trong muc 3.3 quy
# ve dung mot vong do co the chi ra; cac vong truoc chi con trong $KEEP.
for pat in summary-load-web02 retries-web02 load-web02; do
    ls -t results/failover/${pat}-*.txt results/failover/${pat}-*.log          results/failover/${pat}-*.csv 2>/dev/null | tail -n +2 | xargs -r rm -f
done

echo ""
echo "Da ghi $OUT va thu muc $KEEP"
