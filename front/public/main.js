const socket = io();
let localStream, peerConnection;
let myId;

const configuration = { iceServers: [{ urls: 'stun:stun.l.google.com:19302' }] };

const localVideo = document.getElementById('localVideo');
const remoteVideo = document.getElementById('remoteVideo');
const joinBtn = document.getElementById('joinBtn');
const roomInput = document.getElementById('room');

joinBtn.onclick = async () => {
    const room = roomInput.value.trim();
    if (!room) return alert('Enter room ID');

    await startLocalStream();
    socket.emit('join', room);
};

async function startLocalStream() {
    localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    localVideo.srcObject = localStream;
}

socket.on('users', users => {
    if (users.length > 0) {
        // Создаем peerConnection и вызываем первого пользователя
        myId = socket.id;
        createPeerConnection();
        peerConnection.createOffer()
            .then(offer => peerConnection.setLocalDescription(offer))
            .then(() => {
                socket.emit('offer', { sdp: peerConnection.localDescription, to: users[0] });
            });
    } else {
        myId = socket.id;
        createPeerConnection();
    }
});

function createPeerConnection() {
    peerConnection = new RTCPeerConnection(configuration);

    peerConnection.onicecandidate = event => {
        if (event.candidate) {
            socket.emit('ice-candidate', { candidate: event.candidate, to: null }); // broadcast
        }
    };

    peerConnection.ontrack = event => {
        remoteVideo.srcObject = event.streams[0];
    };

    localStream.getTracks().forEach(track => peerConnection.addTrack(track, localStream));
}

socket.on('offer', async data => {
    createPeerConnection();
    await peerConnection.setRemoteDescription(data.sdp);
    const answer = await peerConnection.createAnswer();
    await peerConnection.setLocalDescription(answer);
    socket.emit('answer', { sdp: answer, to: data.from });
});

socket.on('answer', async data => {
    await peerConnection.setRemoteDescription(data.sdp);
});

socket.on('ice-candidate', async data => {
    try {
        await peerConnection.addIceCandidate(data.candidate);
    } catch (e) {
        console.error(e);
    }
});
