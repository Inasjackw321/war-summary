"use strict";

// ── Scroll progress bar ───────────────────────────────────────────────────────
(function initScrollProgress() {
  const bar = document.getElementById("scroll-progress");
  const btn = document.getElementById("scrollTop");
  function update() {
    const doc = document.documentElement;
    const pct = doc.scrollTop / (doc.scrollHeight - doc.clientHeight) * 100;
    if (bar) bar.style.width = Math.min(pct, 100) + "%";
    if (btn) btn.classList.toggle("visible", doc.scrollTop > 400);
  }
  window.addEventListener("scroll", update, { passive: true });
  if (btn) btn.addEventListener("click", () => window.scrollTo({ top: 0, behavior: "smooth" }));
})();

// ── Particle background ───────────────────────────────────────────────────────
(function initParticles() {
  const canvas = document.getElementById("particles");
  const ctx = canvas.getContext("2d");
  let W, H, particles;
  function resize() { W = canvas.width = window.innerWidth; H = canvas.height = window.innerHeight; }
  function spawn(n) {
    particles = [];
    for (let i = 0; i < n; i++) particles.push({ x: Math.random()*W, y: Math.random()*H, vx: (Math.random()-0.5)*0.18, vy: (Math.random()-0.5)*0.18, r: Math.random()*1.0+0.2, a: Math.random()*0.3+0.05 });
  }
  function draw() {
    ctx.clearRect(0, 0, W, H);
    particles.forEach(p => {
      ctx.beginPath(); ctx.arc(p.x, p.y, p.r, 0, Math.PI*2);
      ctx.fillStyle = `rgba(59,130,246,${p.a})`; ctx.fill();
      p.x += p.vx; p.y += p.vy;
      if (p.x < 0) p.x = W; if (p.x > W) p.x = 0;
      if (p.y < 0) p.y = H; if (p.y > H) p.y = 0;
    });
    for (let i = 0; i < particles.length; i++) for (let j = i+1; j < particles.length; j++) {
      const dx = particles[i].x-particles[j].x, dy = particles[i].y-particles[j].y, d = Math.sqrt(dx*dx+dy*dy);
      if (d < 90) { ctx.beginPath(); ctx.moveTo(particles[i].x,particles[i].y); ctx.lineTo(particles[j].x,particles[j].y); ctx.strokeStyle=`rgba(59,130,246,${0.05*(1-d/90)})`; ctx.lineWidth=0.4; ctx.stroke(); }
    }
    requestAnimationFrame(draw);
  }
  resize(); spawn(Math.floor((W*H)/18000)); draw();
  window.addEventListener("resize", () => { resize(); spawn(Math.floor((W*H)/18000)); });
})();

// ── Section color config ──────────────────────────────────────────────────────
const SECTION_COLORS = {
  red: "#e53e5b", blue: "#3b82f6", green: "#10b981", orange: "#f59e0b",
  teal: "#06b6d4", yellow: "#eab308", purple: "#8b5cf6", gray: "#64748b",
};

const SECTION_DEFS = {
  middle_east: [
    { key: "executive_summary", label: "Executive Summary",                flag: "EX", color: "blue",   type: "prose" },
    { key: "iran",              label: "Iran",                              flag: "\u{1F1EE}\u{1F1F7}", color: "red",    type: "points" },
    { key: "israel",            label: "Israel",                            flag: "\u{1F1EE}\u{1F1F1}", color: "blue",   type: "points" },
    { key: "gaza_west_bank",    label: "Gaza & West Bank",                  flag: "\u{1F1F5}\u{1F1F8}", color: "blue",   type: "points" },
    { key: "lebanon",           label: "Lebanon",                           flag: "\u{1F1F1}\u{1F1E7}", color: "green",  type: "points" },
    { key: "syria_iraq",        label: "Syria & Iraq",                      flag: "\u{1F1F8}\u{1F1FE}", color: "orange", type: "points" },
    { key: "gulf_states",       label: "Gulf States",                       flag: "\u{1F1F8}\u{1F1E6}", color: "gray",   type: "points" },
    { key: "key_developments",  label: "Key Developments",                  flag: "KD", color: "yellow", type: "keydevs" },
    { key: "threat_assessment", label: "Threat Assessment",                 flag: "TA", color: "red",    type: "prose-threat" },
    { key: "regional_response", label: "Regional & International Response", flag: "RI", color: "teal",   type: "prose-regional" },
    { key: "intelligence_notes",label: "Intelligence Notes",                flag: "IN", color: "purple", type: "prose-intel" },
  ],
  ukraine: [
    { key: "executive_summary", label: "Executive Summary",     flag: "EX", color: "blue",   type: "prose" },
    { key: "ukraine",           label: "Ukraine",                flag: "\u{1F1FA}\u{1F1E6}", color: "blue",   type: "points" },
    { key: "russia",            label: "Russia",                 flag: "\u{1F1F7}\u{1F1FA}", color: "red",    type: "points" },
    { key: "eastern_front",     label: "Eastern Front",          flag: "EF", color: "orange", type: "points" },
    { key: "northern_front",    label: "Northern Front",         flag: "NF", color: "teal",   type: "points" },
    { key: "southern_front",    label: "Southern Front",         flag: "SF", color: "yellow", type: "points" },
    { key: "air_war",           label: "Air War",                flag: "AW", color: "purple", type: "points" },
    { key: "key_developments",  label: "Key Developments",       flag: "KD", color: "yellow", type: "keydevs" },
    { key: "threat_assessment", label: "Threat Assessment",      flag: "TA", color: "red",    type: "prose-threat" },
    { key: "regional_response", label: "International Response", flag: "RI", color: "teal",   type: "prose-regional" },
    { key: "intelligence_notes",label: "Intelligence Notes",     flag: "IN", color: "purple", type: "prose-intel" },
  ],
};

// ── Charts registry ───────────────────────────────────────────────────────────
const charts = {};
// Most-recent post URL per channel, set by populatePanel before rendering source tags
let currentUrlMap = {};
const CHART_DEFAULTS = {
  responsive: true, maintainAspectRatio: false,
  animation: { duration: 900, easing: "easeOutQuart" },
  plugins: { legend: { display: false }, tooltip: { backgroundColor: "rgba(15,18,25,0.97)", borderColor: "rgba(255,255,255,0.1)", borderWidth: 1, titleColor: "#dde4f0", bodyColor: "#a8b4cc", padding: 10, titleFont: { family: "'JetBrains Mono', monospace", size: 11 }, bodyFont: { family: "'JetBrains Mono', monospace", size: 11 }, cornerRadius: 6 } },
  scales: {
    x: { grid: { color: "rgba(255,255,255,0.04)", drawBorder: false }, ticks: { color: "#5a6a88", font: { family: "'JetBrains Mono', monospace", size: 9 }, maxRotation: 0 } },
    y: { grid: { color: "rgba(255,255,255,0.04)", drawBorder: false }, ticks: { color: "#5a6a88", font: { family: "'JetBrains Mono', monospace", size: 9 }, maxTicksLimit: 4 }, beginAtZero: true },
  },
};

function makeHourLabels() {
  const now = new Date();
  return Array.from({ length: 24 }, (_, i) => { const h = new Date(now.getTime() - (23-i)*3600000); return String(h.getUTCHours()).padStart(2,"0")+":00"; });
}

function renderAlertChart(id, timelineRaw) {
  const canvas = document.getElementById(id); if (!canvas) return;
  const data = (timelineRaw||[]).map(v => v || 0);
  const cfg = { type:"bar", data: { labels: makeHourLabels(), datasets: [{ data, backgroundColor: data.map(v => v>3?"rgba(229,62,91,0.85)":v>0?"rgba(229,62,91,0.55)":"rgba(229,62,91,0.1)"), borderWidth:0, borderRadius:2, hoverBackgroundColor:"#e53e5b" }] }, options: { ...CHART_DEFAULTS, plugins: { ...CHART_DEFAULTS.plugins, tooltip: { ...CHART_DEFAULTS.plugins.tooltip, callbacks: { label: c => `Alerts: ${c.raw}` } } }, scales: { ...CHART_DEFAULTS.scales } } };
  if (charts[id]) { charts[id].data.datasets[0].data=data; charts[id].data.datasets[0].backgroundColor=cfg.data.datasets[0].backgroundColor; charts[id].update("active"); }
  else charts[id] = new Chart(canvas, cfg);
}

function renderActivityChart(id, timeline) {
  const canvas = document.getElementById(id); if (!canvas) return;
  const data = timeline||[];
  const cfg = { type:"bar", data: { labels: makeHourLabels(), datasets: [{ data, backgroundColor:"rgba(59,130,246,0.45)", borderWidth:0, borderRadius:2, hoverBackgroundColor:"rgba(59,130,246,0.9)" }] }, options: { ...CHART_DEFAULTS, plugins: { ...CHART_DEFAULTS.plugins, tooltip: { ...CHART_DEFAULTS.plugins.tooltip, callbacks: { label: c => `Messages: ${c.raw}` } } } } };
  if (charts[id]) { charts[id].data.datasets[0].data=data; charts[id].update("active"); }
  else charts[id] = new Chart(canvas, cfg);
}

function renderHistoryChart(id, entries) {
  const canvas = document.getElementById(id); if (!canvas || !entries?.length) return;
  const byMonth = {};
  entries.forEach(e => {
    const m = e.date.slice(0, 7);
    if (!byMonth[m]) byMonth[m] = { missiles: 0, drones: 0 };
    byMonth[m].missiles += e.missiles || 0;
    byMonth[m].drones   += e.drones   || 0;
  });
  const labels  = Object.keys(byMonth).sort();
  const missiles = labels.map(l => byMonth[l].missiles);
  const drones   = labels.map(l => byMonth[l].drones);
  const cfg = {
    type: "bar",
    data: { labels, datasets: [
      { label: "Missiles", data: missiles, backgroundColor: "rgba(229,62,91,0.75)",  borderWidth: 0, borderRadius: 2, stack: "s" },
      { label: "Drones",   data: drones,   backgroundColor: "rgba(59,130,246,0.55)", borderWidth: 0, borderRadius: 2, stack: "s" },
    ]},
    options: { ...CHART_DEFAULTS,
      scales: {
        x: { ...CHART_DEFAULTS.scales.x, stacked: true },
        y: { ...CHART_DEFAULTS.scales.y, stacked: true },
      },
      plugins: { ...CHART_DEFAULTS.plugins,
        legend: { display: true, labels: { color: "#5a6a88", font: { family: "'JetBrains Mono', monospace", size: 9 }, boxWidth: 10, padding: 8 } },
        tooltip: { ...CHART_DEFAULTS.plugins.tooltip, callbacks: { label: c => `${c.dataset.label}: ${c.raw.toLocaleString()}` } },
      },
    },
  };
  if (charts[id]) { charts[id].data = cfg.data; charts[id].update("active"); }
  else charts[id] = new Chart(canvas, cfg);
}

function renderChannelChart(id, msgsByChannel) {
  const canvas = document.getElementById(id); if (!canvas||!msgsByChannel) return;
  const entries = Object.entries(msgsByChannel).sort((a,b)=>b[1]-a[1]).slice(0,10);
  const labels = entries.map(([ch])=>ch), data = entries.map(([,v])=>v), max = Math.max(...data,1);
  const cfg = { type:"bar", data: { labels, datasets: [{ data, backgroundColor: data.map(v=>`rgba(16,185,129,${0.3+0.6*(v/max)})`), borderWidth:0, borderRadius:3, hoverBackgroundColor:"rgba(16,185,129,0.95)" }] }, options: { ...CHART_DEFAULTS, indexAxis:"y", plugins: { ...CHART_DEFAULTS.plugins, tooltip: { ...CHART_DEFAULTS.plugins.tooltip, callbacks: { label: c => `${c.raw} messages` } } }, scales: { x: { ...CHART_DEFAULTS.scales.x, ticks: { ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit:4 } }, y: { ...CHART_DEFAULTS.scales.y, grid:{display:false}, ticks: { color:"#a8b4cc", font:{family:"'JetBrains Mono', monospace",size:9} } } } } };
  if (charts[id]) { charts[id].data.labels=labels; charts[id].data.datasets[0].data=data; charts[id].data.datasets[0].backgroundColor=cfg.data.datasets[0].backgroundColor; charts[id].update("active"); }
  else charts[id] = new Chart(canvas, cfg);
}

// ── Scroll-spy ────────────────────────────────────────────────────────────────
function initScrollSpy(prefix) {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      const key = entry.target.id.replace("section-","");
      document.querySelectorAll(`#${prefix}-sections-nav .sections-nav-item[data-section="${key}"]`).forEach(n => n.classList.toggle("active", entry.isIntersecting));
    });
  }, { rootMargin:"-20% 0px -60% 0px", threshold:0 });
  document.querySelectorAll(`#panel-${prefix} .section-block`).forEach(el => observer.observe(el));
}

// ── News ticker ───────────────────────────────────────────────────────────────
function buildTicker(datasets) {
  const items = [];
  datasets.forEach(d => { if (!d) return; const name = d.conflict ? d.conflict.toUpperCase() : ""; (d.key_points||[]).forEach(p => items.push(`${name}: ${p}`)); });
  if (!items.length) return;
  const el = document.getElementById("tickerContent"); if (!el) return;
  const text = items.join("  ·  ");
  el.textContent = text + "   ◈   " + text;
  el.style.animation = "none"; el.offsetHeight;
  const dur = Math.max(200, items.length * 22);
  el.style.animation = `ticker-run ${dur}s linear infinite`;
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function leadBold(text) {
  const m = text.match(/^(.+?[.!?])\s+(.+)/s);
  if (m && m[1].length < text.length * 0.65) return `<strong>${m[1]}</strong> ${m[2]}`;
  return text;
}

function highlightLabels(text) {
  return text
    .replace(/(PRIMARY RISK|SECONDARY RISK|CRITICAL|MODERATE-HIGH|MODERATE|HIGH|LOW):/g, '<strong>$1:</strong>')
    .replace(/\b(CONFIRMED|UNCONFIRMED|DEVELOPING|BREAKING)\b/g, '<strong>$1</strong>');
}

function renderSourceTags(text) {
  return text.replace(/\(Source:\s*(@[\w,\s@]+)\)/gi, (_, src) => {
    const tags = src.split(',').map(s => s.trim()).filter(Boolean).map(s => {
      const handle = s.startsWith('@') ? s : '@' + s;
      const ch = handle.slice(1);
      const url = currentUrlMap[ch] || `https://t.me/${ch}`;
      return `<a class="src-tag" href="${url}" target="_blank" rel="noopener">${handle}</a>`;
    }).join(' ');
    return `<span class="src-tags">${tags}</span>`;
  });
}

// ── Section block builder ─────────────────────────────────────────────────────
function buildSectionBlock(def, sectionsData, index) {
  const raw    = sectionsData ? sectionsData[def.key] : null;
  const color  = SECTION_COLORS[def.color] || "#3b82f6";
  const isExec = def.key === "executive_summary";
  const isKD   = def.type === "keydevs";
  const isEmoji = def.flag.length > 2;

  const block = document.createElement("div");
  block.className = `section-block${isExec?" section-block--executive":""}${isKD?" open":""}`;
  block.id = `section-${def.key}`;
  block.style.animationDelay = `${index * 45}ms`;

  let countStr = "";
  if (!isExec && !isKD && raw) {
    const pts = typeof raw === "object" && raw.points ? raw.points.length : 0;
    if (pts) countStr = `<span class="section-count-badge">${pts}</span>`;
  }
  const subtitleHtml = (typeof raw === "object" && raw && raw.subtitle) ? `<div class="section-subtitle">${raw.subtitle}</div>` : "";
  const flagHtml = isEmoji
    ? `<span class="section-flag section-flag--emoji">${def.flag}</span>`
    : `<span class="section-flag flag--${def.color}">${def.flag}</span>`;

  block.innerHTML = `
    <div class="section-header">
      ${flagHtml}
      <div class="section-title-wrap">
        <div class="section-title">${def.label}${countStr}</div>
        ${subtitleHtml}
      </div>
      <button class="section-copy-btn" title="Copy section to clipboard" aria-label="Copy">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/>
        </svg>
      </button>
      <svg class="section-chevron" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <polyline points="9 18 15 12 9 6"/>
      </svg>
    </div>
    <div class="section-body"></div>
  `;

  const body = block.querySelector(".section-body");

  if (isExec) {
    const text = typeof raw === "string" ? raw : "";
    body.innerHTML = `<p class="section-summary-text">${text}</p>`;

  } else if (def.type === "points") {
    const points = (typeof raw === "object" && raw && raw.points) ? raw.points : [];
    body.innerHTML = `<div class="section-points">${
      points.map((pt, i) => `
        <div class="section-point" style="animation-delay:${i*40}ms;--point-accent:${color}">
          <div class="section-point-inner">${renderSourceTags(leadBold(pt))}</div>
        </div>`).join("")
    }</div>`;

  } else if (isKD) {
    const items = Array.isArray(raw) ? raw : [];
    body.innerHTML = `<div class="key-dev-list">${
      items.map((item, i) => `
        <div class="key-dev-item" style="animation-delay:${i*50}ms">
          <span class="key-dev-num">${i+1}</span>
          <span class="key-dev-text">${renderSourceTags(item)}</span>
        </div>`).join("")
    }</div>`;

  } else if (def.type === "prose-threat") {
    const text = typeof raw === "string" ? raw : "";
    body.innerHTML = `<p class="section-prose">${renderSourceTags(highlightLabels(text))}</p>`;

  } else if (def.type === "prose-regional") {
    const text = typeof raw === "string" ? raw : "";
    body.innerHTML = `<p class="section-prose prose--regional">${renderSourceTags(text)}</p>`;

  } else if (def.type === "prose-intel") {
    const text = typeof raw === "string" ? raw : "";
    body.innerHTML = `<p class="section-prose prose--intel">${renderSourceTags(highlightLabels(text))}</p>`;
  }

  if (!isExec && !isKD) {
    block.querySelector(".section-header").addEventListener("click", e => {
      if (e.target.closest(".section-copy-btn")) return;
      block.classList.toggle("open");
    });
  }

  const copyBtn = block.querySelector(".section-copy-btn");
  if (copyBtn) {
    copyBtn.addEventListener("click", e => {
      e.stopPropagation();
      navigator.clipboard.writeText(`${def.label}\n\n${body.innerText||body.textContent}`).then(() => {
        copyBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>`;
        setTimeout(() => { copyBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>`; }, 1800);
      }).catch(() => {});
    });
  }

  return block;
}

function buildSectionsNav(prefix, defs) {
  const nav = document.getElementById(`${prefix}-sections-nav`); if (!nav) return;
  nav.innerHTML = "";
  defs.forEach(def => {
    const color = SECTION_COLORS[def.color] || "#3b82f6";
    const item = document.createElement("a");
    item.className = "sections-nav-item"; item.dataset.section = def.key;
    if (def.key === "executive_summary" || def.type === "keydevs") item.classList.add("active");
    item.innerHTML = `<span class="nav-color-dot" style="background:${color};color:${color}"></span><span class="nav-label">${def.label}</span><span class="nav-status-dot"></span>`;
    item.addEventListener("click", e => {
      e.preventDefault();
      const target = document.getElementById(`section-${def.key}`); if (!target) return;
      if (!target.classList.contains("open") && !target.classList.contains("section-block--executive")) target.classList.add("open");
      target.scrollIntoView({ behavior:"smooth", block:"start" });
    });
    nav.appendChild(item);
  });
}

// ── Section controls (expand/collapse all + filter) ───────────────────────────
function initSectionControls(sp) {
  const expandBtn  = document.getElementById(`${sp}-expand-all`);
  const collapseBtn = document.getElementById(`${sp}-collapse-all`);
  const prefix = sp === "me" ? "middle_east" : "ukraine";
  if (expandBtn) expandBtn.addEventListener("click", () => {
    document.querySelectorAll(`#panel-${prefix} .section-block:not(.section-block--executive)`).forEach(b => b.classList.add("open"));
  });
  if (collapseBtn) collapseBtn.addEventListener("click", () => {
    document.querySelectorAll(`#panel-${prefix} .section-block:not(.section-block--executive)`).forEach(b => b.classList.remove("open"));
  });
}

function initSectionFilter(sp) {
  const input = document.getElementById(`${sp}-filter`); if (!input) return;
  const prefix = sp === "me" ? "middle_east" : "ukraine";
  input.addEventListener("input", () => {
    const q = input.value.toLowerCase().trim();
    document.querySelectorAll(`#panel-${prefix} .section-point`).forEach(pt => {
      const visible = !q || pt.textContent.toLowerCase().includes(q);
      pt.style.display = visible ? "" : "none";
    });
    document.querySelectorAll(`#panel-${prefix} .section-block`).forEach(block => {
      if (block.classList.contains("section-block--executive")) return;
      const pts = block.querySelectorAll(".section-point");
      if (!pts.length) return;
      const anyVisible = [...pts].some(p => p.style.display !== "none");
      block.style.opacity = anyVisible || !q ? "" : "0.3";
      if (anyVisible && q) block.classList.add("open");
    });
  });
}

// ── Populate panel ────────────────────────────────────────────────────────────
function populatePanel(prefix, data) {
  const sp   = prefix === "middle_east" ? "me" : "ua";
  const defs = SECTION_DEFS[prefix];

  // Update source-tag URL map so citations link to actual recent posts
  currentUrlMap = data.recent_post_urls || {};

  animateValue(`${sp}-red-alerts`, 0, data.red_alerts || 0, 800);
  animateValue(`${sp}-msg-count`,  0, data.message_count||0, 1000);

  const chEl = document.getElementById(`${sp}-channel-count`);
  if (chEl) chEl.textContent = `${(data.channels||[]).length} channels`;

  // Sentiment badge in panel controls
  const sentBadge = document.getElementById(`${sp}-sentiment-badge`);
  if (sentBadge) {
    const sent = (data.sentiment || "unknown").toLowerCase();
    sentBadge.textContent = sent.toUpperCase();
    sentBadge.dataset.sentiment = sent;
  }

  const container = document.getElementById(`${sp}-sections-content`);
  if (container) {
    container.innerHTML = "";
    defs.forEach((def, i) => container.appendChild(buildSectionBlock(def, data.sections||{}, i)));
  }

  buildSectionsNav(sp, defs);
  setTimeout(() => initScrollSpy(prefix), 200);
  initSectionControls(sp);
  initSectionFilter(sp);

  renderAlertChart(`${sp}-chart-alerts`,    data.red_alerts_timeline);
  renderActivityChart(`${sp}-chart-activity`, data.combined_activity_timeline);
  renderChannelChart(`${sp}-chart-channels`,  data.messages_by_channel);

  const sourcesList = document.getElementById(`${sp}-sources-list`);
  if (sourcesList) {
    sourcesList.innerHTML = (data.channels||[])
      .map(ch => `<li><a href="https://t.me/${ch}" target="_blank" rel="noopener noreferrer">@${ch}</a></li>`)
      .join("");
  }

  // Wire "MESSAGES ANALYSED" card → sources modal
  const msgCard = document.getElementById(`${sp}-stat-messages`);
  if (msgCard) {
    const fresh = msgCard.cloneNode(true);
    msgCard.parentNode.replaceChild(fresh, msgCard);
    fresh.addEventListener("click", () => sourcesModal.open(data.channels, data.messages_by_channel));
    fresh.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sourcesModal.open(data.channels, data.messages_by_channel); } });
  }
}

// ── Animated counter ──────────────────────────────────────────────────────────
function animateValue(id, from, to, duration) {
  const el = document.getElementById(id); if (!el) return;
  const start = performance.now();
  function step(now) {
    const p = Math.min((now-start)/duration, 1), ease = 1-Math.pow(1-p, 3);
    el.textContent = Math.round(from+(to-from)*ease).toLocaleString();
    if (p < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── Refresh toast ─────────────────────────────────────────────────────────────
function showToast(msg) {
  let el = document.querySelector(".refresh-toast");
  if (!el) { el = document.createElement("div"); el.className = "refresh-toast"; el.innerHTML = `<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> <span></span>`; document.body.appendChild(el); }
  el.querySelector("span").textContent = msg;
  el.classList.add("show"); setTimeout(() => el.classList.remove("show"), 3500);
}

// ── Sources modal ─────────────────────────────────────────────────────────────
const sourcesModal = (function () {
  const backdrop = document.getElementById("sourcesModalBackdrop");
  const closeBtn  = document.getElementById("sourcesModalClose");
  const list      = document.getElementById("sourcesModalList");
  let isOpen = false;

  function open(channels, msgsByChannel) {
    if (!backdrop || !list) return;
    list.innerHTML = (channels || []).map(ch => {
      const cnt = (msgsByChannel || {})[`@${ch}`] || 0;
      return `<li><a href="https://t.me/${ch}" target="_blank" rel="noopener noreferrer">@${ch}${cnt ? `<span class="sources-modal-count">${cnt} msgs</span>` : ""}</a></li>`;
    }).join("");
    backdrop.setAttribute("aria-hidden", "false");
    backdrop.classList.add("open");
    isOpen = true;
    document.body.style.overflow = "hidden";
  }

  function close() {
    if (!backdrop) return;
    backdrop.classList.remove("open");
    backdrop.setAttribute("aria-hidden", "true");
    isOpen = false;
    document.body.style.overflow = "";
  }

  if (closeBtn) closeBtn.addEventListener("click", close);
  if (backdrop) backdrop.addEventListener("click", e => { if (e.target === backdrop) close(); });
  document.addEventListener("keydown", e => { if (isOpen && e.key === "Escape") close(); });

  return { open, close };
})();

// ── Auto-refresh ──────────────────────────────────────────────────────────────
function scheduleAutoRefresh(updatedAt) {
  const ONE_HOUR = 60*60*1000, elapsed = Date.now()-new Date(updatedAt).getTime();
  const wait = Math.max(ONE_HOUR-elapsed, 60000);
  setTimeout(async () => {
    try {
      delete dataCache["middle_east"]; delete dataCache["ukraine"];
      const [me, ua] = await Promise.all([loadConflict("middle_east"), loadConflict("ukraine")]);
      if (me) { populatePanel("middle_east", me); buildTicker([me, ua]); }
      if (ua) populatePanel("ukraine", ua);
      if (me) updateHeaderForConflict(activeTab === "ukraine" ? ua : me);
      showToast("Data refreshed"); scheduleAutoRefresh(new Date().toISOString());
    } catch (e) { console.warn("Auto-refresh failed:", e); scheduleAutoRefresh(new Date().toISOString()); }
  }, wait);
}

// ── Countdown ─────────────────────────────────────────────────────────────────
function startCountdown(updatedAt) {
  const ONE_HOUR = 60*60*1000, updated = new Date(updatedAt).getTime();
  function tick() {
    const remaining = ONE_HOUR-(Date.now()-updated);
    if (remaining <= 0) { document.getElementById("countdown").textContent = "now"; return; }
    const m = Math.floor((remaining%3600000)/60000), s = Math.floor((remaining%60000)/1000);
    document.getElementById("countdown").textContent = `${String(m).padStart(2,"0")}m ${String(s).padStart(2,"0")}s`;
  }
  tick(); setInterval(tick, 1000);
}

// ── Header datetime ───────────────────────────────────────────────────────────
function updateDatetime() {
  const el = document.getElementById("headerDatetime"); if (!el) return;
  el.textContent = new Date().toLocaleString("en-GB", { day:"2-digit", month:"short", year:"numeric", hour:"2-digit", minute:"2-digit", timeZone:"UTC", timeZoneName:"short" });
}

// ── Data loading ──────────────────────────────────────────────────────────────
const dataCache = {};
async function loadConflict(key) {
  if (dataCache[key]) return dataCache[key];
  try {
    const resp = await fetch(`data/${key}.json?t=${Date.now()}`);
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const data = await resp.json(); dataCache[key] = data; return data;
  } catch (e) { console.error(`Failed to load ${key}:`, e); return null; }
}

// ── Tab switching ─────────────────────────────────────────────────────────────
let activeTab = "middle_east";
function switchTab(key) {
  if (key === activeTab) return; activeTab = key;
  document.querySelectorAll(".tab-btn").forEach(b => b.classList.toggle("active", b.dataset.tab === key));
  document.querySelectorAll(".conflict-panel").forEach(p => {
    const visible = p.id === `panel-${key}`;
    p.classList.toggle("hidden", !visible);
    if (visible) { p.style.animation="none"; p.offsetHeight; p.style.animation=""; }
  });
  if (dataCache[key]) updateHeaderForConflict(dataCache[key]);
  else loadConflict(key).then(d => { if (d) { populatePanel(key, d); updateHeaderForConflict(d); } });
}

function updateHeaderForConflict(data) {
  // Logo area always shows "War Summary" — no dynamic update
}

// ── Init ──────────────────────────────────────────────────────────────────────
async function loadUkraineHistory() {
  try {
    const resp = await fetch(`data/ukraine_history.json?t=${Date.now()}`);
    if (!resp.ok) return null;
    return await resp.json();
  } catch { return null; }
}

async function init() {
  updateDatetime(); setInterval(updateDatetime, 30000);
  document.querySelectorAll(".tab-btn").forEach(btn => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));

  const [me, ua, history] = await Promise.all([
    loadConflict("middle_east"),
    loadConflict("ukraine"),
    loadUkraineHistory(),
  ]);
  if (me) { populatePanel("middle_east", me); startCountdown(me.updated_at); scheduleAutoRefresh(me.updated_at); }
  if (ua) populatePanel("ukraine", ua);
  if (history?.entries?.length) renderHistoryChart("ua-chart-history", history.entries);
  buildTicker([me, ua]);
}

document.addEventListener("DOMContentLoaded", init);
