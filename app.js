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
        vx: (Math.random() - 0.5) * 0.18,
        vy: (Math.random() - 0.5) * 0.18,
        r:  Math.random() * 1.0 + 0.2,
        a:  Math.random() * 0.3 + 0.05,
      });
    }
  }

  function draw() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => {
      ctx.beginPath();
      ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(59,130,246,${p.a})`;
      ctx.fill();
      p.x += p.vx;
      p.y += p.vy;
      if (p.x < 0) p.x = W;
      if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H;
      if (p.y > H) p.y = 0;
    });

    for (let i = 0; i < particles.length; i++) {
      for (let j = i + 1; j < particles.length; j++) {
        const dx = particles[i].x - particles[j].x;
        const dy = particles[i].y - particles[j].y;
        const dist = Math.sqrt(dx * dx + dy * dy);
        if (dist < 90) {
          ctx.beginPath();
          ctx.moveTo(particles[i].x, particles[i].y);
          ctx.lineTo(particles[j].x, particles[j].y);
          ctx.strokeStyle = `rgba(59,130,246,${0.05 * (1 - dist / 90)})`;
          ctx.lineWidth = 0.4;
          ctx.stroke();
        }
      }
    }
    requestAnimationFrame(draw);
  }

  resize();
  spawn(Math.floor((W * H) / 18000));
  draw();
  window.addEventListener("resize", () => { resize(); spawn(Math.floor((W * H) / 18000)); });
})();

// ── Section color config ─────────────────────────────────────────────────────
const SECTION_COLORS = {
  red:    "#e53e5b",
  blue:   "#3b82f6",
  green:  "#10b981",
  orange: "#f59e0b",
  teal:   "#06b6d4",
  yellow: "#eab308",
  purple: "#8b5cf6",
  gray:   "#64748b",
};

// Section definitions per conflict
const SECTION_DEFS = {
  middle_east: [
    { key: "executive_summary", label: "Executive Summary", flag: "EX", color: "blue", type: "prose" },
    { key: "iran",              label: "Iran",              flag: "IR", color: "red",    type: "points" },
    { key: "israel",            label: "Israel",            flag: "IL", color: "blue",   type: "points" },
    { key: "gaza_west_bank",    label: "Gaza & West Bank",  flag: "PS", color: "blue",   type: "points" },
    { key: "lebanon",           label: "Lebanon",           flag: "LB", color: "green",  type: "points" },
    { key: "syria_iraq",        label: "Syria & Iraq",      flag: "SY", color: "orange", type: "points" },
    { key: "gulf_states",       label: "Gulf States",       flag: "GS", color: "gray",   type: "points" },
    { key: "key_developments",  label: "Key Developments",  flag: "KD", color: "yellow", type: "keydevs" },
    { key: "threat_assessment", label: "Threat Assessment", flag: "TA", color: "red",    type: "prose-threat" },
    { key: "regional_response", label: "Regional & International Response", flag: "RI", color: "teal", type: "prose-regional" },
    { key: "intelligence_notes",label: "Intelligence Notes",flag: "IN", color: "purple", type: "prose-intel" },
  ],
  ukraine: [
    { key: "executive_summary", label: "Executive Summary", flag: "EX", color: "blue",   type: "prose" },
    { key: "ukraine",           label: "Ukraine",           flag: "UA", color: "blue",   type: "points" },
    { key: "russia",            label: "Russia",            flag: "RU", color: "red",    type: "points" },
    { key: "eastern_front",     label: "Eastern Front",     flag: "EF", color: "orange", type: "points" },
    { key: "northern_front",    label: "Northern Front",    flag: "NF", color: "teal",   type: "points" },
    { key: "southern_front",    label: "Southern Front",    flag: "SF", color: "yellow", type: "points" },
    { key: "air_war",           label: "Air War",           flag: "AW", color: "purple", type: "points" },
    { key: "key_developments",  label: "Key Developments",  flag: "KD", color: "yellow", type: "keydevs" },
    { key: "threat_assessment", label: "Threat Assessment", flag: "TA", color: "red",    type: "prose-threat" },
    { key: "regional_response", label: "International Response", flag: "RI", color: "teal", type: "prose-regional" },
    { key: "intelligence_notes",label: "Intelligence Notes",flag: "IN", color: "purple", type: "prose-intel" },
  ],
};

// ── Charts registry ──────────────────────────────────────────────────────────
const charts = {};

const CHART_DEFAULTS = {
  responsive: true,
  maintainAspectRatio: false,
  animation: { duration: 900, easing: "easeOutQuart" },
  plugins: {
    legend: { display: false },
    tooltip: {
      backgroundColor: "rgba(15,18,25,0.95)",
      borderColor: "rgba(255,255,255,0.1)",
      borderWidth: 1,
      titleColor: "#dde4f0",
      bodyColor: "#a8b4cc",
      padding: 10,
      titleFont: { family: "'JetBrains Mono', monospace", size: 11 },
      bodyFont: { family: "'JetBrains Mono', monospace", size: 11 },
      cornerRadius: 6,
    },
  },
  scales: {
    x: {
      grid: { color: "rgba(255,255,255,0.04)", drawBorder: false },
      ticks: { color: "#5a6a88", font: { family: "'JetBrains Mono', monospace", size: 9 }, maxRotation: 0 },
    },
    y: {
      grid: { color: "rgba(255,255,255,0.04)", drawBorder: false },
      ticks: { color: "#5a6a88", font: { family: "'JetBrains Mono', monospace", size: 9 }, maxTicksLimit: 4 },
      beginAtZero: true,
    },
  },
};

function makeHourLabels() {
  const now = new Date();
  return Array.from({ length: 24 }, (_, i) => {
    const h = new Date(now - (23 - i) * 3600000);
    return String(h.getUTCHours()).padStart(2, "0") + ":00";
  });
}

function renderAlertChart(canvasId, timelineRaw) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  // ÷2 as requested
  const data = (timelineRaw || []).map(v => Math.round(v / 2));
  const labels = makeHourLabels();

  const cfg = {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: data.map(v =>
          v > 3 ? "rgba(229,62,91,0.85)" : v > 0 ? "rgba(229,62,91,0.55)" : "rgba(229,62,91,0.12)"
        ),
        borderColor: "rgba(229,62,91,0.6)",
        borderWidth: 0,
        borderRadius: 2,
        hoverBackgroundColor: "rgba(229,62,91,1)",
      }],
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        tooltip: {
          ...CHART_DEFAULTS.plugins.tooltip,
          callbacks: {
            label: ctx => `Alerts: ${ctx.raw}`,
          },
        },
      },
      scales: { ...CHART_DEFAULTS.scales },
    },
  };

  if (charts[canvasId]) {
    charts[canvasId].data.datasets[0].data = data;
    charts[canvasId].data.datasets[0].backgroundColor = cfg.data.datasets[0].backgroundColor;
    charts[canvasId].update("active");
  } else {
    charts[canvasId] = new Chart(canvas, cfg);
  }
}

function renderActivityChart(canvasId, timeline) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  const data = timeline || [];
  const labels = makeHourLabels();

  const cfg = {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: "rgba(59,130,246,0.5)",
        borderColor: "rgba(59,130,246,0.3)",
        borderWidth: 0,
        borderRadius: 2,
        hoverBackgroundColor: "rgba(59,130,246,0.9)",
      }],
    },
    options: {
      ...CHART_DEFAULTS,
      plugins: {
        ...CHART_DEFAULTS.plugins,
        tooltip: {
          ...CHART_DEFAULTS.plugins.tooltip,
          callbacks: {
            label: ctx => `Messages: ${ctx.raw}`,
          },
        },
      },
      scales: { ...CHART_DEFAULTS.scales },
    },
  };

  if (charts[canvasId]) {
    charts[canvasId].data.datasets[0].data = data;
    charts[canvasId].update("active");
  } else {
    charts[canvasId] = new Chart(canvas, cfg);
  }
}

function renderChannelChart(canvasId, msgsByChannel) {
  const canvas = document.getElementById(canvasId);
  if (!canvas) return;
  if (!msgsByChannel) return;

  const entries = Object.entries(msgsByChannel)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const labels = entries.map(([ch]) => ch);
  const data   = entries.map(([, v]) => v);
  const max    = Math.max(...data) || 1;

  const cfg = {
    type: "bar",
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: data.map(v =>
          `rgba(16,185,129,${0.35 + 0.55 * (v / max)})`
        ),
        borderColor: "rgba(16,185,129,0.3)",
        borderWidth: 0,
        borderRadius: 3,
        hoverBackgroundColor: "rgba(16,185,129,0.95)",
      }],
    },
    options: {
      ...CHART_DEFAULTS,
      indexAxis: "y",
      plugins: {
        ...CHART_DEFAULTS.plugins,
        tooltip: {
          ...CHART_DEFAULTS.plugins.tooltip,
          callbacks: {
            label: ctx => `${ctx.raw} messages`,
          },
        },
      },
      scales: {
        x: {
          ...CHART_DEFAULTS.scales.x,
          ticks: { ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit: 4 },
        },
        y: {
          ...CHART_DEFAULTS.scales.y,
          grid: { display: false },
          ticks: {
            color: "#a8b4cc",
            font: { family: "'JetBrains Mono', monospace", size: 9 },
            maxRotation: 0,
          },
        },
      },
    },
  };

  if (charts[canvasId]) {
    charts[canvasId].data.labels   = labels;
    charts[canvasId].data.datasets[0].data = data;
    charts[canvasId].data.datasets[0].backgroundColor = cfg.data.datasets[0].backgroundColor;
    charts[canvasId].update("active");
  } else {
    charts[canvasId] = new Chart(canvas, cfg);
  }
}

// ── Section rendering ────────────────────────────────────────────────────────
function buildSectionBlock(def, sectionsData, index) {
  const raw = sectionsData[def.key];
  if (!raw && def.key !== "executive_summary") return null;

  const color = SECTION_COLORS[def.color] || "#3b82f6";
  const isExec = def.key === "executive_summary";

  const block = document.createElement("div");
  block.className = `section-block${isExec ? " section-block--executive" : ""}`;
  block.id = `section-${def.key}`;
  block.style.animationDelay = `${index * 50}ms`;

  // Header
  const header = document.createElement("div");
  header.className = "section-header";
  header.innerHTML = `
    <span class="section-flag flag--${def.color}">${def.flag}</span>
    <div class="section-title-wrap">
      <div class="section-title">${def.label}</div>
      ${(typeof raw === "object" && raw.subtitle) ? `<div class="section-subtitle">${raw.subtitle}</div>` : ""}
    </div>
    <svg class="section-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
      <polyline points="9 18 15 12 9 6"/>
    </svg>
  `;

  const body = document.createElement("div");
  body.className = "section-body";

  if (def.type === "prose" || isExec) {
    const text = typeof raw === "string" ? raw : (raw && raw.text) || "";
    body.innerHTML = `<p class="section-summary-text">${text}</p>`;
    if (isExec) block.classList.add("open");
  } else if (def.type === "points") {
    const points = (typeof raw === "object" && raw.points) ? raw.points : [];
    body.innerHTML = `
      <div class="section-points">
        ${points.map((pt, i) => `
          <div class="section-point" style="animation-delay:${i * 40}ms">
            <span class="section-point-bullet" style="background:${color}"></span>
            <span>${pt}</span>
          </div>`).join("")}
      </div>`;
  } else if (def.type === "keydevs") {
    const items = Array.isArray(raw) ? raw : [];
    body.innerHTML = `
      <div class="key-dev-list">
        ${items.map((item, i) => `
          <div class="key-dev-item" style="animation-delay:${i * 40}ms">
            <span class="key-dev-num">0${i + 1}</span>
            <span>${item}</span>
          </div>`).join("")}
      </div>`;
    block.classList.add("open");
  } else if (def.type === "prose-threat") {
    const text = typeof raw === "string" ? raw : "";
    body.innerHTML = `<p class="section-prose">${text}</p>`;
  } else if (def.type === "prose-regional") {
    const text = typeof raw === "string" ? raw : "";
    body.innerHTML = `<p class="section-prose prose--regional">${text}</p>`;
  } else if (def.type === "prose-intel") {
    const text = typeof raw === "string" ? raw : "";
    body.innerHTML = `<p class="section-prose prose--intel">${text}</p>`;
  }

  block.appendChild(header);
  block.appendChild(body);

  // Toggle open/close
  if (!isExec && def.type !== "keydevs") {
    header.addEventListener("click", () => {
      const isOpen = block.classList.toggle("open");
      updateNavActive(def.key, isOpen);
    });
  }

  return block;
}

function updateNavActive(sectionKey, isOpen) {
  const navItems = document.querySelectorAll(`.sections-nav-item[data-section="${sectionKey}"]`);
  navItems.forEach(item => item.classList.toggle("active", isOpen));
}

function buildSectionsNav(prefix, defs, sectionsData) {
  const nav = document.getElementById(`${prefix}-sections-nav`);
  if (!nav) return;
  nav.innerHTML = "";

  defs.forEach(def => {
    const color = SECTION_COLORS[def.color] || "#3b82f6";
    const item = document.createElement("a");
    item.className = "sections-nav-item";
    item.dataset.section = def.key;
    const isActive = def.key === "executive_summary" || def.type === "keydevs";
    if (isActive) item.classList.add("active");
    item.innerHTML = `
      <span class="nav-color-dot" style="background:${color};color:${color}"></span>
      <span class="nav-label">${def.label}</span>
      <span class="nav-status-dot"></span>
    `;
    item.addEventListener("click", e => {
      e.preventDefault();
      const target = document.getElementById(`section-${def.key}`);
      if (!target) return;
      target.scrollIntoView({ behavior: "smooth", block: "start" });
      if (!target.classList.contains("open") && !target.classList.contains("section-block--executive")) {
        target.classList.add("open");
        updateNavActive(def.key, true);
      }
    });
    nav.appendChild(item);
  });
}

// ── Populate panel ───────────────────────────────────────────────────────────
function populatePanel(prefix, data) {
  const shortPrefix = prefix === "middle_east" ? "me" : "ua";
  const defs = SECTION_DEFS[prefix];

  // Stats
  const rawAlerts = data.red_alerts || 0;
  const displayAlerts = Math.round(rawAlerts / 2);
  animateValue(`${shortPrefix}-red-alerts`, 0, displayAlerts, 800);

  animateValue(`${shortPrefix}-msg-count`, 0, data.message_count || 0, 1000);
  const chCountEl = document.getElementById(`${shortPrefix}-channel-count`);
  if (chCountEl) chCountEl.textContent = `${(data.channels || []).length} channels`;

  const intensityEl = document.getElementById(`${shortPrefix}-intensity-val`);
  if (intensityEl) intensityEl.textContent = `${data.intensity || "—"}/10`;

  const sentimentEl = document.getElementById(`${shortPrefix}-sentiment-val`);
  if (sentimentEl) sentimentEl.textContent = (data.sentiment || "unknown").toUpperCase();

  // Sections content
  const container = document.getElementById(`${shortPrefix}-sections-content`);
  if (container && data.sections) {
    container.innerHTML = "";
    defs.forEach((def, i) => {
      const block = buildSectionBlock(def, data.sections, i);
      if (block) container.appendChild(block);
    });
  }

  // Sections nav
  buildSectionsNav(shortPrefix, defs, data.sections || {});

  // Charts
  renderAlertChart(`${shortPrefix}-chart-alerts`, data.red_alerts_timeline);
  renderActivityChart(`${shortPrefix}-chart-activity`, data.combined_activity_timeline);
  renderChannelChart(`${shortPrefix}-chart-channels`, data.messages_by_channel);

  // Sources
  const sourcesList = document.getElementById(`${shortPrefix}-sources-list`);
  if (sourcesList) {
    sourcesList.innerHTML = (data.channels || []).map(ch => `
      <li><a href="https://t.me/${ch}" target="_blank" rel="noopener noreferrer">@${ch}</a></li>
    `).join("");
  }
}

// ── Animated counter ─────────────────────────────────────────────────────────
function animateValue(id, from, to, duration) {
  const el = document.getElementById(id);
  if (!el) return;
  const start = performance.now();
  function step(now) {
    const p = Math.min((now - start) / duration, 1);
    const ease = 1 - Math.pow(1 - p, 3);
    el.textContent = Math.round(from + (to - from) * ease).toLocaleString();
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── Countdown timer (1 hour) ─────────────────────────────────────────────────
function startCountdown(updatedAt) {
  const ONE_HOUR = 60 * 60 * 1000;
  const updated  = new Date(updatedAt).getTime();

  function tick() {
    const remaining = ONE_HOUR - (Date.now() - updated);
    if (remaining <= 0) {
      document.getElementById("countdown").textContent = "any moment";
      return;
    }
    const m = Math.floor((remaining % 3600000) / 60000);
    const s = Math.floor((remaining % 60000) / 1000);
    document.getElementById("countdown").textContent =
      `${String(m).padStart(2, "0")}m ${String(s).padStart(2, "0")}s`;
  }
  tick();
  setInterval(tick, 1000);
}

// ── Header datetime ──────────────────────────────────────────────────────────
function updateDatetime() {
  const el = document.getElementById("headerDatetime");
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleString("en-GB", {
    day: "2-digit", month: "short", year: "numeric",
    hour: "2-digit", minute: "2-digit", timeZone: "UTC",
    timeZoneName: "short",
  });
}

// ── Data loading ─────────────────────────────────────────────────────────────
const dataCache = {};

async function loadConflict(key) {
  if (dataCache[key]) return dataCache[key];
  try {
    const resp = await fetch(`data/${key}.json?t=${Date.now()}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json();
    dataCache[key] = data;
    return data;
  } catch (e) {
    console.error(`Failed to load ${key}:`, e);
    return null;
  }
}

// ── Tab switching ────────────────────────────────────────────────────────────
let activeTab = "middle_east";

function switchTab(key) {
  if (key === activeTab) return;
  activeTab = key;

  document.querySelectorAll(".tab-btn").forEach(b =>
    b.classList.toggle("active", b.dataset.tab === key)
  );
  document.querySelectorAll(".conflict-panel").forEach(p => {
    const visible = p.id === `panel-${key}`;
    p.classList.toggle("hidden", !visible);
    if (visible) {
      p.style.animation = "none";
      p.offsetHeight;
      p.style.animation = "";
    }
  });

  const cached = dataCache[key];
  if (!cached) {
    loadConflict(key).then(data => {
      if (data) {
        populatePanel(key, data);
        updateHeaderForConflict(data);
      }
    });
  } else {
    updateHeaderForConflict(cached);
  }
}

function updateHeaderForConflict(data) {
  const titleEl = document.getElementById("siteTitle");
  if (!titleEl) return;
  const name = data.conflict || "War Summary";
  titleEl.innerHTML = `${name} <span>(24 Hours)</span>`;
}

// ── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  updateDatetime();
  setInterval(updateDatetime, 30000);

  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.addEventListener("click", () => switchTab(btn.dataset.tab));
  });

  const [me, ua] = await Promise.all([
    loadConflict("middle_east"),
    loadConflict("ukraine"),
  ]);

  if (me) {
    populatePanel("middle_east", me);
    updateHeaderForConflict(me);
    startCountdown(me.updated_at);
  }

  if (ua) {
    populatePanel("ukraine", ua);
  }
}

document.addEventListener("DOMContentLoaded", init);
