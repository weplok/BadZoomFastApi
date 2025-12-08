#!/usr/bin/env sh
set -e

# Подставляем переменные в основной конфиг
VARS='$NGINX_SERVER_NAMES $NGINX_DOMAIN'
envsubst "$VARS" < /usr/local/bin/nginx.conf.template > /etc/nginx/nginx.conf

# Генерируем ssl.conf только если сертификаты указаны
is_ssl_enabled() {
    case "$1" in
        ""|false|False|0) return 1 ;;
        *) return 0 ;;
    esac
}

if is_ssl_enabled "$SSL_CERTIFICATES"; then
    echo "SSL enabled — generating ssl.conf..."
    envsubst '$VARS' < /usr/local/bin/ssl.conf.template > /etc/nginx/ssl.conf
else
    echo "SSL disabled — creating empty ssl.conf..."
    echo "" > /etc/nginx/ssl.conf
fi

exec "$@";
