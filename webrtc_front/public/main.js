const socket = io();
const localVideo = document.createElement('video');
localVideo.autoplay = true;
localVideo.muted = true;
localVideo.playsInline = true;

const videosContainer = document.getElementById('videos');
videosContainer.appendChild(localVideo);

let localStream;
let peers = {}; // {socketId: RTCPeerConnection}
let videoEnabled = true;
let audioEnabled = true;

// Функция запроса камеры и микрофона
async function startLocalStream(retry = true) {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localVideo.srcObject = localStream;
        await localVideo.play().catch(err => console.warn("⚠️ Не удалось автозапустить локальное видео:", err));
        console.log("🎥 Камера и микрофон активны");
        socket.emit("ready");
    } catch (err) {
        console.error("❌ Ошибка при получении локальной камеры:", err);
        if (retry) {
            console.log("⏳ Попробуем снова через 15 секунд...");
            setTimeout(() => startLocalStream(false), 15000);
        } else {
            alert("Не удалось получить доступ к камере/микрофону. Проверьте разрешения.");
        }
    }
}

// Запуск камеры сразу для desktop, кнопка для Safari/iOS
if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
    const btn = document.createElement('button');
    btn.innerText = "Включить камеру";
    btn.onclick = () => startLocalStream();
    document.body.appendChild(btn);
} else {
    startLocalStream();
}

// Кнопки управления видео/аудио
const controls = document.createElement('div');
controls.style.margin = "10px";

const videoBtn = document.createElement('button');
videoBtn.innerText = "Выкл видео";
videoBtn.onclick = () => {
    if (!localStream) return;
    videoEnabled = !videoEnabled;
    localStream.getVideoTracks().forEach(track => track.enabled = videoEnabled);
    videoBtn.innerText = videoEnabled ? "Выкл видео" : "Вкл видео";
};

const audioBtn = document.createElement('button');
audioBtn.innerText = "Выкл звук";
audioBtn.onclick = () => {
    if (!localStream) return;
    audioEnabled = !audioEnabled;
    localStream.getAudioTracks().forEach(track => track.enabled = audioEnabled);
    audioBtn.innerText = audioEnabled ? "Выкл звук" : "Вкл звук";
};

controls.appendChild(videoBtn);
controls.appendChild(audioBtn);
document.body.appendChild(controls);

// Создание peerConnection
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

    // Добавляем локальные треки, клонируем поток
    if (localStream) {
        localStream.getTracks().forEach(track => peer.addTrack(track.clone(), localStream));
    } else {
        console.warn("⏳ localStream ещё не готов при создании peerConnection");
    }

    // ICE кандидаты
    peer.onicecandidate = event => {
        if (event.candidate) {
            socket.emit('ice-candidate', { candidate: event.candidate, to: socketId, from: socket.id });
        }
    };

    // Получаем удаленные треки
    peer.ontrack = event => {
        let remoteVideo = document.getElementById(socketId);
        if (!remoteVideo) {
            remoteVideo = document.createElement('video');
            remoteVideo.id = socketId;
            remoteVideo.autoplay = true;
            remoteVideo.playsInline = true;
            videosContainer.appendChild(remoteVideo);
        }
        remoteVideo.srcObject = event.streams[0];
        remoteVideo.play().catch(err => console.warn("⚠️ Не удалось автозапустить remote video:", err));
    };

    // Лог состояния соединения
    peer.onconnectionstatechange = () => {
        console.log(`🔗 ${socketId} connection state:`, peer.connectionState);
    };

    return peer;
}

// Socket.io события
socket.on('new-user', async socketId => {
    console.log("🟢 Новый пользователь:", socketId);
    const peer = createPeerConnection(socketId);
    peers[socketId] = peer;

    try {
        const offer = await peer.createOffer();
        await peer.setLocalDescription(offer);
        socket.emit('offer', { sdp: offer, to: socketId, from: socket.id });
    } catch (err) {
        console.error("❌ Ошибка при создании offer:", err);
    }
});

socket.on('offer', async data => {
    console.log("📩 Получен offer от", data.from);
    const peer = createPeerConnection(data.from);
    peers[data.from] = peer;

    try {
        await peer.setRemoteDescription(data.sdp);
        const answer = await peer.createAnswer();
        await peer.setLocalDescription(answer);
        socket.emit('answer', { sdp: answer, to: data.from, from: socket.id });
    } catch (err) {
        console.error("❌ Ошибка при обработке offer:", err);
    }
});

socket.on('answer', async data => {
    const peer = peers[data.from];
    if (!peer) return;
    try {
        await peer.setRemoteDescription(data.sdp);
    } catch (err) {
        console.error("❌ Ошибка при обработке answer:", err);
    }
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
