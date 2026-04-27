import os
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# --- CONFIGURATION ---
# These will be pulled from your Railway "Variables" tab
TG_TOKEN = os.getenv('TG_TOKEN')
SOCIALDATA_API = os.getenv('SOCIALDATA_API')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Welcome! Send me any X (Twitter) username, and I'll tell you how many people they are following.\n\n"
        "Example: `elonmusk`"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Get the username from the user's message and clean it
    user_input = update.message.text.strip().replace('@', '')
    
    # Basic validation
    if not user_input:
        await update.message.reply_text("Please enter a valid username.")
        return

    msg = await update.message.reply_text(f"🔍 Fetching following count for @{user_input}...")

    # SocialData API setup
    url = f"https://api.socialdata.tools/twitter/user/{user_input}"
    headers = {
        "Authorization": f"Bearer {SOCIALDATA_API}",
        "Accept": "application/json"
    }

    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            following = data.get('friends_count')
            
            if following is not None:
                await msg.edit_text(f"👤 **@{user_input}**\n✅ Following: **{following}**")
            else:
                await msg.edit_text(f"❌ Could not find following count for @{user_input}.")
        
        elif response.status_code == 404:
            await msg.edit_text(f"❌ Error: The user '@{user_input}' does not exist.")
        elif response.status_code == 429:
            await msg.edit_text("❌ Error: Out of API credits.")
        else:
            await msg.edit_text(f"❌ API Error: {response.status_code}")

    except Exception as e:
        await msg.edit_text(f"❌ System Error: {str(e)}")

if __name__ == '__main__':
    if not TG_TOKEN or not SOCIALDATA_API:
        print("CRITICAL ERROR: Missing TG_TOKEN or SOCIALDATA_API in Variables!")
    else:
        app = ApplicationBuilder().token(TG_TOKEN).build()
        
        # Handle the /start command
        app.add_handler(CommandHandler("start", start))
        
        # Handle all text messages (this is where the username goes)
        # We exclude commands so it doesn't try to scrape "/start"
        app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
        
        print("Bot is live on Railway...")
        app.run_polling()
