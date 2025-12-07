#!/usr/bin/env sh
set -e

# Проверка переменных окружения
[ -z "$NGINX_SERVER_NAMES" ] && echo "ERROR: NGINX_SERVER_NAMES is not set!" && exit 1

# Подставляем env в template
VARS='$NGINX_SERVER_NAMES $SSL_CERTIFICATE $SSL_CERTIFICATE_KEY'

envsubst "$VARS" < /usr/local/bin/nginx.conf.template > /etc/nginx/nginx.conf

# Условно генерируем SSL конфиг
is_disabled() {
    case "$1" in
        ""|false|False|0) return 0 ;;  # значение считается "выключено"
        *) return 1 ;;                 # любое другое значение — "включено"
    esac
}

if ! is_disabled "$SSL_CERTIFICATE" && ! is_disabled "$SSL_CERTIFICATE_KEY"; then
    echo "SSL enabled — generating ssl.conf..."
    envsubst "$VARS" < /usr/local/bin/ssl.conf.template > /etc/nginx/ssl.conf
else
    echo "SSL disabled — creating empty ssl.conf..."
    echo "" > /etc/nginx/ssl.conf
fi

exec "$@";
