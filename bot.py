import threading
import html

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import bot_core

bot_core.ALLOWED_LOCATIONS = [
    {"chat_id": "3988874271", "topic_id": "10394"},
    {"chat_id": "2523097986", "topic_id": "12121"},
]


def build_compact_group_card(bot_username):
    text = (
        "🏟️ <b>SPORTS BOT</b>\n"
        "<b>FIXTURES • TV • LIVE SPORT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚽ Premier League • Championship\n"
        "🌍 La Liga • Serie A • Bundesliga • Ligue 1\n"
        "🏉 Rugby • 🥊 Combat • ⛳ Golf • 🎯 Darts\n"
        "📺 TV listings • 🕒 UK times\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔒 <b>PRIVATE MATCH CENTRE</b>\n"
        "📩 Tap below for fixtures, TV & live scores."
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("⚡ OPEN MATCH CENTRE", url=f"https://t.me/{bot_username}?start=open")
    ]])
    return text, keyboard


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    if not chat or not message:
        return
    if chat.type in ["group", "supergroup"]:
        chat_id = str(chat.id)
        thread_id = str(message.message_thread_id) if message.message_thread_id else None
        allowed = any(
            chat_id.endswith(loc["chat_id"]) and thread_id == loc["topic_id"]
            for loc in bot_core.ALLOWED_LOCATIONS
        )
        if not allowed:
            return
        bot_info = await context.bot.get_me()
        text, keyboard = build_compact_group_card(bot_info.username)
        await message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
        return
    await bot_core.start(update, context)


_original_build_home_page = bot_core.build_home_page


def build_home_page_with_live():
    text, keyboard = _original_build_home_page()
    rows = [[InlineKeyboardButton("🔴 LIVE NOW", callback_data="live_now")], *keyboard.inline_keyboard]
    return text, InlineKeyboardMarkup(rows)


bot_core.build_home_page = build_home_page_with_live

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
        response = requests.get(url, headers={"X-API-KEY": bot_core.SPORTSDB_API_KEY}, timeout=20)
        response.raise_for_status()
        data = response.json()
    except Exception as error:
        bot_core.logger.error("Live score request failed: %s", error)
        return None
    if isinstance(data, list):
        events = data
    elif isinstance(data, dict):
        events = data.get("events") or data.get("livescore") or data.get("livescores") or data.get("event") or []
    else:
        events = []
    if not isinstance(events, list):
        return []
    return [event for event in events if str(event.get("idLeague") or "") in LIVE_LEAGUES]


def fetch_goal_scorers(event_id):
    if not event_id:
        return []

    # Premium V1 timeline endpoint. The API key belongs in the URL path.
    url = f"{bot_core.SPORTSDB_BASE}/{bot_core.SPORTSDB_API_KEY}/lookuptimeline.php"

    try:
        response = requests.get(url, params={"id": event_id}, timeout=15)
        response.raise_for_status()
        data = response.json()
    except Exception as error:
        bot_core.logger.warning("Timeline request failed for event %s: %s", event_id, error)
        return []

    if not isinstance(data, dict):
        return []

    timeline = data.get("timeline") or []
    if not isinstance(timeline, list):
        return []

    goals = []
    for item in timeline:
        if not isinstance(item, dict):
            continue

        event_type = str(
            item.get("strTimeline") or item.get("strType") or item.get("type") or item.get("strEvent") or ""
        ).lower()
        detail = str(
            item.get("strTimelineDetail") or item.get("strDetail") or item.get("detail") or ""
        ).lower()

        if "goal" not in event_type and "goal" not in detail:
            continue

        player = (
            item.get("strPlayer") or item.get("strPlayerName") or item.get("strName") or item.get("player") or "Unknown scorer"
        )
        minute = (
            item.get("intTime") or item.get("strTime") or item.get("intMinute") or item.get("strMinute") or item.get("time") or ""
        )
        team = item.get("strTeam") or item.get("strTeamName") or item.get("team") or ""

        player_text = html.escape(str(player))
        minute_text = str(minute).strip().replace("'", "")
        team_text = html.escape(str(team).strip())

        line = f"⚽ {html.escape(minute_text)}' {player_text}" if minute_text else f"⚽ {player_text}"
        if team_text:
            line += f" — {team_text}"
        if line not in goals:
            goals.append(line)

    return goals


def build_live_page():
    events = fetch_live_football()
    if events is None:
        text = "🔴 <b>LIVE NOW</b>\n━━━━━━━━━━━━━━━━━━━━\nLive scores are temporarily unavailable.\nPlease try again shortly."
    elif not events:
        text = (
            "🔴 <b>LIVE NOW</b>\n━━━━━━━━━━━━━━━━━━━━\nNo matches are live right now across:\n\n"
            "🏴 Premier League • Championship\n🇪🇸 La Liga • 🇮🇹 Serie A\n🇩🇪 Bundesliga • 🇫🇷 Ligue 1"
        )
    else:
        lines = ["🔴 <b>LIVE NOW</b>", "━━━━━━━━━━━━━━━━━━━━"]
        current_league = None
        for event in events:
            league_id = str(event.get("idLeague") or "")
            league_name = LIVE_LEAGUES.get(league_id, str(event.get("strLeague") or "Football"))
            if league_name != current_league:
                lines.extend(["", f"🏆 <b>{html.escape(league_name)}</b>"])
                current_league = league_name

            home = html.escape(str(event.get("strHomeTeam") or "Home"))
            away = html.escape(str(event.get("strAwayTeam") or "Away"))
            home_score = event.get("intHomeScore")
            away_score = event.get("intAwayScore")
            progress = str(event.get("strProgress") or event.get("strStatus") or "LIVE").strip()
            if home_score in (None, ""):
                home_score = "-"
            if away_score in (None, ""):
                away_score = "-"

            lines.append(f"🔴 <b>{home} {home_score}–{away_score} {away}</b>")
            if progress:
                lines.append(f"⏱ {html.escape(progress)}")

            goals = fetch_goal_scorers(str(event.get("idEvent") or ""))
            if goals:
                lines.extend(goals)

        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 REFRESH", callback_data="live_now")],
        [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")],
    ])
    return text, keyboard


async def live_now_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    text, keyboard = build_live_page()
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    if (query.data or "") == "live_now":
        await live_now_handler(update, context)
        return
    await bot_core.button_handler(update, context)


async def preview_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    if not chat or not message or chat.type != "private":
        return
    bot_info = await context.bot.get_me()
    text, keyboard = build_compact_group_card(bot_info.username)
    await message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


def main():
    bot_core.logger.info("Starting Sports Bot...")
    health_thread = threading.Thread(target=bot_core.start_health_server, daemon=True)
    health_thread.start()

    application = Application.builder().token(bot_core.TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("previewgroup", preview_group))
    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_error_handler(bot_core.error_handler)

    bot_core.logger.info("Sports Bot is online.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
