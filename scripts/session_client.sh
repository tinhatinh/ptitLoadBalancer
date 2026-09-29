#!/usr/bin/env bash
# Chay BEN TRONG client01. Giu cookie jar tai /results/session/jar de lan goi
# sau van dung cung mot phien.
set -uo pipefail

LB="https://${LB_HOST:-192.168.240.10}"
JAR="/results/session/jar"
mkdir -p /results/session

HDR="$(mktemp)"

case "${1:-help}" in
login)
    rm -f "$JAR"
    TOKEN="$(curl -sk -c "$JAR" "$LB/login.php" \
        | grep -o 'name="csrf" value="[a-f0-9]*"' | sed 's/.*value="//; s/"//')"
    if [ -z "$TOKEN" ]; then
        echo "LOI: khong lay duoc ma bao ve tu /login.php"
        exit 1
    fi
    CODE="$(curl -sk -b "$JAR" -c "$JAR" -D "$HDR" -o /dev/null -w '%{http_code}' \
        --data-urlencode "csrf=$TOKEN" \
        --data-urlencode "username=${TEST_USER:-danhpt}" \
        --data-urlencode "password=${TEST_PASS:-Lab@De07}" \
        "$LB/login.php")"
    NODE="$(tr -d '\r' < "$HDR" | awk -F': ' 'tolower($1)=="x-node"{print $2}')"
    SETCOOKIE="$(tr -d '\r' < "$HDR" | awk -F': ' 'tolower($1)=="set-cookie"{print $2}')"
    echo "login_http_code=$CODE"
    echo "login_node=${NODE:-none}"
    echo "session_cookie=$SETCOOKIE"
    ;;

probe)
    N="${2:-10}"
    OK=0
    REDIR=0
    OTHER=0
    for ((i = 1; i <= N; i++)); do
        CODE="$(curl -sk -b "$JAR" -o /dev/null -D "$HDR" -w '%{http_code}' "$LB/member.php")" \
            || CODE="000"
        NODE="$(tr -d '\r' < "$HDR" | awk -F': ' 'tolower($1)=="x-node"{print $2}')"
        LOC="$(tr -d '\r' < "$HDR" | awk -F': ' 'tolower($1)=="location"{print $2}')"
        printf '%2d  code=%-3s node=%-6s %s\n' "$i" "$CODE" "${NODE:-none}" "${LOC:+redirect=$LOC}"
        case "$CODE" in
            200) OK=$(( OK + 1 )) ;;
            302) REDIR=$(( REDIR + 1 )) ;;
            *)   OTHER=$(( OTHER + 1 )) ;;
        esac
        sleep 1
    done
    echo ""
    echo "Tong ket: 200_giu_duoc_phien=$OK   302_mat_phien=$REDIR   khac=$OTHER"
    ;;

*)
    echo "Dung: $0 login | $0 probe <so_lan>"
    ;;
esac

rm -f "$HDR"
