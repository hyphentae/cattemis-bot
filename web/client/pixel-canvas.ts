import { hasTelegramAuth, telegramAuthHeaders } from './telegram-auth.ts';

const PALETTE = [
  '#ffffff', '#11111b', '#6c7086', '#cdd6f4',
  '#f5e0dc', '#f38ba8', '#fab387', '#f9e2af',
  '#a6e3a1', '#94e2d5', '#89dceb', '#74c7ec',
  '#89b4fa', '#b4befe', '#cba6f7', '#f5c2e7',
];
const POLL_MS = 2000;
const MIN_ZOOM = 0.5;
const MAX_ZOOM = 40;

export function initPixelCanvas({ telegram, showScreen }) {
  const elements = {
    open: document.getElementById('open-pixel-canvas'),
    leave: document.getElementById('leave-pixel-canvas'),
    canvas: document.getElementById('shared-pixel-canvas') as HTMLCanvasElement,
    stage: document.getElementById('pixel-stage'),
    viewport: document.getElementById('pixel-viewport'),
    palette: document.getElementById('pixel-palette'),
    status: document.getElementById('pixel-status'),
    coordinates: document.getElementById('pixel-coordinates'),
  };
  const context = elements.canvas.getContext('2d', { alpha: false });
  let state = null;
  let pixels = null;
  let selectedColor = 5;
  let zoom = 4;
  let pollTimer = null;
  let cooldownTimer = null;
  let cooldownUntil = 0;
  let placing = false;
  const pointers = new Map();
  let drag = null;
  let pinch = null;
  let pinched = false;

  buildPalette();
  setZoom(zoom);
  elements.open.addEventListener('click', openCanvas);
  elements.leave.addEventListener('click', leaveCanvas);
  elements.canvas.addEventListener('pointerdown', pointerDown);
  elements.canvas.addEventListener('pointermove', pointerMove);
  elements.canvas.addEventListener('pointerup', pointerUp);
  elements.canvas.addEventListener('pointercancel', pointerUp);
  elements.canvas.addEventListener('pointerleave', () => {
    elements.coordinates.textContent = 'x: — · y: —';
  });

  async function openCanvas() {
    showScreen('pixel-canvas');
    if (!hasTelegramAuth(telegram)) {
      setStatus('общий холст работает только внутри Telegram, хозяин');
      return;
    }
    setStatus('загружаю общий рисунок...');
    await refresh(true);
    startPolling();
  }

  function leaveCanvas() {
    stopPolling();
    showScreen('menu');
  }

  function buildPalette() {
    PALETTE.forEach((color, index) => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'pixel-swatch';
      button.style.setProperty('--swatch', color);
      button.setAttribute('aria-label', `Цвет ${index + 1}`);
      button.setAttribute('aria-pressed', String(index === selectedColor));
      button.addEventListener('click', () => {
        selectedColor = index;
        elements.palette.querySelectorAll('.pixel-swatch').forEach((swatch, swatchIndex) => {
          swatch.setAttribute('aria-pressed', String(swatchIndex === selectedColor));
        });
        telegram?.HapticFeedback?.selectionChanged();
      });
      elements.palette.appendChild(button);
    });
  }

  async function refresh(center = false) {
    try {
      const since = state?.version ?? 0;
      const next = await api(`/api/canvas/state?since=${since}`);
      cooldownUntil = Math.max(cooldownUntil, Date.now() + next.cooldown_ms);
      applyServerState(next);
      updateCooldown();
      if (center) window.requestAnimationFrame(centerViewport);
    } catch (error) {
      setStatus(error.message);
    }
  }

  async function placeAt(event) {
    if (!state || placing || Date.now() < cooldownUntil) {
      updateCooldown();
      return;
    }
    const point = pointFromEvent(event);
    if (!point) return;
    placing = true;
    setStatus(`ставлю пиксель ${point.x}, ${point.y}...`);
    try {
      const next = await api('/api/canvas/place', {
        method: 'POST',
        body: JSON.stringify({ x: point.x, y: point.y, color: selectedColor }),
      });
      cooldownUntil = Date.now() + next.cooldown_ms;
      applyServerState(next);
      updateCooldown();
      telegram?.HapticFeedback?.impactOccurred('medium');
    } catch (error) {
      if (error.retryAfterMS) cooldownUntil = Date.now() + error.retryAfterMS;
      setStatus(error.message);
      updateCooldown();
    } finally {
      placing = false;
    }
  }

  function applyServerState(next) {
    if (next.pixels) {
      pixels = new Uint8Array(next.pixels.length);
      for (let index = 0; index < next.pixels.length; index++) {
        pixels[index] = decodeColor(next.pixels.charCodeAt(index));
      }
      state = next;
      elements.canvas.width = next.width;
      elements.canvas.height = next.height;
      setZoom(zoom);
      draw();
      return;
    }
    if (!state || !pixels) return;
    for (const change of next.changes ?? []) {
      pixels[change.y * state.width + change.x] = change.color;
      context.fillStyle = PALETTE[change.color] ?? PALETTE[0];
      context.fillRect(change.x, change.y, 1, 1);
    }
    state = { ...state, ...next };
  }

  function draw() {
    if (!state || !pixels || pixels.length !== state.width * state.height) return;
    context.imageSmoothingEnabled = false;
    const image = context.createImageData(state.width, state.height);
    const rgb = PALETTE.map(hexToRGB);
    for (let index = 0; index < pixels.length; index++) {
      const color = rgb[pixels[index]] ?? rgb[0];
      const offset = index * 4;
      image.data[offset] = color[0];
      image.data[offset + 1] = color[1];
      image.data[offset + 2] = color[2];
      image.data[offset + 3] = 255;
    }
    context.putImageData(image, 0, 0);
  }

  function pointFromEvent(event) {
    if (!state) return null;
    const rect = elements.canvas.getBoundingClientRect();
    const x = Math.floor((event.clientX - rect.left) * state.width / rect.width);
    const y = Math.floor((event.clientY - rect.top) * state.height / rect.height);
    if (x < 0 || x >= state.width || y < 0 || y >= state.height) return null;
    return { x, y };
  }

  function showCoordinates(event) {
    const point = pointFromEvent(event);
    elements.coordinates.textContent = point ? `x: ${point.x} · y: ${point.y}` : 'x: — · y: —';
  }

  function setZoom(value) {
    zoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, value));
    const width = state?.width ?? elements.canvas.width;
    const height = state?.height ?? elements.canvas.height;
    elements.stage.style.width = `${width * zoom}px`;
    elements.stage.style.height = `${height * zoom}px`;
    elements.stage.style.setProperty('--pixel-size', `${zoom}px`);
    elements.stage.classList.toggle('grid-visible', zoom >= 4);
  }

  function centerViewport() {
    elements.viewport.scrollLeft = (elements.stage.clientWidth - elements.viewport.clientWidth) / 2;
    elements.viewport.scrollTop = (elements.stage.clientHeight - elements.viewport.clientHeight) / 2;
  }

  function pointerDown(event) {
    event.preventDefault();
    elements.canvas.setPointerCapture(event.pointerId);
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    if (pointers.size === 1) {
      drag = { lastX: event.clientX, lastY: event.clientY, moved: false };
      pinched = false;
    } else if (pointers.size === 2) {
      beginPinch();
    }
  }

  function pointerMove(event) {
    if (!pointers.has(event.pointerId)) {
      showCoordinates(event);
      return;
    }
    event.preventDefault();
    pointers.set(event.pointerId, { x: event.clientX, y: event.clientY });
    showCoordinates(event);

    if (pointers.size >= 2 && pinch) {
      const [first, second] = [...pointers.values()];
      const distance = Math.max(1, Math.hypot(second.x - first.x, second.y - first.y));
      const midpoint = { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 };
      const nextZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, pinch.zoom * distance / pinch.distance));
      setZoom(nextZoom);
      const viewportRect = elements.viewport.getBoundingClientRect();
      elements.viewport.scrollLeft = pinch.worldX * zoom - (midpoint.x - viewportRect.left);
      elements.viewport.scrollTop = pinch.worldY * zoom - (midpoint.y - viewportRect.top);
      pinched = true;
      return;
    }

    if (pointers.size === 1 && drag) {
      const dx = event.clientX - drag.lastX;
      const dy = event.clientY - drag.lastY;
      if (Math.abs(dx) + Math.abs(dy) > 2) drag.moved = true;
      elements.viewport.scrollLeft -= dx;
      elements.viewport.scrollTop -= dy;
      drag.lastX = event.clientX;
      drag.lastY = event.clientY;
    }
  }

  function pointerUp(event) {
    if (!pointers.has(event.pointerId)) return;
    const wasTap = pointers.size === 1 && drag && !drag.moved && !pinched;
    pointers.delete(event.pointerId);
    if (pointers.size === 1) {
      const remaining = [...pointers.values()][0];
      drag = { lastX: remaining.x, lastY: remaining.y, moved: true };
      pinch = null;
    } else if (pointers.size === 0) {
      drag = null;
      pinch = null;
      if (wasTap) placeAt(event);
    }
  }

  function beginPinch() {
    const [first, second] = [...pointers.values()];
    const midpoint = { x: (first.x + second.x) / 2, y: (first.y + second.y) / 2 };
    const viewportRect = elements.viewport.getBoundingClientRect();
    pinch = {
      distance: Math.max(1, Math.hypot(second.x - first.x, second.y - first.y)),
      zoom,
      worldX: (elements.viewport.scrollLeft + midpoint.x - viewportRect.left) / zoom,
      worldY: (elements.viewport.scrollTop + midpoint.y - viewportRect.top) / zoom,
    };
    pinched = true;
  }

  function updateCooldown() {
    const remaining = Math.max(0, cooldownUntil - Date.now());
    const coolingDown = remaining > 0;
    elements.canvas.classList.toggle('cooling-down', coolingDown);
    if (coolingDown) {
      setStatus(`подожди ${(remaining / 1000).toFixed(1)} сек.`);
    } else if (!placing && state) {
      setStatus('выбери цвет и поставь пиксель, хозяин :3');
    }
  }

  function startPolling() {
    stopPolling();
    pollTimer = window.setInterval(() => {
      if (!document.hidden && !placing) refresh();
    }, POLL_MS);
    cooldownTimer = window.setInterval(updateCooldown, 100);
  }

  function stopPolling() {
    if (pollTimer !== null) window.clearInterval(pollTimer);
    if (cooldownTimer !== null) window.clearInterval(cooldownTimer);
    pollTimer = null;
    cooldownTimer = null;
  }

  async function api(path, options: RequestInit = {}) {
    const response = await fetch(path, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...telegramAuthHeaders(telegram),
        ...options.headers,
      },
    });
    const payload = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(payload.error || 'холст не отвечает... попробуй ещё раз, хозяин') as Error & { retryAfterMS: number };
      error.retryAfterMS = payload.retry_after_ms || 0;
      throw error;
    }
    return payload;
  }

  function setStatus(message) {
    elements.status.textContent = message.toLowerCase().includes('хозяин') ? message : `хозяин, ${message}`;
  }

  function decodeColor(code) { return code <= 57 ? code - 48 : code - 87; }
  function hexToRGB(hex) {
    return [1, 3, 5].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16));
  }
}
