import threading
import html

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import bot_core

# Keep both working Telegram group/topic locks.
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
        InlineKeyboardButton(
            "⚡ OPEN MATCH CENTRE",
            url=f"https://t.me/{bot_username}?start=open",
        )
    ]])
    return text, keyboard


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message

    if not chat or not message:
        return

    if chat.type in ["group", "supergroup"]:
        chat_id = str(chat.id)
        thread_id = (
            str(message.message_thread_id)
            if message.message_thread_id
            else None
        )

        allowed = any(
            chat_id.endswith(loc["chat_id"])
            and thread_id == loc["topic_id"]
            for loc in bot_core.ALLOWED_LOCATIONS
        )

        if not allowed:
            return

        bot_info = await context.bot.get_me()
        text, keyboard = build_compact_group_card(bot_info.username)
        await message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        return

    await bot_core.start(update, context)


# ============================================================
# HOME PAGE PATCH
# ============================================================

_original_build_home_page = bot_core.build_home_page


def build_home_page_with_live():
    text, keyboard = _original_build_home_page()
    rows = [
        [InlineKeyboardButton("🔴 LIVE NOW", callback_data="live:menu")],
        *keyboard.inline_keyboard,
    ]
    return text, InlineKeyboardMarkup(rows)


bot_core.build_home_page = build_home_page_with_live


# ============================================================
# LIVE NOW MENUS
# ============================================================

LIVE_LEAGUES = {
    "4328": "Premier League",
    "4329": "Championship",
    "4335": "La Liga",
    "4332": "Serie A",
    "4331": "Bundesliga",
    "4334": "Ligue 1",
}

LIVE_SPORTS = {
    "rugby": {"title": "Rugby", "icon": "🏉", "api": "rugby"},
    "combat": {"title": "Combat", "icon": "🥊", "api": "fighting"},
    "golf": {"title": "Golf", "icon": "⛳", "api": "golf"},
    "darts": {"title": "Darts", "icon": "🎯", "api": "darts"},
}


def build_live_menu():
    text = (
        "🔴 <b>LIVE NOW</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Choose a sport to keep live results separated and easy to read."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⚽ FOOTBALL", callback_data="live:football")],
        [
            InlineKeyboardButton("🏉 RUGBY", callback_data="live:sport:rugby"),
            InlineKeyboardButton("🥊 COMBAT", callback_data="live:sport:combat"),
        ],
        [
            InlineKeyboardButton("⛳ GOLF", callback_data="live:sport:golf"),
            InlineKeyboardButton("🎯 DARTS", callback_data="live:sport:darts"),
        ],
        [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")],
    ])

    return text, keyboard


def build_live_football_menu():
    text = (
        "⚽ <b>LIVE FOOTBALL</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Choose a league to view only its live matches."
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🏴 Premier League", callback_data="live:league:4328"),
            InlineKeyboardButton("🏴 Championship", callback_data="live:league:4329"),
        ],
        [
            InlineKeyboardButton("🇪🇸 La Liga", callback_data="live:league:4335"),
            InlineKeyboardButton("🇮🇹 Serie A", callback_data="live:league:4332"),
        ],
        [
            InlineKeyboardButton("🇩🇪 Bundesliga", callback_data="live:league:4331"),
            InlineKeyboardButton("🇫🇷 Ligue 1", callback_data="live:league:4334"),
        ],
        [InlineKeyboardButton("⬅️ LIVE SPORTS", callback_data="live:menu")],
        [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")],
    ])

    return text, keyboard


# ============================================================
# LIVE SCORE DATA
# ============================================================

def fetch_live_sport(api_sport):
    url = f"https://www.thesportsdb.com/api/v2/json/livescore/{api_sport}"

    try:
        response = requests.get(
            url,
            headers={"X-API-KEY": bot_core.SPORTSDB_API_KEY},
            timeout=20,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as error:
        bot_core.logger.error(
            "Live score request failed for %s: %s",
            api_sport,
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

    return events if isinstance(events, list) else []


def fetch_live_football_league(league_id):
    events = fetch_live_sport("soccer")
    if events is None:
        return None

    return [
        event
        for event in events
        if str(event.get("idLeague") or "") == str(league_id)
    ]


# ============================================================
# GOAL SCORERS
# ============================================================

def fetch_goal_scorers(event_id):
    if not event_id:
        return []

    url = (
        f"{bot_core.SPORTSDB_BASE}/"
        f"{bot_core.SPORTSDB_API_KEY}/"
        "lookuptimeline.php"
    )

    try:
        response = requests.get(
            url,
            params={"id": event_id},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
    except Exception as error:
        bot_core.logger.warning(
            "Timeline request failed for event %s: %s",
            event_id,
            error,
        )
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
            item.get("strTimeline")
            or item.get("strType")
            or item.get("type")
            or item.get("strEvent")
            or ""
        ).lower()

        detail = str(
            item.get("strTimelineDetail")
            or item.get("strDetail")
            or item.get("detail")
            or ""
        ).lower()

        if "goal" not in event_type and "goal" not in detail:
            continue

        player = (
            item.get("strPlayer")
            or item.get("strPlayerName")
            or item.get("strName")
            or item.get("player")
            or "Unknown scorer"
        )

        minute = (
            item.get("intTime")
            or item.get("strTime")
            or item.get("intMinute")
            or item.get("strMinute")
            or item.get("time")
            or ""
        )

        team = (
            item.get("strTeam")
            or item.get("strTeamName")
            or item.get("team")
            or ""
        )

        player_text = html.escape(str(player))
        minute_text = str(minute).strip().replace("'", "")
        team_text = html.escape(str(team).strip())

        if minute_text:
            line = f"⚽ {html.escape(minute_text)}' {player_text}"
        else:
            line = f"⚽ {player_text}"

        if team_text:
            line += f" — {team_text}"

        if line not in goals:
            goals.append(line)

    return goals


# ============================================================
# LIVE PAGE FORMATTERS
# ============================================================

def event_title(event):
    home = str(event.get("strHomeTeam") or "").strip()
    away = str(event.get("strAwayTeam") or "").strip()

    if home and away:
        return f"{home} vs {away}"

    return str(event.get("strEvent") or "Live Event").strip()


def event_score_line(event):
    home = html.escape(str(event.get("strHomeTeam") or "Home"))
    away = html.escape(str(event.get("strAwayTeam") or "Away"))
    home_score = event.get("intHomeScore")
    away_score = event.get("intAwayScore")

    if home_score in (None, "") or away_score in (None, ""):
        return f"🔴 <b>{html.escape(event_title(event))}</b>"

    return f"🔴 <b>{home} {home_score}–{away_score} {away}</b>"


def event_progress(event):
    return str(
        event.get("strProgress")
        or event.get("strStatus")
        or "LIVE"
    ).strip()


def build_live_league_page(league_id):
    league_name = LIVE_LEAGUES.get(str(league_id), "Football")
    events = fetch_live_football_league(league_id)

    if events is None:
        text = (
            f"🔴 <b>{html.escape(league_name.upper())} LIVE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Live scores are temporarily unavailable."
        )
    elif not events:
        text = (
            f"🔴 <b>{html.escape(league_name.upper())} LIVE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "No matches are live in this league right now."
        )
    else:
        lines = [
            f"🔴 <b>{html.escape(league_name.upper())} LIVE</b>",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        for event in events:
            lines.extend(["", event_score_line(event)])

            progress = event_progress(event)
            if progress:
                lines.append(f"⏱ {html.escape(progress)}")

            goals = fetch_goal_scorers(str(event.get("idEvent") or ""))
            if goals:
                lines.extend(goals)

        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 REFRESH", callback_data=f"live:league:{league_id}")],
        [InlineKeyboardButton("⬅️ LIVE FOOTBALL", callback_data="live:football")],
        [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")],
    ])

    return text, keyboard


def build_live_sport_page(sport_key):
    sport = LIVE_SPORTS.get(sport_key)

    if not sport:
        return build_live_menu()

    events = fetch_live_sport(sport["api"])
    title = f"{sport['icon']} {sport['title'].upper()} LIVE"

    if events is None:
        text = (
            f"{title}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "Live scores are temporarily unavailable."
        )
    elif not events:
        text = (
            f"{title}\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"No {sport['title'].lower()} events are live right now."
        )
    else:
        lines = [
            f"{sport['icon']} <b>{sport['title'].upper()} LIVE</b>",
            "━━━━━━━━━━━━━━━━━━━━",
        ]

        for event in events[:20]:
            lines.extend(["", event_score_line(event)])

            league = str(event.get("strLeague") or "").strip()
            if league:
                lines.append(f"🏆 {html.escape(league)}")

            progress = event_progress(event)
            if progress:
                lines.append(f"⏱ {html.escape(progress)}")

        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 REFRESH", callback_data=f"live:sport:{sport_key}")],
        [InlineKeyboardButton("⬅️ LIVE SPORTS", callback_data="live:menu")],
        [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")],
    ])

    return text, keyboard


# ============================================================
# CALLBACK ROUTER
# ============================================================

async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if not query:
        return

    data = query.data or ""

    if data.startswith("live:"):
        await query.answer()

        if data == "live:menu":
            text, keyboard = build_live_menu()

        elif data == "live:football":
            text, keyboard = build_live_football_menu()

        elif data.startswith("live:league:"):
            league_id = data.split(":", 2)[2]
            text, keyboard = build_live_league_page(league_id)

        elif data.startswith("live:sport:"):
            sport_key = data.split(":", 2)[2]
            text, keyboard = build_live_sport_page(sport_key)

        else:
            text, keyboard = build_live_menu()

        await query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )
        return

    await bot_core.button_handler(update, context)


# ============================================================
# PRIVATE GROUP PREVIEW
# ============================================================

async def preview_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message

    if not chat or not message or chat.type != "private":
        return

    bot_info = await context.bot.get_me()
    text, keyboard = build_compact_group_card(bot_info.username)

    await message.reply_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# START BOT
# ============================================================

def main():
    bot_core.logger.info("Starting Sports Bot...")

    health_thread = threading.Thread(
        target=bot_core.start_health_server,
        daemon=True,
    )
    health_thread.start()

    application = (
        Application.builder()
        .token(bot_core.TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("previewgroup", preview_group))
    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_error_handler(bot_core.error_handler)

    bot_core.logger.info("Sports Bot is online.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
