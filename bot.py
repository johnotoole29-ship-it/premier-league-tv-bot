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

        return response.json()

    except requests.RequestException as error:

        logger.error(
            "SportsDB request failed: %s",
            error,
        )

        return None

    except ValueError as error:

        logger.error(
            "SportsDB returned invalid JSON: %s",
            error,
        )

        return None


# ============================================================
# UK DATE
# ============================================================

def uk_now():

    return datetime.now(TIMEZONE)


def date_from_offset(offset):

    date = (
        uk_now().date()
        + timedelta(days=offset)
    )

    return date.strftime(
        "%Y-%m-%d"
    )


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
    Get ONLY Premier League fixtures
    for the requested date.
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

    events = data.get(
        "events"
    ) or []

    fixtures = []

    for event in events:

        league = (
            event.get("strLeague")
            or ""
        ).strip().lower()

        if league == "english premier league":

            fixtures.append(event)

    fixtures.sort(
        key=lambda event: (
            event.get("strTime")
            or event.get("strEventTime")
            or "99:99:99"
        )
    )

    return fixtures


# ============================================================
# UK TV LISTINGS
# ============================================================

def get_uk_tv_for_date(date_string):

    """
    Get UK TV listings for a specific date.

    TheSportsDB supports filtering TV events by:
        d = date
        a = country
        s = sport
    """

    data = sportsdb_get(
        "eventstv.php",
        {
            "d": date_string,
            "a": "United Kingdom",
            "s": "Soccer",
        },
    )

    if not data:

        logger.warning(
            "No TV data returned for %s",
            date_string,
        )

        return {}

    tv_events = (
        data.get("tvevents")
        or data.get("events")
        or []
    )

    tv_by_event = {}

    for item in tv_events:

        event_id = (
            item.get("idEvent")
            or item.get("id")
        )

        if not event_id:
            continue

        channel = (
            item.get("strChannel")
            or item.get("strName")
            or item.get("strEvent")
        )

        country = (
            item.get("strCountry")
            or item.get("strLocation")
            or ""
        )

        if not channel:
            continue

        event_id = str(event_id)

        tv_by_event.setdefault(
            event_id,
            [],
        )

        tv_by_event[event_id].append(
            {
                "channel": str(
                    channel
                ).strip(),

                "country": str(
                    country
                ).strip(),
            }
        )

    return tv_by_event


# ============================================================
# CLEAN TV CHANNELS
# ============================================================

def clean_channels(channels):

    seen = set()

    result = []

    for item in channels:

        channel = (
            item.get("channel")
            or ""
        ).strip()

        if not channel:
            continue

        key = channel.lower()

        if key in seen:
            continue

        seen.add(key)

        result.append(channel)

    return result


# ============================================================
# GET TV FOR ONE MATCH
# ============================================================

def get_tv_for_event(event, tv_by_event):

    event_id = event.get(
        "idEvent"
    )

    if not event_id:

        return []

    event_id = str(event_id)

    channels = tv_by_event.get(
        event_id,
        [],
    )

    return clean_channels(
        channels
    )


# ============================================================
# FORMAT TV
# ============================================================

def format_tv(event, tv_by_event):

    channels = get_tv_for_event(
        event,
        tv_by_event,
    )

    if not channels:

        return (
            "📺 **UK TV:** "
            "Not currently listed"
        )

    lines = [
        "📺 **UK TV:**"
    ]

    for channel in channels[:6]:

        lines.append(
            f"• {channel}"
        )

    return "\n".join(lines)


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

    return value[:5]


# ============================================================
# BUILD FIXTURE TEXT
# ============================================================

def build_fixture_page(date_string):

    fixtures = get_premier_league_fixtures(
        date_string
    )

    # Get UK TV listings ONCE for this date.
    # This is important so we don't make a TV API
    # request for every single fixture.

    tv_by_event = get_uk_tv_for_date(
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
            f"**{index}. {time} — "
            f"{home} vs {away}**"
        )

        lines.append(
            format_tv(
                event,
                tv_by_event,
            )
        )

        lines.append("")

    return "\n".join(lines).strip()


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
# HOME
# ============================================================

def home_text():

    return (
        "🔥 **SPORT PULSE ALERTS**\n\n"
        "⚽ **Premier League Fixtures**\n\n"
        "📺 UK TV channels included\n\n"
        "🇬🇧 All times are UK time."
    )


# ============================================================
# START
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
# SHOW DAY
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

        # TV listings for this particular date

        tv_by_event = get_uk_tv_for_date(
            date_string
        )

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

            tv_channels = get_tv_for_event(
                event,
                tv_by_event,
            )

            if tv_channels:

                lines.append(
                    "  📺 **UK TV:** "
                    + ", ".join(
                        tv_channels[:4]
                    )
                )

            else:

                lines.append(
                    "  📺 **UK TV:** "
                    "Not currently listed"
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
# BUTTON HANDLER
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    data = query.data

    # HOME

    if data == "home":

        await query.edit_message_text(
            home_text(),
            parse_mode="Markdown",
            reply_markup=main_menu(),
        )

        return

    # DAY

    if data.startswith("day:"):

        try:

            offset = int(
                data.split(":")[1]
            )

        except Exception:

            offset = 0

        # Keep navigation sensible

        offset = max(
            -30,
            min(offset, 30)
        )

        await show_day(
            query,
            offset,
        )

        return

    # NEXT 7 DAYS

    if data == "next7":

        await show_next_7_days(
            query
        )

        return

    # REFRESH

    if data == "refresh":

        text = build_fixture_page(
            date_from_offset(0)
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
    update,
    context,
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

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

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
