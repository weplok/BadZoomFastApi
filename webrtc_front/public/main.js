const socket = io({
    path: "/webrtc/socket.io"
});

const videosContainer = document.getElementById("videos");

const localVideo = document.createElement("video");
localVideo.autoplay = true;
localVideo.muted = true;
localVideo.playsInline = true;
videosContainer.appendChild(localVideo);

let localStream = null;
let localReady = false;

let peers = {};      // {socketId: RTCPeerConnection}
let senders = {};    // {socketId: {video, audio}}
let makingOffer = {}; // {socketId: boolean}
let politePeer = {};  // {socketId: boolean}

let videoEnabled = true;
let audioEnabled = true;

/* ------------------------------------------------------
    1. Получение камеры и микрофона
------------------------------------------------------ */
async function startLocalStream(retry = true) {
    try {
        localStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: true
        });

        localVideo.srcObject = localStream;
        await localVideo.play().catch(e =>
            console.warn("⚠️ Не удалось автозапустить локальное видео:", e)
        );

        localReady = true;
        console.log("🎥 Локальный стрим готов");
        socket.emit("ready");

        // Если у нас уже есть peer'ы (мы вошли позже), добавим треки в них
        attachLocalTracksToAllPeers();

    } catch (err) {
        console.error("❌ Ошибка камеры:", err);
        if (retry) {
            console.log("⏳ Повтор через 15 секунд");
            setTimeout(() => startLocalStream(false), 15000);
        } else {
            alert("Не удалось получить доступ к камере/микрофону. Проверьте разрешения.");
        }
    }
}

function attachLocalTracksToPeer(peer, socketId) {
    if (!localStream || !peer) return;

    // Если уже есть senders — не добавляем дубликаты
    if (!senders[socketId]) senders[socketId] = { video: null, audio: null };

    localStream.getTracks().forEach(track => {
        // если уже есть sender с этим track.kind — обновим track в sender (replaceTrack) если возможно
        const existing = track.kind === "video" ? senders[socketId].video : senders[socketId].audio;
        if (existing) {
            try {
                existing.replaceTrack(track);
            } catch (e) {
                // fallback: addTrack (в редких случаях)
                const s = peer.addTrack(track, localStream);
                if (track.kind === "video") senders[socketId].video = s;
                if (track.kind === "audio") senders[socketId].audio = s;
            }
        } else {
            const s = peer.addTrack(track, localStream);
            if (track.kind === "video") senders[socketId].video = s;
            if (track.kind === "audio") senders[socketId].audio = s;
        }
    });
}

function attachLocalTracksToAllPeers() {
    Object.keys(peers).forEach(id => {
        try {
            attachLocalTracksToPeer(peers[id], id);
        } catch (e) {
            console.warn("⚠️ Ошибка attachLocalTracksToPeer:", e);
        }
    });
}

if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
    const btn = document.createElement("button");
    btn.innerText = "Включить камеру";
    btn.onclick = () => startLocalStream();
    document.body.appendChild(btn);
} else {
    startLocalStream();
}

/* ------------------------------------------------------
    2. Элементы управления
------------------------------------------------------ */
const controls = document.createElement("div");
controls.style.margin = "10px";

const videoBtn = document.createElement("button");
videoBtn.innerText = "Выкл видео";
videoBtn.onclick = () => {
    if (!localStream) return;
    videoEnabled = !videoEnabled;
    localStream.getVideoTracks().forEach(t => (t.enabled = videoEnabled));
    Object.values(senders).forEach(s => s.video && (s.video.track.enabled = videoEnabled));
    videoBtn.innerText = videoEnabled ? "Выкл видео" : "Вкл видео";
};

const audioBtn = document.createElement("button");
audioBtn.innerText = "Выкл звук";
audioBtn.onclick = () => {
    if (!localStream) return;
    audioEnabled = !audioEnabled;
    localStream.getAudioTracks().forEach(t => (t.enabled = audioEnabled));
    Object.values(senders).forEach(s => s.audio && (s.audio.track.enabled = audioEnabled));
    audioBtn.innerText = audioEnabled ? "Выкл звук" : "Вкл звук";
};

controls.appendChild(videoBtn);
controls.appendChild(audioBtn);
document.body.appendChild(controls);

/* ------------------------------------------------------
    3. Создание PeerConnection
------------------------------------------------------ */
async function createPeerConnection(socketId) {
    const config = await fetch("/webrtc/config").then(r => r.json());
    const configuration = {
        iceServers: [
            { urls: ['stun:stun.l.google.com:19302','stun:stun1.l.google.com:19302'] },
            {
                urls: [config.turnUdp, config.turnTcp, config.turnsUdp, config.turnsTcp],
                username: config.username,
                credential: config.password
            }
        ]
    };

    const peer = new RTCPeerConnection({
        configuration,
        sdpSemantics: "unified-plan"
    });

    peers[socketId] = peer;
    senders[socketId] = { video: null, audio: null };
    makingOffer[socketId] = false;

    // polite: детерминированное сравнение id (строки одинаково сравниваются на обеих сторонах)
    politePeer[socketId] = socket.id > socketId;

    /* ---- Добавляем локальные треки (если уже есть) ---- */
    if (localStream) {
        attachLocalTracksToPeer(peer, socketId);
    }

    /* ---- ICE ---- */
    peer.onicecandidate = e => {
        if (e.candidate) {
            socket.emit("ice-candidate", {
                candidate: e.candidate,
                to: socketId,
                from: socket.id
            });
        }
    };

    /* ---- Remote video ---- */
    peer.ontrack = event => {
        let remoteVideo = document.getElementById(socketId);
        if (!remoteVideo) {
            remoteVideo = document.createElement("video");
            remoteVideo.id = socketId;
            remoteVideo.autoplay = true;
            remoteVideo.playsInline = true;
            videosContainer.appendChild(remoteVideo);
        }

        // используем streams[0] — обычно один stream
        remoteVideo.srcObject = event.streams[0];

        // отложенный play чтобы уменьшить вероятность AbortError
        setTimeout(() => {
            remoteVideo.play().catch(err =>
                console.warn("⚠️ Не удалось play() remote video:", err)
            );
        }, 50);
    };

    /* ---- Negotiation ---- */
    peer.onnegotiationneeded = async () => {
        console.log("🟡 onnegotiationneeded →", socketId);

        // защищаемся от коллизий: не отправляем offer, если уже делаем offer
        if (makingOffer[socketId]) {
            console.log("    already making offer для", socketId);
            return;
        }

        try {
            makingOffer[socketId] = true;
            const offer = await peer.createOffer();
            await peer.setLocalDescription(offer);

            socket.emit("offer", {
                sdp: peer.localDescription,
                to: socketId,
                from: socket.id
            });

        } catch (e) {
            console.warn("❌ Ошибка negotiation:", e);
        } finally {
            makingOffer[socketId] = false;
        }
    };

    peer.onconnectionstatechange = () => {
        console.log(`🔗 ${socketId} = ${peer.connectionState}`);
    };

    return peer;
}

/* ------------------------------------------------------
    4. Socket.io signaling
------------------------------------------------------ */

function waitLocalReady() {
    return new Promise(resolve => {
        if (localReady) return resolve();
        const i = setInterval(() => {
            if (localReady) {
                clearInterval(i);
                resolve();
            }
        }, 50);
    });
}

/* ---- new user ----
   ВАЖНО: не создаём offer тут — только создаём PeerConnection.
   Оффер создастся через onnegotiationneeded после attachLocalTracks.
*/
socket.on("new-user", async socketId => {
    console.log("🟢 Новый пользователь:", socketId);

    await waitLocalReady();

    await createPeerConnection(socketId);
});

/* ---- incoming offer ---- */
socket.on("offer", async data => {
    await waitLocalReady();

    const socketId = data.from;
    const desc = data.sdp;

    const peer = await createPeerConnection(socketId);

    const offerCollision =
        desc.type === "offer" &&
        (makingOffer[socketId] || peer.signalingState !== "stable");

    const ignoreOffer = !politePeer[socketId] && offerCollision;

    if (ignoreOffer) {
        console.log("🚫 Игнорируем offer от", socketId);
        return;
    }

    try {
        if (offerCollision) {
            console.log("🔁 rollback (collision) от", socketId);
            // rollback + применить remote desc
            await Promise.all([
                peer.setLocalDescription({ type: "rollback" }),
                peer.setRemoteDescription(desc)
            ]);
        } else {
            await peer.setRemoteDescription(desc);
        }

        if (desc.type === "offer") {
            const answer = await peer.createAnswer();
            await peer.setLocalDescription(answer);

            socket.emit("answer", {
                sdp: answer,
                to: socketId,
                from: socket.id
            });
        }

    } catch (err) {
        console.error("❌ Ошибка обработки offer:", err);
    }
});

/* ---- answer ---- */
socket.on("answer", async data => {
    const peer = peers[data.from];
    if (!peer) return;

    try {
        await peer.setRemoteDescription(data.sdp);
    } catch (err) {
        console.error("❌ Ошибка обработки answer:", err);
    }
});

/* ---- ice ---- */
socket.on("ice-candidate", async data => {
    const peer = peers[data.from];
    if (!peer) return;

    try {
        await peer.addIceCandidate(data.candidate);
    } catch (err) {
        console.warn("⚠️ ICE ошибка:", err);
    }
});

/* ---- disconnect ---- */
socket.on("user-disconnected", socketId => {
    console.log("🔴 отключился:", socketId);

    if (peers[socketId]) {
        peers[socketId].close();
        delete peers[socketId];
        delete senders[socketId];
        delete makingOffer[socketId];
        delete politePeer[socketId];
    }

    const vid = document.getElementById(socketId);
    if (vid) vid.remove();
});
