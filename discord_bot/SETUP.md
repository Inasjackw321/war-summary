# Discord Bot Setup

Reads the hourly-updated JSON summaries directly from GitHub and posts them on command.
Hosted on **Fly.io** free tier — always-on, no credit card charges.

---

## 1 — Create the Discord Application

1. Go to https://discord.com/developers/applications → **New Application**
2. Name it (e.g. "War Summary") → Create
3. Left sidebar → **Bot** → **Add Bot**
4. Under **Token** → **Reset Token** → copy it (you'll need this)
5. Under **Privileged Gateway Intents**, enable **Message Content Intent** (needed for `!summary` prefix)
6. Left sidebar → **OAuth2 → URL Generator**
   - Scopes: `bot`, `applications.commands`
   - Bot Permissions: `Send Messages`, `Embed Links`, `Read Message History`
   - Copy the generated URL → open it → invite the bot to your server

---

## 2 — Get the channel ID (optional — restricts the command to one channel)

In Discord: **Settings → Advanced → Developer Mode ON**  
Right-click the channel you want → **Copy Channel ID**

---

## 3 — Deploy to Fly.io

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh

# Sign up / log in (free, credit card for verification only)
fly auth signup        # or: fly auth login

# From the discord_bot/ directory:
cd discord_bot

# Launch (only first time — creates the app on Fly)
fly launch --name war-summary-bot --region iad --no-deploy

# Set secrets
fly secrets set DISCORD_TOKEN=your_token_here
fly secrets set ALLOWED_CHANNEL_ID=your_channel_id_here   # optional

# Deploy
fly deploy
```

After deploy, the bot starts immediately and runs 24/7 for free.

---

## 4 — Commands

| Command | What it does |
|---|---|
| `/summary` | Both conflict summaries |
| `/summary Middle East` | Middle East only |
| `/summary Ukraine-Russia` | Ukraine-Russia only |
| `!summary` | Same as above (prefix version) |
| `!summary middleeast` | Middle East only |
| `!summary ukraine` | Ukraine-Russia only |

Slash commands take up to 1 hour to register globally after the first deploy.
Use `!summary` immediately if needed.

---

## 5 — Updating / redeploying

The bot reads data live from GitHub on every command — no redeployment needed when summaries update.
To update the bot code itself: edit `bot.py` then `fly deploy`.

## Viewing logs

```bash
fly logs
```
