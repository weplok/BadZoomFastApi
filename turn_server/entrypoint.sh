#!/bin/sh

envsubst < /etc/turnserver.conf.template > /etc/turnserver.conf

exec "$@"