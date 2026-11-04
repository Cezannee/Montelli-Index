# Montelli-Index

A Discord bot that posts BBCA (Bank Central Asia, IDX: BBCA) price updates during Indonesian stock market sessions and notifies subscribers when the configured target price is exceeded.

## Requirements

- Python 3.10 or later
- A Discord application and bot token
- A Discord text channel where the bot can view the channel, send messages, and add/read reactions

The bot uses `discord.py` gateway intents for guilds, members, messages, reactions, and message content. Enable the **Server Members Intent** and **Message Content Intent** under **Discord Developer Portal → Applications → Your App → Bot → Privileged Gateway Intents**. Invite the bot to your server with permissions to view channels, send messages, and add reactions.

## Setup

1. Clone this repository and enter its directory:

   ```bash
   git clone https://github.com/Cezannee/Montelli-Index.git
   cd Montelli-Index
   ```

2. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   ```

   On Windows PowerShell, activate it with:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

3. Install the project dependencies:

   ```bash
   python -m pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root with these values:

   ```dotenv
   DISCORD_BOT_TOKEN=your_discord_bot_token
   CH_ID=your_discord_text_channel_id
   TARGET=your_target_price
   ```

   For example, `TARGET=10000`. To copy a channel ID in Discord, enable Developer Mode in **User Settings → Advanced**, then right-click the channel and choose **Copy Channel ID**. Keep the bot token private and do not commit `.env`.

5. Start the bot:

   ```bash
   python main.py
   ```

## Behavior

- On startup, the bot posts a message users can react to with ✅ to subscribe or ❌ to unsubscribe.
- Subscriber IDs are stored in `subscribers.json` in the current working directory.
- During market sessions (09:00–12:00 and 13:30–15:00 WIB, UTC+7), the bot checks the BBCA price and posts an update every hour.
- Subscribers are mentioned when the fetched price is above `TARGET`.
- Outside market sessions, the bot posts a market status update every hour.

Price data is fetched from Google Finance. The bot needs an internet connection while running.
