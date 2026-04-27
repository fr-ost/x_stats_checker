import os
import requests
import re
import sqlite3
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONFIG ---
TG_TOKEN = os.getenv('TG_TOKEN')
SOCIALDATA_API = os.getenv('SOCIALDATA_API')
current_data = {"username": "0x_nation"}
DB_PATH = '/app/data/bot_database.db'

# --- DATABASE LOGIC ---
def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS stats_history
                 (username TEXT, timestamp DATETIME, following INTEGER, followers INTEGER, verified INTEGER)''')
    conn.commit()
    conn.close()

def save_snapshot(username, following, followers, verified):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT INTO stats_history (username, timestamp, following, followers, verified) VALUES (?, ?, ?, ?, ?)",
              (username, datetime.now(), int(following), int(followers), int(verified)))
    conn.commit()
    conn.close()

def get_last_snapshot(username):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT following, followers, verified FROM stats_history WHERE username=? ORDER BY timestamp DESC LIMIT 1 OFFSET 1", (username,))
    row = c.fetchone()
    conn.close()
    return row

def escape_md(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

def get_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Analyse Profile", callback_data='analyse')],
        [InlineKeyboardButton("⚙️ Set Target User", callback_data='how_to_change')]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = escape_md(current_data["username"])
    await update.message.reply_text(f"📊 *Dashboard for @{user}*", reply_markup=get_menu_keyboard(), parse_mode='MarkdownV2')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'menu':
        await query.edit_message_text(f"📊 *Dashboard for @{escape_md(current_data['username'])}*", reply_markup=get_menu_keyboard(), parse_mode='MarkdownV2')
        return

    if query.data == 'analyse':
        user_raw = current_data["username"]
        await query.edit_message_text(f"📡 *Fetching data for @{escape_md(user_raw)}\.\.\.*", parse_mode='MarkdownV2')
        
        try:
            # 1. GET PRIMARY DATA
            res = requests.get(f"https://api.socialdata.tools/twitter/user/{user_raw}", 
                               headers={"Authorization": f"Bearer {SOCIALDATA_API}"})
            data = res.json()
            
            # 2. EXTRACT NUMBERS (WITH SMART FALLBACKS)
            f_cur = data.get('friends_count') or data.get('public_metrics', {}).get('following_count', 0)
            fl_cur = data.get('followers_count') or data.get('public_metrics', {}).get('followers_count', 0)
            
            # --- THE VERIFIED FIX ---
            # Try 4 different common field names for Verified Followers
            v_cur = (
                data.get('verified_followers_count') or 
                data.get('blue_verified_followers_count') or 
                data.get('public_metrics', {}).get('verified_followers_count', 0) or
                data.get('ext_is_blue_verified_count', 0)
            )

            # Convert booleans to 0/1 if necessary
            f_cur = int(f_cur) if not isinstance(f_cur, bool) else 0
            fl_cur = int(fl_cur) if not isinstance(fl_cur, bool) else 0
            v_cur = int(v_cur) if not isinstance(v_cur, bool) else 0

            save_snapshot(user_raw, f_cur, fl_cur, v_cur)
            prev = get_last_snapshot(user_raw)
            
            def diff_fmt(cur, old):
                d = cur - old
                return f" \(\+{d}\)" if d > 0 else (f" \({d}\)" if d < 0 else "")

            report = (
                f"👤 *Profile:* @{escape_md(user_raw)}\n"
                f"📅 *Update:* {escape_md(datetime.now().strftime('%Y\-%m\-%d %H:%M'))}\n"
                f"{escape_md('───────────────')}\n"
                f"📈 *Following:* `{f_cur}`{diff_fmt(f_cur, prev[0]) if prev else ''}\n"
                f"👥 *Followers:* `{fl_cur}`{diff_fmt(fl_cur, prev[1]) if prev else ''}\n"
                f"💎 *Verified:* `{v_cur}`{diff_fmt(v_cur, prev[2]) if prev else ''}\n"
                f"{escape_md('───────────────')}"
            )
            
            await query.edit_message_text(text=report, reply_markup=get_menu_keyboard(), parse_mode='MarkdownV2')

        except Exception as e:
            await query.edit_message_text(f"❌ Error: {escape_md(str(e))}", parse_mode='MarkdownV2')

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setuser", lambda u, c: None)) # Placeholder
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()
