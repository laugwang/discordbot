import pandas as pd
import plotly.express as px
import discord
from discord.ext import commands
import asyncio
from config import kw
import config
from shop import run_crawler
from dotenv import load_dotenv
import os

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f'✅ 已登入: {bot.user}')

@bot.command(aliases=["kw"])
async def kwset(ctx, *args):
    config.kw = list(args)
    await ctx.send(f'已更新關鍵字: {config.kw}，開始爬蟲...')

    # 執行爬蟲
    await asyncio.to_thread(run_crawler)
    await ctx.send('✅ 爬蟲完成，請查看 result.csv')

    try:
        # 傳送 CSV 檔案
        await ctx.send("📄 這是爬蟲結果：", file=discord.File("result.csv"))

        # 讀取爬蟲結果
        df = pd.read_csv("result.csv")

        # 處理單價欄位：轉為 float 並移除錯誤值
        df = df[pd.to_numeric(df["單價"], errors="coerce").notnull()]
        df["單價"] = df["單價"].astype(float)

        # 加入 hover 顯示資訊（品名、單價、連結）
        df["hover"] = df.apply(lambda row: f"品名: {row['品名']}<br>單價: {row['單價']}<br>連結: {row['連結']}", axis=1)

        # 建立互動式折線圖
        fig = px.line(
            df,
            x=df.index,
            y="單價",
            markers=True,
            hover_name="hover",
            custom_data=["連結"]
        )

        # 調整圖表外觀
        fig.update_traces(
            marker=dict(size=8)
        )

        fig.update_layout(
            title="輪迴碑石價格互動圖",
            xaxis_title="商品索引",
            yaxis_title="單價 (T)",
            hoverlabel=dict(bgcolor="white"),
        )

        # 儲存為 HTML 並加入 JavaScript 點擊事件
        fig.write_html("interactive_chart.html", include_plotlyjs='cdn', full_html=True)

        # 加入 JS，點擊點時開啟對應連結
        with open("interactive_chart.html", "r", encoding="utf-8") as f:
            html = f.read()

        click_js = """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            var plot = document.getElementsByClassName('plotly-graph-div')[0];
            plot.on('plotly_click', function(data){
                var link = data.points[0].customdata[0];
                window.open(link, '_blank');
            });
        });
        </script>
        """

        # 插入 JS 到 HTML 檔
        html = html.replace("</body>", f"{click_js}</body>")

        with open("interactive_chart.html", "w", encoding="utf-8") as f:
            f.write(html)

        # 傳送 HTML 到 Discord
        await ctx.send("📊 點開這個檔案互動查看價格與連結：", file=discord.File("interactive_chart.html"))

    except Exception as e:
        await ctx.send(f"❌ 發生錯誤：{str(e)}")


load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
bot.run(TOKEN)