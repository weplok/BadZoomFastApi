FROM canyan/janus-gateway:latest

COPY janus-config/ /usr/local/etc/janus/

# 8188 — WebSocket
# 8088 — HTTP API (если нужно)
# 20000-40000 — RTP/RTCP для медиа
EXPOSE 8188 8088 20000-40000/udp

ENTRYPOINT ["/usr/local/bin/janus"]
