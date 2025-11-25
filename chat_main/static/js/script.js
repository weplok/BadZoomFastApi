const ws = new WebSocket(`ws://${location.host}/main/ws`);
const messagesDiv = document.getElementById('messages');
const input = document.getElementById('messageInput');
const sendBtn = document.getElementById('sendBtn');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (document.getElementById(msg.htmlid)) {
        const p = document.getElementById(msg.htmlid);
        p.textContent = `${msg.sender}: ${msg.text}`;
    } else {
        const p = document.createElement('p');
        p.id = msg.htmlid;
        p.textContent = `${msg.sender}: ${msg.text}`;
        messagesDiv.appendChild(p);
    }
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
};

function sendMessage() {
  const text = input.value.trim();
  if (text) {
    ws.send(text);
    input.value = '';
    input.focus();
  }
}

sendBtn.onclick = sendMessage;

input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    sendMessage();
  }
});

input.focus();