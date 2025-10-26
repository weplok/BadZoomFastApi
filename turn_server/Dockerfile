FROM coturn/coturn:latest

# Настройка окружения
ENV TURN_USER=weplok
ENV TURN_PASSWORD=weplok
ENV REALM=call.weplok.ru

# Создаём директорию для конфигов
RUN mkdir -p /etc/turnserver

# Добавляем конфиг
COPY turnserver.conf /etc/turnserver/turnserver.conf

EXPOSE 3478 3478/udp 5349 5349/udp

CMD ["turnserver", "-c", "/etc/turnserver/turnserver.conf", "-v"]
