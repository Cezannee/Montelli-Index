import discord
import requests
import asyncio
import os
import json
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone
from bs4 import BeautifulSoup


# Load env vars
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CH_ID"))
TARGET_HARGA = float(os.getenv("TARGET"))

# Setup intents
intents = discord.Intents.default()
intents.reactions = True
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

client = discord.Client(intents=intents)

reaction_message_id = None
DATA_FILE = "subscribers.json"

# Load/save subscribers
def load_subscribers():
    try:
        with open(DATA_FILE, "r") as f:
            return set(json.load(f))
    except:
        return set()

def save_subscribers(users):
    with open(DATA_FILE, "w") as f:
        json.dump(list(users), f)

subscribed_users = load_subscribers()

# Dapatkan sesi pasar (WIB)
def get_session_info():
    now = datetime.now(timezone(timedelta(hours=7)))  # timezone WIB
    hour, minute = now.hour, now.minute
    jam = hour + minute / 60

    if jam < 9:
        return "❌ Pasar belum buka", False
    elif 9 <= jam < 12:
        return "🟢 Sesi 1", True
    elif 12 <= jam < 13.5:
        return "⏸ Istirahat", False
    elif 13.5 <= jam < 15:
        return "🟢 Sesi 2", True
    else:
        return "🔒 Pasar Tutup", False

# Ambil harga BBCA dari Google Finance
def get_bbca_price_from_google():
    try:
        url = "https://www.google.com/finance/quote/BBCA:IDX"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(res.text, "html.parser")
        tag = soup.select_one("div.YMlKec.fxKbKc")

        if tag:
            harga_str = tag.text.strip().replace("Rp", "").replace(",", "").replace(".", "")
            return float(harga_str) / 100  # Google kadang tampilkan format sen
        return None
    except Exception as e:
        print(f"❌ Error ambil harga: {e}")
        return None

# Kirim pesan reaksi awal
async def post_reaction_message():
    global reaction_message_id
    channel = client.get_channel(CHANNEL_ID)
    msg = await channel.send("Tekan ✅ untuk **notifikasi target harga BBCA**, ❌ untuk unsubscribe.")
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
        save_subscribers(subscribed_users)
        print(f"🟢 User {payload.user_id} SUBSCRIBED")
    elif str(payload.emoji) == "❌":
        subscribed_users.discard(payload.user_id)
        save_subscribers(subscribed_users)
        print(f"🔴 User {payload.user_id} UNSUBSCRIBED")

@client.event
async def on_raw_reaction_remove(payload):
    if payload.message_id != reaction_message_id:
        return
    if str(payload.emoji) == "✅":
        subscribed_users.discard(payload.user_id)
        save_subscribers(subscribed_users)
        print(f"🔴 User {payload.user_id} UNSUBSCRIBED (reaction removed)")

# Cek harga BBCA dan kirim notifikasi
async def cek_harga_per_jam():
    await client.wait_until_ready()
    channel = client.get_channel(CHANNEL_ID)

    while not client.is_closed():
        try:
            now = datetime.now(timezone(timedelta(hours=7)))  # WIB
            waktu_str = now.strftime("%H:%M")
            sesi_status, is_open = get_session_info()

            if is_open:
                harga = get_bbca_price_from_google()
                if harga:
                    pesan = f"📊 **Update Saham BBCA [Pukul {waktu_str} WIB]**\n"
                    pesan += f"- 🕒 Status Pasar: {sesi_status}\n"
                    pesan += f"- 🎯 Target: Rp.{TARGET_HARGA:,.0f}"
                    pesan += f"- 💰 Harga Saat Ini: **Rp{harga:,.0f}**"

                    if harga > TARGET_HARGA and subscribed_users:
                        mention = " ".join(f"<@{uid}>" for uid in subscribed_users)
                        pesan += f"\n🚨 **Harga melewati Rp{TARGET_HARGA:,.0f}!** {mention}"
                else:
                    pesan = f"⚠️ Gagal mengambil harga BBCA [Pukul {waktu_str} WIB]"
            else:
                pesan = (
                    f"🔒 **Pasar Tidak Aktif [Pukul {waktu_str} WIB]**\n"
                    f"- 🕒 Status: {sesi_status}\n"
                    f"- 💤 Update harga akan dilanjutkan saat pasar buka."
                )

            await channel.send(pesan)
            await asyncio.sleep(3600)

        except Exception as e:
            print(f"❌ Error di loop harga: {e}")
            await asyncio.sleep(3600)

# Jalankan bot
async def main():
    async with client:
        await client.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
