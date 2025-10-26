const fs = require('fs');
const https = require('https');
const express = require('express');
const app = express();
const server = https.createServer({
  key: fs.readFileSync('localhost-key.pem'),
  cert: fs.readFileSync('localhost.pem')
}, app);
const io = require('socket.io')(server);

app.use(express.static('public'));

const ROOM = 'main-room';
let users = {};

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

server.listen(3000, () => console.log('HTTPS server on https://localhost:3000'));
