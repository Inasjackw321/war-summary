import os
import aiohttp
import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timezone

DISCORD_TOKEN     = os.environ["DISCORD_TOKEN"]
ALLOWED_CHANNEL   = int(os.environ.get("ALLOWED_CHANNEL_ID", "0"))  # 0 = any channel

DATA_URLS = {
    "middle_east": "https://raw.githubusercontent.com/inasjackw321/war-summary/main/data/middle_east.json",
    "ukraine":     "https://raw.githubusercontent.com/inasjackw321/war-summary/main/data/ukraine.json",
}

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)


async def fetch_conflict(conflict: str) -> dict:
    url = DATA_URLS.get(conflict)
    if not url:
        return {}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, timeout=aiohttp.ClientTimeout(total=10)) as r:
                if r.status == 200:
                    return await r.json(content_type=None)
    except Exception as e:
        print(f"[bot] fetch failed for {conflict}: {e}")
    return {}


def build_embed(data: dict, title: str, color: int) -> discord.Embed:
    summary = data.get("summary", "No summary available.")
    updated = data.get("updated_at", "")

    ts = None
    if updated:
        try:
            ts = datetime.fromisoformat(updated.replace("Z", "+00:00"))
        except ValueError:
            pass

    embed = discord.Embed(title=title, description=summary, color=color, timestamp=ts or datetime.now(timezone.utc))

    key_points = data.get("key_points") or []
    if key_points:
        text = "\n".join(f"• {p}" for p in key_points[:7])
        if len(text) > 1024:
            text = text[:1020] + "…"
        embed.add_field(name="Key Points", value=text, inline=False)

    channels = data.get("channels") or []
    embed.set_footer(text=f"{len(channels)} sources monitored · Last updated")
    return embed


def _wrong_channel(channel_id: int) -> bool:
    return bool(ALLOWED_CHANNEL) and channel_id != ALLOWED_CHANNEL


# ── Slash command ─────────────────────────────────────────────────────────────
@bot.tree.command(name="summary", description="Show the latest conflict intelligence summary")
@app_commands.describe(conflict="Which conflict to show (default: both)")
@app_commands.choices(conflict=[
    app_commands.Choice(name="Middle East",    value="middleeast"),
    app_commands.Choice(name="Ukraine-Russia", value="ukraine"),
    app_commands.Choice(name="Both",           value="both"),
])
async def slash_summary(interaction: discord.Interaction, conflict: str = "both"):
    if _wrong_channel(interaction.channel_id):
        await interaction.response.send_message(
            "This command can only be used in the designated summary channel.", ephemeral=True
        )
        return

    await interaction.response.defer()
    embeds = await _collect_embeds(conflict)
    if embeds:
        await interaction.followup.send(embeds=embeds[:2])
    else:
        await interaction.followup.send("⚠ Failed to fetch summary data. Try again in a moment.")


# ── Prefix command (!summary) ─────────────────────────────────────────────────
@bot.command(name="summary")
async def prefix_summary(ctx: commands.Context, conflict: str = "both"):
    if _wrong_channel(ctx.channel.id):
        return
    embeds = await _collect_embeds(conflict.lower())
    if embeds:
        await ctx.send(embeds=embeds[:2])
    else:
        await ctx.send("⚠ Failed to fetch summary data.")


async def _collect_embeds(conflict: str) -> list[discord.Embed]:
    embeds = []
    if conflict in ("middleeast", "both"):
        data = await fetch_conflict("middle_east")
        if data:
            embeds.append(build_embed(data, "🌍  Middle East — Intelligence Brief", 0xf59e0b))
    if conflict in ("ukraine", "both"):
        data = await fetch_conflict("ukraine")
        if data:
            embeds.append(build_embed(data, "🇺🇦  Ukraine-Russia — Intelligence Brief", 0x3b82f6))
    return embeds


@bot.event
async def on_ready():
    print(f"[bot] Logged in as {bot.user} (id={bot.user.id})")
    await bot.tree.sync()
    print("[bot] Slash commands synced globally")


bot.run(DISCORD_TOKEN)
