from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from typing import Dict, Set
from uuid import uuid4
from aiortc import RTCPeerConnection, RTCSessionDescription

app = FastAPI()

# Хранилище комнат и подключений
rooms: Dict[str, Set[WebSocket]] = {}

# HTML клиентская часть с аудио и видео
html = """
<!DOCTYPE html>
<html>
<head>
  <title>FastAPI WebRTC Audio/Video Conference</title>
  <style>video { width: 300px; margin: 5px; }</style>
</head>
<body>
<h2>Конференция</h2>
<video id="localVideo" autoplay muted playsinline></video>
<div id="remoteVideos"></div>

<script>
  const roomId = window.location.pathname.split("/").pop();
  const localVideo = document.getElementById('localVideo');
  const remoteVideos = document.getElementById('remoteVideos');

  const pc = new RTCPeerConnection({
    iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
  });

  navigator.mediaDevices.getUserMedia({ video: true, audio: true })
    .then(stream => {
      localVideo.srcObject = stream;
      stream.getTracks().forEach(track => pc.addTrack(track, stream));
    })
    .catch(error => console.error('Media error:', error));

  pc.ontrack = event => {
    const remoteVideo = document.createElement('video');
    remoteVideo.srcObject = event.streams[0];
    remoteVideo.autoplay = true;
    remoteVideo.playsinline = true;
    remoteVideos.appendChild(remoteVideo);
  };

  const ws = new WebSocket(`ws://${window.location.host}/ws/${roomId}`);

  ws.onmessage = async (event) => {
    const data = JSON.parse(event.data);
    if (data.sdp) {
      await pc.setRemoteDescription(new RTCSessionDescription(data));
      if (data.type === 'offer') {
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        ws.send(JSON.stringify(pc.localDescription));
      }
    } else if (data.candidate) {
      await pc.addIceCandidate(data.candidate);
    }
  };

  pc.onicecandidate = event => {
    if (event.candidate) {
      ws.send(JSON.stringify({ candidate: event.candidate }));
    }
  };

  pc.createOffer().then(offer => {
    pc.setLocalDescription(offer);
    ws.onopen = () => ws.send(JSON.stringify(offer));
  });
</script>
</body>
</html>
"""

@app.post("/create-room")
async def create_room():
    room_id = str(uuid4())
    rooms[room_id] = set()
    return {"room_id": room_id, "url": f"/room/{room_id}"}

@app.get("/room/{room_id}")
async def get_room(room_id: str):
    if room_id not in rooms:
        raise HTTPException(status_code=404, detail="Room not found")
    return HTMLResponse(html)

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str):
    if room_id not in rooms:
        rooms[room_id] = set()
    await websocket.accept()
    rooms[room_id].add(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            for connection in rooms[room_id]:
                if connection != websocket:
                    await connection.send_json(data)
    except WebSocketDisconnect:
        rooms[room_id].remove(websocket)
        if not rooms[room_id]:
            del rooms[room_id]
