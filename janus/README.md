Janus SFU PoC (fast setup)
=========================

What is included
- Janus Gateway container (meetEcho official image)
- nginx container serving a minimal frontend on http://localhost:8015
- Minimal frontend that uses janus.js to join a VideoRoom (room id 1234) as publisher/subscriber.
- No backend required for quick PoC — Janus handles WebRTC signaling via its JS library.

Quick start (one night PoC)
1) Make sure Docker and Docker Compose are installed on your machine.
2) From this project's root, run:
   docker compose up --build

3) Open http://localhost:8015 in your browser (Chrome/Edge recommended).
   It will try to connect to Janus at ws://localhost:8188 (WebSocket). If your setup uses different host/port,
   edit frontend/main.js and change the "server" variable.

Notes & caveats
- This is a minimal PoC to get a working SFU-based conference quickly. It is intentionally lightweight.
- For production you should:
  * Add TURN (coturn) and configure Janus to use it.
  * Protect Janus with HTTPS/WSS.
  * Add authentication, room management, persistent storage, monitoring.
  * Consider using Redis for scaling and sharding rooms across multiple Janus instances.
- The frontend uses janus.js from the official Janus demo host. If you work offline, download janus.js and update index.html.

Files:
- docker-compose.yml
- frontend/index.html
- frontend/main.js
- janus-config/ (empty — you can add custom janus.cfg if needed)
