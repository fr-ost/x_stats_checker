import os
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- INITIAL CONFIG ---
TG_TOKEN = os.getenv('TG_TOKEN')
SOCIALDATA_API = os.getenv('SOCIALDATA_API')

# We use a global variable to store the username in memory
# Defaulting to 0x_nation if none is set
current_data = {"username": "0x_nation"}

def get_menu_keyboard():
    keyboard = [
        [InlineKeyboardButton("📈 Following", callback_data='friends_count')],
        [InlineKeyboardButton("👥 Total Followers", callback_data='followers_count')],
        [InlineKeyboardButton("💎 Verified Followers", callback_data='verified_followers_count')],
        [InlineKeyboardButton("⚙️ How to Change User", callback_data='how_to_change')]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_to_show = current_data["username"]
    await update.message.reply_text(
        f"📊 **Dashboard for @{user_to_show}**\n\nChoose a metric below:",
        reply_markup=get_menu_keyboard(),
        parse_mode='Markdown'
    )

async def set_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: `/setuser username`", parse_mode='Markdown')
        return
    
    new_name = context.args[0].replace('@', '').strip()
    current_data["username"] = new_name
    
    # After setting, we automatically show the new menu to save you a click
    await update.message.reply_text(
        f"✅ Target changed to **@{new_name}**",
        reply_markup=get_menu_keyboard(),
        parse_mode='Markdown'
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    await query.answer()

    if data == 'how_to_change':
        await query.edit_message_text(
            "📝 **To change the target:**\nType `/setuser anyname`",
            reply_markup=get_menu_keyboard(),
            parse_mode='Markdown'
        )
        return

    if data == 'menu':
        await query.edit_message_text(
            f"📊 **Dashboard for @{current_data['username']}**",
            reply_markup=get_menu_keyboard(),
            parse_mode='Markdown'
        )
        return

    # Fetching Data
    target = current_data["username"]
    await query.edit_message_text(f"🔍 Fetching {data.replace('_', ' ')} for @{target}...")

    url = f"https://api.socialdata.tools/twitter/user/{target}"
    headers = {"Authorization": f"Bearer {SOCIALDATA_API}", "Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers)
        res_data = response.json()
        
        # Display Mapping
        names = {
            'friends_count': 'Following',
            'followers_count': 'Followers',
            'verified_followers_count': 'Verified Followers'
        }
        
        val = res_data.get(data, "N/A")
        
        back_btn = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data='menu')]])
        await query.edit_message_text(
            text=f"👤 **@{target}**\n📊 **{names.get(data, data)}:** `{val}`",
            reply_markup=back_btn,
            parse_mode='Markdown'
        )
    except Exception as e:
        await query.edit_message_text(f"❌ API Error: {str(e)}")

if __name__ == '__main__':
    if not TG_TOKEN:
        print("CRITICAL: TG_TOKEN is missing!")
    else:
        app = ApplicationBuilder().token(TG_TOKEN).build()
        
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("setuser", set_user_command))
        app.add_handler(CallbackQueryHandler(handle_callback)) # One handler for all buttons
        
        print("Bot is running...")
        app.run_polling()
