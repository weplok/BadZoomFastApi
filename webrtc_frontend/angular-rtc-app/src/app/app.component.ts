import { Component, ElementRef, OnInit, ViewChild } from '@angular/core';

interface PeerConnectionMap {
  [id: string]: RTCPeerConnection;
}

@Component({
  selector: 'app-root',
  standalone: true,
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css'],
})
export class AppComponent implements OnInit {
  @ViewChild('localVideo') localVideo!: ElementRef<HTMLVideoElement>;

  ws!: WebSocket;
  localStream!: MediaStream;
  remoteStreams: MediaStream[] = [];
  peers: PeerConnectionMap = {};

  videoEnabled = true;
  audioEnabled = true;

  BACKEND_URL = 'ws://localhost:8014/ws'; // или environment variable

  ngOnInit() {
    this.start();
  }

  async start() {
    // 1️⃣ Получаем локальный медиа поток
    try {
      this.localStream = await navigator.mediaDevices.getUserMedia({
        video: true,
        audio: true,
      });
      this.localVideo.nativeElement.srcObject = this.localStream;
    } catch (err) {
      console.error('Error accessing media devices.', err);
      return;
    }

    // 2️⃣ Подключаемся к WebSocket серверу
    this.ws = new WebSocket(this.BACKEND_URL);

    this.ws.onopen = () => console.log('Connected to WebSocket');
    this.ws.onmessage = (msg) => this.handleSignal(JSON.parse(msg.data));
  }

  // 3️⃣ Обработка сигналов
  async handleSignal(data: any) {
    const { type, from, payload } = data;

    // Игнорируем свои сообщения
    if (from === this.wsId) return;

    switch (type) {
      case 'offer':
        await this.createPeer(from, false);
        await this.peers[from].setRemoteDescription(new RTCSessionDescription(payload));
        const answer = await this.peers[from].createAnswer();
        await this.peers[from].setLocalDescription(answer);
        this.ws.send(JSON.stringify({ type: 'answer', to: from, payload: answer }));
        break;

      case 'answer':
        await this.peers[from].setRemoteDescription(new RTCSessionDescription(payload));
        break;

      case 'ice-candidate':
        if (this.peers[from]) {
          await this.peers[from].addIceCandidate(payload);
        }
        break;

      case 'new-peer':
        await this.createPeer(from, true);
        break;
    }
  }

  wsId = crypto.randomUUID(); // уникальный идентификатор клиента

  async createPeer(peerId: string, isInitiator: boolean) {
    if (this.peers[peerId]) return;

    const pc = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }],
    });

    // Отправка ICE кандидатов через WS
    pc.onicecandidate = (event) => {
      if (event.candidate) {
        this.ws.send(
          JSON.stringify({ type: 'ice-candidate', to: peerId, from: this.wsId, payload: event.candidate })
        );
      }
    };

    // Добавляем удалённый поток
    pc.ontrack = (event) => {
      const stream = event.streams[0];
      if (!this.remoteStreams.includes(stream)) this.remoteStreams.push(stream);
    };

    // Добавляем локальные треки
    this.localStream.getTracks().forEach((track) => pc.addTrack(track, this.localStream));

    this.peers[peerId] = pc;

    if (isInitiator) {
      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      this.ws.send(JSON.stringify({ type: 'offer', to: peerId, from: this.wsId, payload: offer }));
    }
  }

  toggleVideo() {
    this.videoEnabled = !this.videoEnabled;
    this.localStream.getVideoTracks().forEach((t) => (t.enabled = this.videoEnabled));
  }

  toggleAudio() {
    this.audioEnabled = !this.audioEnabled;
    this.localStream.getAudioTracks().forEach((t) => (t.enabled = this.audioEnabled));
  }
}
