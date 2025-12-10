import os
import telebot
import redis
import time
import threading
from dotenv import load_dotenv

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

# Initialize Bot
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Commands
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
	bot.reply_to(message, "Exhaustion Bot Monitor.\n/status - Check status\n/stop - Kill Switch\n/start_bot - Resume")

@bot.message_handler(commands=['status'])
def send_status(message):
    kill_switch = r.get("bot:kill_switch")
    status = "STOPPED" if kill_switch == "1" else "RUNNING"
    bot.reply_to(message, f"Bot Status: {status}")

@bot.message_handler(commands=['stop'])
def stop_bot(message):
    r.set("bot:kill_switch", "1")
    bot.reply_to(message, "Kill Switch ACTIVATED. Bot stopped.")

@bot.message_handler(commands=['start_bot'])
def start_bot(message):
    r.set("bot:kill_switch", "0")
    bot.reply_to(message, "Bot Resumed.")

def notification_listener():
    # Listen to Redis PubSub or Queue for notifications from other modules
    # Using a list 'notifications' as queue
    print("Notification Listener started")
    while True:
        try:
            msg = r.rpop("notifications")
            if msg and TELEGRAM_CHAT_ID:
                bot.send_message(TELEGRAM_CHAT_ID, f"ALERT: {msg}")
            time.sleep(1)
        except Exception as e:
            print(f"Listener error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram Token not set.")
    else:
        # Start listener thread
        t = threading.Thread(target=notification_listener, daemon=True)
        t.start()
        
        print("Telegram Bot Polling...")
        bot.infinity_polling()
