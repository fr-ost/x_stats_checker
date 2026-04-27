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
              (username, datetime.now(), following, followers, verified))
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
    """Deep escape for MarkdownV2 to prevent parsing errors."""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

def get_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("🔍 Analyse Profile", callback_data='analyse')],
        [InlineKeyboardButton("⚙️ Set Target User", callback_data='how_to_change')]
    ]
    return InlineKeyboardMarkup(keyboard)

# --- HANDLERS ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = escape_md(current_data["username"])
    await update.message.reply_text(
        f"📊 *Dashboard for @{user}*\n\nSnapshots are saved automatically when you analyse\.",
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
    data = query.data
    await query.answer()

    user_raw = current_data["username"]
    user_esc = escape_md(user_raw)

    if data == 'how_to_change':
        await query.edit_message_text(
            f"📝 *To change the target:*\nType `/setuser username`",
            reply_markup=get_menu_keyboard(),
            parse_mode='MarkdownV2'
        )
        return

    if data == 'menu':
        await query.edit_message_text(f"📊 *Dashboard for @{user_esc}*", reply_markup=get_menu_keyboard(), parse_mode='MarkdownV2')
        return

    if data == 'analyse':
        await query.edit_message_text(f"📡 *Analysing @{user_esc}\.\.\.*", parse_mode='MarkdownV2')
        
        url = f"https://api.socialdata.tools/twitter/user/{user_raw}"
        headers = {"Authorization": f"Bearer {SOCIALDATA_API}", "Accept": "application/json"}

        try:
            response = requests.get(url, headers=headers)
            res_data = response.json()
            metrics = res_data.get('public_metrics', {})

            f_cur = metrics.get('friends_count') or res_data.get('friends_count') or 0
            fl_cur = metrics.get('followers_count') or res_data.get('followers_count') or 0
            v_cur = metrics.get('verified_followers_count') or res_data.get('blue_verified_followers_count') or 0
            
            f_cur = 0 if isinstance(f_cur, bool) else int(f_cur)
            fl_cur = 0 if isinstance(fl_cur, bool) else int(fl_cur)
            v_cur = 0 if isinstance(v_cur, bool) else int(v_cur)

            save_snapshot(user_raw, f_cur, fl_cur, v_cur)
            prev = get_last_snapshot(user_raw)
            
            def format_diff(cur, old):
                diff = cur - old
                if diff > 0: return f" \(\+{diff}\)"
                if diff < 0: return f" \({diff}\)"
                return ""

            f_diff = format_diff(f_cur, prev[0]) if prev else ""
            fl_diff = format_diff(fl_cur, prev[1]) if prev else ""
            v_diff = format_diff(v_cur, prev[2]) if prev else ""

            # Ensure the date and separator use escaped characters
            date_str = escape_md(datetime.now().strftime('%Y-%m-%d %H:%M'))
            sep = escape_md("───────────────")

            report = (
                f"👤 *Profile:* @{user_esc}\n"
                f"📅 *Last Update:* {date_str}\n"
                f"{sep}\n"
                f"📈 *Following:* `{escape_md(f_cur)}`{f_diff}\n"
                f"👥 *Followers:* `{escape_md(fl_cur)}`{fl_diff}\n"
                f"💎 *Verified:* `{escape_md(v_cur)}`{v_diff}\n"
                f"{sep}\n"
                f"ℹ️ _Growth tracking active since first check\._"
            )
            
            back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Menu", callback_data='menu')]])
            await query.edit_message_text(text=report, reply_markup=back_btn, parse_mode='MarkdownV2')

        except Exception as e:
            await query.edit_message_text(f"❌ Error: {escape_md(str(e))}", parse_mode='MarkdownV2')

if __name__ == '__main__':
    init_db()
    if not TG_TOKEN or not SOCIALDATA_API:
        print("CRITICAL: Environment Variables missing!")
    else:
        app = ApplicationBuilder().token(TG_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("setuser", set_user_command))
        app.add_handler(CallbackQueryHandler(handle_callback))
        app.run_polling()
