import threading

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import bot_core


async def preview_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    chat = update.effective_chat
    message = update.effective_message

    if not chat or not message:
        return

    # Private chat only so this command can never spam a group.
    if chat.type != "private":
        return

    bot_info = await context.bot.get_me()
    bot_username = bot_info.username

    group_text = (
        "🏟️ <b>SPORTS BOT</b>\n"
        "<b>FIXTURES • TV • LIVE SPORT</b>\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "⚡ <b>YOUR MATCHDAY COMPANION</b>\n\n"
        "⚽ Premier League & Championship\n"
        "🌍 La Liga • Serie A • Bundesliga • Ligue 1\n"
        "🏉 Rugby • 🥊 Combat • ⛳ Golf • 🎯 Darts\n"
        "📺 TV & streaming broadcast listings\n"
        "🕒 All fixtures shown in UK local time\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🔒 <b>PRIVATE MATCH CENTRE</b>\n\n"
        "Your fixtures and TV guide are delivered privately, "
        "keeping the group clean and uncluttered.\n\n"
        "📩 <b>Tap below and Sports Bot will send you a private message.</b>\n\n"
        "👇 <b>OPEN YOUR MATCH CENTRE</b>"
    )

    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                "⚡ LAUNCH SPORTS BOT ⚡",
                url=f"https://t.me/{bot_username}?start=open",
            )
        ]]
    )

    await message.reply_text(
        group_text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


def main():
    bot_core.logger.info("Starting Sports Bot...")

    health_thread = threading.Thread(
        target=bot_core.start_health_server,
        daemon=True,
    )
    health_thread.start()

    application = (
        Application
        .builder()
        .token(bot_core.TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", bot_core.start)
    )

    application.add_handler(
        CommandHandler("previewgroup", preview_group)
    )

    application.add_handler(
        CallbackQueryHandler(bot_core.button_handler)
    )

    application.add_error_handler(
        bot_core.error_handler
    )

    bot_core.logger.info("Sports Bot is online.")

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
