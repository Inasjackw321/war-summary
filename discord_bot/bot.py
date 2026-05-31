import os
import json
import re
import asyncio
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone, timedelta
from pathlib import Path

DISCORD_TOKEN  = os.environ["DISCORD_TOKEN"]
CONFIG_PATH    = Path(os.environ.get("CONFIG_PATH", "/data/config.json"))
UPSTASH_URL    = os.environ.get("UPSTASH_REDIS_REST_URL", "")
UPSTASH_TOKEN  = os.environ.get("UPSTASH_REDIS_REST_TOKEN", "")
_UPSTASH_KEY   = "warsummary:guild_config"

DATA_URLS = {
    "middle_east": "https://warsummary.live/data/middle_east.json",
    "ukraine":     "https://warsummary.live/data/ukraine.json",
}
CONFLICT_META = {
    "middle_east": ("Middle East", "🌍", 0xf59e0b),
    "ukraine":     ("Ukraine-Russia", "🇺🇦", 0x3b82f6),
}
# Pre-rendered PNGs committed to data/ by the hourly GitHub Action
GRAPH_URLS = {
    "ukraine":     "https://warsummary.live/data/ukraine_graph.png",
    "middle_east": "https://warsummary.live/data/middle_east_graph.png",
}

# Sources known to be heavily biased or state-controlled (excluded globally)
_EXCLUDED_SOURCES = {"presstv", "rasedal3ado138e", "SharghDaily"}
_EXCLUDED_LOWER   = {s.lower() for s in _EXCLUDED_SOURCES}

# For Middle East summaries only show points sourced from this approved list
_ME_ALLOWED = {
    "faytuks_network", "naya_foriraq", "n12chat", "shin_persian",
    "idf_telegram", "manniefabian", "tzevaadom_en", "amitsegal", "redlinkleb",
}

_cfg: dict = {}
_session: aiohttp.ClientSession | None = None

async def _load():
    global _cfg
    if UPSTASH_URL and UPSTASH_TOKEN:
        try:
            s = await _get_session()
            async with s.post(
                UPSTASH_URL,
                headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
                json=["GET", _UPSTASH_KEY],
            ) as r:
                if r.status == 200:
                    data = await r.json()
                    if data.get("result"):
                        _cfg = json.loads(data["result"])
                        print(f"[config] loaded from upstash: {len(_cfg)} guilds")
                        return
        except Exception as e:
            print(f"[config] upstash load error: {e}")
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            _cfg = json.loads(CONFIG_PATH.read_text())
            print(f"[config] loaded from file: {len(_cfg)} guilds")
        except Exception:
            _cfg = {}

def _save():
    try:
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(json.dumps(_cfg, indent=2))
    except Exception:
        pass

async def _push_config():
    """Persist config to Upstash after every change."""
    _save()
    if not (UPSTASH_URL and UPSTASH_TOKEN):
        return
    try:
        s = await _get_session()
        async with s.post(
            UPSTASH_URL,
            headers={"Authorization": f"Bearer {UPSTASH_TOKEN}"},
            json=["SET", _UPSTASH_KEY, json.dumps(_cfg)],
        ) as r:
            if r.status != 200:
                print(f"[config] upstash push failed: {r.status}")
    except Exception as e:
        print(f"[config] upstash push error: {e}")

MAX_CHANNELS_PER_CONFLICT = 3

def _get_channels(guild_id: int, conflict: str) -> list[int]:
    """Return list of channel IDs for a conflict, migrating legacy int format."""
    val = _cfg.get(str(guild_id), {}).get(conflict)
    if val is None:
        return []
    if isinstance(val, int):
        return [val]
    return list(val)

def _set_channel(guild_id: int, conflict: str, channel_id: int) -> str:
    """Add channel to conflict. Returns 'added', 'exists', or 'full'."""
    guild = _cfg.setdefault(str(guild_id), {})
    channels = _get_channels(guild_id, conflict)
    if channel_id in channels:
        return "exists"
    if len(channels) >= MAX_CHANNELS_PER_CONFLICT:
        return "full"
    channels.append(channel_id)
    guild[conflict] = channels
    return "added"

def _remove_channel(guild_id: int, conflict: str, channel_id: int):
    channels = _get_channels(guild_id, conflict)
    if channel_id in channels:
        channels.remove(channel_id)
    guild = _cfg.get(str(guild_id), {})
    if channels:
        guild[conflict] = channels
    else:
        guild.pop(conflict, None)

def _conflict_for_channel(guild_id: int, channel_id: int) -> str | None:
    for conflict in _cfg.get(str(guild_id), {}):
        if channel_id in _get_channels(guild_id, conflict):
            return conflict
    return None

async def _get_session() -> aiohttp.ClientSession:
    global _session
    if _session is None or _session.closed:
        _session = aiohttp.ClientSession()
    return _session

async def _fetch(conflict: str) -> dict:
    try:
        s = await _get_session()
        async with s.get(DATA_URLS[conflict], timeout=aiohttp.ClientTimeout(total=10)) as r:
            if r.status == 200:
                return await r.json(content_type=None)
    except Exception as e:
        print(f"[bot] fetch error ({conflict}): {e}")
    return {}

# Matches any inline citation: (Source: @channel/123), (Source: @channel), (@channel/123)
# Requires @ so generic parenthetical words like "(Gaza)" aren't caught
_CITE_ANY_RE = re.compile(r'\((?:Source:\s*)?@(\w+)(?:/(\d+))?\)\.?\s*', re.IGNORECASE)
# Matches trailing citation with post ID at end of string (for link generation)
_CITATION_RE = re.compile(r'\((?:Source:\s*)?@?(\w+)/(\d+)\)\.?\s*$', re.IGNORECASE)
_SOURCE_RE   = re.compile(r'\s*\([^)]*?(?:source|@)[^)]*\)', re.IGNORECASE)

def _cited_sources(text: str) -> set[str]:
    return {m.group(1).lower() for m in _CITE_ANY_RE.finditer(text)}

def _filter_points(points: list) -> list:
    """Remove points sourced solely from excluded channels, and drop near-empty points."""
    out = []
    for p in points:
        cited = _cited_sources(str(p))
        # Drop if every cited source is excluded (pure propaganda/biased sourcing)
        if cited and cited.issubset(_EXCLUDED_LOWER):
            continue
        # Drop if stripping citations leaves almost nothing
        if len(_SOURCE_RE.sub("", str(p)).strip()) < 25:
            continue
        out.append(p)
    return out

def _clean_point(text: str) -> str:
    """Strip all source citations from a point."""
    return _CITE_ANY_RE.sub("", _SOURCE_RE.sub("", str(text))).strip()

def _truncate(text: str, max_words: int = 40) -> str:
    """Trim to max_words words, breaking cleanly at word boundary."""
    words = text.split()
    if len(words) <= max_words:
        return text
    return " ".join(words[:max_words]).rstrip(",.;:") + "…"

def _first_sentence(text: str) -> str:
    """Return only the first sentence of a block of text."""
    m = re.search(r'(?<=[.!?])\s+[A-Z]', text)
    if m and m.start() > 40:
        return text[:m.start() + 1].strip()
    return text.strip()

def _is_vague(clean: str) -> bool:
    """True for points that promise details but deliver none."""
    lower = clean.lower().rstrip(".… ")
    return any(lower.endswith(e) for e in (
        "to follow", "details to follow", "further details to follow",
        "more details to follow", "details pending", "developing",
        "no further details", "no details provided",
    ))

def _ngram_overlap(a: str, b: str, n: int = 7) -> bool:
    """True if two texts share a run of n consecutive words (catches near-duplicates)."""
    wa = a.lower().split()
    wb = b.lower().split()
    if len(wa) < n or len(wb) < n:
        return a.lower()[:50] == b.lower()[:50]
    grams_b = {tuple(wb[i:i+n]) for i in range(len(wb) - n + 1)}
    return any(tuple(wa[i:i+n]) in grams_b for i in range(len(wa) - n + 1))

def _point_with_link(text: str) -> str:
    """Return truncated point text with a Telegram source link if available."""
    m = _CITATION_RE.search(str(text))
    clean = _truncate(_clean_point(text))
    if m:
        ch, post_id = m.group(1), m.group(2)
        if ch.lower() not in _EXCLUDED_LOWER:
            return f"{clean} [(src)](https://t.me/{ch}/{post_id})"
    return clean

def _collect_points(data: dict, conflict: str) -> list[str]:
    """
    Gather the most important unique points across all sections.
    Priority: key_developments first, then major front/region sections.
    """
    sections = data.get("sections") or {}

    if conflict == "ukraine":
        priority = [
            "key_developments",
            "eastern_front", "northern_front", "southern_front",
            "air_war", "ukraine", "russia",
        ]
    else:
        priority = [
            "key_developments",
            "israel", "gaza_west_bank", "iran",
            "lebanon", "syria_iraq",
        ]

    accepted: list[str] = []   # raw point texts kept so far
    accepted_clean: list[str] = []  # their cleaned versions for overlap checks

    for key in priority:
        raw = sections.get(key)
        if not raw:
            continue
        items = raw if isinstance(raw, list) else (raw.get("points") or [])
        for p in items:
            clean = _clean_point(p)
            if len(clean) < 30:
                continue
            if _is_vague(clean):
                continue
            cited = _cited_sources(str(p))
            if conflict == "middle_east":
                if not cited or not cited.intersection(_ME_ALLOWED):
                    continue
            else:
                if cited and cited.issubset(_EXCLUDED_LOWER):
                    continue
            # Near-duplicate check against every already-accepted point
            if any(_ngram_overlap(clean, prev) for prev in accepted_clean):
                continue
            accepted.append(str(p))
            accepted_clean.append(clean)

    return accepted


def _embed(data: dict, conflict: str) -> discord.Embed:
    label, icon, color = CONFLICT_META[conflict]

    updated = data.get("updated_at", "")
    ts = None
    if updated:
        try:
            ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        except ValueError:
            pass

    # One-sentence lead from the executive summary
    raw_exec = (data.get("sections") or {}).get("executive_summary") or data.get("summary") or ""
    exec_line = _first_sentence(raw_exec) if raw_exec else ""

    embed = discord.Embed(
        title=f"{icon}  {label} — Latest Updates",
        description=f"*{exec_line}*" if exec_line else None,
        color=color,
        timestamp=ts or datetime.now(timezone.utc),
    )

    # Stats row
    if conflict == "middle_east":
        alerts = data.get("red_alerts")
        if alerts is not None:
            embed.add_field(name="🚨 Red Alerts", value=f"**{round(alerts / 2)}** · Israel today", inline=True)
    elif conflict == "ukraine":
        missiles = data.get("missiles")
        drones   = data.get("drones")
        if missiles is not None:
            embed.add_field(name="🚀 Missiles", value=f"**{missiles}** launched", inline=True)
        if drones is not None:
            embed.add_field(name="🛸 Drones", value=f"**{drones}** launched", inline=True)

    # Key developments — single field, max 8 points
    all_points = _collect_points(data, conflict)
    if all_points:
        bullets = []
        total_len = 0
        markers = ["▸", "▸", "▸", "▸", "▸", "▸", "▸", "▸"]
        for i, p in enumerate(all_points[:8]):
            line = f"**{i+1}.** {_point_with_link(p)}"
            if total_len + len(line) + 1 > 1020:
                break
            bullets.append(line)
            total_len += len(line) + 1
        embed.add_field(name="📋  Key Developments", value="\n".join(bullets), inline=False)

    n = len(data.get("channels") or [])
    embed.set_footer(text=f"⚠ AI-generated · {n} sources · Verify before sharing")
    return embed

OPERATOR_ROLE = "War Summary Operator"

def _is_operator(interaction: discord.Interaction) -> bool:
    if not interaction.guild:
        return False
    if interaction.guild.owner_id == interaction.user.id:
        return True
    return any(r.name == OPERATOR_ROLE for r in interaction.user.roles)

# ── Bot setup ──────────────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)
grp = app_commands.Group(name="warsummary", description="War Summary bot")

# ── /summary ──────────────────────────────────────────────────────────────────
@bot.tree.command(name="summary", description="Post the latest intelligence brief for this channel")
async def slash_summary(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command only works in a server.", ephemeral=True)
        return
    conflict = _conflict_for_channel(interaction.guild_id, interaction.channel_id)
    if not conflict:
        await interaction.response.send_message(
            "This channel isn't assigned to a conflict. Ask an admin to run `/warsummary setup`.",
            ephemeral=True,
        )
        return
    await interaction.response.defer()
    data = await _fetch(conflict)
    if data:
        await interaction.followup.send(embed=_embed(data, conflict))
    else:
        await interaction.followup.send("⚠ Failed to fetch data — try again in a moment.")

# ── /graph ────────────────────────────────────────────────────────────────────
@bot.tree.command(name="graph", description="Show attack stats: 7-day chart (Ukraine) or 24h red alerts (Middle East)")
async def slash_graph(interaction: discord.Interaction):
    if not interaction.guild:
        await interaction.response.send_message("This command only works in a server.", ephemeral=True)
        return
    conflict = _conflict_for_channel(interaction.guild_id, interaction.channel_id)
    if not conflict:
        await interaction.response.send_message(
            "This channel isn't assigned to a conflict. Ask an admin to run `/warsummary setup`.",
            ephemeral=True,
        )
        return
    await interaction.response.defer()
    # Fetch main data just for the updated_at timestamp used as a cache-buster,
    # so Discord re-fetches the pre-rendered PNG when data actually changes.
    data = await _fetch(conflict)
    if not data:
        await interaction.followup.send("📊 Failed to fetch data — try again in a moment.")
        return
    ts = re.sub(r"[^0-9]", "", data.get("updated_at", ""))[:12]
    img_url = f"{GRAPH_URLS[conflict]}?t={ts}"
    label, icon, color = CONFLICT_META[conflict]
    title = (f"{icon}  {label} — 7-Day History"
             if conflict == "ukraine" else f"{icon}  {label} — 24h Red Alerts")
    embed = discord.Embed(title=title, color=color, timestamp=datetime.now(timezone.utc))
    embed.set_image(url=img_url)
    embed.set_footer(text="warsummary.live · Updated hourly")
    await interaction.followup.send(embed=embed)

# ── /warsummary setup ──────────────────────────────────────────────────────────
@grp.command(name="setup", description="Assign a conflict to a channel (up to 3 channels per conflict)")
@app_commands.describe(conflict="Which conflict to assign", channel="Channel to post updates in")
@app_commands.choices(conflict=[
    app_commands.Choice(name="Middle East",    value="middle_east"),
    app_commands.Choice(name="Ukraine-Russia", value="ukraine"),
])
async def cmd_setup(interaction: discord.Interaction, conflict: str, channel: discord.TextChannel):
    if not _is_operator(interaction):
        await interaction.response.send_message(
            f"❌ You need the **{OPERATOR_ROLE}** role or be the server owner.", ephemeral=True
        )
        return
    result = _set_channel(interaction.guild_id, conflict, channel.id)
    label = "Middle East" if conflict == "middle_east" else "Ukraine-Russia"
    count = len(_get_channels(interaction.guild_id, conflict))
    if result == "exists":
        await interaction.response.send_message(
            f"ℹ {channel.mention} is already assigned to **{label}**.", ephemeral=True
        )
    elif result == "full":
        await interaction.response.send_message(
            f"❌ **{label}** already has {MAX_CHANNELS_PER_CONFLICT} channels assigned. Remove one first with `/warsummary remove`.",
            ephemeral=True,
        )
    else:
        await _push_config()
        await interaction.response.send_message(
            f"✅ **{label}** → {channel.mention} ({count}/{MAX_CHANNELS_PER_CONFLICT} channels)\n"
            f"Use `/summary` in that channel to pull the latest brief.",
            ephemeral=True,
        )

# ── /warsummary remove ─────────────────────────────────────────────────────────
@grp.command(name="remove", description="Remove a channel from a conflict assignment")
@app_commands.describe(conflict="Which conflict", channel="Channel to remove")
@app_commands.choices(conflict=[
    app_commands.Choice(name="Middle East",    value="middle_east"),
    app_commands.Choice(name="Ukraine-Russia", value="ukraine"),
])
async def cmd_remove(interaction: discord.Interaction, conflict: str, channel: discord.TextChannel):
    if not _is_operator(interaction):
        await interaction.response.send_message(
            f"❌ You need the **{OPERATOR_ROLE}** role or be the server owner.", ephemeral=True
        )
        return
    _remove_channel(interaction.guild_id, conflict, channel.id)
    await _push_config()
    label = "Middle East" if conflict == "middle_east" else "Ukraine-Russia"
    await interaction.response.send_message(
        f"🗑 {channel.mention} removed from **{label}**.", ephemeral=True
    )

# ── /warsummary status ─────────────────────────────────────────────────────────
@grp.command(name="status", description="Show current channel assignments for this server")
async def cmd_status(interaction: discord.Interaction):
    if not _is_operator(interaction):
        await interaction.response.send_message(
            f"❌ You need the **{OPERATOR_ROLE}** role or be the server owner.", ephemeral=True
        )
        return
    guild_cfg = _cfg.get(str(interaction.guild_id), {})
    if not guild_cfg:
        await interaction.response.send_message(
            "No channels configured yet. Use `/warsummary setup` to assign channels.", ephemeral=True
        )
        return
    lines = []
    for conflict, _ in guild_cfg.items():
        icon = "🌍" if conflict == "middle_east" else "🇺🇦"
        label = "Middle East" if conflict == "middle_east" else "Ukraine-Russia"
        channels = _get_channels(interaction.guild_id, conflict)
        mentions = " ".join(f"<#{ch}>" for ch in channels)
        lines.append(f"{icon} **{label}** ({len(channels)}/{MAX_CHANNELS_PER_CONFLICT}) → {mentions}")
    await interaction.response.send_message("\n".join(lines), ephemeral=True)

bot.tree.add_command(grp)

# ── !summary prefix command ────────────────────────────────────────────────────
@bot.command(name="summary")
async def prefix_summary(ctx: commands.Context):
    if not ctx.guild:
        return
    conflict = _conflict_for_channel(ctx.guild.id, ctx.channel.id)
    if not conflict:
        return
    data = await _fetch(conflict)
    if data:
        await ctx.send(embed=_embed(data, conflict))
    else:
        await ctx.send("⚠ Failed to fetch data.")

# ── !graph prefix command ──────────────────────────────────────────────────────
@bot.command(name="graph")
async def prefix_graph(ctx: commands.Context):
    if not ctx.guild:
        return
    conflict = _conflict_for_channel(ctx.guild.id, ctx.channel.id)
    if not conflict:
        return
    data = await _fetch(conflict)
    if not data:
        await ctx.send("📊 Failed to fetch data — try again in a moment.")
        return
    ts = re.sub(r"[^0-9]", "", data.get("updated_at", ""))[:12]
    img_url = f"{GRAPH_URLS[conflict]}?t={ts}"
    label, icon, color = CONFLICT_META[conflict]
    title = (f"{icon}  {label} — 7-Day History"
             if conflict == "ukraine" else f"{icon}  {label} — 24h Red Alerts")
    embed = discord.Embed(title=title, color=color, timestamp=datetime.now(timezone.utc))
    embed.set_image(url=img_url)
    embed.set_footer(text="warsummary.live · Updated hourly")
    await ctx.send(embed=embed)

# ── Startup ────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    await _load()
    await bot.tree.sync()
    print(f"[bot] Ready — logged in as {bot.user}")
    print(f"[bot] Loaded config: {_cfg}")

async def main():
    try:
        async with bot:
            await bot.start(DISCORD_TOKEN)
    finally:
        if _session and not _session.closed:
            await _session.close()

asyncio.run(main())
