FROM coturn/coturn:latest

# Работаем под root для копирования файлов
USER root

# Копируем конфиг прямо в стандартное место coturn
COPY turnserver.conf /etc/turnserver.conf

# Возвращаемся к безопасному пользователю
USER turnserver

# Открываем стандартные порты STUN/TURN
EXPOSE 3478 3478/udp 5349 5349/udp

CMD ["turnserver", "-c", "/etc/turnserver.conf", "-v"]
