import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


# ============================================================
# CONFIG
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

SPORTSDB_API_KEY = (
    os.getenv("SPORTSDB_API_KEY")
    or os.getenv("FOOTBALL_API_KEY")
)

TIMEZONE = ZoneInfo("Europe/London")

SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"

# Premier League
PREMIER_LEAGUE_ID = "4328"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("SportPulseAlerts")


# ============================================================
# STARTUP CHECK
# ============================================================

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN is missing."
    )

if not SPORTSDB_API_KEY:
    raise RuntimeError(
        "SPORTSDB_API_KEY is missing."
    )


# ============================================================
# SPORTS DB REQUEST
# ============================================================

def sportsdb_get(endpoint, params=None):

    url = (
        f"{SPORTSDB_BASE}/"
        f"{SPORTSDB_API_KEY}/"
        f"{endpoint}"
    )

    try:

        response = requests.get(
            url,
            params=params or {},
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        return data

    except Exception as error:

        logger.exception(
            "SportsDB error: %s",
            error,
        )

        return None


# ============================================================
# UK DATE / TIME
# ============================================================

def uk_now():

    return datetime.now(TIMEZONE)


def uk_date():

    return uk_now().strftime("%Y-%m-%d")


def date_from_offset(days):

    date = uk_now().date() + timedelta(days=days)

    return date.strftime("%Y-%m-%d")


def display_date(date_string):

    try:

        date = datetime.strptime(
            date_string,
            "%Y-%m-%d",
        )

        return date.strftime(
            "%A %d %B %Y"
        )

    except Exception:

        return date_string


# ============================================================
# PREMIER LEAGUE FIXTURES
# ============================================================

def get_premier_league_fixtures(date_string):

    """
    Get fixtures for one specific date.

    We deliberately retrieve Soccer fixtures for the date
    and then ONLY keep Premier League matches.

    This prevents the bot from dumping hundreds of
    unrelated football fixtures.
    """

    data = sportsdb_get(
        "eventsday.php",
        {
            "d": date_string,
            "s": "Soccer",
        },
    )

    if not data:

        return []

    events = data.get("events") or []

    results = []

    for event in events:

        league = (
            event.get("strLeague")
            or ""
        ).strip().lower()

        if league == "english premier league":

            results.append(event)

    # Sort by time

    results.sort(
        key=lambda event: (
            event.get("strTime")
            or event.get("strEventTime")
            or "99:99:99"
        )
    )

    return results


# ============================================================
# NEXT PREMIER LEAGUE FIXTURES
# ============================================================

def get_next_premier_league():

    """
    Get upcoming Premier League matches.

    This is used as a fallback if the requested day
    has no fixtures.
    """

    data = sportsdb_get(
        "eventsnextleague.php",
        {
            "id": PREMIER_LEAGUE_ID,
        },
    )

    if not data:

        return []

    events = data.get("events") or []

    return events


# ============================================================
# MATCH TIME
# ============================================================

def match_time(event):

    value = (
        event.get("strTime")
        or event.get("strEventTime")
    )

    if not value:

        return "TBC"

    try:

        return value[:5]

    except Exception:

        return "TBC"


# ============================================================
# MATCH TEXT
# ============================================================

def fixture_line(number, event):

    home = (
        event.get("strHomeTeam")
        or "Home"
    )

    away = (
        event.get("strAwayTeam")
        or "Away"
    )

    time = match_time(event)

    return (
        f"{number}. "
        f"**{time}** — "
        f"{home} vs {away}"
    )


# ============================================================
# FIXTURE PAGE
# ============================================================

def build_fixture_page(date_string):

    fixtures = get_premier_league_fixtures(
        date_string
    )

    lines = []

    lines.append(
        f"📅 **{display_date(date_string)}**"
    )

    lines.append(
        "🏆 **Premier League**"
    )

    lines.append("")

    if not fixtures:

        lines.append(
            "📭 **No Premier League fixtures today.**"
        )

        return "\n".join(lines)

    lines.append(
        f"⚽ **{len(fixtures)} fixture"
        f"{'s' if len(fixtures) != 1 else ''}**"
    )

    lines.append("")

    for index, event in enumerate(
        fixtures,
        start=1,
    ):

        lines.append(
            fixture_line(
                index,
                event,
            )
        )

    return "\n".join(lines)


# ============================================================
# MAIN MENU
# ============================================================

def main_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 Today",
                callback_data="day:0",
            ),

            InlineKeyboardButton(
                "📅 Tomorrow",
                callback_data="day:1",
            ),
        ],

        [
            InlineKeyboardButton(
                "📆 Next 7 Days",
                callback_data="next7",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔄 Refresh",
                callback_data="refresh",
            ),
        ],

    ]

    return InlineKeyboardMarkup(
        keyboard
    )


# ============================================================
# DAY NAVIGATION
# ============================================================

def day_menu(offset):

    keyboard = [

        [
            InlineKeyboardButton(
                "◀️ Previous Day",
                callback_data=f"day:{offset - 1}",
            ),

            InlineKeyboardButton(
                "▶️ Next Day",
                callback_data=f"day:{offset + 1}",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="home",
            ),
        ],

    ]

    return InlineKeyboardMarkup(
        keyboard
    )


# ============================================================
# HOME MESSAGE
# ============================================================

def home_text():

    return (
        "🔥 **SPORT PULSE ALERTS**\n\n"
        "⚽ **Football Fixtures**\n\n"
        "Choose what you want to see below.\n\n"
        "🇬🇧 Times are shown in UK time."
    )


# ============================================================
# START COMMAND
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        home_text(),
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


# ============================================================
# SHOW A DAY
# ============================================================

async def show_day(
    query,
    offset,
):

    date_string = date_from_offset(
        offset
    )

    text = build_fixture_page(
        date_string
    )

    await query.edit_message_text(
        text,
        parse_mode="Markdown",
        reply_markup=day_menu(offset),
    )


# ============================================================
# NEXT 7 DAYS
# ============================================================

async def show_next_7_days(query):

    lines = []

    lines.append(
        "📆 **NEXT 7 DAYS**"
    )

    lines.append(
        "🏆 **Premier League**"
    )

    lines.append("")

    found = False

    for offset in range(7):

        date_string = date_from_offset(
            offset
        )

        fixtures = get_premier_league_fixtures(
            date_string
        )

        if not fixtures:

            continue

        found = True

        lines.append(
            f"📅 **{display_date(date_string)}**"
        )

        for event in fixtures:

            home = (
                event.get("strHomeTeam")
                or "Home"
            )

            away = (
                event.get("strAwayTeam")
                or "Away"
            )

            time = match_time(event)

            lines.append(
                f"• **{time}** — "
                f"{home} vs {away}"
            )

        lines.append("")

    if not found:

        lines.append(
            "📭 No Premier League fixtures "
            "found in the next 7 days."
        )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🔙 Back",
                    callback_data="home",
                )
            ]
        ]
    )

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    data = query.data

    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    if data == "home":

        await query.edit_message_text(
            home_text(),
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )

        return

    # --------------------------------------------------------
    # TODAY / TOMORROW / DAY NAVIGATION
    # --------------------------------------------------------

    if data.startswith("day:"):

        try:

            offset = int(
                data.split(":")[1]
            )

        except Exception:

            offset = 0

        # Prevent accidentally going too far backwards

        if offset < -30:
            offset = -30

        # And don't allow absurdly large requests

        if offset > 30:
            offset = 30

        await show_day(
            query,
            offset,
        )

        return

    # --------------------------------------------------------
    # NEXT 7 DAYS
    # --------------------------------------------------------

    if data == "next7":

        await show_next_7_days(
            query
        )

        return

    # --------------------------------------------------------
    # REFRESH
    # --------------------------------------------------------

    if data == "refresh":

        date_string = uk_date()

        text = build_fixture_page(
            date_string
        )

        await query.edit_message_text(
            text,
            parse_mode="Markdown",
            reply_markup=day_menu(0),
        )

        return


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.exception(
        "Telegram error: %s",
        context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "Starting SportPulseAlerts..."
    )

    application = (
        Application
        .builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    # Commands

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # Buttons

    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    # Errors

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Bot is running."
    )

    application.run_polling(
        drop_pending_updates=True
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
