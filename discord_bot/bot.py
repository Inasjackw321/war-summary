import os
import json
import re
import asyncio
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone
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

# Sources known to be heavily biased or state-controlled
_EXCLUDED_SOURCES = {"presstv", "rasedal3ado138e", "SharghDaily", "naya_foriraq"}
_EXCLUDED_LOWER   = {s.lower() for s in _EXCLUDED_SOURCES}

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

# Matches any inline citation: (Source: @channel/123) or (@channel/123)
_CITE_ANY_RE = re.compile(r'\((?:Source:\s*)?@?(\w+)/(\d+)\)\.?\s*', re.IGNORECASE)
# Matches trailing citation at end of string (for link extraction)
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

def _embed(data: dict, conflict: str) -> discord.Embed:
    label, icon, color = CONFLICT_META[conflict]

    updated = data.get("updated_at", "")
    ts = None
    if updated:
        try:
            ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        except ValueError:
            pass

    exec_summary = (data.get("sections") or {}).get("executive_summary") or data.get("summary") or ""

    embed = discord.Embed(
        title=f"{icon}  {label} — Latest Updates",
        url="https://warsummary.live",
        description=f"*{exec_summary}*" if exec_summary else None,
        color=color,
        timestamp=ts or datetime.now(timezone.utc),
    )
    # Stats — shown before key developments
    if conflict == "middle_east":
        alerts = data.get("red_alerts")
        if alerts is not None:
            embed.add_field(name="🚨 Red Alerts · Israel", value=f"**{round(alerts / 2)}** today", inline=False)
    elif conflict == "ukraine":
        missiles = data.get("missiles")
        drones   = data.get("drones")
        if missiles is not None:
            embed.add_field(name="🚀 Missiles", value=f"**{missiles}** launched · 24h", inline=True)
        if drones is not None:
            embed.add_field(name="🛸 Drones", value=f"**{drones}** launched · 24h", inline=True)

    sections = data.get("sections") or {}
    key_devs = sections.get("key_developments") or []
    raw_points = key_devs if isinstance(key_devs, list) and key_devs else (data.get("key_points") or [])
    points = _filter_points(raw_points)

    if points:
        nums = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
        lines = []
        total = 0
        for i, p in enumerate(points[:10]):
            num = nums[i] if i < len(nums) else f"{i+1}."
            m = _CITATION_RE.search(str(p))
            if m:
                ch, post_id = m.group(1), m.group(2)
                clean = _CITATION_RE.sub("", str(p)).strip()
                if ch.lower() not in _EXCLUDED_LOWER:
                    url = f"https://t.me/{ch}/{post_id}"
                    line = f"{num} [{clean}]({url})"
                else:
                    line = f"{num} {clean}"
            else:
                clean = _SOURCE_RE.sub("", str(p)).strip()
                line = f"{num} {clean}"
            if total + len(line) + 1 > 1020:
                break
            lines.append(line)
            total += len(line) + 1
        embed.add_field(name="📋  Key Developments", value="\n".join(lines), inline=False)

    n = len(data.get("channels") or [])
    embed.set_footer(text=f"⚠ AI-generated · {n} channels monitored · Verify before sharing")
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
