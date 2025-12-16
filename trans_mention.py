import requests
import schedule
import time
import os
from datetime import datetime
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
import matplotlib.pyplot as plt
import matplotlib as mpl
import platform
import matplotlib.font_manager as fm
import os
import asyncio

# 配置信息 - 建议使用环境变量存储敏感信息
# todo 添加配置
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', '')
TELEGRAM_CHAT_ID = -100
DISCORD_WEBHOOK = os.getenv('DISCORD_WEBHOOK', 'YOUR_DISCORD_WEBHOOK_URL')
EMAIL_CONFIG = {
    'sender': 'your_email@service.com',
    'password': os.getenv('EMAIL_PASSWORD'),
    'receiver': 'target_email@service.com'
}

def setup_chinese_font():
    """设置中文字体支持"""
    try:
        # 尝试使用系统自带字体
        if platform.system() == 'Darwin':  # macOS
            font_names = ['PingFang HK', 'Heiti TC', 'Songti SC', 'Arial Unicode MS']
        elif platform.system() == 'Windows':
            font_names = ['Microsoft YaHei', 'SimHei']
        else:  # Linux
            font_names = ['WenQuanYi Micro Hei', 'Noto Sans CJK SC']
        
        # 检查字体是否存在
        available_fonts = set([f.name for f in fm.fontManager.ttflist])
        for name in font_names:
            if name in available_fonts:
                plt.rcParams['font.family'] = name
                print(f"使用系统字体: {name}")
                return
        
        # 如果系统字体不存在，尝试加载文泉驿微米黑
        font_path = None
        possible_paths = [
            '/usr/local/share/fonts/font-wqy-microhei/wqy-microhei.ttc',  # Homebrew 安装路径
            '/Library/Fonts/wqy-microhei.ttc',  # macOS 系统路径
            '/usr/share/fonts/wqy-microhei/wqy-microhei.ttc'  # Linux 路径
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                font_path = path
                break
        
        if font_path:
            # 添加字体到Matplotlib
            font_prop = fm.FontProperties(fname=font_path)
            plt.rcParams['font.family'] = font_prop.get_name()
            print(f"使用文泉驿字体: {font_path}")
        else:
            print("警告: 未找到中文字体，使用默认字体")
    
    except Exception as e:
        print(f"字体设置错误: {e}")
    
    # 确保正确显示负号
    plt.rcParams['axes.unicode_minus'] = False

#
def get_fear_greed_index():
    """从Alternative.me API获取贪婪恐慌指数"""
    url = "https://api.alternative.me/fng/"
    try:
        response = requests.get(url, params={'limit': 30})  # 获取30天数据
        data = response.json()
        
        if 'data' in data and data['data']:
            latest = data['data'][0]
            historical = data['data'][1:]
            
            return {
                'current_value': int(latest['value']),
                'classification': latest['value_classification'],
                'historical': [{
                    'date': datetime.utcfromtimestamp(int(entry['timestamp'])).strftime('%Y-%m-%d'),
                    'value': int(entry['value']),
                    'class': entry['value_classification']
                } for entry in historical]
            }
    except Exception as e:
        print(f"Error fetching data: {e}")
    return None

def generate_index_chart(historical_data):
    """生成历史趋势图表"""
    df = pd.DataFrame(historical_data[::-1])  # 反转使最新日期在右侧
    df['value'] = df['value'].astype(int)
    
    plt.figure(figsize=(10, 6))
    plt.plot(df['date'], df['value'], marker='o', color='#ff9900', linewidth=2.5)
    plt.fill_between(df['date'], df['value'], 0, alpha=0.2, color='#ff9900')
    
    # 添加关键水平线
    plt.axhline(y=25, color='green', linestyle='--', alpha=0.5)
    plt.axhline(y=75, color='red', linestyle='--', alpha=0.5)
    
    # 标记极端区域
    plt.fill_between(df['date'], 0, 25, color='green', alpha=0.1)
    plt.fill_between(df['date'], 75, 100, color='red', alpha=0.1)
    
    plt.title('30天贪婪恐慌指数趋势', fontsize=14)
    plt.ylabel('指数值', fontsize=12)
    plt.xticks(rotation=45)
    plt.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    
    # 保存为内存中的字节流
    img_buffer = BytesIO()
    plt.savefig(img_buffer, format='png')
    img_buffer.seek(0)
    plt.close()
    
    return img_buffer

async def send_telegram_message(data, chart_img):
    """通过Telegram发送消息和图表"""
    from telegram import Bot, InputMediaPhoto
    try:
    # 创建消息文本
        message = (
            f"🚨 **加密货币市场情绪报告** 🚨\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"📊 **当前指数**: {data['current_value']} - {data['classification']}\n"
            f"🔍 **解读**: {get_index_interpretation(data['current_value'])}\n\n"
            f"📈 **30天趋势**: 已附图表\n\n"
            f"💡 **操作建议**: {get_trading_suggestion(data['current_value'])}"
        )
        
        # 初始化Bot并发送
        bot = Bot(token=TELEGRAM_TOKEN)
        await bot.send_media_group(
            chat_id=TELEGRAM_CHAT_ID,
            media=[InputMediaPhoto(media=chart_img, caption=message)]
        )
        print("Telegram消息发送成功")
    except Exception as e:
        print(f"Telegram消息发送失败: {e}")

def send_discord_message(data, chart_img):
    """通过Discord发送消息"""
    import discord
    from discord import Webhook, RequestsWebhookAdapter
    
    # 创建消息
    embed = discord.Embed(
        title="加密货币贪婪恐慌指数报告",
        description=f"当前指数: **{data['current_value']}** - {data['classification']}",
        color=0xff9900
    )
    embed.add_field(name="解读", value=get_index_interpretation(data['current_value']), inline=False)
    embed.add_field(name="操作建议", value=get_trading_suggestion(data['current_value']), inline=False)
    embed.set_footer(text=f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 发送到Webhook
    webhook = Webhook.from_url(DISCORD_WEBHOOK, adapter=RequestsWebhookAdapter())
    webhook.send(embed=embed, file=discord.File(chart_img, filename='fear_greed_chart.png'))

def get_index_interpretation(value):
    """根据指数值返回解读"""
    if value <= 25:
        return "市场极度恐慌，可能出现超卖机会"
    elif value <= 45:
        return "市场处于恐慌状态，投资者谨慎"
    elif value <= 55:
        return "市场情绪中性，无明显方向"
    elif value <= 75:
        return "市场贪婪情绪上升，需警惕过热"
    else:
        return "市场极度贪婪，高风险区域，回调可能性高"

def get_trading_suggestion(value):
    """根据指数值返回交易建议"""
    if value <= 25:
        return "考虑分批建仓，关注价值币种"
    elif value <= 45:
        return "可选择性建仓，控制仓位规模"
    elif value <= 55:
        return "保持现有仓位，等待明确信号"
    elif value <= 75:
        return "考虑部分获利了结，收紧止损"
    else:
        return "减少高风险仓位，增加稳定币配置"

def send_email_report(data, chart_img):
    """通过电子邮件发送报告（可选）"""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.image import MIMEImage
    
    # 创建邮件内容
    msg = MIMEMultipart()
    msg['From'] = EMAIL_CONFIG['sender']
    msg['To'] = EMAIL_CONFIG['receiver']
    msg['Subject'] = f"加密货币情绪报告 - {datetime.now().strftime('%Y-%m-%d')}"
    
    # 创建HTML内容
    html = f"""
    <html>
      <body>
        <h2>加密货币贪婪恐慌指数报告</h2>
        <p><strong>当前指数</strong>: {data['current_value']} - {data['classification']}</p>
        <p><strong>解读</strong>: {get_index_interpretation(data['current_value'])}</p>
        <p><strong>操作建议</strong>: {get_trading_suggestion(data['current_value'])}</p>
        <p><strong>更新时间</strong>: {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
        <img src="cid:fear_greed_chart">
      </body>
    </html>
    """
    
    msg.attach(MIMEText(html, 'html'))
    
    # 添加图表
    img = MIMEImage(chart_img.getvalue())
    img.add_header('Content-ID', '<fear_greed_chart>')
    msg.attach(img)
    
    # 发送邮件
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
        server.login(EMAIL_CONFIG['sender'], EMAIL_CONFIG['password'])
        server.send_message(msg)

def send_daily_report():
    """每日报告发送主函数"""
    print(f"{datetime.now()} - 开始获取贪婪恐慌指数...")
    data = get_fear_greed_index()
    
    if not data:
        print("获取数据失败，跳过本次发送")
        return
    
    print(f"当前指数: {data['current_value']} ({data['classification']})")
    
    # 生成图表
    chart_img = generate_index_chart(data['historical'])
    
    # 发送到不同平台
    if TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        # 发送Telegram消息（异步）
        loop = asyncio.get_event_loop()
        loop.run_until_complete(send_telegram_message(data, chart_img))
    
    # if DISCORD_WEBHOOK:
    #     send_discord_message(data, chart_img)
    
    # if EMAIL_CONFIG.get('sender') and EMAIL_CONFIG.get('password'):
    #     send_email_report(data, chart_img)
    
    print("报告发送完成\n")

if __name__ == "__main__":
    # 在代码开头调用
    setup_chinese_font()
    #设置定时任务（每天北京时间20:00发送）
    schedule.every().day.at("12:00").do(send_daily_report)  # UTC时间12:00 = 北京时间20:00
    
    # 立即发送一次测试
    send_daily_report()
    
    # 保持程序运行
    # while True:
    #     schedule.run_pending()
    #     time.sleep(60)