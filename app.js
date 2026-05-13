/* ── Global Conflict Intelligence — app.js ── */
"use strict";

// ── Particle background ──────────────────────────────────────────────────────
(function initParticles() {
  const canvas = document.getElementById("particles");
  const ctx = canvas.getContext("2d");
  let W, H, particles;

  function resize() {
    W = canvas.width  = window.innerWidth;
    H = canvas.height = window.innerHeight;
  }

  function spawn(n) {
    particles = [];
    for (let i = 0; i < n; i++) {
      particles.push({
        x:  Math.random() * W,
        y:  Math.random() * H,
        vx: (Math.random() - 0.5) * 0.25,
        vy: (Math.random() - 0.5) * 0.25,
        r:  Math.random() * 1.2 + 0.3,
        a:  Math.random() * 0.4 + 0.1,
      });
    }
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(79,156,249,${p.a})`;
      ctx.fill();

      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0) p.x = W;
      if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H;
      if (p.y > H) p.y = 0;
    });

    // Connect nearby particles
    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 100) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(79,156,249,${0.06 * (1 - dist / 100)})`;
          ctx.lineWidth = 0.5;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }

  resize();
  spawn(Math.floor((W * H) / 14000));
  draw();
  window.addEventListener("resize", () => { resize(); spawn(Math.floor((W * H) / 14000)); });
})();

// ── Maps ─────────────────────────────────────────────────────────────────────
const MAP_CONFIGS = {
  ukraine: {
    center: [48.8, 32.0],
    zoom: 5,
    hotspots: [
      { lat: 47.9, lng: 37.8, label: "Donetsk Front", intensity: 9 },
      { lat: 49.0, lng: 36.2, label: "Kharkiv Region", intensity: 7 },
      { lat: 47.1, lng: 38.6, label: "Mariupol Area", intensity: 6 },
      { lat: 46.9, lng: 35.4, label: "Zaporizhzhia", intensity: 8 },
      { lat: 48.7, lng: 30.7, label: "Vinnytsia", intensity: 4 },
    ],
    cities: [
      { lat: 50.45, lng: 30.52, label: "Kyiv" },
      { lat: 49.99, lng: 36.23, label: "Kharkiv" },
      { lat: 46.48, lng: 30.72, label: "Odessa" },
      { lat: 47.83, lng: 35.14, label: "Zaporizhzhia" },
    ],
  },
  middle_east: {
    center: [31.5, 35.5],
    zoom: 5,
    hotspots: [
      { lat: 31.5, lng: 34.5, label: "Gaza Strip", intensity: 10 },
      { lat: 33.0, lng: 35.5, label: "South Lebanon", intensity: 7 },
      { lat: 33.5, lng: 36.3, label: "Damascus Region", intensity: 6 },
      { lat: 36.3, lng: 43.1, label: "Northern Iraq", intensity: 5 },
      { lat: 32.8, lng: 35.0, label: "West Bank", intensity: 7 },
    ],
    cities: [
      { lat: 32.08, lng: 34.78, label: "Tel Aviv" },
      { lat: 31.77, lng: 35.23, label: "Jerusalem" },
      { lat: 33.89, lng: 35.50, label: "Beirut" },
      { lat: 33.51, lng: 36.29, label: "Damascus" },
      { lat: 30.06, lng: 31.24, label: "Cairo" },
    ],
  },
};

const maps = {};

function createPulseIcon(color, size) {
  return L.divIcon({
    className: "",
    html: `<div style="
      width:${size}px;height:${size}px;border-radius:50%;
      background:${color};opacity:0.8;
      box-shadow:0 0 0 0 ${color};
      animation:pulse-ring 2s cubic-bezier(0.215,0.61,0.355,1) infinite;
    "></div>`,
    iconSize:   [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function initMap(key) {
  const cfg = MAP_CONFIGS[key];
  const el = document.getElementById(`map-${key}`);
  if (!el || maps[key]) return;

  const map = L.map(el, {
    center: cfg.center,
    zoom:   cfg.zoom,
    zoomControl: true,
    attributionControl: false,
  });

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    maxZoom: 18,
  }).addTo(map);

  // Hotspot markers (red pulses)
  cfg.hotspots.forEach(h => {
    const sz = 8 + h.intensity;
    const icon = createPulseIcon("#e85d75", sz);
    L.marker([h.lat, h.lng], { icon })
      .addTo(map)
      .bindPopup(
        `<b style="color:#e85d75">${h.label}</b><br>Intensity: ${h.intensity}/10`,
        { className: "dark-popup" }
      );
  });

  // City markers (blue dots)
  cfg.cities.forEach(c => {
    const icon = createPulseIcon("#4f9cf9", 8);
    L.marker([c.lat, c.lng], { icon })
      .addTo(map)
      .bindPopup(`<b style="color:#4f9cf9">${c.label}</b>`, { className: "dark-popup" });
  });

  maps[key] = map;
}

// ── Doughnut gauge ───────────────────────────────────────────────────────────
const gauges = {};

function intensityColor(v) {
  if (v >= 8) return "#e85d75";
  if (v >= 5) return "#f0a500";
  return "#48bb78";
}

function renderGauge(key, value) {
  const id = `gauge-${key}`;
  const canvas = document.getElementById(id);
  if (!canvas) return;

  const clamp  = Math.max(1, Math.min(10, value || 5));
  const color  = intensityColor(clamp);
  const remain = 10 - clamp;

  if (gauges[key]) {
    gauges[key].data.datasets[0].data = [clamp, remain];
    gauges[key].data.datasets[0].backgroundColor = [color, "rgba(255,255,255,0.05)"];
    gauges[key].update("active");
  } else {
    gauges[key] = new Chart(canvas, {
      type: "doughnut",
      data: {
        datasets: [{
          data: [clamp, remain],
          backgroundColor: [color, "rgba(255,255,255,0.05)"],
          borderWidth: 0,
          hoverOffset: 4,
        }],
      },
      options: {
        cutout: "75%",
        animation: { duration: 900, easing: "easeInOutQuart" },
        plugins: { legend: { display: false }, tooltip: { enabled: false } },
      },
    });
  }

  document.getElementById(`${id}-label`).textContent = `${clamp}/10`;
  document.getElementById(`${id}-label`).style.color = color;
}

// ── Ticker ───────────────────────────────────────────────────────────────────
function buildTicker(datasets) {
  const items = [];
  datasets.forEach(d => {
    if (d && d.key_points) {
      d.key_points.forEach(p => items.push(`${d.conflict.toUpperCase()}: ${p}`));
    }
  });
  if (!items.length) return;

  const text = items.join("  ·  ");
  const doubled = text + "   ◈   " + text;

  const el = document.getElementById("tickerContent");
  el.textContent = doubled;

  // Reset animation so it restarts cleanly
  el.style.animation = "none";
  el.offsetHeight; // reflow
  const dur = Math.max(40, items.length * 8);
  el.style.animation = `ticker-scroll ${dur}s linear infinite`;
}

// ── Populate conflict panel ──────────────────────────────────────────────────
function populatePanel(key, data) {
  const d = data;

  // Summary
  document.getElementById(`${key}-summary`).textContent = d.summary || "No summary available.";

  // Key points
  const kpEl = document.getElementById(`${key}-keypoints`);
  kpEl.innerHTML = "";
  (d.key_points || []).forEach((pt, i) => {
    const div = document.createElement("div");
    div.className = "key-point";
    div.textContent = pt;
    div.style.animationDelay = `${i * 80}ms`;
    kpEl.appendChild(div);
  });

  // Details
  const terEl = document.getElementById(`${key}-territorial`);
  const casEl = document.getElementById(`${key}-casualties`);
  if (terEl) terEl.textContent = d.territorial || "—";
  if (casEl) casEl.textContent = d.casualties_mentioned || "—";

  // Intensity badge
  const v = d.intensity || 5;
  const badge = document.getElementById(`${key}-intensity`);
  badge.textContent = `INTENSITY ${v}/10`;
  badge.className = "intensity-badge";
  if (v >= 8)      badge.classList.add("level-high");
  else if (v >= 5) badge.classList.add("level-medium");
  else             badge.classList.add("level-low");

  // Gauge
  renderGauge(key, v);

  // Sentiment
  const sentEl = document.getElementById(`${key}-sentiment`);
  const sentRow = document.getElementById(`${key}-sentiment-row`);
  const sent = (d.sentiment || "stable").toLowerCase().replace(/\s+/g, "-");
  sentEl.textContent = sent.replace(/-/g, " ");
  sentRow.className = `sentiment-row sentiment--${sent}`;

  // Channels
  const chEl = document.getElementById(`${key}-channels`);
  chEl.innerHTML = "";
  (d.channels || []).forEach(ch => {
    const li = document.createElement("li");
    const a  = document.createElement("a");
    a.className = "channel-item";
    a.href = `https://t.me/${ch}`;
    a.target = "_blank";
    a.rel = "noopener noreferrer";
    a.textContent = `t.me/${ch}`;
    li.appendChild(a);
    chEl.appendChild(li);
  });

  // Message count
  const mcEl = document.getElementById(`${key}-msgcount`);
  if (mcEl) mcEl.textContent = d.message_count || 0;
}

// ── Countdown timer ──────────────────────────────────────────────────────────
function startCountdown(updatedAt) {
  const THREE_HOURS = 3 * 60 * 60 * 1000;
  const updated = new Date(updatedAt).getTime();

  function tick() {
    const remaining = THREE_HOURS - (Date.now() - updated);
    if (remaining <= 0) {
      document.getElementById("countdown").textContent = "any moment";
      return;
    }
    const h = Math.floor(remaining / 3600000);
    const m = Math.floor((remaining % 3600000) / 60000);
    const s = Math.floor((remaining % 60000) / 1000);
    document.getElementById("countdown").textContent =
      `${h}h ${String(m).padStart(2, "0")}m ${String(s).padStart(2, "0")}s`;
  }
  tick();
  setInterval(tick, 1000);
}

// ── Format date ──────────────────────────────────────────────────────────────
function fmtDate(iso) {
  try {
    return new Date(iso).toLocaleString("en-US", {
      month: "short", day: "numeric", hour: "2-digit",
      minute: "2-digit", timeZoneName: "short",
    });
  } catch { return iso; }
}

// ── Load data ────────────────────────────────────────────────────────────────
const dataCache = {};

async function loadConflict(key) {
  if (dataCache[key]) { populatePanel(key, dataCache[key]); return; }

  try {
    const resp = await fetch(`data/${key}.json?t=${Date.now()}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    dataCache[key] = data;
    populatePanel(key, data);
    return data;
  } catch (e) {
    console.error(`Failed to load ${key}:`, e);
    document.getElementById(`${key}-summary`).textContent =
      "Could not load conflict data. Please refresh the page.";
  }
}

// ── Tab switching ────────────────────────────────────────────────────────────
function switchTab(key) {
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === key));
  document.querySelectorAll(".conflict-panel").forEach(p => {
    const visible = p.id === `panel-${key}`;
    p.classList.toggle("hidden", !visible);
    if (visible) {
      p.style.animation = "none";
      p.offsetHeight;
      p.style.animation = "";
    }
  });

  // Lazy-init map when panel becomes visible
  setTimeout(() => {
    initMap(key);
    if (maps[key]) maps[key].invalidateSize();
  }, 50);

  if (!dataCache[key]) loadConflict(key);
}

// ── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  // Load both datasets
  const [uk, me] = await Promise.all([
    loadConflict("ukraine"),
    loadConflict("middle_east"),
  ]);

  buildTicker([uk, me]);

  // Header meta
  const latest = uk || me;
  if (latest) {
    document.getElementById("lastUpdated").textContent =
      `Last updated: ${fmtDate(latest.updated_at)}`;
    startCountdown(latest.updated_at);
  }

  // Init visible map (ukraine is default tab)
  setTimeout(() => initMap("ukraine"), 100);
}

document.addEventListener("DOMContentLoaded", init);
