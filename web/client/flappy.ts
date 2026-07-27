import { loadLeaderboard, submitLeaderboardScore } from './leaderboard.ts';
import { t } from './i18n.ts';

export function initFlappy({ telegram, showScreen }) {
  const canvas = document.getElementById('flappy-canvas') as HTMLCanvasElement;
  const context = canvas.getContext('2d');
  const overlay = document.getElementById('flappy-overlay');
  const scoreElement = document.getElementById('flappy-score');
  const bestElement = document.getElementById('flappy-best');
  const leaderboard = document.getElementById('flappy-leaderboard');
  const open = document.getElementById('open-flappy');
  const leave = document.getElementById('leave-flappy');
  const restart = document.getElementById('restart-flappy');

  let state = null;
  let frame = null;
  let best = Number(localStorage.getItem('cattemis-flappy-best') || 0);
  bestElement.textContent = String(best);

  open.addEventListener('click', () => {
    newGame();
    showScreen('flappy');
  });
  leave.addEventListener('click', () => {
    stop();
    showScreen('menu');
  });
  restart.addEventListener('click', newGame);
  canvas.addEventListener('pointerdown', (event) => {
    event.preventDefault();
    flap();
  });
  document.addEventListener('keydown', (event) => {
    if (document.getElementById('screen-flappy').classList.contains('active') && event.code === 'Space') {
      event.preventDefault();
      flap();
    }
  });
  window.addEventListener('resize', () => {
    if (!state) return;
    sizeCanvas();
    draw();
  });

  function sizeCanvas() {
    const rect = canvas.getBoundingClientRect();
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = Math.round(rect.width * ratio);
    canvas.height = Math.round(rect.height * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    if (state) {
      state.width = rect.width;
      state.height = rect.height;
    }
  }

  function newGame() {
    stop();
    sizeCanvas();
    state = {
      width: canvas.clientWidth,
      height: canvas.clientHeight,
      y: canvas.clientHeight * 0.42,
      velocity: 0,
      pipes: [],
      score: 0,
      running: false,
      over: false,
      spawn: 0,
      last: performance.now(),
    };
    scoreElement.textContent = '0';
    bestElement.textContent = String(best);
    overlay.hidden = false;
    overlay.querySelector('strong').textContent = t('web.game.flappy.start', {}, 'Нажми, чтобы начать');
    overlay.querySelector('span').textContent = t('web.game.flappy.hint', {}, 'тапай по полю и пролети между трубами');
    draw();
    void loadLeaderboard({ telegram, game: 'flappy', difficulty: 'normal', element: leaderboard });
  }

  function flap() {
    if (!state) return;
    if (state.over) newGame();
    if (!state.running) {
      state.running = true;
      state.last = performance.now();
      overlay.hidden = true;
      frame = requestAnimationFrame(update);
    }
    state.velocity = -Math.max(270, state.height * 0.48);
    telegram?.HapticFeedback?.impactOccurred('light');
  }

  function update(now) {
    if (!state?.running) return;
    const delta = Math.min((now - state.last) / 1000, 0.035);
    state.last = now;
    const gravity = Math.max(820, state.height * 1.45);
    const speed = Math.max(115, state.width * 0.34);
    const birdX = state.width * 0.25;
    const radius = Math.max(12, state.width * 0.038);
    state.velocity += gravity * delta;
    state.y += state.velocity * delta;
    state.spawn -= delta;
    if (state.spawn <= 0) {
      const gap = Math.max(105, state.height * 0.25);
      const margin = 65;
      const top = margin + Math.random() * (state.height - gap - margin * 2);
      state.pipes.push({ x: state.width + 25, top, gap, scored: false });
      state.spawn = 1.55;
    }
    state.pipes.forEach((pipe) => {
      pipe.x -= speed * delta;
      if (!pipe.scored && pipe.x + 54 < birdX) {
        pipe.scored = true;
        state.score += 1;
        scoreElement.textContent = String(state.score);
        telegram?.HapticFeedback?.selectionChanged();
      }
    });
    state.pipes = state.pipes.filter((pipe) => pipe.x > -70);
    const collision = state.pipes.some((pipe) =>
      birdX + radius > pipe.x
      && birdX - radius < pipe.x + 54
      && (state.y - radius < pipe.top || state.y + radius > pipe.top + pipe.gap));
    if (collision || state.y + radius >= state.height - 24 || state.y - radius <= 0) {
      endGame();
      return;
    }
    draw();
    frame = requestAnimationFrame(update);
  }

  function endGame() {
    const score = state.score;
    state.running = false;
    state.over = true;
    cancelAnimationFrame(frame);
    frame = null;
    if (score > best) {
      best = score;
      localStorage.setItem('cattemis-flappy-best', String(score));
      bestElement.textContent = String(score);
    }
    overlay.hidden = false;
    overlay.querySelector('strong').textContent = t('web.dynamic.flappy.game_over_score', { score }, `Счёт: ${score}`);
    overlay.querySelector('span').textContent = t('web.dynamic.flappy.retry', {}, 'нажми, чтобы попробовать ещё раз');
    telegram?.HapticFeedback?.notificationOccurred('error');
    draw();
    if (score > 0) {
      void submitLeaderboardScore({
        telegram,
        game: 'flappy',
        difficulty: 'normal',
        seconds: 0,
        score,
        element: leaderboard,
      });
    }
  }

  function stop() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = null;
    if (state) state.running = false;
  }

  function draw() {
    if (!state) return;
    const { width, height } = state;
    const sky = context.createLinearGradient(0, 0, 0, height);
    sky.addColorStop(0, '#76d5ee');
    sky.addColorStop(1, '#d8f5ef');
    context.fillStyle = sky;
    context.fillRect(0, 0, width, height);
    context.fillStyle = 'rgba(255,255,255,.58)';
    for (let index = 0; index < 4; index += 1) {
      const x = (index * width * 0.34 + 35) % (width + 70) - 30;
      const y = 55 + (index % 2) * 70;
      context.beginPath();
      context.arc(x, y, 25, 0, Math.PI * 2);
      context.arc(x + 27, y + 4, 20, 0, Math.PI * 2);
      context.fill();
    }
    state.pipes.forEach((pipe) => {
      context.fillStyle = '#3dbd78';
      context.strokeStyle = '#218b57';
      context.lineWidth = 3;
      context.fillRect(pipe.x, 0, 54, pipe.top);
      context.strokeRect(pipe.x, -3, 54, pipe.top + 3);
      context.fillRect(pipe.x, pipe.top + pipe.gap, 54, height);
      context.strokeRect(pipe.x, pipe.top + pipe.gap, 54, height);
    });
    context.fillStyle = '#5acb72';
    context.fillRect(0, height - 24, width, 24);
    context.fillStyle = '#d8b56c';
    context.fillRect(0, height - 13, width, 13);
    context.save();
    context.translate(width * 0.25, state.y);
    context.rotate(Math.max(-0.35, Math.min(0.7, state.velocity / 650)));
    context.font = `${Math.max(28, width * 0.09)}px sans-serif`;
    context.textAlign = 'center';
    context.textBaseline = 'middle';
    context.fillText('🐈', 0, 0);
    context.restore();
  }
}
