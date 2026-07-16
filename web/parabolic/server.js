'use strict';

const express = require('express');
const http = require('http');
const WebSocket = require('ws');
const path = require('path');
const { createGame } = require('./state');

const app = express();
app.use(express.static(path.join(__dirname, 'public')));

const server = http.createServer(app);
const wss = new WebSocket.Server({ server });

const rooms = new Map();
let publicQueue = [];
let clientCount = 0;

function genCode() {
  const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
  let code = '';
  for (let i = 0; i < 4; i++) code += chars[Math.floor(Math.random() * chars.length)];
  return rooms.has(code) ? genCode() : code;
}

function send(ws, obj) {
  if (ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj));
}

function broadcast(room, obj) {
  for (const p of room.players) send(p.ws, obj);
}

function cleanPublicQueue() {
  publicQueue = publicQueue.filter(client => client.readyState === WebSocket.OPEN && !client._roomCode);
}

function broadcastLobbyState() {
  cleanPublicQueue();
  for (const client of wss.clients) send(client, { type: 'lobbyState', waiting: publicQueue.length });
}

function startGame(room) {
  room.game = createGame();
  const state = room.game.getState({ status: null });
  const code = room.players[0].ws._roomCode;
  console.log(`[${code}] game started - white: ${room.players[0].ws._id}, black: ${room.players[1].ws._id}`);
  for (const p of room.players) {
    send(p.ws, { type: 'start', color: p.color, code });
    send(p.ws, { type: 'state', ...state });
  }
}

function createRoom(ws1, ws2, code) {
  const room = {
    players: [
      { ws: ws1, color: 'white', wantsRematch: false },
      { ws: ws2, color: 'black', wantsRematch: false },
    ],
    game: null,
  };
  rooms.set(code, room);
  ws1._roomCode = code;
  ws2._roomCode = code;
  console.log(`[${code}] room created - ${ws1._id} + ${ws2._id}`);
  startGame(room);
}

wss.on('connection', ws => {
  ws._roomCode = null;
  ws._id = 'client-' + (++clientCount);
  console.log(`[connect] ${ws._id} (total: ${wss.clients.size})`);

  ws.on('message', raw => {
    let msg;
    try { msg = JSON.parse(raw); } catch { return; }

    if (msg.type === 'lobby') {
      cleanPublicQueue();
      send(ws, { type: 'lobbyState', waiting: publicQueue.length });
      return;
    }

    if (msg.type === 'join') {
      const wantsCode = msg.code ? msg.code.toUpperCase().trim() : null;

      if (msg.public || msg.random) {
        cleanPublicQueue();
        publicQueue = publicQueue.filter(client => client !== ws);
        const other = publicQueue.shift();
        if (other) {
          const code = genCode();
          console.log(`[public] matched ${other._id} + ${ws._id}`);
          createRoom(other, ws, code);
        } else {
          publicQueue.push(ws);
          console.log(`[public] ${ws._id} queued, waiting for opponent...`);
          send(ws, { type: 'waiting', public: true });
        }
        broadcastLobbyState();
        return;
      }

      if (wantsCode) {
        if (rooms.has(wantsCode)) {
          const room = rooms.get(wantsCode);
          if (room.players.length === 1) {
            room.players.push({ ws, color: 'black', wantsRematch: false });
            ws._roomCode = wantsCode;
            console.log(`[${wantsCode}] ${ws._id} joined room`);
            startGame(room);
          } else {
            console.log(`[${wantsCode}] ${ws._id} tried to join full room`);
            send(ws, { type: 'error', message: 'Room is full or already started.' });
          }
        } else {
          const room = { players: [{ ws, color: 'white', wantsRematch: false }], game: null };
          rooms.set(wantsCode, room);
          ws._roomCode = wantsCode;
          console.log(`[${wantsCode}] ${ws._id} created room, waiting...`);
          send(ws, { type: 'waiting', code: wantsCode });
        }
      }
      return;
    }

    if (msg.type === 'moveRequest') {
      const room = ws._roomCode ? rooms.get(ws._roomCode) : null;
      if (!room || !room.game) return;
      const player = room.players.find(p => p.ws === ws);
      if (!player) return;

      const ok = room.game.applyMoveRequest({
        color: player.color,
        from:  msg.from,
        to:    msg.to,
        promo: msg.promo || null,
      });

      if (!ok) {
        console.log(`[${ws._roomCode}] illegal move from ${ws._id} (${player.color}): ${msg.from}->${msg.to}`);
        return;
      }

      const status = room.game.checkGameOver();
      console.log(`[${ws._roomCode}] move ${msg.from}->${msg.to} by ${ws._id} (${player.color})${status ? ' — ' + status : ''}`);
      const state = room.game.getState({ status });
      broadcast(room, { type: 'state', ...state });

      if (status) {
        for (const p of room.players) p.wantsRematch = false;
      }
      return;
    }

    if (msg.type === 'rematch') {
      const room = ws._roomCode ? rooms.get(ws._roomCode) : null;
      if (!room) return;
      const player = room.players.find(p => p.ws === ws);
      if (!player) return;
      player.wantsRematch = true;
      console.log(`[${ws._roomCode}] ${ws._id} wants rematch`);

      const other = room.players.find(p => p.ws !== ws);
      if (!other) return;

      if (other.wantsRematch) {
        console.log(`[${ws._roomCode}] rematch accepted — swapping colors`);
        for (const p of room.players) {
          p.color = p.color === 'white' ? 'black' : 'white';
          p.wantsRematch = false;
        }
        startGame(room);
      } else {
        send(other.ws, { type: 'rematchOffer' });
      }
      return;
    }
  });

  ws.on('close', () => {
    const queued = publicQueue.includes(ws);
    publicQueue = publicQueue.filter(client => client !== ws);
    if (queued) {
      console.log(`[public] ${ws._id} left queue`);
      broadcastLobbyState();
    }

    const code = ws._roomCode;
    if (!code) { console.log(`[disconnect] ${ws._id} (was in lobby)`); return; }

    console.log(`[${code}] ${ws._id} disconnected`);
    const room = rooms.get(code);
    if (!room) return;

    const other = room.players.find(p => p.ws !== ws);
    if (other && other.ws.readyState === WebSocket.OPEN) {
      other.ws._roomCode = null;
      send(other.ws, { type: 'opponentDisconnected' });
    }

    rooms.delete(code);
    console.log(`[${code}] room closed (${rooms.size} rooms active)`);
  });
});

const PORT = process.env.PORT || 3000;
server.listen(PORT, "0.0.0.0", () => console.log(`Serving on port ${PORT}`));
