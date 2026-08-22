import os
import logging
from datetime import datetime, timedelta, timezone
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
SPORTSDB_API_KEY = os.getenv("SPORTSDB_API_KEY")

SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"

UK_TIMEZONE = ZoneInfo("Europe/London")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("SportPulse")


# ============================================================
# CHECK ENVIRONMENT VARIABLES
# ============================================================

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN is missing. "
        "Add TELEGRAM_TOKEN to Bunny.net Environment Variables."
    )

if not SPORTSDB_API_KEY:
    raise RuntimeError(
        "SPORTSDB_API_KEY is missing. "
        "Add SPORTSDB_API_KEY to Bunny.net Environment Variables."
    )


# ============================================================
# SPORTSDB REQUEST
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

    return datetime.now(
        UK_TIMEZONE
    )


def uk_date():

    return uk_now().date()


def date_string(date_value):

    return date_value.strftime(
        "%Y-%m-%d"
    )


def pretty_date(date_value):

    return date_value.strftime(
        "%A %d %B %Y"
    )


# ============================================================
# CONVERT SPORTSDB TIME
# ============================================================

def event_datetime_uk(event):

    # --------------------------------------------------------
    # Best option:
    # SportsDB strTimestamp
    # --------------------------------------------------------

    timestamp = event.get("strTimestamp")

    if timestamp:

        try:

            # Unix timestamp
            if str(timestamp).isdigit():

                utc_time = datetime.fromtimestamp(
                    int(timestamp),
                    tz=timezone.utc,
                )

                return utc_time.astimezone(
                    UK_TIMEZONE
                )

            # ISO timestamp
            cleaned = str(timestamp).replace(
                "Z",
                "+00:00",
            )

            parsed = datetime.fromisoformat(
                cleaned
            )

            # If SportsDB doesn't include timezone,
            # treat it as UTC.
            if parsed.tzinfo is None:

                parsed = parsed.replace(
                    tzinfo=timezone.utc
                )

            return parsed.astimezone(
                UK_TIMEZONE
            )

        except Exception as error:

            logger.warning(
                "Could not parse strTimestamp %s: %s",
                timestamp,
                error,
            )

    # --------------------------------------------------------
    # Fallback:
    # SportsDB strTime is UTC
    # --------------------------------------------------------

    date_value = (
        event.get("dateEvent")
        or event.get("dateEventLocal")
    )

    time_value = (
        event.get("strTime")
        or event.get("strEventTime")
        or "00:00:00"
    )

    if not date_value:
        return None

    try:

        clean_time = str(time_value)[:8]

        if len(clean_time) == 5:
            clean_time += ":00"

        utc_datetime = datetime.strptime(
            f"{date_value} {clean_time}",
            "%Y-%m-%d %H:%M:%S",
        ).replace(
            tzinfo=timezone.utc
        )

        return utc_datetime.astimezone(
            UK_TIMEZONE
        )

    except Exception as error:

        logger.warning(
            "Could not convert event time: %s",
            error,
        )

        return None


# ============================================================
# GET FOOTBALL FIXTURES
# ============================================================

def get_football_events(date_value):

    data = sportsdb_get(
        "eventsday.php",
        {
            "d": date_string(date_value),
            "s": "Soccer",
        },
    )

    if not data:

        return []

    events = data.get(
        "events"
    )

    if not events:

        return []

    return events


# ============================================================
# GET PREMIER LEAGUE FIXTURES
# ============================================================

def get_premier_league_events(date_value):

    events = get_football_events(
        date_value
    )

    results = []

    for event in events:

        league = (
            event.get("strLeague")
            or ""
        ).lower()

        if (
            "premier league" in league
            or
            "english premier league" in league
        ):

            results.append(event)

    return results


# ============================================================
# GET UK TV CHANNELS
# ============================================================

def get_uk_tv(date_value):

    data = sportsdb_get(
        "eventstv.php",
        {
            "d": date_string(date_value),
            "s": "Soccer",
            "a": "United_Kingdom",
        },
    )

    if not data:

        return {}

    broadcasts = (
        data.get("tvevents")
        or data.get("events")
        or []
    )

    tv_by_event = {}

    for broadcast in broadcasts:

        event_id = (
            broadcast.get("idEvent")
            or broadcast.get("id")
        )

        if not event_id:
            continue

        channel = (
            broadcast.get("strChannel")
            or broadcast.get("strName")
            or ""
        ).strip()

        if not channel:
            continue

        event_key = str(
            event_id
        )

        tv_by_event.setdefault(
            event_key,
            [],
        )

        if channel not in tv_by_event[event_key]:

            tv_by_event[event_key].append(
                channel
            )

    return tv_by_event


# ============================================================
# GET WORLDWIDE TV
# ============================================================

def get_worldwide_tv(event):

    event_id = event.get(
        "idEvent"
    )

    if not event_id:

        return []

    data = sportsdb_get(
        "lookuptv.php",
        {
            "id": event_id,
        },
    )

    if not data:

        return []

    broadcasts = (
        data.get("tvevents")
        or data.get("events")
        or []
    )

    results = []

    seen = set()

    for broadcast in broadcasts:

        channel = (
            broadcast.get("strChannel")
            or broadcast.get("strName")
            or ""
        ).strip()

        country = (
            broadcast.get("strCountry")
            or broadcast.get("strLocation")
            or "International"
        ).strip()

        if not channel:
            continue

        key = (
            country.lower(),
            channel.lower(),
        )

        if key in seen:
            continue

        seen.add(key)

        results.append(
            {
                "country": country,
                "channel": channel,
            }
        )

    return results


# ============================================================
# UK TV DISPLAY
# ============================================================

def uk_tv_text(
    event,
    tv_by_event,
):

    event_id = str(
        event.get("idEvent")
        or ""
    )

    channels = tv_by_event.get(
        event_id,
        [],
    )

    if not channels:

        return "📺 **UK TV:** TBC"

    lines = [
        "📺 **UK TV:**"
    ]

    for channel in channels[:8]:

        lines.append(
            f"• {channel}"
        )

    return "\n".join(
        lines
    )


# ============================================================
# MATCH TEXT
# ============================================================

def match_text(
    event,
    tv_by_event,
    number=None,
):

    home = (
        event.get("strHomeTeam")
        or "Home"
    )

    away = (
        event.get("strAwayTeam")
        or "Away"
    )

    event_time = event_datetime_uk(
        event
    )

    if event_time:

        time_text = event_time.strftime(
            "%H:%M"
        )

    else:

        time_text = "TBC"

    prefix = ""

    if number is not None:

        prefix = f"{number}. "

    text = (
        f"{prefix}"
        f"🕒 **{time_text} UK**\n"
        f"⚽ **{home} vs {away}**\n"
        f"{uk_tv_text(event, tv_by_event)}"
    )

    return text


# ============================================================
# MAIN FIXTURE PAGE
# ============================================================

def fixtures_page(
    date_value,
    mode="premier",
):

    if mode == "premier":

        events = get_premier_league_events(
            date_value
        )

        title = "🏆 Premier League"

    else:

        events = get_football_events(
            date_value
        )

        title = "⚽ Football"

    # --------------------------------------------------------
    # Sort by UK time
    # --------------------------------------------------------

    events.sort(
        key=lambda event: (
            event_datetime_uk(event)
            or datetime.max.replace(
                tzinfo=UK_TIMEZONE
            )
        )
    )

    # --------------------------------------------------------
    # TV listings
    # --------------------------------------------------------

    tv_by_event = get_uk_tv(
        date_value
    )

    # --------------------------------------------------------
    # Header
    # --------------------------------------------------------

    text = (
        f"📅 **{pretty_date(date_value)}**\n"
        f"{title}\n\n"
    )

    if not events:

        text += (
            "❌ **No fixtures found.**\n\n"
            "Try the next day."
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Previous Day",
                        callback_data=f"day:{date_string(date_value - timedelta(days=1))}:{mode}",
                    ),
                    InlineKeyboardButton(
                        "Next Day ➡️",
                        callback_data=f"day:{date_string(date_value + timedelta(days=1))}:{mode}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "⬅️ Back",
                        callback_data="home",
                    )
                ],
            ]
        )

        return text, keyboard

    # --------------------------------------------------------
    # Don't dump hundreds of fixtures
    # --------------------------------------------------------

    # Premier League normally only has a small number.
    #
    # For all football we deliberately show the first 20.
    # This keeps Telegram usable.
    display_events = events[:20]

    text += (
        f"📋 **{len(events)} fixture"
        f"{'s' if len(events) != 1 else ''}**\n\n"
    )

    for index, event in enumerate(
        display_events,
        start=1,
    ):

        text += (
            match_text(
                event,
                tv_by_event,
                index,
            )
            + "\n\n"
        )

    if len(events) > 20:

        text += (
            f"ℹ️ Showing first 20 of "
            f"{len(events)} fixtures.\n\n"
        )

    # --------------------------------------------------------
    # Navigation
    # --------------------------------------------------------

    keyboard = [

        [
            InlineKeyboardButton(
                "⬅️ Previous Day",
                callback_data=(
                    f"day:"
                    f"{date_string(date_value - timedelta(days=1))}:"
                    f"{mode}"
                ),
            ),

            InlineKeyboardButton(
                "Next Day ➡️",
                callback_data=(
                    f"day:"
                    f"{date_string(date_value + timedelta(days=1))}:"
                    f"{mode}"
                ),
            ),
        ],

        [
            InlineKeyboardButton(
                "🌍 View Match TV",
                callback_data="tv_help",
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="home",
            )
        ],
    ]

    return (
        text,
        InlineKeyboardMarkup(
            keyboard
        ),
    )


# ============================================================
# HOME MENU
# ============================================================

def home_keyboard():

    keyboard = [

        [
            InlineKeyboardButton(
                "🏆 Premier League",
                callback_data="premier_today",
            )
        ],

        [
            InlineKeyboardButton(
                "⚽ All Football",
                callback_data="football_today",
            )
        ],

        [
            InlineKeyboardButton(
                "📺 TV Channels",
                callback_data="tv_help",
            )
        ],

    ]

    return InlineKeyboardMarkup(
        keyboard
    )


def home_text():

    return (
        "🔥 **SPORT PULSE ALERTS**\n\n"
        "⚽ Football fixtures and TV channels\n\n"
        "Choose an option below.\n\n"
        "🕒 All match times are shown in "
        "**UK time**."
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
        reply_markup=home_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# SHOW FIXTURES
# ============================================================

async def show_fixtures(
    query,
    date_value,
    mode,
):

    await query.answer()

    try:

        await query.edit_message_text(
            "⏳ **Loading fixtures and TV channels...**",
            parse_mode="Markdown",
        )

        text, keyboard = fixtures_page(
            date_value,
            mode,
        )

        await query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

    except Exception as error:

        logger.exception(
            "Fixture error: %s",
            error,
        )

        await query.edit_message_text(
            "❌ **Something went wrong.**\n\n"
            "Please try again.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Back",
                            callback_data="home",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
        )


# ============================================================
# CALLBACK BUTTONS
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    data = query.data

    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    if data == "home":

        await query.answer()

        await query.edit_message_text(
            home_text(),
            reply_markup=home_keyboard(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # PREMIER LEAGUE TODAY
    # --------------------------------------------------------

    if data == "premier_today":

        await show_fixtures(
            query,
            uk_date(),
            "premier",
        )

        return

    # --------------------------------------------------------
    # FOOTBALL TODAY
    # --------------------------------------------------------

    if data == "football_today":

        await show_fixtures(
            query,
            uk_date(),
            "football",
        )

        return

    # --------------------------------------------------------
    # PREVIOUS / NEXT DAY
    # --------------------------------------------------------

    if data.startswith("day:"):

        await query.answer()

        parts = data.split(":")

        if len(parts) != 3:

            return

        date_text = parts[1]
        mode = parts[2]

        try:

            selected_date = datetime.strptime(
                date_text,
                "%Y-%m-%d",
            ).date()

        except ValueError:

            return

        await show_fixtures(
            query,
            selected_date,
            mode,
        )

        return

    # --------------------------------------------------------
    # TV HELP
    # --------------------------------------------------------

    if data == "tv_help":

        await query.answer()

        text = (
            "📺 **TV CHANNELS**\n\n"
            "The bot checks TheSportsDB's TV listings "
            "for each football fixture.\n\n"
            "If a UK broadcaster is listed, it appears "
            "directly underneath the match.\n\n"
            "If no UK broadcaster is currently listed, "
            "you will see:\n\n"
            "📺 **UK TV: TBC**\n\n"
            "Tap a match's TV button in future versions "
            "to see worldwide broadcasters."
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Back",
                        callback_data="home",
                    )
                ]
            ]
        )

        await query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # UNKNOWN BUTTON
    # --------------------------------------------------------

    await query.answer(
        "This button is no longer available."
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context,
):

    logger.exception(
        "Telegram error:",
        exc_info=context.error,
    )


# ================================================
