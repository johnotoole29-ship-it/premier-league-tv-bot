import os
import json
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
# SPORTPULSE
# Premium UK Sports TV Guide
# ============================================================


# ============================================================
# CONFIG
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

SPORTSDB_API_KEY = (
    os.getenv("SPORTSDB_API_KEY")
    or os.getenv("FOOTBALL_API_KEY")
)

UK_TIMEZONE = ZoneInfo("Europe/London")

SPORTSDB_BASE = (
    "https://www.thesportsdb.com/api/v1/json"
)

DATA_FILE = "sportpulse_data.json"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO,
)

logger = logging.getLogger(
    "SportPulse"
)


# ============================================================
# CONFIG VALIDATION
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
# DATA STORAGE
# ============================================================

def load_data():

    try:

        if not os.path.exists(DATA_FILE):
            return {
                "users": {}
            }

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        data.setdefault(
            "users",
            {}
        )

        return data

    except Exception as error:

        logger.error(
            "Could not load data: %s",
            error,
        )

        return {
            "users": {}
        }


def save_data(data):

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )

    except Exception as error:

        logger.error(
            "Could not save data: %s",
            error,
        )


DATA = load_data()


def get_user_data(user_id):

    user_id = str(user_id)

    if user_id not in DATA["users"]:

        DATA["users"][user_id] = {
            "teams": [],
            "alerts": [],
        }

        save_data(DATA)

    return DATA["users"][user_id]


# ============================================================
# DATE / TIME
# ============================================================

def uk_now():

    return datetime.now(
        UK_TIMEZONE
    )


def uk_date(offset=0):

    return (
        uk_now()
        + timedelta(days=offset)
    ).strftime(
        "%Y-%m-%d"
    )


def format_display_date(
    date_string
):

    try:

        date_object = datetime.strptime(
            date_string,
            "%Y-%m-%d",
        )

        return date_object.strftime(
            "%A %d %B %Y"
        )

    except Exception:

        return date_string


def format_match_time(event):

    event_time = (
        event.get("strTime")
        or event.get("strEventTime")
    )

    if not event_time:
        return "TBC"

    return str(event_time)[:5]


# ============================================================
# SPORTSDB API
# ============================================================

def sportsdb_get(
    endpoint,
    params=None,
):

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
# EVENTS FOR A DAY
# ============================================================

def get_events_for_day(
    date,
    sport=None,
    league=None,
):

    params = {
        "d": date,
    }

    if sport:
        params["s"] = sport

    if league:
        params["l"] = league

    data = sportsdb_get(
        "eventsday.php",
        params,
    )

    if not data:
        return []

    return data.get(
        "events"
    ) or []


# ============================================================
# PREMIER LEAGUE
# ============================================================

def get_premier_league(date):

    events = get_events_for_day(
        date,
        sport="Soccer",
        league="English Premier League",
    )

    if events:
        return events

    # Fallback
    events = get_events_for_day(
        date,
        sport="Soccer",
    )

    results = []

    for event in events:

        league = (
            event.get("strLeague")
            or ""
        ).lower()

        if (
            "premier league"
            in league
        ):

            results.append(event)

    return results


# ============================================================
# CHAMPIONSHIP
# ============================================================

def get_championship(date):

    events = get_events_for_day(
        date,
        sport="Soccer",
        league="English League Championship",
    )

    if events:
        return events

    events = get_events_for_day(
        date,
        sport="Soccer",
    )

    results = []

    for event in events:

        league = (
            event.get("strLeague")
            or ""
        ).lower()

        if "championship" in league:

            results.append(event)

    return results


# ============================================================
# RUGBY
# ============================================================

def get_rugby_union(date):

    events = get_events_for_day(
        date,
        sport="Rugby",
    )

    excluded = {
        "super league",
        "nrl",
        "national rugby league",
    }

    results = []

    for event in events:

        league = (
            event.get("strLeague")
            or ""
        ).lower()

        if not any(
            item in league
            for item in excluded
        ):

            results.append(event)

    return results


def get_super_league(date):

    events = get_events_for_day(
        date,
        sport="Rugby",
    )

    return [
        event
        for event in events
        if "super league"
        in (
            event.get("strLeague")
            or ""
        ).lower()
    ]


def get_nrl(date):

    events = get_events_for_day(
        date,
        sport="Rugby",
    )

    results = []

    for event in events:

        league = (
            event.get("strLeague")
            or ""
        ).lower()

        name = (
            event.get("strEvent")
            or ""
        ).lower()

        if (
            "nrl" in league
            or "national rugby league"
            in league
            or "nrl" in name
        ):

            results.append(event)

    return results


# ============================================================
# GENERAL SPORTS
# ============================================================

SPORT_NAMES = {

    "cricket":
        "Cricket",

    "tennis":
        "Tennis",

    "horse":
        "Horse Racing",

    "darts":
        "Darts",

    "f1":
        "Motorsport",

    "golf":
        "Golf",

    "combat":
        "Fighting",
}


def get_sport_events(
    date,
    sport_key,
):

    sport_name = SPORT_NAMES.get(
        sport_key
    )

    if not sport_name:
        return []

    return get_events_for_day(
        date,
        sport=sport_name,
    )


# ============================================================
# TV - UK ONLY
# ============================================================

def get_uk_tv_for_date(date):

    """
    Gets the complete UK TV schedule for one day.

    TheSportsDB supports:
        eventstv.php
        d = date
        a = United_Kingdom

    We fetch the TV schedule ONCE and then
    match each broadcast to its event ID.
    """

    data = sportsdb_get(
        "eventstv.php",
        {
            "d": date,
            "a": "United_Kingdom",
        },
    )

    if not data:

        logger.warning(
            "No UK TV data returned for %s",
            date,
        )

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
            or broadcast.get("strEvent")
        )

        if not channel:
            continue

        country = (
            broadcast.get("strCountry")
            or "United Kingdom"
        )

        item = {
            "channel": str(
                channel
            ).strip(),

            "country": str(
                country
            ).strip(),
        }

        event_key = str(
            event_id
        )

        tv_by_event.setdefault(
            event_key,
            [],
        ).append(item)

    # Remove duplicates
    for event_id in tv_by_event:

        tv_by_event[event_id] = (
            clean_tv_channels(
                tv_by_event[event_id]
            )
        )

    logger.info(
        "Found UK TV listings for %s events on %s",
        len(tv_by_event),
        date,
    )

    return tv_by_event


def clean_tv_channels(
    channels
):

    seen = set()
    cleaned = []

    for item in channels:

        channel = str(
            item.get(
                "channel",
                "",
            )
        ).strip()

        country = str(
            item.get(
                "country",
                "",
            )
        ).strip()

        if not channel:
            continue

        key = (
            channel.lower(),
            country.lower(),
        )

        if key in seen:
            continue

        seen.add(key)

        cleaned.append(
            {
                "channel": channel,
                "country": country,
            }
        )

    return cleaned


# ============================================================
# EVENT TEXT
# ============================================================

def event_title(event):

    home = (
        event.get("strHomeTeam")
        or ""
    )

    away = (
        event.get("strAwayTeam")
        or ""
    )

    if home and away:

        return (
            f"{home} vs {away}"
        )

    return (
        event.get("strEvent")
        or "Event"
    )


def event_league(event):

    return (
        event.get("strLeague")
        or "Competition TBC"
    )


def event_channels(
    event,
    tv_data,
):

    event_id = event.get(
        "idEvent"
    )

    if not event_id:
        return []

    return tv_data.get(
        str(event_id),
        [],
    )


# ============================================================
# SPORT LOOKUP
# ============================================================

def get_events_for_menu(
    date,
    sport_key,
):

    if sport_key == "premier":
        return get_premier_league(
            date
        )

    if sport_key == "championship":
        return get_championship(
            date
        )

    if sport_key == "rugby_union":
        return get_rugby_union(
            date
        )

    if sport_key == "super_league":
        return get_super_league(
            date
        )

    if sport_key == "nrl":
        return get_nrl(
            date
        )

    return get_sport_events(
        date,
        sport_key,
    )


# ============================================================
# DISPLAY NAMES
# ============================================================

SPORT_DISPLAY_NAMES = {

    "football":
        "Football",

    "cricket":
        "Cricket",

    "tennis":
        "Tennis",

    "horse":
        "Horse Racing",

    "darts":
        "Darts",

    "f1":
        "Formula 1",

    "golf":
        "Golf",

    "combat":
        "Combat Sports",

    "premier":
        "Premier League",

    "championship":
        "Championship",

    "rugby_union":
        "Rugby Union",

    "super_league":
        "Super League",

    "nrl":
        "NRL",
}


# ============================================================
# MAIN MENU
# ============================================================

def main_keyboard():

    return InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "⚽ Football",
                    callback_data="football",
                ),

                InlineKeyboardButton(
                    "🏉 Rugby",
                    callback_data="rugby",
                ),
            ],

            [
                InlineKeyboardButton(
                    "🏏 Cricket",
                    callback_data="cricket",
                ),

                InlineKeyboardButton(
                    "🎾 Tennis",
                    callback_data="tennis",
                ),
            ],

            [
                InlineKeyboardButton(
                    "🐎 Horse Racing",
                    callback_data="horse",
                ),

                InlineKeyboardButton(
                    "🎯 Darts",
                    callback_data="darts",
                ),
            ],

            [
                InlineKeyboardButton(
                    "🏎 Formula 1",
                    callback_data="f1",
                ),

                InlineKeyboardButton(
                    "⛳ Golf",
                    callback_data="golf",
                ),
            ],

            [
                InlineKeyboardButton(
                    "🥊 Combat Sports",
                    callback_data="combat",
                ),
            ],

            [
                InlineKeyboardButton(
                    "📅 Today",
                    callback_data="day:0",
                ),

                InlineKeyboardButton(
                    "📆 Tomorrow",
                    callback_data="day:1",
                ),
            ],

            [
                InlineKeyboardButton(
                    "🔔 My Alerts",
                    callback_data="alerts",
                ),
            ],
        ]
    )


# ============================================================
# FOOTBALL MENU
# ============================================================

def football_keyboard():

    return InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "🏆 Premier League",
                    callback_data="premier",
                ),
            ],

            [
                InlineKeyboardButton(
                    "🏆 Championship",
                    callback_data="championship",
                ),
            ],

            [
                InlineKeyboardButton(
                    "📅 Today's Football",
                    callback_data="football",
                ),
            ],

            [
                InlineKeyboardButton(
                    "🔙 Sports",
                    callback_data="home",
                ),
            ],
        ]
    )


# ============================================================
# RUGBY MENU
# ============================================================

def rugby_keyboard():

    return InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "🏉 Rugby Union",
                    callback_data="rugby_union",
                ),
            ],

            [
                InlineKeyboardButton(
                    "🔥 Super League",
                    callback_data="super_league",
                ),
            ],

            [
                InlineKeyboardButton(
                    "🇦🇺 NRL",
                    callback_data="nrl",
                ),
            ],

            [
                InlineKeyboardButton(
                    "🔙 Sports",
                    callback_data="home",
                ),
            ],
        ]
    )


# ============================================================
# DATE NAVIGATION
# ============================================================

def date_keyboard(
    sport_key,
    offset,
):

    return InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "◀ Previous Day",
                    callback_data=(
                        f"date:"
                        f"{sport_key}:"
                        f"{offset - 1}"
                    ),
                ),

                InlineKeyboardButton(
                    "Next Day ▶",
                    callback_data=(
                        f"date:"
                        f"{sport_key}:"
                        f"{offset + 1}"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(
                    "🔙 Sports",
                    callback_data="home",
                ),
            ],
        ]
    )


# ============================================================
# EVENT LIST
# ============================================================

def build_events_text(
    events,
    date,
    sport_name,
    tv_data,
):

    lines = [

        f"📅 *{format_display_date(date)}*",

        f"🏆 *{sport_name}*",

        "",
    ]

    if not events:

        lines.append(
            "ℹ️ No events found for this day."
        )

        return "\n".join(lines)

    for number, event in enumerate(
        events,
        start=1,
    ):

        time = format_match_time(
            event
        )

        title = event_title(
            event
        )

        lines.append(
            f"*{number}. {time}* — {title}"
        )

        channels = event_channels(
            event,
            tv_data,
        )

        if channels:

            names = ", ".join(
                channel["channel"]
                for channel in channels
            )

            lines.append(
                f"📺 *UK TV:* {names}"
            )

        else:

            lines.append(
                "📺 *UK TV:* TBC"
            )

        lines.append("")

    return "\n".join(lines)


# ============================================================
# SHOW SPORT
# ============================================================

async def show_sport(
    query,
    sport_key,
    offset=0,
):

    date = uk_date(
        offset
    )

    logger.info(
        "Loading %s for %s",
        sport_key,
        date,
    )

    events = get_events_for_menu(
        date,
        sport_key,
    )

    tv_data = get_uk_tv_for_date(
        date
    )

    # Sort by time
    events = sorted(
        events,
        key=lambda event: (
            format_match_time(
                event
            ) == "TBC",

            format_match_time(
                event
            ),
        ),
    )

    sport_name = (
        SPORT_DISPLAY_NAMES.get(
            sport_key,
            sport_key.title(),
        )
    )

    text = build_events_text(
        events,
        date,
        sport_name,
        tv_data,
    )

    await query.edit_message_text(

        text,

        reply_markup=date_keyboard(
            sport_key,
            offset,
        ),

        parse_mode="Markdown",
    )


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if update.effective_user:

        get_user_data(
            update.effective_user.id
        )

    text = (

        "🏆 *SPORTPULSE*\n"

        "\n"

        "Your premium UK sports TV guide.\n"

        "\n"

        "⚽ Football\n"
        "🏉 Rugby\n"
        "🏏 Cricket\n"
        "🎾 Tennis\n"
        "🐎 Horse Racing\n"
        "🎯 Darts\n"
        "🏎 Formula 1\n"
        "⛳ Golf\n"
        "🥊 Combat Sports\n"

        "\n"

        "📺 UK TV listings\n"
        "🕐 UK time\n"
        "📅 Daily schedules\n"

        "\n"

        "*Choose a sport:*"
    )

    await update.message.reply_text(

        text,

        reply_markup=main_keyboard(),

        parse_mode="Markdown",
    )


# ============================================================
# HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = (

        "ℹ️ *SportPulse Help*\n"

        "\n"

        "/start — Main menu\n"
        "/help — Help\n"

        "\n"

        "Select a sport to view upcoming events "
        "and available UK TV channels."
    )

    await update.message.reply_text(

        text,

        reply_markup=main_keyboard(),

        parse_mode="Markdown",
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

    data = query.data or ""

    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    if data == "home":

        await query.edit_message_text(

            "🏆 *SPORTPULSE*\n\n"
            "*Choose a sport:*",

            reply_markup=main_keyboard(),

            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # FOOTBALL
    # --------------------------------------------------------

    if data == "football":

        await query.edit_message_text(

            "⚽ *FOOTBALL*\n\n"
            "Choose a competition:",

            reply_markup=football_keyboard(),

            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # RUGBY
    # --------------------------------------------------------

    if data == "rugby":

        await query.edit_message_text(

            "🏉 *RUGBY*\n\n"
            "Choose a competition:",

            reply_markup=rugby_keyboard(),

            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # ALERTS
    # --------------------------------------------------------

    if data == "alerts":

        user_data = get_user_data(
            query.from_user.id
        )

        teams = user_data.get(
            "teams",
            [],
        )

        if teams:

            text = (
                "🔔 *MY ALERTS*\n\n"
                + "\n".join(
                    f"• {team}"
                    for team in teams
                )
            )

        else:

            text = (
                "🔔 *MY ALERTS*\n\n"
                "You don't have any alerts yet."
            )

        keyboard = InlineKeyboardMarkup(

            [

                [
                    InlineKeyboardButton(
                        "🔙 Main Menu",
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
    # DAY
    # --------------------------------------------------------

    if data.startswith("day:"):

        try:

            offset = int(
                data.split(":")[1]
            )

        except Exception:

            offset = 0

        await show_sport(
            query,
            "premier",
            offset,
        )

        return

    # --------------------------------------------------------
    # DATE
    # --------------------------------------------------------

    if data.startswith("date:"):

        parts = data.split(":")

        if len(parts) != 3:
            return

        sport_key = parts[1]

        try:

            offset = int(
                parts[2]
            )

        except Exception:

            offset = 0

        await show_sport(
            query,
            sport_key,
            offset,
        )

        return

    # --------------------------------------------------------
    # SPORTS
    # --------------------------------------------------------

    sport_keys = {
        "cricket",
        "tennis",
        "horse",
        "darts",
        "f1",
        "golf",
        "combat",
        "premier",
        "championship",
        "rugby_union",
        "super_league",
        "nrl",
    }

    if data in sport_keys:

        await show_sport(
            query,
            data,
            0,
        )

        return


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context,
):

    logger.error(
        "Telegram error: %s",
        context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "Starting SportPulse..."
    )

    application = (
        Application
        .builder()
        .token(
            TELEGRAM_TOKEN
        )
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            button_handler,
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "SportPulse is running."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
