import os
import requests
import re
import sqlite3
from datetime import datetime
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONFIGURATION ---
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

# --- UTILS ---
def escape_md(text):
    """Aggressive escape for MarkdownV2 to prevent any parsing errors."""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

def get_menu_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔍 Analyse Profile", callback_data='analyse')],
        [InlineKeyboardButton("⚙️ Set Target User", callback_data='how_to_change')]
    ])

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = escape_md(current_data["username"])
    await update.message.reply_text(
        f"📊 *Dashboard for @{user}*",
        reply_markup=get_menu_keyboard(),
        parse_mode='MarkdownV2'
    )

async def set_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/setuser username`", parse_mode='MarkdownV2')
        return
    new_name = context.args[0].replace('@', '').strip()
    current_data["username"] = new_name
    await update.message.reply_text(
        f"✅ Target changed to *@{escape_md(new_name)}*",
        reply_markup=get_menu_keyboard(),
        parse_mode='MarkdownV2'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_raw = current_data["username"]
    user_esc = escape_md(user_raw)

    if query.data == 'how_to_change':
        await query.edit_message_text(
            f"📝 *To change the target:*\nType `/setuser username`",
            reply_markup=get_menu_keyboard(),
            parse_mode='MarkdownV2'
        )
        return

    if query.data == 'menu':
        await query.edit_message_text(f"📊 *Dashboard for @{user_esc}*", reply_markup=get_menu_keyboard(), parse_mode='MarkdownV2')
        return

    if query.data == 'analyse':
        await query.edit_message_text(f"📡 *Fetching data for @{user_esc}\.\.\.*", parse_mode='MarkdownV2')
        
        try:
            res = requests.get(f"https://api.socialdata.tools/twitter/user/{user_raw}", 
                               headers={"Authorization": f"Bearer {SOCIALDATA_API}"})
            data = res.json()
            
            # Extract numbers with safety
            f_cur = data.get('friends_count') or data.get('public_metrics', {}).get('following_count', 0)
            fl_cur = data.get('followers_count') or data.get('public_metrics', {}).get('followers_count', 0)
            v_cur = (
                data.get('verified_followers_count') or 
                data.get('blue_verified_followers_count') or 
                data.get('public_metrics', {}).get('verified_followers_count', 0) or
                data.get('ext_is_blue_verified_count', 0)
            )

            # Ensure they are integers
            f_cur = int(f_cur) if not isinstance(f_cur, bool) else 0
            fl_cur = int(fl_cur) if not isinstance(fl_cur, bool) else 0
            v_cur = int(v_cur) if not isinstance(v_cur, bool) else 0

            save_snapshot(user_raw, f_cur, fl_cur, v_cur)
            prev = get_last_snapshot(user_raw)
            
            def diff_fmt(cur, old):
                d = cur - old
                if d > 0: return escape_md(f" (+{d})")
                if d < 0: return escape_md(f" ({d})")
                return ""

            date_str = escape_md(datetime.now().strftime('%Y-%m-%d %H:%M'))
            sep = escape_md("───────────────")

            report = (
                f"👤 *Profile:* @{user_esc}\n"
                f"📅 *Update:* {date_str}\n"
                f"{sep}\n"
                f"📈 *Following:* `{f_cur}`{diff_fmt(f_cur, prev[0]) if prev else ''}\n"
                f"👥 *Followers:* `{fl_cur}`{diff_fmt(fl_cur, prev[1]) if prev else ''}\n"
                f"💎 *Verified:* `{v_cur}`{diff_fmt(v_cur, prev[2]) if prev else ''}\n"
                f"{sep}"
            )
            
            await query.edit_message_text(text=report, reply_markup=get_menu_keyboard(), parse_mode='MarkdownV2')

        except Exception as e:
            await query.edit_message_text(f"❌ Error: {escape_md(str(e))}", parse_mode='MarkdownV2')

if __name__ == '__main__':
    init_db()
    if not TG_TOKEN or not SOCIALDATA_API:
        print("Variables missing!")
    else:
        app = ApplicationBuilder().token(TG_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("setuser", set_user_command))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.run_polling()
