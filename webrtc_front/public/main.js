const socket = io();
const localVideo = document.createElement('video');
localVideo.autoplay = true;
localVideo.muted = true;

const videosContainer = document.getElementById('videos');
videosContainer.appendChild(localVideo);

let localStream;
let peers = {}; // {socketId: RTCPeerConnection}

async function start() {
    localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    localVideo.srcObject = localStream;
}

start();

// Когда приходит новый пользователь
socket.on('new-user', socketId => {
    const peer = createPeerConnection(socketId);
    peers[socketId] = peer;

    // Создаем offer
    peer.createOffer()
        .then(offer => peer.setLocalDescription(offer))
        .then(() => {
            socket.emit('offer', { sdp: peer.localDescription, to: socketId, from: socket.id });
        });
});

socket.on('offer', async data => {
    const peer = createPeerConnection(data.from);
    peers[data.from] = peer;

    await peer.setRemoteDescription(data.sdp);
    const answer = await peer.createAnswer();
    await peer.setLocalDescription(answer);
    socket.emit('answer', { sdp: answer, to: data.from, from: socket.id });
});

socket.on('answer', async data => {
    const peer = peers[data.from];
    if (!peer) return;
    await peer.setRemoteDescription(data.sdp);
});

socket.on('ice-candidate', async data => {
    const peer = peers[data.from];
    if (!peer) return;
    await peer.addIceCandidate(data.candidate);
});

socket.on('user-disconnected', socketId => {
    if (peers[socketId]) {
        peers[socketId].close();
        delete peers[socketId];
        const vid = document.getElementById(socketId);
        if (vid) vid.remove();
    }
});

function createPeerConnection(socketId) {
    const peer = new RTCPeerConnection({
        iceServers: [
          { "urls": 'stun:stun.l.google.com:19302' },
          {
            "urls": [
                'turn:weplok.ru:8347?transport=udp',
                'turn:weplok.ru:8347?transport=tcp'
            ],
            "username": "weplok",
            "credential": "weplok"
          }
        ],

        // Рекомендуемые настройки для WebRTC
        iceCandidatePoolSize: 10
    });

    // Логирование ICE-событий (очень помогает при отладке)
    peer.onicecandidate = (event) => {
        if (event.candidate) {
            console.log('New ICE candidate:', event.candidate);
            socket.emit('ice-candidate', { candidate: event.candidate, to: socketId });
        }
    };

    peer.onconnectionstatechange = () => {
        console.log('ICE connection state:', peer.connectionState);
    };

    return peer;
}


    // Добавляем локальные треки
    localStream.getTracks().forEach(track => peer.addTrack(track, localStream));

    // Когда получаем трек от другого пользователя
    peer.ontrack = event => {
        let remoteVideo = document.getElementById(socketId);
        if (!remoteVideo) {
            remoteVideo = document.createElement('video');
            remoteVideo.id = socketId;
            remoteVideo.autoplay = true;
            videosContainer.appendChild(remoteVideo);
        }
        remoteVideo.srcObject = event.streams[0];
    };

    peer.onicecandidate = event => {
        if (event.candidate) {
            socket.emit('ice-candidate', { candidate: event.candidate, to: socketId, from: socket.id });
        }
    };

    return peer;
}
