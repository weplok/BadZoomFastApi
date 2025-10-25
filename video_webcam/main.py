from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from starlette.responses import HTMLResponse
from aiortc import RTCPeerConnection, RTCSessionDescription

app = FastAPI()
pcs = {}

html = """
<!DOCTYPE html>
<html>
  <head>
    <title>WebRTC Video Chat</title>
    <style>video { width: 45%; margin: 5px; }</style>
  </head>
  <body>
    <video id="localVideo" autoplay muted playsinline></video>
    <video id="remoteVideo" autoplay playsinline></video>

    <script>
      const localVideo = document.getElementById('localVideo');
      const remoteVideo = document.getElementById('remoteVideo');

      const pc = new RTCPeerConnection({
        iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
      });

      navigator.mediaDevices.getUserMedia({ video: true, audio: true })
        .then(stream => {
          localVideo.srcObject = stream;
          stream.getTracks().forEach(track => pc.addTrack(track, stream));
        })
        .catch(error => console.error('Error accessing media devices:', error));

      pc.ontrack = event => {
        if(remoteVideo.srcObject !== event.streams[0]) {
          remoteVideo.srcObject = event.streams[0];
        }
      };

      const ws = new WebSocket(`ws://${window.location.host}/ws/client1`);

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

      pc.createOffer()
        .then(offer => {
          pc.setLocalDescription(offer);
          ws.onopen = () => ws.send(JSON.stringify(offer));
        })
        .catch(console.error);
    </script>
  </body>
</html>
"""

@app.get("/")
async def index():
    return HTMLResponse(html)

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await websocket.accept()
    pc = RTCPeerConnection()
    pcs[client_id] = pc

    @pc.on("track")
    async def on_track(track):
        print(f"Received track: kind={track.kind}")

    try:
        while True:
            msg = await websocket.receive_json()
            if "sdp" in msg:
                desc = RTCSessionDescription(sdp=msg["sdp"], type=msg["type"])
                await pc.setRemoteDescription(desc)
                if desc.type == "offer":
                    answer = await pc.createAnswer()
                    await pc.setLocalDescription(answer)
                    await websocket.send_json({
                        "sdp": pc.localDescription.sdp,
                        "type": pc.localDescription.type
                    })
            elif "candidate" in msg:
                candidate = msg["candidate"]
                await pc.addIceCandidate(candidate)
    except WebSocketDisconnect:
        await pc.close()
        pcs.pop(client_id, None)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
