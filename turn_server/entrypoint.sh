#!/usr/bin/env sh
set -e

# Проверка переменных окружения
[ -z "$TURN_SECRET" ] && echo "ERROR: TURN_SECRET is not set!" && exit 1
[ -z "$TURN_REALM" ] && echo "ERROR: TURN_REALM is not set!" && exit 1
[ -z "$EXTERNAL_IP" ] && echo "ERROR: EXTERNAL_IP is not set!" && exit 1

echo "Generating /etc/turnserver.conf from template..."

# Подставляем env в template
envsubst < /usr/local/bin/turnserver.conf.template > /etc/turnserver.conf

echo "Generated /etc/turnserver.conf:"
echo "--------------------------------------------------"
cat /etc/turnserver.conf
echo "--------------------------------------------------"

# Запускаем coturn (CMD игнорируется, заменяется на exec)
exec "$@"
