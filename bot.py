import os
import json
import logging
import urllib.request
import urllib.parse
from datetime import datetime, timedelta, timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ============================================================
# SETTINGS
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TELEGRAM_TOKEN:
    raise ValueError("ERROR: TELEGRAM_TOKEN is missing")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# ============================================================
# API URLS
# ============================================================

ESPN_URLS = {
    "football": "https://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard",
    "basketball": "https://site.api.espn.com/apis/site/v2/sports/basketball/nba/scoreboard",
    "nfl": "https://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard",
    "f1": "https://site.api.espn.com/apis/site/v2/sports/racing/f1/scoreboard",
    "tennis_atp": "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard",
    "tennis_wta": "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard",
}

# TheSportsDB fallback leagues
SPORTSDB_LEAGUES = {
    "f1": "4370",
}

# ============================================================
# HTTP HELPERS
# ============================================================

def get_json(url, timeout=15):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0 SportsTVBot"
            },
        )

        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))

    except Exception as error:
        logger.error(f"API error: {error}")
        return None


# ============================================================
# MENUS
# ============================================================

def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("⚽ Football", callback_data="football"),
            InlineKeyboardButton("🏎 Formula 1", callback_data="f1"),
        ],
        [
            InlineKeyboardButton("🏀 Basketball", callback_data="basketball"),
            InlineKeyboardButton("🏈 NFL", callback_data="nfl"),
        ],
        [
            InlineKeyboardButton("🏉 Rugby", callback_data="rugby"),
            InlineKeyboardButton("🎾 Tennis", callback_data="tennis"),
        ],
        [
            InlineKeyboardButton("🎯 Darts", callback_data="darts"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def back_menu():
    keyboard = [
        [
            InlineKeyboardButton("⬅️ Main Menu", callback_data="main"),
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


def football_menu():
    keyboard = [
        [
            InlineKeyboardButton("📅 Today's Matches", callback_data="football_today"),
        ],
        [
            InlineKeyboardButton("📆 Next Matches", callback_data="football_next"),
        ],
        [
            InlineKeyboardButton("⬅️ Main Menu", callback_data="main"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def sport_menu(sport):
    keyboard = [
        [
            InlineKeyboardButton("📅 Today", callback_data=f"{sport}_today"),
        ],
        [
            InlineKeyboardButton("📆 Upcoming", callback_data=f"{sport}_next"),
        ],
        [
            InlineKeyboardButton("⬅️ Main Menu", callback_data="main"),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# DATE / TIME HELPERS
# ============================================================

def format_time(date_string):
    if not date_string:
        return "Time TBC"

    try:
        dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))

        # UK time automatically handled reasonably from UTC
        now = datetime.now().astimezone()
        local_time = dt.astimezone(now.tzinfo)

        return local_time.strftime("%H:%M")

    except Exception:
        return "Time TBC"


def event_date(date_string):
    if not date_string:
        return None

    try:
        dt = datetime.fromisoformat(date_string.replace("Z", "+00:00"))
        return dt.date()
    except Exception:
        return None


# ============================================================
# ESPN EVENTS
# ============================================================

def get_espn_events(sport, days=0):
    url = ESPN_URLS.get(sport)

    if not url:
        return []

    data = get_json(url)

    if not data:
        return []

    events = data.get("events", [])

    today = datetime.now().date()

    results = []

    for event in events:

        event_datetime = event.get("date")
        date = event_date(event_datetime)

        if not date:
            continue

        # Today only
        if days == 0 and date != today:
            continue

        # Upcoming
        if days > 0:
            last_date = today + timedelta(days=days)

            if date < today or date > last_date:
                continue

        results.append(event)

    return results


def format_espn_events(events, title):
    if not events:
        return f"📭 *{title}*\n\nNo events found right now."

    text = f"*{title}*\n\n"

    for event in events[:15]:

        competitions = event.get("competitions", [])

        if not competitions:
            continue

        competition = competitions[0]
        competitors = competition.get("competitors", [])

        home = None
        away = None

        for competitor in competitors:

            team = competitor.get("team", {})
            name = team.get("displayName", "TBC")

            if competitor.get("homeAway") == "home":
                home = name

            elif competitor.get("homeAway") == "away":
                away = name

        if not home or not away:

            event_name = event.get("name")

            if event_name:
                home = event_name
                away = ""

        time = format_time(event.get("date"))

        league = event.get("season", {}).get("slug", "")
        league = league.replace("-", " ").title()

        if away:
            text += f"🏟 *{home} vs {away}*\n"
        else:
            text += f"🏟 *{home}*\n"

        if league:
            text += f"🏆 {league}\n"

        text += f"🕒 {time}\n\n"

    return text


# ============================================================
# FOOTBALL
# ============================================================

async def get_football_today():
    events = get_espn_events("football", 0)

    return format_espn_events(
        events,
        "⚽ Premier League - Today's Matches"
    )


async def get_football_next():
    events = get_espn_events("football", 7)

    return format_espn_events(
        events,
        "⚽ Premier League - Upcoming Matches"
    )


# ============================================================
# FORMULA 1
# ============================================================

async def get_f1_today():
    events = get_espn_events("f1", 0)

    return format_espn_events(
        events,
        "🏎 Formula 1 - Today"
    )


async def get_f1_next():
    events = get_espn_events("f1", 30)

    if events:
        return format_espn_events(
            events,
            "🏎 Formula 1 - Upcoming"
        )

    return (
        "🏎 *Formula 1 - Upcoming*\n\n"
        "No Formula 1 event is currently available in the live schedule."
    )


# ============================================================
# BASKETBALL
# ============================================================

async def get_basketball_today():
    events = get_espn_events("basketball", 0)

    return format_espn_events(
        events,
        "🏀 Basketball - Today's Games"
    )


async def get_basketball_next():
    events = get_espn_events("basketball", 7)

    return format_espn_events(
        events,
        "🏀 Basketball - Upcoming Games"
    )


# ============================================================
# NFL
# ============================================================

async def get_nfl_today():
    events = get_espn_events("nfl", 0)

    return format_espn_events(
        events,
        "🏈 NFL - Today's Games"
    )


async def get_nfl_next():
    events = get_espn_events("nfl", 14)

    return format_espn_events(
        events,
        "🏈 NFL - Upcoming Games"
    )


# ============================================================
# TENNIS
# ============================================================

async def get_tennis_events(days=0):
    atp = get_espn_events("tennis_atp", days)
    wta = get_espn_events("tennis_wta", days)

    events = atp + wta

    return events


async def get_tennis_today():
    events = await get_tennis_events(0)

    return format_espn_events(
        events,
        "🎾 Tennis - Today's Matches"
    )


async def get_tennis_next():
    events = await get_tennis_events(14)

    return format_espn_events(
        events,
        "🎾 Tennis - Upcoming Matches"
    )


# ============================================================
# RUGBY
# ============================================================

async def get_rugby_today():
    return (
        "🏉 *Rugby - Today's Matches*\n\n"
        "Live rugby fixtures are being prepared for this section.\n\n"
        "The Rugby menu is now active and will be connected to the same live fixture system as the other sports."
    )


async def get_rugby_next():
    return (
        "🏉 *Rugby - Upcoming Matches*\n\n"
        "Upcoming rugby fixtures will appear here."
    )


# ============================================================
# DARTS
# ============================================================

async def get_darts_today():
    return (
        "🎯 *Darts - Today*\n\n"
        "No major darts event is currently scheduled in the live feed."
    )


async def get_darts_next():
    return (
        "🎯 *Darts - Upcoming Events*\n\n"
        "Upcoming PDC and major darts events will appear here."
    )


# ============================================================
# START COMMAND
# ============================================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    await update.message.reply_text(
        "🏆 *SPORTS TV BOT*\n\n"
        "Choose a sport:",
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


# ============================================================
# TODAY COMMAND
# ============================================================

async def today(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = await get_football_today()

    await update.message.reply_text(
        text,
        reply_markup=football_menu(),
        parse_mode="Markdown",
    )


# ============================================================
# BUTTON HANDLER
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    choice = query.data

    # --------------------------------------------------------
    # MAIN MENU
    # --------------------------------------------------------

    if choice == "main":

        await query.edit_message_text(
            "🏆 *SPORTS TV BOT*\n\n"
            "Choose a sport:",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # FOOTBALL MENU
    # --------------------------------------------------------

    if choice == "football":

        await query.edit_message_text(
            "⚽ *FOOTBALL*\n\n"
            "Choose an option:",
            reply_markup=football_menu(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # FOOTBALL TODAY
    # --------------------------------------------------------

    if choice == "football_today":

        await query.edit_message_text(
            "⏳ Loading today's football...",
        )

        text = await get_football_today()

        await query.edit_message_text(
            text,
            reply_markup=football_menu(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # FOOTBALL UPCOMING
    # --------------------------------------------------------

    if choice == "football_next":

        await query.edit_message_text(
            "⏳ Loading upcoming football...",
        )

        text = await get_football_next()

        await query.edit_message_text(
            text,
            reply_markup=football_menu(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # FORMULA 1
    # --------------------------------------------------------

    if choice == "f1":

        await query.edit_message_text(
            "🏎 *FORMULA 1*\n\n"
            "Choose an option:",
            reply_markup=sport_menu("f1"),
            parse_mode="Markdown",
        )

        return

    if choice == "f1_today":

        await query.edit_message_text("⏳ Loading Formula 1...")

        text = await get_f1_today()

        await query.edit_message_text(
            text,
            reply_markup=sport_menu("f1"),
            parse_mode="Markdown",
        )

        return

    if choice == "f1_next":

        await query.edit_message_text("⏳ Loading upcoming Formula 1...")

        text = await get_f1_next()

        await query.edit_message_text(
            text,
            reply_markup=sport_menu("f1"),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # BASKETBALL
    # --------------------------------------------------------

    if choice == "basketball":

        await query.edit_message_text(
            "🏀 *BASKETBALL*\n\n"
            "Choose an option:",
            reply_markup=sport_menu("basketball"),
            parse_mode="Markdown",
        )

        return

    if choice == "basketball_today":

        await query.edit_message_text("⏳ Loading basketball...")

        text = await get_basketball_today()

        await query.edit_message_text(
            text,
            reply_markup=sport_menu("basketball"),
            parse_mode="Markdown",
        )

        return

    if choice == "basketball_next":

        await query.edit_message_text("⏳ Loading upcoming basketball...")

        text = await get_basketball_next()

        await query.edit_message_text(
            text,
            reply_markup=sport_menu("basketball"),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # NFL
    # --------------------------------------------------------

    if choice == "nfl":

        await query.edit_message_text(
            "🏈 *NFL*\n\n"
            "Choose an option:",
            reply_markup=sport_menu("nfl"),
            parse_mode="Markdown",
        )

        return

    if choice == "nfl_today":

        await query.edit_message_text("⏳ Loading NFL...")

        text = await get_nfl_today()

        await query.edit_message_text(
            text,
            reply_markup=sport_menu("nfl"),
            parse_mode="Markdown",
        )

        return

    if choice == "nfl_next":

        await query.edit_message_text("⏳ Loading upcoming NFL...")

        text = await get_nfl_next()

        await query.edit_message_text(
            text,
            reply_markup=sport_menu("nfl"),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # RUGBY
    # --------------------------------------------------------

    if choice == "rugby":

        await query.edit_message_text(
            "🏉 *RUGBY*\n\n"
            "Choose an option:",
            reply_markup=sport_menu("rugby"),
            parse_mode="Markdown",
        )

        return

    if choice == "rugby_today":

        text = await get_rugby_today()

        await query.edit_message_text(
            text,
            reply_markup=sport_menu("rugby"),
            parse_mode="Markdown",
        )

        return

    if choice == "rugby_next":

        text = await get_rugby_next()

        await query.edit_message_text(
            text,
            reply_markup=sport_menu("rugby"),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # TENNIS
    # --------------------------------------------------------

    if choice == "tennis":

        await query.edit_message_text(
            "🎾 *TENNIS*\n\n"
            "Choose an option:",
            reply_markup=sport_menu("tennis"),
            parse_mode="Markdown",
        )

        return

    if choice == "tennis_today":

        await query.edit_message_text("⏳ Loading tennis...")

        text = await get_tennis_today()

        await query.edit_message_text(
            text,
            reply_markup=sport_menu("tennis"),
            parse_mode="Markdown",
        )

        return

    if choice == "tennis_next":

        await query.edit_message_text("⏳ Loading upcoming tennis...")

        text = await get_tennis_next()

        await query.edit_message_text(
            text,
            reply_markup=sport_menu("tennis"),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # DARTS
    # --------------------------------------------------------

    if choice == "darts":

        await query.edit_message_text(
            "🎯 *DARTS*\n\n"
            "Choose an option:",
            reply_markup=sport_menu("darts"),
            parse_mode="Markdown",
        )

        return

    if choice == "darts_today":

        text = await get_darts_today()

        await query.edit_message_text(
            text,
            reply_markup=sport_menu("darts"),
            parse_mode="Markdown",
        )

        return

    if choice == "darts_next":

        text = await get_darts_next()

        await query.edit_message_text(
            text,
            reply_markup=sport_menu("darts"),
            parse_mode="Markdown",
        )

        return


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Exception while handling an update:",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("today", today)
    )

    application.add_handler(
        CallbackQueryHandler(button_handler)
    )

    application.add_error_handler(
        error_handler
    )

    print("Sports TV Bot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()
