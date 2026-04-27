import os
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# --- INITIAL CONFIG ---
TG_TOKEN = os.getenv('TG_TOKEN')
SOCIALDATA_API = os.getenv('SOCIALDATA_API')

# This starts with a default, but we can change it via Telegram
current_user = {"username": os.getenv('X_USERNAME', '0x_nation')}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📈 Following", callback_data='friends_count')],
        [InlineKeyboardButton("👥 Total Followers", callback_data='followers_count')],
        [InlineKeyboardButton("💎 Verified Followers", callback_data='verified_followers_count')],
        [InlineKeyboardButton("⚙️ Change Username", callback_data='change_user')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📊 **Dashboard for @{current_user['username']}**\nSelect a metric or change the target:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def set_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please provide a username.\nExample: `/setuser elonmusk`", parse_mode='Markdown')
        return
    
    new_name = context.args[0].replace('@', '')
    current_user['username'] = new_name
    await update.message.reply_text(f"✅ Success! Target changed to **@{new_name}**.\nType /start to see the menu.")

async def handle_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    metric_type = query.data
    await query.answer()

    if metric_type == 'change_user':
        await query.edit_message_text("📝 To change the username, type:\n`/setuser username`", parse_mode='Markdown')
        return

    await query.edit_message_text(f"🔍 Fetching data for @{current_user['username']}...")

    url = f"https://api.socialdata.tools/twitter/user/{current_user['username']}"
    headers = {"Authorization": f"Bearer {SOCIALDATA_API}", "Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        names = {
            'friends_count': 'Following',
            'followers_count': 'Total Followers',
            'verified_followers_count': 'Verified Followers'
        }
        
        value = data.get(metric_type, "N/A")
        back_markup = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data='menu')]])

        await query.edit_message_text(
            text=f"👤 **@{current_user['username']}**\n📊 **{names[metric_type]}:** `{value}`",
            reply_markup=back_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📈 Following", callback_data='friends_count')],
        [InlineKeyboardButton("👥 Total Followers", callback_data='followers_count')],
        [InlineKeyboardButton("💎 Verified Followers", callback_data='verified_followers_count')],
        [InlineKeyboardButton("⚙️ Change Username", callback_data='change_user')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(f"📊 **Dashboard for @{current_user['username']}**", reply_markup=reply_markup, parse_mode='Markdown')

if __name__ == '__main__':
    app = ApplicationBuilder().token(TG_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("setuser", set_user_command))
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern='^menu$'))
    app.add_handler(CallbackQueryHandler(handle_metrics)) # Catch-all for metrics
    
    print("Multi-User Bot is live...")
    app.run_polling()
