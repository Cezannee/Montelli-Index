import discord
import yfinance as yf
import asyncio
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CH_ID"))
TARGET_HARGA = float(os.getenv("TARGET"))

intents = discord.Intents.default()
intents.reactions = True
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

subscribed_users = set()
reaction_message_id = None

async def post_reaction_message():
    global reaction_message_id
    channel = client.get_channel(CHANNEL_ID)
    msg = await channel.send(
        "📢 React ✅ untuk **subscribe notifikasi harga BBCA**, ❌ untuk unsubscribe."
    )
    await msg.add_reaction("✅")
    await msg.add_reaction("❌")
    reaction_message_id = msg.id

@client.event
async def on_ready():
    print(f"✅ Bot login sebagai {client.user}")
    await post_reaction_message()
    asyncio.create_task(cek_harga_per_jam())

@client.event
async def on_raw_reaction_add(payload):
    if payload.message_id != reaction_message_id:
        return
    if str(payload.emoji) == "✅":
        subscribed_users.add(payload.user_id)
        print(f"🟢 User {payload.user_id} SUBSCRIBED")
    elif str(payload.emoji) == "❌":
        subscribed_users.discard(payload.user_id)
        print(f"🔴 User {payload.user_id} UNSUBSCRIBED")

@client.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != reaction_message_id:
        return
    if str(payload.emoji) == "✅":
        subscribed_users.discard(payload.user_id)
        print(f"🔴 User {payload.user_id} UNSUBSCRIBED (reaction removed)")

async def cek_harga_per_jam():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            ticker = yf.Ticker("BBCA.JK")
            data = ticker.history(period="2d", interval="1h")

            if not data.empty:
                harga_terakhir = data['Close'].iloc[-1]
                harga_open = data['Open'].iloc[-1]
                harga_prev_close = data['Close'].iloc[-2] if len(data) > 1 else None

                waktu = datetime.now().strftime("%H:%M")
                pesan = f"📊 **Update Saham BBCA [Pukul {waktu}]**\n"
                pesan += f"- 💹 Harga Buka: **Rp{harga_open:,.0f}**\n"
                if harga_prev_close:
                    pesan += f"- 🔚 Harga Tutup Kemarin: **Rp{harga_prev_close:,.0f}**\n"
                pesan += f"- 📍 Harga Saat Ini: **Rp{harga_terakhir:,.0f}**"

                await channel.send(pesan)

                if harga_terakhir > TARGET_HARGA and subscribed_users:
                    mention = " ".join(f"<@{uid}>" for uid in subscribed_users)
                    await channel.send(
                        f"🚨 **Harga BBCA melewati Rp{TARGET_HARGA:,.0f}!**\n"
                        f"Harga saat ini: **Rp{harga_terakhir:,.0f}**\n{mention}"
                    )

            await asyncio.sleep(3600)  # cek tiap jam
        except Exception as e:
            print(f"Error saat cek harga: {e}")
            await asyncio.sleep(3600)
async def main():
    async with client:
        await client.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())