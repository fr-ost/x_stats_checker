import os
import requests
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONFIG ---
TG_TOKEN = os.getenv('TG_TOKEN')
SOCIALDATA_API = os.getenv('SOCIALDATA_API')
current_data = {"username": "0x_nation"}

# Helper function to escape special characters for MarkdownV2
def escape_md(text):
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!])', r'\\\1', str(text))

def get_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📈 Following", callback_data='friends_count')],
        [InlineKeyboardButton("👥 Total Followers", callback_data='followers_count')],
        [InlineKeyboardButton("💎 Verified Followers", callback_data='verified_followers_count')],
        [InlineKeyboardButton("⚙️ How to Change User", callback_data='how_to_change')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = escape_md(current_data["username"])
    await update.message.reply_text(
        f"📊 *Dashboard for @{user}*\n\nChoose a metric below:",
        reply_markup=get_menu_keyboard(),
        parse_mode='MarkdownV2'
    )

async def set_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/setuser username`", parse_mode='MarkdownV2')
        return
    
    new_name = context.args[0].replace('@', '').strip()
    current_data["username"] = new_name
    user_escaped = escape_md(new_name)
    
    await update.message.reply_text(
        f"✅ Target changed to *@{user_escaped}*",
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
        await query.edit_message_text(
            f"📊 *Dashboard for @{user_esc}*",
            reply_markup=get_menu_keyboard(),
            parse_mode='MarkdownV2'
        )
        return

    await query.edit_message_text(f"🔍 Fetching data for @{user_esc}...")

    url = f"https://api.socialdata.tools/twitter/user/{user_raw}"
    headers = {"Authorization": f"Bearer {SOCIALDATA_API}", "Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers)
        res_data = response.json()
        
        names = {
            'friends_count': 'Following',
            'followers_count': 'Followers',
            'verified_followers_count': 'Verified Followers'
        }
        
        val = res_data.get(data, "N/A")
        display_name = escape_md(names.get(data, data))
        val_esc = escape_md(val)
        
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data='menu')]])
        await query.edit_message_text(
            text=f"👤 *@{user_esc}*\n📊 *{display_name}:* `{val_esc}`",
            reply_markup=back_btn,
            parse_mode='MarkdownV2'
        )
    except Exception as e:
        await query.edit_message_text(f"❌ API Error: {escape_md(str(e))}", parse_mode='MarkdownV2')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setuser", set_user_command))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()
