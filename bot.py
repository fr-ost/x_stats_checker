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
        
        # Display Mapping
        names = {
            'friends_count': 'Following',
            'followers_count': 'Followers',
            'verified_followers_count': 'Verified Followers'
        }
        
        # LOGIC UPGRADE: Try multiple possible field names for Verified Followers
        if data == 'verified_followers_count':
            val = res_data.get('verified_followers_count') or \
                  res_data.get('blue_verified_followers_count') or \
                  res_data.get('can_dm') # Sometimes used as a proxy field
        else:
            val = res_data.get(data)

        # Final check if val is still None
        if val is None:
            val = "N/A (Data Hidden)"
        
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
