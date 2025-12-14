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

def start_telegram_bot():
    if not TELEGRAM_BOT_TOKEN:
        print("Telegram Token not set. Skpping Bot startup.")
        return

    # Start listener thread (Redis -> Telegram)
    t_listener = threading.Thread(target=notification_listener, daemon=True)
    t_listener.start()
    
    # Start Polling thread (Telegram -> Bot Commands)
    def _poll():
        try:
             print("Telegram Bot Polling...")
             bot.infinity_polling(restart_on_change=False)
        except Exception as e:
             if "409" in str(e) or "Conflict" in str(e):
                 print("Telegram Conflict (409): Another bot instance is running. Disabling polling on this instance.")
                 return # Exit thread cleanly
             print(f"Telegram Polling Error: {e}")

    t_poll = threading.Thread(target=_poll, daemon=True)
    t_poll.start()

if __name__ == "__main__":
    start_telegram_bot()
    # Keep main thread alive if running standalone
    while True:
        time.sleep(1)
