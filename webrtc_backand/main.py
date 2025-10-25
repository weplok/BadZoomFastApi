from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
clients: dict[str, WebSocket] = {}

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    client_id = str(id(ws))
    clients[client_id] = ws
    try:
        # notify others about new peer
        for cid, client in clients.items():
            if cid != client_id:
                await client.send_json({"type": "new-peer", "from": client_id})

        while True:
            data = await ws.receive_json()
            to = data.get("to")
            if to and to in clients:
                await clients[to].send_json(data)
    except WebSocketDisconnect:
        del clients[client_id]
