const socket = io();
const videosContainer = document.getElementById('videos');

let localStream;
let peers = {};   // {socketId: RTCPeerConnection}
let senders = {}; // {socketId: {video: RTCRtpSender, audio: RTCRtpSender}}
let videoEnabled = true;
let audioEnabled = true;

// --- Кнопки управления ---
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
    socket.emit('media-status-changed', { video: videoEnabled, audio: audioEnabled });
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
    socket.emit('media-status-changed', { video: videoEnabled, audio: audioEnabled });
};

controls.appendChild(videoBtn);
controls.appendChild(audioBtn);
document.body.appendChild(controls);

// --- Запуск локального потока с повторной попыткой ---
async function startLocalStream(retry = true) {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
        socket.emit("ready");
    } catch (err) {
        console.warn("Ошибка получения камеры/микрофона:", err);
        if (retry) setTimeout(() => startLocalStream(false), 15000);
        else alert("Не удалось получить доступ к камере/микрофону.");
    }
}
startLocalStream();

// --- Работа с видео сеткой и индикаторами ---
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

        const videoIcon = document.createElement('div');
        videoIcon.id = `video-icon-${socketId}`;
        videoIcon.style.position = 'absolute';
        videoIcon.style.top = '50%';
        videoIcon.style.left = '50%';
        videoIcon.style.transform = 'translate(-50%, -50%)';
        videoIcon.style.fontSize = '50px';
        container.appendChild(videoIcon);

        const micIcon = document.createElement('span');
        micIcon.id = `mic-${socketId}`;
        micIcon.style.position = 'absolute';
        micIcon.style.bottom = '5px';
        micIcon.style.right = '5px';
        micIcon.style.fontSize = '18px';
        container.appendChild(micIcon);

        videosContainer.appendChild(container);
    }

    const video = document.getElementById(`video-${socketId}`);
    video.srcObject = stream;
    video.play().catch(() => {});

    updateIndicators(socketId, stream);
}

function updateIndicators(socketId, stream) {
    const videoIcon = document.getElementById(`video-icon-${socketId}`);
    const micIcon = document.getElementById(`mic-${socketId}`);

    const videoTrack = stream.getVideoTracks()[0];
    const audioTrack = stream.getAudioTracks()[0];

    videoIcon.innerText = (videoTrack && !videoTrack.enabled) ? '👤' : '';
    micIcon.innerText = (audioTrack && !audioTrack.enabled) ? '🔇' : '';
}

function updateLocalIndicators() {
    if (localStream) updateIndicators('local', localStream);
    Object.keys(peers).forEach(id => {
        const peer = peers[id];
        const streams = peer.getSenders().map(s => s.track).filter(Boolean);
        const streamObj = new MediaStream(streams);
        updateIndicators(id, streamObj);
    });
}

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
        if (event.candidate) socket.emit('ice-candidate', { candidate: event.candidate, to: socketId, from: socket.id });
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

// --- Синхронизация медиа-статусов ---
socket.on('peer-media-status', data => {
    const { id, video, audio } = data;
    const videoIcon = document.getElementById(`video-icon-${id}`);
    const micIcon = document.getElementById(`mic-${id}`);
    if (videoIcon) videoIcon.innerText = video ? '' : '👤';
    if (micIcon) micIcon.innerText = audio ? '' : '🔇';
});
