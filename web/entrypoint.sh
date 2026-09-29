#!/bin/sh
set -eu

: "${NODE_NAME:?NODE_NAME is required}"
: "${REDIS_HOST:?REDIS_HOST is required}"
: "${DB_HOST:?DB_HOST is required}"

sed "s|@NODE_NAME@|${NODE_NAME}|g" /etc/nginx/node.conf.tpl > /etc/nginx/node.conf
# Neu phep thay the khong chay het, node van len may binh thuong nhung moi
# request tra ve X-Node "@NODE_NAME@" va phep dem request roi vao node nao se
# dem mot thung khong co that.
if grep -q '@NODE_NAME@' /etc/nginx/node.conf; then
    echo "node.conf con chura @NODE_NAME@ sau khi render" >&2
    exit 1
fi

SESSION_DIR=/var/lib/php83/sessions
mkdir -p "$SESSION_DIR"
chown nobody:nobody "$SESSION_DIR"

case "${SESSION_STORE:-redis}" in
    redis)
    : "${REDIS_PASSWORD:?REDIS_PASSWORD is required when SESSION_STORE=redis}"
    cat > /etc/php83/conf.d/99-session.ini <<EOF
session.save_handler = redis
session.save_path    = "tcp://${REDIS_HOST}:${REDIS_PORT:-6379}?auth=${REDIS_PASSWORD}&database=0&prefix=de07:"
EOF
        ;;
    file)
    cat > /etc/php83/conf.d/99-session.ini <<EOF
session.save_handler = files
session.save_path    = "${SESSION_DIR}"
EOF
        ;;
    *)
    # Truoc day moi gia tri khac "redis" im lang bi hieu la luu dia. Mot
    # cai ten sai trong .env se bi hoi thanh "phien mat khi tat node" ma
    # khong ai bao la cau hinh khong duoc hieu.
    echo "SESSION_STORE='$SESSION_STORE' khong hop le (redis|file)" >&2
    exit 1
    ;;
esac

cat >> /etc/php83/conf.d/99-session.ini <<'EOF'

session.name              = DE07SID
session.use_cookies       = 1
session.use_only_cookies  = 1
session.use_strict_mode   = 1
session.sid_length        = 32
session.sid_bits_per_character = 5
session.cookie_httponly   = 1
session.cookie_secure     = 1
session.cookie_samesite   = Lax
session.cookie_lifetime   = 0
session.gc_maxlifetime    = 1800
EOF

php-fpm83 -D

exec nginx -c /etc/nginx/node.conf
