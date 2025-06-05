from flask import Flask
from threading import Thread
import schedule
import time
import datetime
import discord
from discord.ext import tasks
from pytrends.request import TrendReq
import feedparser
import re
from dotenv import load_dotenv
import os

# ====== 環境設定 ======
CHANNEL_ID = 1116735137594474577  # ← 送信先チャンネルID
load_dotenv(dotenv_path="env/.env")

# ====== Discord設定 ======
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ====== Flaskサーバー ======
app = Flask(__name__)


@app.route("/")
def home():
    return "Bot is running!"


def run_flask():
    app.run(host="0.0.0.0", port=8080)


# ====== トレンド取得関数（共通） ======
async def fetch_trends():
    try:
        rss_url = "https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja"
        feed = feedparser.parse(rss_url)

        # ポジティブワード（必要に応じて増やせます）
        positive_keywords = [
            "優勝", "快挙", "開業", "開店", "新発売", "発表", "好評", "オープン", "受賞", "上昇",
            "最高", "新記録", "成長", "成功", "人気", "活躍", "新曲", "映画", "イベント", "祭り",
            "フェス", "コンサート"
        ]

        # フィルターして上位5件まで取得
        filtered = [
            entry for entry in feed.entries if any(
                re.search(k, entry.title) for k in positive_keywords)
        ][:5]

        # 5件未満の場合は補完（ネガティブも含める）
        if len(filtered) < 5:
            filtered += feed.entries[:5 - len(filtered)]

        trend_list = "\n".join([
            f"{i+1}. [{entry.title}](<{entry.link}>)"  # 埋め込み抑制
            for i, entry in enumerate(filtered)
        ])
        now = datetime.datetime.now().strftime("%H:%M")

        return f"📃現在のニュース（{now} 現在）\n{trend_list}"

    except Exception as e:
        print("❌ ニュース取得に失敗:", e)
        return "❌ ニュース取得に失敗しました。"


# ====== 定期送信用の関数 ======
async def send_trends():
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        trends = await fetch_trends()
        await channel.send(trends)
    else:
        print("⚠️ チャンネルが見つかりませんでした。")


# ====== スケジューラー（バックグラウンド） ======
def schedule_tasks():

    async def job():
        await send_trends()

    def run_async_job():
        loop = client.loop
        loop.create_task(job())

    # スケジュール設定（朝6時・正午12時・夕方6時）
    schedule.every().day.at("06:00").do(run_async_job)
    schedule.every().day.at("12:00").do(run_async_job)
    schedule.every().day.at("18:00").do(run_async_job)

    while True:
        schedule.run_pending()
        time.sleep(60)


# ====== Discordイベント ======
@client.event
async def on_ready():
    print(f"✅ Bot is ready: {client.user}")
    channel = client.get_channel(CHANNEL_ID)
    print(f"📘 get_channel の型: {type(channel)}")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if message.content == "!gtrand":
        if message.author.guild_permissions.administrator:
            trends = await fetch_trends()
            await message.channel.send(trends)
        else:
            await message.channel.send("❌ このコマンドは管理者のみ使えます。")


# ====== 実行開始 ======
if __name__ == "__main__":
    Thread(target=run_flask).start()
    Thread(target=schedule_tasks).start()
    TOKEN = os.getenv("DISCORD_TOKEN")
