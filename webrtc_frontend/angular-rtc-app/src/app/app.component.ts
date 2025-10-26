import { Component, OnInit } from '@angular/core';

interface PeerConnectionMap {
  [id: string]: RTCPeerConnection;
}

@Component({
  selector: 'app-root',
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  localStream!: MediaStream;
  remoteStreams: { [id: string]: MediaStream } = {};
  connections: PeerConnectionMap = {};
  ws!: WebSocket;

  videoEnabled: boolean = true;
  audioEnabled: boolean = true;

  ngOnInit() {
    this.initLocalStream();
    this.initWebSocket();
  }

  async initLocalStream() {
    this.localStream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    const localVideo: any = document.getElementById('localVideo');
    localVideo.srcObject = this.localStream;
  }

  initWebSocket() {
    this.ws = new WebSocket('ws://localhost:8014/ws');

    this.ws.onmessage = async (event) => {
      const data = JSON.parse(event.data);
      const { type, from, sdp, candidate } = data;

      if (from === 'self') return;

      if (!this.connections[from]) this.createPeerConnection(from, false);

      const pc = this.connections[from];

      if (type === 'offer') {
        await pc.setRemoteDescription(new RTCSessionDescription(sdp));
        const answer = await pc.createAnswer();
        await pc.setLocalDescription(answer);
        this.sendSignal({ type: 'answer', sdp: answer, to: from });
      } else if (type === 'answer') {
        await pc.setRemoteDescription(new RTCSessionDescription(sdp));
      } else if (type === 'candidate' && candidate) {
        await pc.addIceCandidate(new RTCIceCandidate(candidate));
      }
    };
  }

  createPeerConnection(id: string, isOfferer: boolean) {
    const pc = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
    });

    this.localStream.getTracks().forEach(track => pc.addTrack(track, this.localStream));

    pc.ontrack = (event) => {
      if (!this.remoteStreams[id]) this.remoteStreams[id] = new MediaStream();
      event.streams[0].getTracks().forEach(track => this.remoteStreams[id].addTrack(track));
      this.updateRemoteVideos();
    };

    pc.onicecandidate = (event) => {
      if (event.candidate) this.sendSignal({ type: 'candidate', candidate: event.candidate, to: id });
    };

    this.connections[id] = pc;

    if (isOfferer) {
      pc.createOffer().then(offer => {
        pc.setLocalDescription(offer);
        this.sendSignal({ type: 'offer', sdp: offer, to: id });
      });
    }
  }

  sendSignal(message: any) {
    this.ws.send(JSON.stringify({ ...message, from: 'self' }));
  }

  updateRemoteVideos() {
    // Привяжем remoteStreams к шаблону
  }

  toggleVideo() {
    this.videoEnabled = !this.videoEnabled;
    this.localStream.getVideoTracks().forEach(t => t.enabled = this.videoEnabled);
  }

  toggleAudio() {
    this.audioEnabled = !this.audioEnabled;
    this.localStream.getAudioTracks().forEach(t => t.enabled = this.audioEnabled);
  }
}
