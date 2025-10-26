const socket = io();

// Контейнеры и видео
const videosContainer = document.getElementById('videos');
const localVideo = document.createElement('video');
localVideo.autoplay = true;
localVideo.muted = true;
localVideo.playsInline = true;

// Храним peerConnection и отправляемые треки
let localStream;
let peers = {};   // {socketId: RTCPeerConnection}
let senders = {}; // {socketId: {video: RTCRtpSender, audio: RTCRtpSender}}
let videoEnabled = true;
let audioEnabled = true;

videosContainer.appendChild(localVideo);

// --- Функции работы с индикаторами ---
function addRemoteVideo(socketId, stream) {
    let container = document.getElementById(`container-${socketId}`);
    if (!container) {
        container = document.createElement('div');
        container.id = `container-${socketId}`;
        container.style.position = 'relative';
        container.style.display = 'inline-block';
        container.style.margin = '5px';
        container.style.width = '200px';
        container.style.height = '150px';

        const video = document.createElement('video');
        video.id = `video-${socketId}`;
        video.autoplay = true;
        video.playsInline = true;
        video.style.width = '100%';
        video.style.height = '100%';
        container.appendChild(video);

        const camIcon = document.createElement('span');
        camIcon.id = `cam-${socketId}`;
        camIcon.innerText = '👽';
        camIcon.style.position = 'absolute';
        camIcon.style.top = '5px';
        camIcon.style.left = '5px';
        camIcon.style.fontSize = '50px';
        container.appendChild(camIcon);

        const micIcon = document.createElement('span');
        micIcon.id = `mic-${socketId}`;
        micIcon.innerText = '🔇';
        micIcon.style.position = 'absolute';
        micIcon.style.top = '5px';
        micIcon.style.right = '5px';
        micIcon.style.fontSize = '18px';
        container.appendChild(micIcon);

        videosContainer.appendChild(container);
    }

    const video = document.getElementById(`video-${socketId}`);
    video.srcObject = stream;
    video.play().catch(err => console.warn("⚠️ Не удалось автозапустить video:", err));

    updateIndicators(socketId, stream);
}

function updateIndicators(socketId, stream) {
    const camIcon = document.getElementById(`cam-${socketId}`);
    const micIcon = document.getElementById(`mic-${socketId}`);
    const videoTrack = stream.getVideoTracks()[0];
    const audioTrack = stream.getAudioTracks()[0];
    if (camIcon) camIcon.style.opacity = videoTrack && videoTrack.enabled ? '0' : '1';
    if (micIcon) micIcon.style.opacity = audioTrack && audioTrack.enabled ? '0' : '1';
}

function updateLocalIndicators() {
    if (localStream) addRemoteVideo('local', localStream);
}

// --- Функция запуска камеры/микрофона с повторной попыткой ---
async function startLocalStream(retry = true) {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        localVideo.srcObject = localStream;
        await localVideo.play().catch(err => console.warn("⚠️ Не удалось автозапустить локальное видео:", err));
        console.log("🎥 Камера и микрофон активны");
        addRemoteVideo('local', localStream);
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

// --- Автозапуск или кнопка для iOS ---
if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
    const btn = document.createElement('button');
    btn.innerText = "Включить камеру";
    btn.onclick = () => startLocalStream();
    document.body.appendChild(btn);
} else {
    startLocalStream();
}

// --- Кнопки управления видео/аудио ---
const controls = document.createElement('div');
controls.style.margin = "10px";

const videoBtn = document.createElement('button');
videoBtn.innerText = "Выкл видео";
videoBtn.onclick = () => {
    if (!localStream) return;
    videoEnabled = !videoEnabled;
    localStream.getVideoTracks().forEach(track => track.enabled = videoEnabled);
    Object.values(senders).forEach(s => { if (s.video) s.video.track.enabled = videoEnabled; });
    videoBtn.innerText = videoEnabled ? "Выкл видео" : "Вкл видео";
    updateLocalIndicators();
};

const audioBtn = document.createElement('button');
audioBtn.innerText = "Выкл звук";
audioBtn.onclick = () => {
    if (!localStream) return;
    audioEnabled = !audioEnabled;
    localStream.getAudioTracks().forEach(track => track.enabled = audioEnabled);
    Object.values(senders).forEach(s => { if (s.audio) s.audio.track.enabled = audioEnabled; });
    audioBtn.innerText = audioEnabled ? "Выкл звук" : "Вкл звук";
    updateLocalIndicators();
};

controls.appendChild(videoBtn);
controls.appendChild(audioBtn);
document.body.appendChild(controls);

// --- Создание peerConnection ---
function createPeerConnection(socketId) {
    const peer = new RTCPeerConnection({
        iceServers: [
            { urls: 'stun:stun.l.google.com:19302' },
            { urls: ['turn:weplok.ru:8347?transport=udp','turn:weplok.ru:8347?transport=tcp'], username: 'weplok', credential: 'weplok' }
        ],
        iceCandidatePoolSize: 10
    });

    senders[socketId] = { video: null, audio: null };

    if (localStream) {
        localStream.getTracks().forEach(track => {
            const sender = peer.addTrack(track.clone(), localStream);
            if (track.kind === 'video') senders[socketId].video = sender;
            if (track.kind === 'audio') senders[socketId].audio = sender;
        });
    }

    peer.onicecandidate = event => {
        if (event.candidate) {
            socket.emit('ice-candidate', { candidate: event.candidate, to: socketId, from: socket.id });
        }
    };

    peer.ontrack = event => addRemoteVideo(socketId, event.streams[0]);
    peer.onconnectionstatechange = () => console.log(`🔗 ${socketId} state:`, peer.connectionState);

    return peer;
}

// --- Socket.io события ---
socket.on('new-user', async socketId => {
    const peer = createPeerConnection(socketId);
    peers[socketId] = peer;
    try {
        const offer = await peer.createOffer();
        await peer.setLocalDescription(offer);
        socket.emit('offer', { sdp: offer, to: socketId, from: socket.id });
    } catch (err) { console.error(err); }
});

socket.on('offer', async data => {
    const peer = createPeerConnection(data.from);
    peers[data.from] = peer;
    try {
        await peer.setRemoteDescription(data.sdp);
        const answer = await peer.createAnswer();
        await peer.setLocalDescription(answer);
        socket.emit('answer', { sdp: answer, to: data.from, from: socket.id });
    } catch (err) { console.error(err); }
});

socket.on('answer', async data => {
    const peer = peers[data.from];
    if (!peer) return;
    try { await peer.setRemoteDescription(data.sdp); } catch (err) { console.error(err); }
});

socket.on('ice-candidate', async data => {
    const peer = peers[data.from];
    if (!peer) return;
    try { await peer.addIceCandidate(data.candidate); } catch (err) { console.warn(err); }
});

socket.on('user-disconnected', socketId => {
    if (peers[socketId]) peers[socketId].close();
    delete peers[socketId];
    delete senders[socketId];
    const container = document.getElementById(`container-${socketId}`);
    if (container) container.remove();
});
