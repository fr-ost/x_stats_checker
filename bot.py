import requests
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

# --- CONFIGURATION ---
TG_TOKEN = '8770600382:AAEh3HM_xASU6rbYau_fjRUFPahMk9Y73GA'
SOCIALDATA_API = '7707|7xmShcTAUFpCGzVQNbqGIVLSEuRnX3Yo6GXI0qNp0d9f4fb0'
X_USERNAME = '0x_nation' 
# ---------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📊 Check Following Count", callback_data='check')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Tap below to check @{X_USERNAME}'s following count:", reply_markup=reply_markup)

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("🔍 Connecting to X...")

    # The SocialData endpoint for user details
    url = f"https://api.socialdata.tools/twitter/user/{X_USERNAME}"
    headers = {
        "Authorization": f"Bearer {SOCIALDATA_API}", 
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        
        # Check for specific HTTP errors
        if response.status_code == 401:
            await query.edit_message_text("❌ Error: API Key is invalid or expired.")
            return
        elif response.status_code == 404:
            await query.edit_message_text(f"❌ Error: The user '@{X_USERNAME}' was not found.")
            return
        elif response.status_code == 429:
            await query.edit_message_text("❌ Error: Out of API credits or rate limited.")
            return

        data = response.json()
        
        # SocialData usually returns 'friends_count' for following
        # We also check for 'following_count' just in case of API updates
        following = data.get('friends_count') or data.get('following_count')

        if following is not None:
            await query.edit_message_text(f"✅ **@{X_USERNAME}** is following **{following}** people.")
        else:
            # If the data is there but the field name changed, this helps us find it
            await query.edit_message_text("❌ Data found, but 'following' count field is missing.")
            print(f"DEBUG DATA: {data}") # Check your console logs for this

    except Exception as e:
        await query.edit_message_text(f"❌ System Error: {str(e)}")

if __name__ == '__main__':
    app = ApplicationBuilder().token(TG_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button, pattern='check'))
    print("Bot is running... Press Ctrl+C to stop.")
    app.run_polling()