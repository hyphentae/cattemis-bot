(function () {
  'use strict';

  var overlay = document.createElement('div');
  overlay.className = 'network-overlay';
  document.body.appendChild(overlay);

  function setOverlay(html, show) {
    overlay.innerHTML = `<div class="net-card">${html}</div>`;
    overlay.style.display = show === false ? 'none' : 'flex';
  }

  function btn(label, id) {
    return `<button class="net-button" id="${id}">${label}</button>`;
  }

  function input(placeholder, id) {
    return `<input class="net-input" id="${id}" maxlength="4" placeholder="${placeholder}">`;
  }

  function showLobby() {
    setOverlay(`
      <div class="net-title">Parabolic Chess</div>
      <div class="net-copy">хозяин, найдём соперника? поле уже свернулось owo</div>
      ${btn('войти в публичное лобби', 'btn-public')}
      <div class="net-copy" id="public-count">сейчас никто не ждёт — станешь первым :3</div>
      <div class="net-copy">или введи кодик комнаты</div>
      ${input('КОД', 'code-input')}
      ${btn('создать или войти :3', 'btn-code')}
    `);
    document.getElementById('btn-public').onclick = () => ws_join({ publicLobby: true });
    document.getElementById('btn-code').onclick = () => {
      var code = document.getElementById('code-input').value.trim().toUpperCase();
      ws_join({ code: code || genLocalCode() });
    };
    document.getElementById('code-input').onkeydown = e => {
      if (e.key === 'Enter') document.getElementById('btn-code').click();
    };
    if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify({ type: 'lobby' }));
  }

  function genLocalCode() {
    return Math.random().toString(36).slice(2,6).toUpperCase();
  }

  var ws;
  var myColor = null;

  function connect() {
    var proto = location.protocol === 'https:' ? 'wss' : 'ws';
    ws = new WebSocket(`${proto}://${location.host}/parabolic-ws`);

    ws.onopen = () => {
      var invitedRoom = new URLSearchParams(location.hash.slice(1)).get('room');
      if (invitedRoom) ws_join({ code: invitedRoom.toUpperCase() });
      else showLobby();
    };

    ws.onmessage = function (e) {
      var msg = JSON.parse(e.data);

      if (msg.type === 'lobbyState') {
        var count = document.getElementById('public-count');
        if (count) {
          count.textContent = msg.waiting
            ? `игроков в ожидании: ${msg.waiting}`
            : 'сейчас никто не ждёт — станешь первым :3';
        }
        return;
      }

      if (msg.type === 'waiting') {
        setOverlay(`
          <div>ждём соперника, хозяин...</div>
          ${msg.code ? `
            <div class="net-copy">отправь этот кодик другу:</div>
            <div class="net-code">
              ${msg.code}
            </div>
          ` : '<div class="net-copy">ты в публичной очереди :3</div>'}
          ${btn('назад в лобби', 'btn-lobby')}
        `);
        document.getElementById('btn-lobby').onclick = () => location.reload();
        return;
      }

      if (msg.type === 'start') {
        myColor = msg.color;
        window.myColor = myColor;
        var colorLabel = myColor === 'white' ? '⬜ белых' : '⬛ чёрных';
        setOverlay(`<div>начинаем, хозяин :3</div><div class="net-copy">ты играешь за <b>${colorLabel}</b></div>`, false);
        setTimeout(() => setOverlay('', false), 1800);
        return;
      }

      if (msg.type === 'state') {
        window.applyServerState(msg);
        if (msg.status) showGameOver(msg.status);
        return;
      }

      if (msg.type === 'rematchOffer') {
        setOverlay(`
          <div>соперник просит реванш, хозяин!</div>
          ${btn('ещё партию :3', 'btn-rematch-yes')}
          ${btn('не сейчас', 'btn-rematch-no')}
        `);
        document.getElementById('btn-rematch-yes').onclick = () => {
          ws.send(JSON.stringify({ type: 'rematch' }));
          setOverlay('<div>ждём новую партию, мяу...</div>');
        };
        document.getElementById('btn-rematch-no').onclick = () => setOverlay('', false);
        return;
      }

      if (msg.type === 'opponentDisconnected') {
        setOverlay(`
          <div>соперник убежал... только мы остались, хозяин T_T</div>
          ${btn('назад в лобби', 'btn-lobby')}
        `);
        document.getElementById('btn-lobby').onclick = () => {
          myColor = null; window.myColor = null;
          showLobby();
        };
        return;
      }

      if (msg.type === 'error') {
        setOverlay(`
          <div class="net-error">ой, хозяин... ${msg.message}</div>
          ${btn('назад', 'btn-back')}
        `);
        document.getElementById('btn-back').onclick = showLobby;
        return;
      }
    };

    ws.onclose = () => {
      if (overlay.style.display === 'none') {
        setOverlay(`
          <div>связь потерялась, хозяин... T_T</div>
          ${btn('подключиться снова', 'btn-reconnect')}
        `);
        document.getElementById('btn-reconnect').onclick = () => { myColor = null; window.myColor = null; connect(); };
      }
    };
  }

  function ws_join({ publicLobby = false, code = null } = {}) {
    if (publicLobby) {
      setOverlay('<div>ищу соперника, хозяин... :3</div>'); // no code shown
      ws.send(JSON.stringify({ type: 'join', public: true }));
    } else {
      setOverlay('<div>открываю комнату лапкой...</div>');
      ws.send(JSON.stringify({ type: 'join', code }));
    }
  }

  function showGameOver(status) {
    var msg;
    if (status === 'draw')            msg = 'ничья, хозяин... вот это партия owo';
    else if (status === 'white_wins') msg = myColor === 'white' ? 'хозяин победил! :3' : 'мы проиграли... реванш?';
    else                              msg = myColor === 'black' ? 'хозяин победил! :3' : 'мы проиграли... реванш?';

    setOverlay(`
      <div class="net-title">${msg}</div>
      ${btn('реванш', 'btn-rematch')}
      ${btn('назад в лобби', 'btn-lobby')}
    `);
    document.getElementById('btn-rematch').onclick = () => {
      ws.send(JSON.stringify({ type: 'rematch' }));
      setOverlay('<div>ждём ответа соперника, хозяин...</div>');
    };
    document.getElementById('btn-lobby').onclick = () => {
      myColor = null; window.myColor = null;
      showLobby();
    };
  }

  window._netMove = function (move) {
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    if (!myColor) return;
    ws.send(JSON.stringify({
      type:  'moveRequest',
      from:  move.from,
      to:    move.to,
      promo: move.promo || null,
    }));
  };

  connect();
})();
