FROM coturn/coturn:latest

# Работаем под root для копирования файлов
USER root

# Копируем конфиг прямо в стандартное место coturn
COPY turnserver.conf /etc/turnserver.conf

# Открываем стандартные порты STUN/TURN
EXPOSE 8347 8347/udp 8534 8534/udp

CMD ["turnserver", "-c", "/etc/turnserver.conf", "-v"]
