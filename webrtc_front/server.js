const express = require('express');
const app = express();
const http = require('http').createServer(app);
const io = require('socket.io')(http, {
    path: '/webrtc/socket.io'
});
const CryptoJS = require("crypto-js");

app.use(express.static('public'));

const ROOM = 'main-room';
let users = {};

function generateTurnCredentials(realm, secret) {
  // <timestamp>:<realm>
  const username = `${Math.floor(Date.now() / 1000)}:${realm}`;

  // HMAC-SHA1(username, secret) → Base64
  const password = CryptoJS.HmacSHA1(username, secret)
    .toString(CryptoJS.enc.Base64);

  return { username, password };
}

app.get("/config", (req, res) => {

  const creds = generateTurnCredentials(process.env.TURN_REALM, process.env.TURN_SECRET);

  res.json({
    turnUdp: process.env.TURN_URL_UDP,
    turnTcp: process.env.TURN_URL_TCP,
    turnsUdp: process.env.TURNS_URL_UDP,
    turnsTcp: process.env.TURNS_URL_TCP,

    username: creds.username,
    password: creds.password
  });
});

io.on('connection', socket => {
    console.log('New user connected:', socket.id);
    users[socket.id] = socket;

    // Отправляем всем существующим пользователям id нового
    socket.broadcast.emit('new-user', socket.id);

    // Когда получаем offer от нового пользователя
    socket.on('offer', data => {
        if (users[data.to]) {
            users[data.to].emit('offer', data);
        }
    });

    socket.on('answer', data => {
        if (users[data.to]) {
            users[data.to].emit('answer', data);
        }
    });

    socket.on('ice-candidate', data => {
        if (users[data.to]) {
            users[data.to].emit('ice-candidate', data);
        }
    });

    socket.on('disconnect', () => {
        console.log('User disconnected:', socket.id);
        delete users[socket.id];
        socket.broadcast.emit('user-disconnected', socket.id);
    });
});

http.listen(3000, () => console.log('Server running on http://localhost:3000'));
