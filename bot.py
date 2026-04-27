import os
import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONFIGURATION ---
TG_TOKEN = os.getenv('TG_TOKEN')
SOCIALDATA_API = os.getenv('SOCIALDATA_API')
# Change this to your actual username once, or set it in Railway Variables
X_USERNAME = os.getenv('X_USERNAME', '0x_nation') 

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Create the Dashboard Buttons
    keyboard = [
        [InlineKeyboardButton("📈 Following", callback_data='friends_count')],
        [InlineKeyboardButton("👥 Total Followers", callback_data='followers_count')],
        [InlineKeyboardButton("💎 Verified Followers", callback_data='verified_followers_count')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📊 **@{X_USERNAME} Stats Dashboard**\nSelect a metric to check:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def handle_metrics(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    metric_type = query.data # This gets 'friends_count', etc.
    await query.answer()
    
    await query.edit_message_text(f"🔍 Fetching {metric_type.replace('_', ' ')}...")

    url = f"https://api.socialdata.tools/twitter/user/{X_USERNAME}"
    headers = {"Authorization": f"Bearer {SOCIALDATA_API}", "Accept": "application/json"}

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        
        # Mapping for better display names
        names = {
            'friends_count': 'Following',
            'followers_count': 'Total Followers',
            'verified_followers_count': 'Verified Followers'
        }
        
        value = data.get(metric_type, "N/A")
        
        # Create a "Back" button to return to the menu
        back_keyboard = [[InlineKeyboardButton("⬅️ Back to Menu", callback_data='menu')]]
        back_markup = InlineKeyboardMarkup(back_keyboard)

        await query.edit_message_text(
            text=f"👤 **@{X_USERNAME}**\n📊 **{names[metric_type]}:** `{value}`",
            reply_markup=back_markup,
            parse_mode='Markdown'
        )
    except Exception as e:
        await query.edit_message_text(f"❌ Error: {str(e)}")

async def back_to_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # This just resets the message to the original start menu
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📈 Following", callback_data='friends_count')],
        [InlineKeyboardButton("👥 Total Followers", callback_data='followers_count')],
        [InlineKeyboardButton("💎 Verified Followers", callback_data='verified_followers_count')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📊 **@{X_USERNAME} Stats Dashboard**\nSelect a metric to check:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

if __name__ == '__main__':
    app = ApplicationBuilder().token(TG_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    # This handles the metric buttons
    app.add_handler(CallbackQueryHandler(handle_metrics, pattern='^(friends_count|followers_count|verified_followers_count)$'))
    # This handles the "Back" button
    app.add_handler(CallbackQueryHandler(back_to_menu, pattern='^menu$'))
    
    print("Dashboard Bot is live...")
    app.run_polling()
