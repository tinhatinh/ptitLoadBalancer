FROM alpine:3.20

RUN apk add --no-cache \
        nginx \
        curl \
        php83 \
        php83-fpm \
        php83-session \
        php83-redis \
        php83-mysqli \
        php83-openssl \
        php83-curl \
        php83-mbstring \
        tini \
    # php-fpm mac dinh clear_env=yes se xoa toan bo bien moi truong cua
    # container, khien ung dung khong doc duoc DB_HOST va REDIS_HOST.
    && sed -i 's|^;\?clear_env = .*|clear_env = no|' /etc/php83/php-fpm.d/www.conf \
    && sed -i 's|^;\?pm.max_children = .*|pm.max_children = 16|'      /etc/php83/php-fpm.d/www.conf \
    # display_errors = Off la mac dinh cua image, nhung no phai la mot quyet
    # dinh ghi ro trong repo: bat len la du de loi PHP in duong dan tuyet doi
    # va cau truy that ra ngoai khach hang.
    && sed -i 's|^display_errors = .*|display_errors = Off|' /etc/php83/php.ini \
    && mkdir -p /var/www/public /var/log/nginx /var/log/php83 /run/nginx

COPY nginx.conf       /etc/nginx/node.conf.tpl
COPY fastcgi_params   /etc/nginx/fastcgi_params
COPY app/             /var/www/public/
COPY entrypoint.sh    /usr/local/bin/entrypoint.sh

RUN chmod 755 /usr/local/bin/entrypoint.sh

EXPOSE 80

ENTRYPOINT ["/sbin/tini", "--", "/usr/local/bin/entrypoint.sh"]
