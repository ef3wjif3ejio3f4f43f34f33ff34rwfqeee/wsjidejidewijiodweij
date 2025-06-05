const { Client, GatewayIntentBits } = require('discord.js');
const schedule = require('node-schedule');
const express = require('express');
const RSSParser = require('rss-parser');
const dotenv = require('dotenv');
const path = require('path');

dotenv.config({ path: path.join(__dirname, 'env/.env') });

const client = new Client({
  intents: [GatewayIntentBits.Guilds, GatewayIntentBits.GuildMessages, GatewayIntentBits.MessageContent]
});

const parser = new RSSParser();
const app = express();
const port = 8080;

const positiveKeywords = [
  "優勝", "快挙", "開業", "開店", "新発売", "発表", "好評", "オープン", "受賞", "上昇",
  "最高", "新記録", "成長", "成功", "人気", "活躍", "新曲", "映画", "イベント", "祭り",
  "フェス", "コンサート"
];

async function fetchTrends() {
  try {
    const feed = await parser.parseURL('https://news.google.com/rss?hl=ja&gl=JP&ceid=JP:ja');

    let filtered = feed.items.filter(item =>
      positiveKeywords.some(keyword => item.title.includes(keyword))
    ).slice(0, 5);

    if (filtered.length < 5) {
      const extra = feed.items.slice(0, 5 - filtered.length);
      filtered = filtered.concat(extra);
    }

    const now = new Date();
    const timeStr = now.toTimeString().split(' ')[0].slice(0, 5);

    let text = `📃現在のニュース（${timeStr} 現在）\n`;
    filtered.forEach((item, index) => {
      text += `${index + 1}. [${item.title}](${item.link})\n`;
    });

    return text;
  } catch (error) {
    console.error("❌ ニュース取得失敗:", error);
    return "❌ ニュース取得に失敗しました。";
  }
}

async function sendTrends() {
  const channel = await client.channels.fetch(process.env.CHANNEL_ID);
  if (channel) {
    const trends = await fetchTrends();
    await channel.send(trends);
  } else {
    console.log("⚠️ チャンネルが見つかりませんでした。");
  }
}

// 定時実行: 6:00, 12:00, 18:00
schedule.scheduleJob('0 6,12,18 * * *', () => {
  sendTrends();
});

// 起動確認用 express サーバー
app.get('/', (req, res) => {
  res.send('Bot is running!');
});

app.listen(port, () => {
  console.log(`🌐 Express server running on port ${port}`);
});

// Discordイベント
client.once('ready', () => {
  console.log(`✅ Bot is ready: ${client.user.tag}`);
});

client.on('messageCreate', async (message) => {
  if (message.author.bot) return;

  if (message.content === '!gtrand') {
    if (message.member.permissions.has('Administrator')) {
      const trends = await fetchTrends();
      await message.channel.send(trends);
    } else {
      await message.channel.send("❌ このコマンドは管理者のみ使えます。");
    }
  }
});

client.login(process.env.DISCORD_TOKEN);
