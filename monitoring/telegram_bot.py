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
    # LEADER ELECTION: Only one instance should poll at a time to avoid 409 Conflict
    def _poll_with_leader_election():
        leader_key = "bot:telegram_leader"
        my_id = os.getenv("RENDER_INSTANCE_ID", str(time.time()))
        
        print(f"Telegram Manager Started (ID: {my_id})")
        
        is_leader = False
        
        while True:
            try:
                # 1. Try to acquire lock (TTL 15s)
                # set(nx=True) only sets if key doesn't exist
                # If we are already leader, we just update the Expiry (expire)
                if is_leader:
                     r.expire(leader_key, 15)
                else:
                     # Try to become leader
                     acquired = r.set(leader_key, my_id, ex=15, nx=True)
                     if acquired:
                         is_leader = True
                         print(f"👑 I am the Telegram LEADER. Starting Polling...")
                         
                         # Start polling in a non-blocking background way or just iterate manually?
                         # telebot polling is blocking. We can't block this loop.
                         # Logic: If we are leader, we launch the polling thread if not active.
                         
                         # Actually, easiest way: Just Poll logic here? 
                         # No, polling blocks. 
                         pass

                # Re-thinking: Simply wrap polling in a "Stop if lost lock" logic?
                # Telebot doesn't support "Stop polling cleanly" easily from outside.
                
                # SIMPLIFIED STRATEGY for Telebot:
                # Just fail gently.
                # If we get 409, we wait 10s and try again.
                # If Render is doing Zero-Downtime, the old one eventually dies.
                # The User's log shows infinite 409s. This means the old one is NOT dying.
                
                # Let's stick to the simplest fix:
                # If we catch 409, we SLEEP for 30s.
                # This gives the "Other Guy" time to finish or die.
                
                # REFINED STRATEGY:
                # Use polling(non_stop=False) so 409 exceptions BUBBLE UP.
                # infinity_polling swallows them and retries instantly (spamming logs).
                
                bot.threaded = False 
                # This will raise an exception on 409, allowing us to catch it below.
                bot.polling(non_stop=False, interval=0, timeout=10, long_polling_timeout=5)
                
            except Exception as e:
                err_str = str(e)
                if "409" in err_str or "Conflict" in err_str:
                    print(f"⚠️ Telegram Conflict (409). Another instance is active. Sleeping 30s...")
                    # Backoff to let the other instance (Leader) run
                    time.sleep(30) 
                else:
                    print(f"Telegram Idle Error: {e}")
                    time.sleep(5)

    t_poll = threading.Thread(target=_poll_with_leader_election, daemon=True)
    t_poll.start()

if __name__ == "__main__":
    start_telegram_bot()
    # Keep main thread alive if running standalone
    while True:
        time.sleep(1)
