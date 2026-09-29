#!/bin/sh
set -eu

: "${NODE_NAME:?NODE_NAME is required}"
: "${REDIS_HOST:?REDIS_HOST is required}"
: "${DB_HOST:?DB_HOST is required}"

sed "s|@NODE_NAME@|${NODE_NAME}|g" /etc/nginx/node.conf.tpl > /etc/nginx/node.conf

SESSION_DIR=/var/lib/php83/sessions
mkdir -p "$SESSION_DIR"
chown nobody:nobody "$SESSION_DIR"

if [ "${SESSION_STORE:-redis}" = "redis" ]; then
    cat > /etc/php83/conf.d/99-session.ini <<EOF
session.save_handler = redis
session.save_path    = "tcp://${REDIS_HOST}:${REDIS_PORT:-6379}?auth=${REDIS_PASSWORD}&database=0&prefix=de07:"
EOF
else
    cat > /etc/php83/conf.d/99-session.ini <<EOF
session.save_handler = files
session.save_path    = "${SESSION_DIR}"
EOF
fi

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
