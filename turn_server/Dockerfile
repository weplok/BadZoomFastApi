FROM coturn/coturn:latest

USER root

RUN apt-get update && apt-get install -y gettext-base && apt-get clean

COPY entrypoint.sh /usr/local/bin/entrypoint.sh
COPY turnserver.conf.template /usr/local/bin/turnserver.conf.template

EXPOSE 3478 3478/udp 5349 5349/udp

ENTRYPOINT ["entrypoint.sh"]

CMD ["turnserver"]
