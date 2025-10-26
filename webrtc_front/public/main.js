const socket = io();
const localVideo = document.createElement('video');
localVideo.autoplay = true;
localVideo.muted = true;

const videosContainer = document.getElementById('videos');
videosContainer.appendChild(localVideo);

let localStream;
let peers = {}; // {socketId: RTCPeerConnection}

// Запрашиваем камеру и микрофон
async function start() {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localVideo.srcObject = localStream;
        console.log("✅ Камера и микрофон успешно получены");
        socket.emit("ready"); // уведомляем сервер, что готовы подключаться
    } catch (err) {
        console.error("❌ Ошибка доступа к камере или микрофону:", err);
    }
}

start();

// Новый пользователь подключился
socket.on('new-user', async socketId => {
    console.log("🟢 Новый пользователь:", socketId);
    const peer = createPeerConnection(socketId);
    peers[socketId] = peer;

    const offer = await peer.createOffer();
    await peer.setLocalDescription(offer);
    socket.emit('offer', { sdp: offer, to: socketId, from: socket.id });
});

socket.on('offer', async data => {
    console.log("📩 Получен offer от", data.from);
    const peer = createPeerConnection(data.from);
    peers[data.from] = peer;

    await peer.setRemoteDescription(data.sdp);
    const answer = await peer.createAnswer();
    await peer.setLocalDescription(answer);
    socket.emit('answer', { sdp: answer, to: data.from, from: socket.id });
});

socket.on('answer', async data => {
    console.log("📩 Получен answer от", data.from);
    const peer = peers[data.from];
    if (!peer) return;
    await peer.setRemoteDescription(data.sdp);
});

socket.on('ice-candidate', async data => {
    const peer = peers[data.from];
    if (!peer) return;
    try {
        await peer.addIceCandidate(data.candidate);
    } catch (err) {
        console.warn("⚠️ Ошибка при добавлении ICE:", err);
    }
});

socket.on('user-disconnected', socketId => {
    console.log("🔴 Пользователь отключился:", socketId);
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
            { urls: 'stun:stun.l.google.com:19302' },
            {
                urls: [
                    'turn:weplok.ru:8347?transport=udp',
                    'turn:weplok.ru:8347?transport=tcp'
                ],
                username: 'weplok',
                credential: 'weplok'
            }
        ],
        iceCandidatePoolSize: 10
    });

    // Добавляем локальные треки
    if (localStream) {
        localStream.getTracks().forEach(track => peer.addTrack(track, localStream));
    } else {
        console.warn("⚠️ localStream ещё не готов при создании peerConnection");
    }

    // Обработка ICE кандидатов
    peer.onicecandidate = event => {
        if (event.candidate) {
            socket.emit('ice-candidate', {
                candidate: event.candidate,
                to: socketId,
                from: socket.id
            });
        }
    };

    // Получаем поток от другого пользователя
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

    peer.onconnectionstatechange = () => {
        console.log(`🔗 ${socketId} connection state:`, peer.connectionState);
    };

    return peer;
}
