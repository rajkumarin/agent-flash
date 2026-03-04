const videoEl = document.getElementById("camera");
const overlayEl = document.getElementById("overlay");
const wsUrlEl = document.getElementById("wsUrl");
const startBtn = document.getElementById("startBtn");
const connectBtn = document.getElementById("connectBtn");
const connStatus = document.getElementById("connStatus");
const fpsStatus = document.getElementById("fpsStatus");
const latencyStatus = document.getElementById("latencyStatus");
const modelStatus = document.getElementById("modelStatus");
const appStatus = document.getElementById("appStatus");
const debugBox = document.getElementById("debugBox");

const ctx = overlayEl.getContext("2d");
const frameCanvas = document.createElement("canvas");
const frameCtx = frameCanvas.getContext("2d");

let socket = null;
let sendFrameTimer = null;
let latestParts = [];

const host = window.location.hostname || "localhost";
const wsScheme = window.location.protocol === "https:" ? "wss" : "ws";
const defaultPort =
  window.location.port || (window.location.protocol === "https:" ? "8443" : "8080");
wsUrlEl.value = `${wsScheme}://${host}:${defaultPort}/ws/session`;

startBtn.addEventListener("click", startCamera);
connectBtn.addEventListener("click", connectBackend);
window.addEventListener("resize", syncCanvasSize);
renderLoop();
debug(
  `Boot host=${window.location.host} secure=${window.isSecureContext} wsDefault=${wsUrlEl.value}`
);
window.addEventListener("error", (evt) => {
  debug(`window.error: ${evt.message}`);
  try {
    alert(`App error: ${evt.message}`);
  } catch (_) {}
});

async function startCamera() {
  debug("Start Camera clicked");
  try {
    if (!window.isSecureContext) {
      throw new Error("Insecure context. Camera usually requires HTTPS on Android Chrome.");
    }
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      throw new Error("getUserMedia unavailable. Use Chrome on HTTPS or localhost.");
    }

    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        facingMode: { ideal: "environment" },
        width: { ideal: 1280 },
        height: { ideal: 720 },
      },
      audio: false,
    });

    videoEl.srcObject = stream;
    await videoEl.play();
    syncCanvasSize();
    setStatus("Camera started");
    debug("Camera started");
  } catch (err) {
    const msg = err && err.message ? err.message : String(err);
    setStatus(`Camera error: ${msg}`);
    debug(`Camera error: ${msg}`);
    try {
      alert(`Camera error: ${msg}`);
    } catch (_) {}
  }
}

function syncCanvasSize() {
  const rect = videoEl.getBoundingClientRect();
  overlayEl.width = Math.max(1, Math.floor(rect.width));
  overlayEl.height = Math.max(1, Math.floor(rect.height));
}

function connectBackend() {
  debug("Connect Backend clicked");
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.close();
  }

  socket = new WebSocket(wsUrlEl.value.trim());
  connStatus.textContent = "Socket: connecting";
  setStatus(`Connecting to ${wsUrlEl.value.trim()}`);
  debug(`Socket connecting: ${wsUrlEl.value.trim()}`);

  socket.onopen = () => {
    connStatus.textContent = "Socket: connected";
    startFrameSender();
    setStatus("Backend connected");
    debug("Socket connected");
  };

  socket.onmessage = (evt) => {
    const msg = JSON.parse(evt.data);
    if (msg.type === "overlay") {
      latestParts = msg.parts || [];
    } else if (msg.type === "status") {
      fpsStatus.textContent = `FPS: ${msg.fps.toFixed(1)}`;
      latencyStatus.textContent = `Latency: ${msg.latency_ms.toFixed(0)} ms`;
      modelStatus.textContent = `Model: ${msg.model_name}`;
    }
  };

  socket.onerror = () => {
    connStatus.textContent = "Socket: error";
    setStatus("WebSocket error");
    debug("Socket error");
  };

  socket.onclose = (evt) => {
    connStatus.textContent = "Socket: disconnected";
    stopFrameSender();
    setStatus(`Socket closed (code ${evt.code})`);
    debug(`Socket closed code=${evt.code}`);
  };
}

function startFrameSender() {
  stopFrameSender();
  sendFrameTimer = setInterval(() => {
    if (!socket || socket.readyState !== WebSocket.OPEN) {
      return;
    }

    if (videoEl.videoWidth < 2 || videoEl.videoHeight < 2) {
      setStatus("Waiting for camera frames...");
      return;
    }

    frameCanvas.width = 640;
    frameCanvas.height = Math.round((videoEl.videoHeight / videoEl.videoWidth) * 640);
    frameCtx.drawImage(videoEl, 0, 0, frameCanvas.width, frameCanvas.height);

    const jpegBase64 = frameCanvas.toDataURL("image/jpeg", 0.55).split(",")[1];
    socket.send(
      JSON.stringify({
        type: "frame",
        ts: Date.now(),
        jpeg_base64: jpegBase64,
        width: frameCanvas.width,
        height: frameCanvas.height,
      })
    );
    setStatus("Streaming frames to backend");
  }, 180);
}

function stopFrameSender() {
  if (sendFrameTimer) {
    clearInterval(sendFrameTimer);
    sendFrameTimer = null;
  }
}

function renderLoop() {
  if (overlayEl.width > 0 && overlayEl.height > 0) {
    drawOverlay(latestParts);
  }
  requestAnimationFrame(renderLoop);
}

function drawOverlay(parts) {
  ctx.clearRect(0, 0, overlayEl.width, overlayEl.height);

  ctx.lineWidth = 2;
  ctx.font = "14px sans-serif";

  parts.slice(0, 5).forEach((part, idx) => {
    const x = part.bbox.x * overlayEl.width;
    const y = part.bbox.y * overlayEl.height;
    const w = part.bbox.w * overlayEl.width;
    const h = part.bbox.h * overlayEl.height;
    const ax = part.anchor.x * overlayEl.width;
    const ay = part.anchor.y * overlayEl.height;

    const hue = 130 - idx * 15;
    ctx.strokeStyle = `hsl(${hue}, 85%, 60%)`;
    ctx.fillStyle = "rgba(10, 18, 30, 0.8)";

    ctx.strokeRect(x, y, w, h);

    const label = `${idx + 1}. ${part.label} (${(part.conf * 100).toFixed(0)}%)`;
    const tw = ctx.measureText(label).width + 10;
    const tx = Math.max(4, Math.min(overlayEl.width - tw - 4, ax));
    const ty = Math.max(20, ay - 8);

    ctx.fillRect(tx, ty - 16, tw, 20);
    ctx.strokeRect(tx, ty - 16, tw, 20);

    ctx.fillStyle = "#f1f7ff";
    ctx.fillText(label, tx + 5, ty - 2);

    ctx.beginPath();
    ctx.moveTo(tx + 8, ty + 4);
    ctx.lineTo(x + Math.min(14, w / 2), y + 8);
    ctx.stroke();
  });
}

function setStatus(text) {
  if (appStatus) {
    appStatus.textContent = `Status: ${text}`;
  }
}

function debug(text) {
  if (!debugBox) {
    return;
  }
  const ts = new Date().toLocaleTimeString();
  debugBox.textContent += `[${ts}] ${text}\n`;
  debugBox.scrollTop = debugBox.scrollHeight;
}
