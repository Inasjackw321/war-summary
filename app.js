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

// ── Section geo (time + weather) ──────────────────────────────────────────────
const SECTION_GEO = {
  iran:          { city: "Tehran",       lat: 35.69,  lon: 51.39,  tz: "Asia/Tehran"    },
  israel:        { city: "Tel Aviv",     lat: 32.08,  lon: 34.78,  tz: "Asia/Jerusalem" },
  gaza_west_bank:{ city: "Gaza",         lat: 31.52,  lon: 34.45,  tz: "Asia/Jerusalem" },
  lebanon:       { city: "Beirut",       lat: 33.89,  lon: 35.50,  tz: "Asia/Beirut"    },
  syria_iraq:    { city: "Damascus",     lat: 33.51,  lon: 36.29,  tz: "Asia/Damascus"  },
  gulf_states:   { city: "Dubai",        lat: 25.20,  lon: 55.27,  tz: "Asia/Dubai"     },
  ukraine:       { city: "Kyiv",         lat: 50.45,  lon: 30.52,  tz: "Europe/Kiev"    },
  russia:        { city: "Moscow",       lat: 55.75,  lon: 37.62,  tz: "Europe/Moscow"  },
  eastern_front: { city: "Donetsk",      lat: 48.02,  lon: 37.80,  tz: "Europe/Kiev"    },
  northern_front:{ city: "Chernihiv",    lat: 51.50,  lon: 31.30,  tz: "Europe/Kiev"    },
  southern_front:{ city: "Zaporizhzhia", lat: 47.84,  lon: 35.14,  tz: "Europe/Kiev"    },
  air_war:       { city: "Kyiv",         lat: 50.45,  lon: 30.52,  tz: "Europe/Kiev"    },
};

const _weatherCache = {};   // key → { temp, code, fetchedAt }

function _wmoEmoji(code) {
  if (code === 0)           return "☀️";
  if (code <= 2)            return "🌤️";
  if (code === 3)           return "☁️";
  if (code <= 48)           return "🌫️";
  if (code <= 55)           return "🌦️";
  if (code <= 65)           return "🌧️";
  if (code <= 75)           return "🌨️";
  if (code <= 82)           return "🌧️";
  return "⛈️";
}

function _localTime(tz) {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit", minute: "2-digit", timeZone: tz,
  }).format(new Date());
}

async function fetchSectionWeather(key) {
  const geo = SECTION_GEO[key];
  if (!geo) return null;
  const cached = _weatherCache[key];
  if (cached && Date.now() - cached.fetchedAt < 30 * 60 * 1000) return cached;
  try {
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${geo.lat}&longitude=${geo.lon}&current=temperature_2m,weather_code&timezone=auto&forecast_days=1`;
    const r = await fetch(url);
    if (!r.ok) return null;
    const d = await r.json();
    const result = {
      temp: Math.round(d.current.temperature_2m),
      code: d.current.weather_code,
      fetchedAt: Date.now(),
    };
    _weatherCache[key] = result;
    return result;
  } catch { return null; }
}

function updateGeoBar(key) {
  const bar = document.getElementById(`geobar-${key}`);
  if (!bar) return;
  const geo = SECTION_GEO[key];
  if (!geo) return;
  const timeEl = bar.querySelector(".sgb-time");
  if (timeEl) timeEl.textContent = _localTime(geo.tz);
}

// Called once per panel load; fetches weather + sets up per-minute time refresh
async function initGeoBar(key) {
  const bar = document.getElementById(`geobar-${key}`);
  if (!bar) return;
  const geo = SECTION_GEO[key];
  if (!geo) return;

  // Render time immediately (no fetch needed)
  bar.querySelector(".sgb-time").textContent = _localTime(geo.tz);
  bar.querySelector(".sgb-city").textContent = geo.city;

  // Fetch weather async
  const w = await fetchSectionWeather(key);
  if (w) {
    bar.querySelector(".sgb-temp").textContent = `${w.temp}°C`;
    bar.querySelector(".sgb-icon").textContent = _wmoEmoji(w.code);
  }
  bar.classList.remove("sgb--loading");
}

// ── Charts registry ───────────────────────────────────────────────────────────
const charts = {};
// Most-recent post URL per channel, set by populatePanel before rendering source tags
let currentUrlMap = {};
let currentPostImages = {};
let currentAllMedia = {};   // {channel/postId: {localPath, postUrl}}

// ── Section icons ─────────────────────────────────────────────────────────────
const SECTION_ICONS = {
  "EX": `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>`,
  "KD": `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>`,
  "TA": `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`,
  "RI": `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z"/></svg>`,
  "IN": `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/><circle cx="12" cy="12" r="3"/></svg>`,
  "EF": `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg>`,
  "NF": `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="19" x2="12" y2="5"/><polyline points="5 12 12 5 19 12"/></svg>`,
  "SF": `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></svg>`,
  "AW": `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M17.8 19.2L16 11l3.5-3.5C21 6 21.5 4 21 3c-1-.5-3 0-4.5 1.5L13 8 4.8 6.2c-.5-.1-.9.1-1.1.5l-.3.5c-.2.5-.1 1 .3 1.3L9 12l-2 3H4l-1 1 3 2 2 3 1-1v-3l3-2 3.5 5.3c.3.4.8.5 1.3.3l.5-.2c.4-.3.6-.7.5-1.2z"/></svg>`,
};

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

function renderTodayAttackChart(id, missiles, drones) {
  const canvas = document.getElementById(id); if (!canvas) return;
  const cfg = {
    type: "bar",
    data: { labels: ["Missiles", "Drones"], datasets: [{
      data: [missiles || 0, drones || 0],
      backgroundColor: ["rgba(229,62,91,0.75)", "rgba(59,130,246,0.55)"],
      borderWidth: 0, borderRadius: 4,
    }]},
    options: { ...CHART_DEFAULTS, indexAxis: "y",
      plugins: { ...CHART_DEFAULTS.plugins,
        legend: { display: false },
        tooltip: { ...CHART_DEFAULTS.plugins.tooltip, callbacks: { label: c => `${c.raw} launched` } },
      },
      scales: {
        x: { ...CHART_DEFAULTS.scales.x, ticks: { ...CHART_DEFAULTS.scales.x.ticks, maxTicksLimit: 5 } },
        y: { ...CHART_DEFAULTS.scales.y, grid: { display: false }, ticks: { color: "#a8b4cc", font: { family: "'JetBrains Mono', monospace", size: 10 } } },
      },
    },
  };
  if (charts[id]) { charts[id].data = cfg.data; charts[id].update("active"); }
  else charts[id] = new Chart(canvas, cfg);
}

function renderActivityChart(id, timeline) {
  const canvas = document.getElementById(id); if (!canvas) return;
  const data = timeline||[];
  const cfg = { type:"bar", data: { labels: makeHourLabels(), datasets: [{ data, backgroundColor:"rgba(59,130,246,0.45)", borderWidth:0, borderRadius:2, hoverBackgroundColor:"rgba(59,130,246,0.9)" }] }, options: { ...CHART_DEFAULTS, plugins: { ...CHART_DEFAULTS.plugins, tooltip: { ...CHART_DEFAULTS.plugins.tooltip, callbacks: { label: c => `Messages: ${c.raw}` } } } } };
  if (charts[id]) { charts[id].data.datasets[0].data=data; charts[id].update("active"); }
  else charts[id] = new Chart(canvas, cfg);
}



const MEDIA_CHANNELS = new Set(["Faytuks_Network", "manniefabian", "idf_telegram", "kpszsu", "eRadarrua", "VahidOnline", "amitsegal"]);


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

// Defined here so renderSourceTags can reference it
const BIASED_SOURCES_LOWER = new Set(["sharghDaily", "naya_foriraq", "presstv", "tass_agency", "rasedal3ado138e"].map(s => s.toLowerCase()));
function isBiasedSource(ch) { return BIASED_SOURCES_LOWER.has(ch.toLowerCase()); }

function renderSourceTags(text) {
  // Matches: "(Source: @ch/123)", "(Source: @ch/123-456)", "(@ch)", "(ch/123)" — requires @ or /digits
  return text.replace(
    /\((?:Source:\s*)?((?:@?[\w]+(?:\/[\d-]+)?)(?:[,;]\s*(?:@?[\w]+(?:\/[\d-]+)?))*)\)/gi,
    (match, src) => {
      if (!src.includes('@') && !src.includes('/')) return match;
      const tags = src.split(/[,;]/).map(s => s.trim()).filter(Boolean).map(s => {
        const raw = s.startsWith('@') ? s.slice(1) : s;
        const slash = raw.indexOf('/');
        let ch, url;
        if (slash !== -1) {
          ch = raw.slice(0, slash);
          const idPart = raw.slice(slash + 1).split('-')[0];
          url = `https://t.me/${ch}/${idPart}`;
        } else {
          ch = raw;
          url = currentUrlMap[ch] || `https://t.me/${ch}`;
        }
        const biased = isBiasedSource(ch);
        const warnHtml = biased
          ? `<span class="source-warn src-tag-warn"><svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></span>`
          : '';
        // Check if this specific post has an associated image
        const postKey = slash !== -1 ? `${ch}/${raw.slice(slash + 1).split('-')[0]}` : null;
        const imgPostUrl = postKey ? currentPostImages[postKey] : null;
        return `<a class="src-tag${biased?' src-tag--biased':''}" href="${url}" target="_blank" rel="noopener"${biased?` data-biased="1" data-ch="${ch}" data-url="${url}"`:''}> @${ch}</a>${warnHtml}`;
      }).join('');
      return `<span class="src-tags">${tags}</span>`;
    }
  );
}

// Build a lowercase → canonical key map once per panel population, cleared in populatePanel
let _mediaKeysByLower = {};   // lowercase key → canonical key

function _rebuildMediaIndex() {
  _mediaKeysByLower = {};
  for (const k of Object.keys(currentAllMedia)) {
    _mediaKeysByLower[k.toLowerCase()] = k;
  }
}

function extractImageKeys(rawText) {
  const results = [];
  const seenKeys  = new Set();
  const seenPaths = new Set();

  // Match (Source: @channel/postId) citations — exact first, then case-insensitive fallback
  const re = /\((?:Source:\s*)?@?([\w]+)\/([\d]+)/gi;
  let m;
  while ((m = re.exec(rawText)) !== null) {
    const chRaw = m[1], pid = m[2];
    const keyExact = `${chRaw}/${pid}`;
    const canonKey = currentAllMedia[keyExact]
      ? keyExact
      : (_mediaKeysByLower[keyExact.toLowerCase()] || null);
    if (!canonKey || seenKeys.has(canonKey)) continue;
    const entry = currentAllMedia[canonKey];
    if (!entry) continue;
    // Dedup by file path too — aliases may point to the same image
    if (entry.localPath && seenPaths.has(entry.localPath)) continue;
    seenKeys.add(canonKey);
    if (entry.localPath) seenPaths.add(entry.localPath);
    results.push({
      path: entry.localPath,
      ch: canonKey.split('/')[0],
      key: canonKey,
      postUrl: entry.postUrl || `https://t.me/${chRaw}/${pid}`,
    });
  }

  return results;
}

function openLocalMediaLightbox(src, postUrl) {
  const existing = document.getElementById("mediaLightbox");
  if (existing) existing.remove();
  const lb = document.createElement("div");
  lb.id = "mediaLightbox";
  lb.className = "media-lightbox";
  const linkHtml = postUrl ? `<a class="media-lightbox-open-link" href="${postUrl}" target="_blank" rel="noopener">Open on Telegram ↗</a>` : "";
  lb.innerHTML = `<div class="media-lightbox-inner media-lightbox-local">
    <div class="media-lightbox-topbar">
      ${linkHtml}
      <div class="media-lightbox-close">✕</div>
    </div>
    <img src="${src}" alt="Post media">
  </div>`;
  document.body.appendChild(lb);
  lb.addEventListener("click", e => { if (e.target === lb || e.target.closest(".media-lightbox-close")) lb.remove(); });
  document.addEventListener("keydown", function h(e) { if (e.key === "Escape") { lb.remove(); document.removeEventListener("keydown", h); } });
}

function imgMediaHtml(path, ch, postUrl) {
  if (path) {
    return `<figure class="spm-thumb" data-src="${path}" data-posturl="${postUrl}">
      <img src="${path}" alt="" loading="lazy">
      <figcaption>@${ch}</figcaption>
    </figure>`;
  }
  const icon = `<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8.5" cy="8.5" r="1.5"/><polyline points="21 15 16 10 5 21"/></svg>`;
  return `<a class="spm-tg-link" href="${postUrl}" target="_blank" rel="noopener">${icon} @${ch} ↗</a>`;
}

// Returns filtered imgs (deduped within section, capped), mutates seenKeys + counter
function filterImgs(candidates, seenKeys, counter, MAX) {
  const out = [];
  for (const img of candidates) {
    if (counter.n >= MAX || seenKeys.has(img.key)) continue;
    seenKeys.add(img.key);
    counter.n++;
    out.push(img);
  }
  return out;
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
    : `<span class="section-flag section-flag--icon flag--${def.color}">${SECTION_ICONS[def.flag] || def.flag}</span>`;

  const hasGeo = !!SECTION_GEO[def.key];
  const geoBarHtml = hasGeo ? `
    <div class="section-geo-bar sgb--loading" id="geobar-${def.key}">
      <span class="sgb-icon">—</span>
      <span class="sgb-temp"></span>
      <span class="sgb-sep">·</span>
      <span class="sgb-city"></span>
      <span class="sgb-sep">·</span>
      <span class="sgb-time"></span> <span class="sgb-label">local</span>
    </div>` : "";

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
    ${geoBarHtml}
    <div class="section-body"></div>
  `;

  const body = block.querySelector(".section-body");

  if (isExec) {
    const text = typeof raw === "string" ? raw : "";
    body.innerHTML = `<p class="section-summary-text">${text}</p>`;

  } else if (def.type === "points") {
    const points = (typeof raw === "object" && raw && raw.points) ? raw.points : [];
    const seenImgKeys = new Set(); const imgCounter = { n: 0 };
    body.innerHTML = `<div class="section-points">${
      points.map((pt, i) => {
        const imgs = filterImgs(extractImageKeys(pt), seenImgKeys, imgCounter, 3);
        const mediaHtml = imgs.length
          ? `<div class="section-point-media">${imgs.map(({path,ch,postUrl}) => imgMediaHtml(path,ch,postUrl)).join("")}</div>`
          : "";
        return `<div class="section-point" style="animation-delay:${i*40}ms;--point-accent:${color}">
          <div class="section-point-inner">${renderSourceTags(leadBold(pt))}</div>
          ${mediaHtml}
        </div>`;
      }).join("")
    }</div>`;

  } else if (isKD) {
    const items = Array.isArray(raw) ? raw : [];
    const seenImgKeys = new Set(); const imgCounter = { n: 0 };
    body.innerHTML = `<div class="key-dev-list">${
      items.map((item, i) => {
        const imgs = filterImgs(extractImageKeys(item), seenImgKeys, imgCounter, 3);
        const mediaHtml = imgs.length
          ? `<div class="section-point-media">${imgs.map(({path,ch,postUrl}) => imgMediaHtml(path,ch,postUrl)).join("")}</div>`
          : "";
        return `<div class="key-dev-item" style="animation-delay:${i*50}ms">
          <span class="key-dev-num">${i+1}</span>
          <span class="key-dev-text">${renderSourceTags(item)}</span>
          ${mediaHtml}
        </div>`;
      }).join("")
    }</div>`;

  } else if (def.type === "prose-threat" || def.type === "prose-regional" || def.type === "prose-intel") {
    const cls = def.type === "prose-regional" ? " prose--regional" : def.type === "prose-intel" ? " prose--intel" : "";
    const hl  = def.type === "prose-regional" ? (t => t) : highlightLabels;
    if (typeof raw === "string" && raw) {
      body.innerHTML = `<p class="section-prose${cls}">${renderSourceTags(hl(raw))}</p>`;
    } else if (raw?.points?.length) {
      body.innerHTML = `<div class="section-points">${
        raw.points.map((pt, i) => `
          <div class="section-point" style="animation-delay:${i*40}ms;--point-accent:${color}">
            <div class="section-point-inner">${renderSourceTags(leadBold(pt))}</div>
          </div>`).join("")
      }</div>`;
    }
  }

  // Toggle open/close on header click
  const header = block.querySelector(".section-header");
  if (header && !isExec) {
    header.addEventListener("click", e => {
      if (e.target.closest(".section-copy-btn")) return;
      block.classList.toggle("open");
    });
  }

  // Copy section content
  const copyBtn = block.querySelector(".section-copy-btn");
  if (copyBtn) {
    copyBtn.addEventListener("click", e => {
      e.stopPropagation();
      const text = body.innerText || body.textContent || "";
      navigator.clipboard?.writeText(text).then(() => {
        copyBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="20 6 9 17 4 12"/></svg>`;
        setTimeout(() => { copyBtn.innerHTML = `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="9" y="9" width="13" height="13" rx="2"/><path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1"/></svg>`; }, 1800);
      });
    });
  }

  return block;
}

// ── Sections nav builder ──────────────────────────────────────────────────────
function buildSectionsNav(sp, defs) {
  const nav = document.getElementById(`${sp}-sections-nav`); if (!nav) return;
  nav.innerHTML = "";
  defs.forEach(def => {
    const item = document.createElement("div");
    item.className = "sections-nav-item";
    item.dataset.section = def.key;
    item.textContent = def.label;
    item.addEventListener("click", () => {
      const el = document.getElementById(`section-${def.key}`);
      if (el) { el.scrollIntoView({ behavior: "smooth", block: "start" }); el.classList.add("open"); }
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
  currentPostImages = data.post_images || {};
  // Build combined media lookup: Telegram URL + local path (if downloaded)
  currentAllMedia = {};
  (data.media || []).filter(m => MEDIA_CHANNELS.has(m.channel)).forEach(m => {
    const key = `${m.channel}/${m.post_id}`;
    currentAllMedia[key] = { localPath: currentPostImages[key] || null, postUrl: m.post_url };
  });
  Object.entries(currentPostImages).forEach(([key, path]) => {
    if (!currentAllMedia[key]) currentAllMedia[key] = { localPath: path, postUrl: null };
  });
  _rebuildMediaIndex();

  // Middle East: divide by 2. Ukraine: show missiles + drones as separate counters
  const alertCount = prefix === "middle_east" ? Math.ceil((data.red_alerts || 0) / 2) : (data.red_alerts || 0);
  if (prefix === "ukraine") {
    animateValue(`ua-missiles`, 0, data.missiles || 0, 800);
    animateValue(`ua-drones`, 0, data.drones || 0, 800);
  } else {
    animateValue(`${sp}-red-alerts`, 0, alertCount, 800);
  }

  // Pulse alert card when count is non-zero
  const alertCard = document.getElementById(`${sp}-stat-alerts`);
  if (alertCard) alertCard.classList.toggle("stat-card--pulsing", alertCount > 0);

  const chEl = document.getElementById(`${sp}-channel-count`);
  if (chEl) chEl.textContent = `${(data.channels||[]).length} channels`;

  // Data freshness timestamp
  const tsEl = document.getElementById(`${sp}-data-time`);
  if (tsEl && data.updated_at) {
    const d = new Date(data.updated_at);
    tsEl.textContent = `${String(d.getUTCHours()).padStart(2,"0")}:${String(d.getUTCMinutes()).padStart(2,"0")} UTC`;
  }

  // Sentiment badge + threat level bar
  const sentBadge = document.getElementById(`${sp}-sentiment-badge`);
  if (sentBadge) {
    const sent = (data.sentiment || "unknown").toLowerCase();
    sentBadge.textContent = sent.toUpperCase();
    sentBadge.dataset.sentiment = sent;
    const fill = document.getElementById(`${sp}-threat-fill`);
    if (fill) {
      const pct = { escalating:90, volatile:70, active:70, tense:60, stable:35, calm:20, neutral:50 }[sent] || 50;
      const col = { escalating:"#e53e5b", volatile:"#f59e0b", active:"#f59e0b", tense:"#f59e0b", stable:"#10b981", calm:"#3b82f6", neutral:"#64748b" }[sent] || "#3b82f6";
      fill.style.width = `${pct}%`;
      fill.style.background = `linear-gradient(90deg, ${col}88, ${col})`;
    }
  }

  const container = document.getElementById(`${sp}-sections-content`);
  if (container) {
    container.innerHTML = "";
    defs.forEach((def, i) => {
      container.appendChild(buildSectionBlock(def, data.sections||{}, i));
      if (SECTION_GEO[def.key]) initGeoBar(def.key);
    });
  }

  buildSectionsNav(sp, defs);
  setTimeout(() => initScrollSpy(prefix), 200);
  initSectionControls(sp);
  initSectionFilter(sp);

  if (prefix === "ukraine") {
    renderTodayAttackChart(`ua-chart-alerts`, data.missiles, data.drones);
    renderAlertChart(`ua-chart-history`, data.kpszsu_timeline || []);
  } else {
    const alertTimeline = (data.red_alerts_timeline || []).map(v => Math.round((v || 0) / 2));
    renderAlertChart(`${sp}-chart-alerts`, alertTimeline);
  }
  renderActivityChart(`${sp}-chart-activity`, data.combined_activity_timeline);
  renderChannelChart(`${sp}-chart-channels`,  data.messages_by_channel);

  const sourcesList = document.getElementById(`${sp}-sources-list`);
  if (sourcesList) {
    const warnSvg = `<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
    sourcesList.innerHTML = (data.channels||[]).map(ch => {
      const isBiased = isBiasedSource(ch);
      const url = `https://t.me/${ch}`;
      const interceptAttr = isBiased ? ` data-biased="1" data-ch="${ch}" data-url="${url}"` : "";
      const warnHtml = isBiased ? `<span class="src-list-warn">${warnSvg}</span>` : "";
      return `<li class="${isBiased?"src-list-item--biased":""}"><a href="${url}" target="_blank" rel="noopener noreferrer"${interceptAttr}>@${ch}${warnHtml}</a></li>`;
    }).join("");
    sourcesList.querySelectorAll("a[data-biased]").forEach(a => {
      a.addEventListener("click", e => { e.preventDefault(); showSourceWarningPopup(a.dataset.ch, a.dataset.url); });
    });
  }

  // Wire "MESSAGES ANALYSED" card → sources modal.
  const msgCard = document.getElementById(`${sp}-stat-messages`);
  if (msgCard) {
    const fresh = msgCard.cloneNode(true);
    msgCard.parentNode.replaceChild(fresh, msgCard);
    fresh.addEventListener("click", () => sourcesModal.open(data.channels, data.messages_by_channel));
    fresh.addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); sourcesModal.open(data.channels, data.messages_by_channel); } });
    animateValue(`${sp}-msg-count`, 0, data.message_count || 0, 1000);
  }
  // Re-run twemoji on newly injected content so flag emojis render as images
  if (typeof twemoji !== "undefined") twemoji.parse(document.body, { folder: "svg", ext: ".svg" });
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
// isBiasedSource() defined earlier alongside renderSourceTags
const WARN_TIP = "This source may provide inaccurate or biased information. Always double-check and cross-reference reports with other sources.";

// JS tooltip to avoid overflow-clipping inside the modal
(function initSourceTooltip() {
  const tip = document.createElement("div");
  tip.className = "source-tooltip";
  document.body.appendChild(tip);
  let hideTimer;
  document.addEventListener("mouseover", e => {
    const w = e.target.closest(".source-warn");
    if (!w) return;
    clearTimeout(hideTimer);
    tip.textContent = WARN_TIP;
    tip.classList.add("visible");
    const r = w.getBoundingClientRect();
    tip.style.left = Math.min(r.left + r.width/2 - tip.offsetWidth/2, window.innerWidth - tip.offsetWidth - 8) + "px";
    tip.style.top = (r.top - tip.offsetHeight - 8) + "px";
  });
  document.addEventListener("mouseout", e => {
    if (e.target.closest(".source-warn")) hideTimer = setTimeout(() => tip.classList.remove("visible"), 150);
  });
})();

// Warning popup when clicking a biased source
function showSourceWarningPopup(ch, url) {
  const existing = document.getElementById("sourceWarnPopup");
  if (existing) existing.remove();
  const el = document.createElement("div");
  el.id = "sourceWarnPopup";
  el.className = "source-warn-popup";
  el.innerHTML = `
    <div class="source-warn-popup-inner">
      <div class="source-warn-popup-icon"><svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></div>
      <div class="source-warn-popup-title">Source Advisory — @${ch}</div>
      <div class="source-warn-popup-body">${WARN_TIP}</div>
      <div class="source-warn-popup-actions">
        <button class="source-warn-cancel">Cancel</button>
        <a class="source-warn-continue" href="${url}" target="_blank" rel="noopener noreferrer">Continue to source</a>
      </div>
    </div>`;
  document.body.appendChild(el);
  el.querySelector(".source-warn-cancel").addEventListener("click", () => el.remove());
  el.addEventListener("click", e => { if (e.target === el) el.remove(); });
}

const WARN_ICON = `<span class="source-warn"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg></span>`;

const sourcesModal = (function () {
  const backdrop = document.getElementById("sourcesModalBackdrop");
  const closeBtn  = document.getElementById("sourcesModalClose");
  const list      = document.getElementById("sourcesModalList");
  let isOpen = false;

  function open(channels, msgsByChannel) {
    if (!backdrop || !list) return;
    const warnSvg = `<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="#f59e0b" stroke-width="2.5"><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>`;
    list.innerHTML = (channels || []).map(ch => {
      const cnt = (msgsByChannel || {})[`@${ch}`] || 0;
      const isBiased = isBiasedSource(ch);
      const url = `https://t.me/${ch}`;
      const interceptAttr = isBiased ? ` data-biased="1" data-ch="${ch}" data-url="${url}"` : "";
      const warnHtml = isBiased ? `<span class="src-modal-warn">${warnSvg}</span>` : "";
      const cntHtml = cnt ? `<span class="sources-modal-count">${cnt} msgs</span>` : "";
      return `<li class="${isBiased?"src-modal-item--biased":""}"><a href="${url}" target="_blank" rel="noopener noreferrer"${interceptAttr}>@${ch}${cntHtml}${warnHtml}</a></li>`;
    }).join("");
    // Intercept clicks on biased source links
    list.querySelectorAll("a[data-biased]").forEach(a => {
      a.addEventListener("click", e => {
        e.preventDefault();
        showSourceWarningPopup(a.dataset.ch, a.dataset.url);
      });
    });
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

// ── Auto-refresh ─────────────────────────────────────────────────────────────
let _lastKnownUpdatedAt = null;
let _autoRefreshInterval = null;

function _snapshotItems(sp) {
  const texts = new Set();
  document.querySelectorAll(`#${sp}-sections-content .section-point, #${sp}-sections-content .key-dev-item`).forEach(el => {
    texts.add(el.textContent.replace(/\s+/g, " ").trim().slice(0, 100));
  });
  return texts;
}

function _animateNewItems(sp, prev) {
  document.querySelectorAll(`#${sp}-sections-content .section-point, #${sp}-sections-content .key-dev-item`).forEach(el => {
    const t = el.textContent.replace(/\s+/g, " ").trim().slice(0, 100);
    if (!prev.has(t)) el.classList.add("item--just-added");
  });
}

async function checkForRefresh() {
  try {
    const r = await fetch("data/middle_east.json?_=" + Date.now());
    if (!r.ok) return false;
    const fresh = await r.json();
    if (fresh.updated_at && fresh.updated_at !== _lastKnownUpdatedAt) {
      _lastKnownUpdatedAt = fresh.updated_at;

      const scrollY = window.scrollY;
      const prevMe = _snapshotItems("me");
      const prevUa = _snapshotItems("ua");

      delete dataCache["middle_east"]; delete dataCache["ukraine"];
      const [me, ua] = await Promise.all([loadConflict("middle_east"), loadConflict("ukraine")]);
      if (me) { populatePanel("middle_east", me); buildTicker([me, ua]); }
      if (ua) populatePanel("ukraine", ua);
      if (me) updateHeaderForConflict(activeTab === "ukraine" ? ua : me);

      window.scrollTo({ top: scrollY, behavior: "instant" });
      _animateNewItems("me", prevMe);
      _animateNewItems("ua", prevUa);

      showToast("Data refreshed");
      return true;
    }
    return false;
  } catch (e) { console.warn("Auto-refresh check failed:", e); return false; }
}

function scheduleAutoRefresh(updatedAt) {
  if (!_lastKnownUpdatedAt) _lastKnownUpdatedAt = updatedAt;
  if (_autoRefreshInterval) return;
  _autoRefreshInterval = setInterval(checkForRefresh, 5 * 60 * 1000);
}

// ── Countdown ─────────────────────────────────────────────────────────────────
function startCountdown(updatedAt) {
  const ONE_HOUR = 60 * 60 * 1000;
  const updated = new Date(updatedAt).getTime();
  let overduePolling = false;
  const cdEl = () => document.getElementById("countdown");

  function tick() {
    const remaining = ONE_HOUR - (Date.now() - updated);
    if (remaining <= 0) {
      if (!overduePolling) {
        overduePolling = true;
        cdEl().innerHTML = `<span class="cd-checking">checking…</span>`;
        clearInterval(_autoRefreshInterval);
        _autoRefreshInterval = null;
        checkForRefresh();
        _autoRefreshInterval = setInterval(async () => {
          const didUpdate = await checkForRefresh();
          if (didUpdate) {
            clearInterval(_autoRefreshInterval);
            _autoRefreshInterval = setInterval(checkForRefresh, 5 * 60 * 1000);
            overduePolling = false;
          }
        }, 60 * 1000);
      }
      return;
    }
    const m = Math.floor((remaining % 3600000) / 60000);
    const s = Math.floor((remaining % 60000) / 1000);
    cdEl().textContent = `${String(m).padStart(2,"0")}m ${String(s).padStart(2,"0")}s`;
  }
  tick();
  setInterval(tick, 1000);
}

// ── Header datetime ───────────────────────────────────────────────────────────
function updateDatetime() {
  const el = document.getElementById("headerDatetime"); if (!el) return;
  el.textContent = new Date().toLocaleString("en-GB", { day:"2-digit", month:"short", year:"numeric", hour:"2-digit", minute:"2-digit", timeZone:"UTC", timeZoneName:"short" });
}

// ── Data loading ─────────────────────────────────────────────────────────────
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
async function init() {
  updateDatetime(); setInterval(updateDatetime, 30000);
  document.querySelectorAll(".tab-btn").forEach(btn => btn.addEventListener("click", () => switchTab(btn.dataset.tab)));

  const [me, ua] = await Promise.all([
    loadConflict("middle_east"),
    loadConflict("ukraine"),
  ]);
  if (me) { populatePanel("middle_east", me); startCountdown(me.updated_at); scheduleAutoRefresh(me.updated_at); }
  if (ua) populatePanel("ukraine", ua);
  buildTicker([me, ua]);

  // Refresh geo-bar times every minute (no network call needed)
  setInterval(() => {
    Object.keys(SECTION_GEO).forEach(key => updateGeoBar(key));
  }, 60 * 1000);
}

// Global click handlers
document.addEventListener("click", e => {
  const a = e.target.closest("a.src-tag--biased");
  if (a) { e.preventDefault(); showSourceWarningPopup(a.dataset.ch, a.dataset.url); return; }
  const thumb = e.target.closest(".spm-thumb");
  if (thumb) { e.stopPropagation(); openLocalMediaLightbox(thumb.dataset.src, thumb.dataset.posturl); }
});

document.addEventListener("DOMContentLoaded", init);
