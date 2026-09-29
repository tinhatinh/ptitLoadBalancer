#!/usr/bin/env bash
# Tao chung chi TLS tu ky cho load balancer. Chay mot lan truoc khi khoi dong.
set -euo pipefail

# Hai bẫy đường dẫn trên Git Bash: MSYS tự đổi tham số bắt đầu bằng dấu /
# (lam hong chuoi -subj), va openssl bản Windows không đọc được dạng /c/...
export MSYS_NO_PATHCONV=1
export MSYS2_ARG_CONV_EXCL='*'

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="$ROOT/nginx/lb/certs"
mkdir -p "$CERT_DIR"
CERT_DIR="$(cd "$CERT_DIR" && (pwd -W 2>/dev/null || pwd))"

pair_ok() {
    [ -s "$CERT_DIR/cluster.crt" ] && [ -s "$CERT_DIR/cluster.key" ] || return 1
    # openssl req -newkey viet file key TRUOC roi moi ghi file cert, nen mot
    # lan bi chen giua de lai cap key/cert khong khop nhau. Neu chi kiem tra "ca
    # hai file deu ton tai" thi lan chay sau bo qua mai mai va nginx chi bao
    # "SSL_CTX_use_PrivateKey_file failed", khong noi ro nguyen nhan.
    [ "$(openssl x509 -noout -pubkey -in "$CERT_DIR/cluster.crt" 2>/dev/null | openssl md5)" = \
      "$(openssl pkey -pubout -in "$CERT_DIR/cluster.key" 2>/dev/null | openssl md5)" ] || return 1
    # Con hieu luc it nhat mot thang nua.
    openssl x509 -checkend $(( 30 * 86400 )) -noout -in "$CERT_DIR/cluster.crt" >/dev/null 2>&1
}

if pair_ok; then
    echo "Da co san cap chung chi hop le, bo qua."
    chmod 600 "$CERT_DIR/cluster.key" 2>/dev/null || true
    exit 0
fi

if [ -f "$CERT_DIR/cluster.crt" ] || [ -f "$CERT_DIR/cluster.key" ]; then
    echo "Cap chung chi cu hong hoac da het han, sinh lai."
fi
rm -f "$CERT_DIR/cluster.crt" "$CERT_DIR/cluster.key"

openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$CERT_DIR/cluster.key" \
    -out "$CERT_DIR/cluster.crt" \
    -days 825 \
    -subj "/C=VN/ST=Ha Noi/L=Ha Noi/O=PTIT ATTT/OU=Nhom 15/CN=de07-cluster.local" \
    -addext "subjectAltName=IP:192.168.240.10,IP:127.0.0.1,DNS:localhost" \
    -addext "basicConstraints=critical,CA:FALSE" \
    -addext "keyUsage=digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=serverAuth"

# Khoa ngam dinh sinh ra theo umask cua he dieu hanh, tren may nay la 0644:
# bat ky tai khoan nao doc duoc danh sach file nam trong thu muc deu co the
# gia dang load balancer. Repo khong theo doi thu muc nay nhung file van ton
# tai tren may chay lab.
chmod 600 "$CERT_DIR/cluster.key"
chmod 644 "$CERT_DIR/cluster.crt"

echo "Da sinh chung chi tai $CERT_DIR"
