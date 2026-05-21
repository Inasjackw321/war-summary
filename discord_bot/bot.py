import os
import json
import re
import asyncio
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timezone
from pathlib import Path

DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
CONFIG_PATH   = Path(os.environ.get("CONFIG_PATH", "/data/config.json"))

DATA_URLS = {
    "middle_east": "https://raw.githubusercontent.com/inasjackw321/war-summary/main/data/middle_east.json",
    "ukraine":     "https://raw.githubusercontent.com/inasjackw321/war-summary/main/data/ukraine.json",
}
CONFLICT_META = {
    "middle_east": ("Middle East", "🌍", 0xf59e0b),
    "ukraine":     ("Ukraine-Russia", "🇺🇦", 0x3b82f6),
}

# Channels filtered out of the bot's Sources display only
_BOT_EXCLUDED_SOURCES = {"presstv", "rasedal3ado138e", "SharghDaily", "naya_foriraq"}

_cfg: dict = {}

def _load():
    global _cfg
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    if CONFIG_PATH.exists():
        try:
            _cfg = json.loads(CONFIG_PATH.read_text())
        except Exception:
            _cfg = {}

def _save():
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(_cfg, indent=2))

def _set_channel(guild_id: int, conflict: str, channel_id: int):
    _cfg.setdefault(str(guild_id), {})[conflict] = channel_id
    _save()

def _remove_channel(guild_id: int, conflict: str):
    _cfg.get(str(guild_id), {}).pop(conflict, None)
    _save()

def _conflict_for_channel(guild_id: int, channel_id: int) -> str | None:
    for conflict, ch_id in _cfg.get(str(guild_id), {}).items():
        if ch_id == channel_id:
            return conflict
    return None

async def _fetch(conflict: str) -> dict:
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(DATA_URLS[conflict], timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    return await r.json(content_type=None)
    except Exception as e:
        print(f"[bot] fetch error ({conflict}): {e}")
    return {}

_SENTIMENT_EMOJI = {
    "escalating": "🔴",
    "volatile":   "🟠",
    "active":     "🟡",
    "tense":      "🟡",
    "stable":     "🟢",
    "calm":       "🔵",
}

_SOURCE_RE = re.compile(r'\s*\([^)]*?(?:source|@)[^)]*\)', re.IGNORECASE)

def _intensity_color(intensity: int) -> int:
    if intensity >= 8:
        return 0xef4444
    if intensity >= 6:
        return 0xf97316
    if intensity >= 4:
        return 0xeab308
    return 0x22c55e

def _embed(data: dict, conflict: str) -> discord.Embed:
    label, icon, base_color = CONFLICT_META[conflict]

    updated = data.get("updated_at", "")
    ts = None
    if updated:
        try:
            ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        except ValueError:
            pass

    intensity = int(data.get("intensity") or 5)
    sentiment = (data.get("sentiment") or "").lower()
    sent_emoji = _SENTIMENT_EMOJI.get(sentiment, "⚪")
    color = _intensity_color(intensity)

    exec_summary = (data.get("sections") or {}).get("executive_summary") or data.get("summary") or ""

    embed = discord.Embed(
        title=f"{icon}  {label} — Latest Updates",
        description=f"*{exec_summary}*" if exec_summary else None,
        color=color,
        timestamp=ts or datetime.now(timezone.utc),
    )

    # Conflict-specific stats
    if conflict == "ukraine":
        missiles = data.get("missiles") or 0
        drones = data.get("drones") or 0
        if missiles or drones:
            parts = []
            if missiles:
                parts.append(f"🚀 **{missiles}** missiles launched")
            if drones:
                parts.append(f"🛸 **{drones}** Shahed/UAVs launched")
            embed.add_field(name="Last 24h — Attack Overview", value="\n".join(parts), inline=False)
    elif conflict == "middle_east":
        red_alerts = data.get("red_alerts") or 0
        if red_alerts:
            embed.add_field(name="🚨 Red Alert Activations", value=f"**{red_alerts}** alerts in the last 24h", inline=False)

    # Key points — strip inline source citations
    points = data.get("key_points") or []
    if points:
        nums = ["①", "②", "③", "④", "⑤", "⑥", "⑦", "⑧", "⑨", "⑩"]
        lines = []
        total = 0
        for i, p in enumerate(points[:10]):
            clean = _SOURCE_RE.sub("", p).strip()
            line = f"{nums[i] if i < len(nums) else f'{i+1}.'} {clean}"
            if total + len(line) + 1 > 1020:
                break
            lines.append(line)
            total += len(line) + 1
        embed.add_field(name="Key Developments", value="\n".join(lines), inline=False)

    # Sources — exclude filtered channels
    urls: dict = data.get("cited_post_urls") or data.get("recent_post_urls") or {}
    filtered = {ch: url for ch, url in urls.items() if ch not in _BOT_EXCLUDED_SOURCES}
    if filtered:
        links = "  ·  ".join(f"[{ch}]({url})" for ch, url in list(filtered.items())[:8])
        embed.add_field(name="Sources", value=links, inline=False)

    bar = "█" * intensity + "░" * (10 - intensity)
    n = len(data.get("channels") or [])
    embed.set_footer(text=f"{sent_emoji} {sentiment.capitalize()}  ·  [{bar}]  ·  {n} channels  ·  Updated")
    return embed

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
@grp.command(name="setup", description="Assign a conflict to a channel")
@app_commands.describe(conflict="Which conflict to assign", channel="Channel to post updates in")
@app_commands.choices(conflict=[
    app_commands.Choice(name="Middle East",    value="middle_east"),
    app_commands.Choice(name="Ukraine-Russia", value="ukraine"),
])
@app_commands.default_permissions(administrator=True)
async def cmd_setup(interaction: discord.Interaction, conflict: str, channel: discord.TextChannel):
    _set_channel(interaction.guild_id, conflict, channel.id)
    label = "Middle East" if conflict == "middle_east" else "Ukraine-Russia"
    await interaction.response.send_message(
        f"✅ **{label}** → {channel.mention}\n"
        f"Updates will be posted every 3 hours. Use `/summary` to pull the latest now.",
        ephemeral=True,
    )

# ── /warsummary remove ─────────────────────────────────────────────────────────
@grp.command(name="remove", description="Remove the conflict assignment for a channel")
@app_commands.describe(conflict="Which conflict assignment to remove")
@app_commands.choices(conflict=[
    app_commands.Choice(name="Middle East",    value="middle_east"),
    app_commands.Choice(name="Ukraine-Russia", value="ukraine"),
])
@app_commands.default_permissions(administrator=True)
async def cmd_remove(interaction: discord.Interaction, conflict: str):
    _remove_channel(interaction.guild_id, conflict)
    label = "Middle East" if conflict == "middle_east" else "Ukraine-Russia"
    await interaction.response.send_message(f"🗑 **{label}** channel assignment removed.", ephemeral=True)

# ── /warsummary status ─────────────────────────────────────────────────────────
@grp.command(name="status", description="Show current channel assignments for this server")
@app_commands.default_permissions(administrator=True)
async def cmd_status(interaction: discord.Interaction):
    guild_cfg = _cfg.get(str(interaction.guild_id), {})
    if not guild_cfg:
        await interaction.response.send_message(
            "No channels configured yet. Use `/warsummary setup` to assign channels.", ephemeral=True
        )
        return
    lines = []
    for conflict, ch_id in guild_cfg.items():
        icon = "🌍" if conflict == "middle_east" else "🇺🇦"
        label = "Middle East" if conflict == "middle_east" else "Ukraine-Russia"
        lines.append(f"{icon} **{label}** → <#{ch_id}>")
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

# ── Auto-post every 3 hours ────────────────────────────────────────────────────
@tasks.loop(hours=3)
async def _auto_post():
    for conflict in DATA_URLS:
        data = await _fetch(conflict)
        if not data:
            continue
        embed = _embed(data, conflict)
        for guild_id_str, guild_cfg in _cfg.items():
            ch_id = guild_cfg.get(conflict)
            if not ch_id:
                continue
            ch = bot.get_channel(ch_id)
            if ch:
                try:
                    await ch.send(embed=embed)
                    print(f"[bot] auto-posted {conflict} to #{ch.name}")
                except Exception as e:
                    print(f"[bot] auto-post failed to {ch_id}: {e}")

@_auto_post.before_loop
async def _before_auto_post():
    await bot.wait_until_ready()

# ── Startup ────────────────────────────────────────────────────────────────────
@bot.event
async def on_ready():
    _load()
    await bot.tree.sync()
    if not _auto_post.is_running():
        _auto_post.start()
    print(f"[bot] Ready — logged in as {bot.user}")
    print(f"[bot] Loaded config: {_cfg}")

async def main():
    async with bot:
        await bot.start(DISCORD_TOKEN)

asyncio.run(main())
