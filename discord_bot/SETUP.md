# Discord Bot Setup

Reads the hourly-updated summaries from GitHub and posts them automatically to configured channels.
Each conflict (Middle East / Ukraine-Russia) gets its own dedicated Discord channel.

---

## 1 — Create the Discord Application

1. Go to https://discord.com/developers/applications → **New Application** (or open an existing one)
2. Left sidebar → **Bot** → **Reset Token** → copy the token
3. Scroll down, enable **Message Content Intent** → Save
4. Left sidebar → **OAuth2 → URL Generator**
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`
   - Copy the URL → open it in browser → select your server → Authorize

---

## 2 — Deploy to Fly.io (free, always-on)

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Sign up / log in
fly auth signup        # or: fly auth login

# From the discord_bot/ directory:
cd discord_bot

# First time only — create the app and volume
fly launch --name war-summary-bot --region iad --no-deploy
fly volume create war_summary_data --region iad --size 1

# Set your bot token
fly secrets set DISCORD_TOKEN=your_token_here

# Deploy
fly deploy
```

---

## 3 — Configure channels inside Discord

Once the bot is in your server, use these **admin-only** slash commands to assign channels:

```
/warsummary setup conflict:Middle East    channel:#middle-east-intel
/warsummary setup conflict:Ukraine-Russia channel:#ukraine-intel
```

The bot will immediately start auto-posting new summaries to those channels every hour when data updates.

**Other admin commands:**
```
/warsummary status          — show current channel assignments
/warsummary remove          — unassign a conflict from its channel
```

---

## 4 — Getting a summary on demand

In any configured channel:
```
!summary              — posts the latest summary for that channel's conflict
/warsummary summary   — same, as a slash command
```

---

## How it works

- The bot checks for new data every 5 minutes
- When the hourly scraper updates the GitHub JSON, the bot detects the new `updated_at` timestamp and auto-posts to the configured channels
- Channel assignments are saved to a persistent volume (`/data/config.json`) — survives restarts and redeployments

## Viewing logs

```bash
fly logs
```
