import { Component, ViewChild, ElementRef, AfterViewInit } from '@angular/core';

@Component({
  selector: 'app-video-call',
  template: `
    <video #localVideo autoplay muted playsinline></video>
    <video #remoteVideo autoplay playsinline></video>
    <button (click)="startCall()">Start Call</button>
  `
})
export class VideoCallComponent implements AfterViewInit {
  @ViewChild('localVideo') localVideo!: ElementRef<HTMLVideoElement>;
  @ViewChild('remoteVideo') remoteVideo!: ElementRef<HTMLVideoElement>;

  private peerConnection!: RTCPeerConnection;
  private ws!: WebSocket;

  async ngAfterViewInit() {
    // Initialize local video stream
    const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
    this.localVideo.nativeElement.srcObject = stream;

    this.peerConnection = new RTCPeerConnection({
      iceServers: [{ urls: 'stun:stun.l.google.com:19302' }]
    });

    stream.getTracks().forEach(track => this.peerConnection.addTrack(track, stream));

    this.peerConnection.ontrack = (event) => {
      this.remoteVideo.nativeElement.srcObject = event.streams[0];
    };

    this.peerConnection.onicecandidate = (event) => {
      if (event.candidate) {
        this.ws.send(JSON.stringify({ candidate: event.candidate }));
      }
    };
  }

  startCall() {
    this.ws = new WebSocket('ws://localhost:8000/ws/client1');
    this.ws.onmessage = async (event) => {
      const message = JSON.parse(event.data);

      if (message.sdp) {
        await this.peerConnection.setRemoteDescription(message);
        if (message.type === 'offer') {
          const answer = await this.peerConnection.createAnswer();
          await this.peerConnection.setLocalDescription(answer);
          this.ws.send(JSON.stringify(this.peerConnection.localDescription));
        }
      } else if (message.candidate) {
        await this.peerConnection.addIceCandidate(message.candidate);
      }
    };

    this.ws.onopen = async () => {
      const offer = await this.peerConnection.createOffer();
      await this.peerConnection.setLocalDescription(offer);
      this.ws.send(JSON.stringify(offer));
    };
  }
}
