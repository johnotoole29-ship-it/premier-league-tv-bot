import threading
import html

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import bot_core


# ============================================================
# HOME PAGE PATCH: ADD LIVE NOW WITHOUT TOUCHING THE CORE FILE
# ============================================================

_original_build_home_page = bot_core.build_home_page


def build_home_page_with_live():
    text, keyboard = _original_build_home_page()

    rows = [
        [
            InlineKeyboardButton(
                "🔴 LIVE NOW",
                callback_data="live_now",
            )
        ],
        *keyboard.inline_keyboard,
    ]

    return text, InlineKeyboardMarkup(rows)


bot_core.build_home_page = build_home_page_with_live


# ============================================================
# LIVE SCORES - THESPORTSDB PREMIUM V2
# ============================================================

LIVE_LEAGUES = {
    "4328": "Premier League",
    "4329": "Championship",
    "4335": "La Liga",
    "4332": "Serie A",
    "4331": "Bundesliga",
    "4334": "Ligue 1",
}


def fetch_live_football():
    url = "https://www.thesportsdb.com/api/v2/json/livescore/soccer"

    try:
        response = requests.get(
            url,
            headers={
                "X-API-KEY": bot_core.SPORTSDB_API_KEY,
            },
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as error:
        bot_core.logger.error(
            "Live score request failed: %s",
            error,
        )
        return None

    if isinstance(data, list):
        events = data
    elif isinstance(data, dict):
        events = (
            data.get("events")
            or data.get("livescore")
            or data.get("livescores")
            or data.get("event")
            or []
        )
    else:
        events = []

    if not isinstance(events, list):
        return []

    filtered = []

    for event in events:
        if str(event.get("idLeague") or "") in LIVE_LEAGUES:
            filtered.append(event)

    return filtered


def build_live_page():
    events = fetch_live_football()

    if events is None:
        text = (
            "🔴 <b>LIVE NOW</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Live scores are temporarily unavailable.\n"
            "Please try again shortly."
        )
    elif not events:
        text = (
            "🔴 <b>LIVE NOW</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "No matches are live right now across:\n\n"
            "🏴 Premier League • Championship\n"
            "🇪🇸 La Liga • 🇮🇹 Serie A\n"
            "🇩🇪 Bundesliga • 🇫🇷 Ligue 1"
        )
    else:
        lines = [
            "🔴 <b>LIVE NOW</b>",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        current_league = None

        for event in events:
            league_id = str(event.get("idLeague") or "")
            league_name = LIVE_LEAGUES.get(
                league_id,
                str(event.get("strLeague") or "Football"),
            )

            if league_name != current_league:
                lines.extend(
                    [
                        "",
                        f"🏆 <b>{html.escape(league_name)}</b>",
                    ]
                )
                current_league = league_name

            home = html.escape(
                str(event.get("strHomeTeam") or "Home")
            )
            away = html.escape(
                str(event.get("strAwayTeam") or "Away")
            )
            home_score = event.get("intHomeScore")
            away_score = event.get("intAwayScore")
            progress = str(
                event.get("strProgress")
                or event.get("strStatus")
                or "LIVE"
            ).strip()

            if home_score in (None, ""):
                home_score = "-"
            if away_score in (None, ""):
                away_score = "-"

            lines.append(
                f"🔴 <b>{home} {home_score}–{away_score} {away}</b>"
            )

            if progress:
                lines.append(
                    f"⏱ {html.escape(progress)}"
                )

        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔄 REFRESH",
                    callback_data="live_now",
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 MAIN MENU",
                    callback_data="menu:home",
                )
            ],
        ]
    )

    return text, keyboard


async def live_now_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    query = update.callback_query

    if not query:
        return

    await query.answer()

    text, keyboard = build_live_page()

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# PRIVATE GROUP-AD PREVIEW
# ============================================================

async def preview_group(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):
    chat = update.effective_chat
    message = update.effective_message

    if not chat or not message:
        return

    if chat.type != "private":
        return

    bot_info = await context.bot.get_me()
    bot_username = bot_info.username

    group_text = (
        "🏟️ <b>SPORTS BOT</b>\n"
        "<b>FIXTURES • TV • LIVE SPORT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚽ Premier League • Championship\n"
        "🌍 La Liga • Serie A • Bundesliga • Ligue 1\n"
        "🏉 Rugby • 🥊 Combat • ⛳ Golf • 🎯 Darts\n"
        "📺 TV & streaming listings • 🕒 UK times\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔒 <b>PRIVATE MATCH CENTRE</b>\n"
        "📩 Tap below for your fixtures & TV guide."
    )

    keyboard = InlineKeyboardMarkup(
        [[
            InlineKeyboardButton(
                "⚡ OPEN MATCH CENTRE",
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
        CallbackQueryHandler(
            live_now_handler,
            pattern=r"^live_now$",
        )
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
