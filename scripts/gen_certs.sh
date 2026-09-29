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

if [ -f "$CERT_DIR/cluster.crt" ] && [ -f "$CERT_DIR/cluster.key" ]; then
    echo "Da co san cluster.crt va cluster.key, bo qua."
    exit 0
fi

openssl req -x509 -nodes -newkey rsa:2048 \
    -keyout "$CERT_DIR/cluster.key" \
    -out "$CERT_DIR/cluster.crt" \
    -days 825 \
    -subj "/C=VN/ST=Ha Noi/L=Ha Noi/O=PTIT ATTT/OU=Nhom 15/CN=de07-cluster.local" \
    -addext "subjectAltName=IP:192.168.240.10,IP:127.0.0.1,DNS:localhost" \
    -addext "basicConstraints=critical,CA:FALSE" \
    -addext "keyUsage=digitalSignature,keyEncipherment" \
    -addext "extendedKeyUsage=serverAuth"

echo "Da sinh chung chi tai $CERT_DIR"
