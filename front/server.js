const express = require('express');
const app = express();
const http = require('http').createServer(app);
const io = require('socket.io')(http);

app.use(express.static('public'));

io.on('connection', socket => {
    console.log('New user connected');

    socket.on('offer', data => {
        socket.to(data.to).emit('offer', data);
    });

    socket.on('answer', data => {
        socket.to(data.to).emit('answer', data);
    });

    socket.on('ice-candidate', data => {
        socket.to(data.to).emit('ice-candidate', data);
    });

    socket.on('join', room => {
        socket.join(room);
        socket.room = room;
        const otherUsers = Array.from(io.sockets.adapter.rooms.get(room) || []).filter(id => id !== socket.id);
        socket.emit('users', otherUsers);
    });

    socket.on('disconnect', () => {
        console.log('User disconnected');
    });
});

http.listen(3000, () => console.log('Server running on http://localhost:3000'));
