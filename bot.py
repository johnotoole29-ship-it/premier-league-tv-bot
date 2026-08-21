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
# CONFIG
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

SPORTSDB_API_KEY = (
    os.getenv("SPORTSDB_API_KEY")
    or os.getenv("FOOTBALL_API_KEY")
)

UK_TIMEZONE = ZoneInfo("Europe/London")

SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"

DATA_FILE = "sportpulse_data.json"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("SportPulseAlerts")


# ============================================================
# CONFIG CHECK
# ============================================================

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN is missing. "
        "Add it to Bunny.net environment variables."
    )

if not SPORTSDB_API_KEY:
    raise RuntimeError(
        "SPORTSDB_API_KEY is missing. "
        "Add it to Bunny.net environment variables."
    )


# ============================================================
# DATA STORAGE
# ============================================================

def load_data():
    try:
        if not os.path.exists(DATA_FILE):
            return {"users": {}}

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

        data.setdefault("users", {})

        return data

    except Exception as error:
        logger.error(
            "Could not load data: %s",
            error,
        )

        return {"users": {}}


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
    return datetime.now(UK_TIMEZONE)


def uk_date(offset=0):
    return (
        uk_now() + timedelta(days=offset)
    ).strftime("%Y-%m-%d")


def format_display_date(date_string):
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


def format_event_datetime(event):
    date_string = (
        event.get("dateEvent")
        or event.get("dateEventLocal")
    )

    time_string = (
        event.get("strTime")
        or event.get("strEventTime")
        or "00:00:00"
    )

    if not date_string:
        return None

    try:
        clean_time = str(time_string)[:8]

        if len(clean_time) == 5:
            clean_time += ":00"

        naive = datetime.strptime(
            f"{date_string} {clean_time}",
            "%Y-%m-%d %H:%M:%S",
        )

        return naive.replace(
            tzinfo=UK_TIMEZONE
        )

    except Exception:
        return None


def format_match_time(event):
    event_time = (
        event.get("strTime")
        or event.get("strEventTime")
    )

    if not event_time:
        return "TBC"

    return str(event_time)[:5]


# ============================================================
# THE SPORTS DB
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
            "Invalid SportsDB JSON: %s",
            error,
        )

        return None


# ============================================================
# EVENTS
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

    return data.get("events") or []


def get_sport_events(date, sport):
    return get_events_for_day(
        date,
        sport=sport,
    )


# ============================================================
# FOOTBALL
# ============================================================

def get_premier_league(date):
    events = get_events_for_day(
        date,
        sport="Soccer",
        league="English Premier League",
    )

    if events:
        return events

    events = get_sport_events(
        date,
        "Soccer",
    )

    return [
        event
        for event in events
        if "premier league"
        in (
            event.get("strLeague") or ""
        ).lower()
    ]


def get_championship(date):
    events = get_events_for_day(
        date,
        sport="Soccer",
        league="English League Championship",
    )

    if events:
        return events

    events = get_sport_events(
        date,
        "Soccer",
    )

    return [
        event
        for event in events
        if "championship"
        in (
            event.get("strLeague") or ""
        ).lower()
    ]


# ============================================================
# RUGBY
# ============================================================

def get_rugby_union(date):
    events = get_sport_events(
        date,
        "Rugby",
    )

    excluded = [
        "super league",
        "nrl",
        "national rugby league",
    ]

    results = []

    for event in events:
        league = (
            event.get("strLeague") or ""
        ).lower()

        if not any(
            item in league
            for item in excluded
        ):
            results.append(event)

    return results


def get_super_league(date):
    events = get_sport_events(
        date,
        "Rugby",
    )

    return [
        event
        for event in events
        if "super league"
        in (
            event.get("strLeague") or ""
        ).lower()
    ]


def get_nrl(date):
    events = get_sport_events(
        date,
        "Rugby",
    )

    results = []

    for event in events:
        league = (
            event.get("strLeague") or ""
        ).lower()

        name = (
            event.get("strEvent") or ""
        ).lower()

        if (
            "nrl" in league
            or "national rugby league" in league
            or "nrl" in name
        ):
            results.append(event)

    return results


# ============================================================
# GENERAL SPORTS
# ============================================================

SPORT_NAMES = {
    "football": "Soccer",
    "cricket": "Cricket",
    "tennis": "Tennis",
    "darts": "Darts",
    "f1": "Motorsport",
    "golf": "Golf",
    "combat": "Fighting",
    "horse": "Horse Racing",
}


def get_sport_events_for_menu(
    date,
    sport_key,
):
    if sport_key == "premier":
        return get_premier_league(date)

    if sport_key == "championship":
        return get_championship(date)

    if sport_key == "rugby_union":
        return get_rugby_union(date)

    if sport_key == "super_league":
        return get_super_league(date)

    if sport_key == "nrl":
        return get_nrl(date)

    sport_name = SPORT_NAMES.get(
        sport_key
    )

    if sport_name:
        return get_sport_events(
            date,
            sport_name,
        )

    return []


# ============================================================
# TV BROADCASTS
# ============================================================

def get_tv_channels_for_date(date):
    data = sportsdb_get(
        "eventstv.php",
        {
            "d": date,
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
            or broadcast.get("strEvent")
            or broadcast.get("strName")
        )

        country = (
            broadcast.get("strCountry")
            or broadcast.get("strLocation")
            or ""
        )

        if not channel:
            continue

        tv_by_event.setdefault(
            str(event_id),
            [],
        ).append(
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


def get_tv_for_event(event):
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

    for broadcast in broadcasts:
        channel = (
            broadcast.get("strChannel")
            or broadcast.get("strEvent")
            or broadcast.get("strName")
        )

        country = (
            broadcast.get("strCountry")
            or broadcast.get("strLocation")
            or ""
        )

        if channel:
            results.append(
                {
                    "channel": str(
                        channel
                    ).strip(),

                    "country": str(
                        country
                    ).strip(),
                }
            )

    return clean_tv_channels(results)


def clean_tv_channels(channels):
    seen = set()
    cleaned = []

    for item in channels:
        channel = item.get(
            "channel",
            "",
        )

        country = item.get(
            "country",
            "",
        )

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
# UK TV
# ============================================================

def is_uk_channel(item):
    country = (
        item.get("country")
        or ""
    ).lower().strip()

    uk_names = {
        "united kingdom",
        "uk",
        "england",
        "scotland",
        "wales",
        "northern ireland",
        "great britain",
    }

    return country in uk_names


def get_uk_channels(event):
    channels = get_tv_for_event(
        event
    )

    uk_channels = [
        channel
        for channel in channels
        if is_uk_channel(channel)
    ]

    return clean_tv_channels(
        uk_channels
    )


# ============================================================
# TEXT HELPERS
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
        return f"{home} vs {away}"

    title = (
        event.get("strEvent")
        or event.get("strLeague")
        or "Event"
    )

    return title


def event_league(event):
    return (
        event.get("strLeague")
        or "Competition TBC"
    )


def event_status(event):
    return (
        event.get("strStatus")
        or ""
    )


# ============================================================
# KEYBOARDS
# ============================================================

def main_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚽ Football",
                    callback_data="sport:football",
                ),
                InlineKeyboardButton(
                    "🏉 Rugby",
                    callback_data="sport:rugby",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏏 Cricket",
                    callback_data="sport:cricket",
                ),
                InlineKeyboardButton(
                    "🎾 Tennis",
                    callback_data="sport:tennis",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🐎 Horse Racing",
                    callback_data="sport:horse",
                ),
                InlineKeyboardButton(
                    "🎯 Darts",
                    callback_data="sport:darts",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏎 Formula 1",
                    callback_data="sport:f1",
                ),
                InlineKeyboardButton(
                    "⛳ Golf",
                    callback_data="sport:golf",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🥊 Combat",
                    callback_data="sport:combat",
                ),
            ],
            [
                InlineKeyboardButton(
                    "📅 Today's Events",
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


def football_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏆 Premier League",
                    callback_data="league:premier",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏆 Championship",
                    callback_data="league:championship",
                ),
            ],
            [
                InlineKeyboardButton(
                    "📅 Today's Football",
                    callback_data="sport:football",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔙 Main Menu",
                    callback_data="home",
                ),
            ],
        ]
    )


def rugby_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏉 Rugby Union",
                    callback_data="league:rugby_union",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔥 Super League",
                    callback_data="league:super_league",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🇦🇺 NRL",
                    callback_data="league:nrl",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔙 Main Menu",
                    callback_data="home",
                ),
            ],
        ]
    )


def date_keyboard(sport_key):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "◀ Yesterday",
                    callback_data=f"date:{sport_key}:-1",
                ),
                InlineKeyboardButton(
                    "Today",
                    callback_data=f"date:{sport_key}:0",
                ),
                InlineKeyboardButton(
                    "Tomorrow ▶",
                    callback_data=f"date:{sport_key}:1",
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


def event_keyboard(
    sport_key,
    offset,
):
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "◀ Previous Day",
                    callback_data=f"date:{sport_key}:{offset - 1}",
                ),
                InlineKeyboardButton(
                    "Next Day ▶",
                    callback_data=f"date:{sport_key}:{offset + 1}",
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
# EVENT DISPLAY
# ============================================================

def build_event_text(event):
    title = event_title(event)
    league = event_league(event)
    time = format_match_time(event)

    lines = [
        f"🏟️ *{title}*",
        "",
        f"🏆 {league}",
        f"🕐 {time} UK",
    ]

    status = event_status(event)

    if status:
        lines.append(
            f"📊 {status}"
        )

    channels = get_uk_channels(
        event
    )

    lines.append("")

    if channels:
        lines.append(
            "📺 *UK TV:*"
        )

        for channel in channels:
            lines.append(
                f"• {channel['channel']}"
            )

    else:
        lines.append(
            "📺 *UK TV:* TBC / Not listed"
        )

    return "\n".join(lines)


def build_events_text(
    events,
    date,
    sport_name,
):
    header = [
        f"📅 *{format_display_date(date)}*",
        f"🏆 *{sport_name}*",
        "",
    ]

    if not events:
        header.append(
            "ℹ️ No events found for this day."
        )

        return "\n".join(header)

    for index, event in enumerate(
        events,
        start=1,
    ):
        title = event_title(event)
        time = format_match_time(event)

        header.append(
            f"*{index}. {time}* — {title}"
        )

        channels = get_uk_channels(
            event
        )

        if channels:
            channel_names = ", ".join(
                channel["channel"]
                for channel in channels
            )

            header.append(
                f"📺 {channel_names}"
            )
        else:
            header.append(
                "📺 UK TV: TBC"
            )

        header.append("")

    return "\n".join(header)


# ============================================================
# SEND EVENTS
# ============================================================

SPORT_DISPLAY_NAMES = {
    "football": "Football",
    "cricket": "Cricket",
    "tennis": "Tennis",
    "horse": "Horse Racing",
    "darts": "Darts",
    "f1": "Formula 1",
    "golf": "Golf",
    "combat": "Combat Sports",
    "premier": "Premier League",
    "championship": "Championship",
    "rugby_union": "Rugby Union",
    "super_league": "Super League",
    "nrl": "NRL",
}


async def show_sport_events(
    query,
    sport_key,
    offset=0,
):
    date = uk_date(offset)

    events = get_sport_events_for_menu(
        date,
        sport_key,
    )

    events = sorted(
        events,
        key=lambda event: (
            format_match_time(event)
            == "TBC",
            format_match_time(event),
        ),
    )

    text = build_events_text(
        events,
        date,
        SPORT_DISPLAY_NAMES.get(
            sport_key,
            sport_key.title(),
        ),
    )

    await query.edit_message_text(
        text,
        reply_markup=event_keyboard(
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
    user = update.effective_user

    if user:
        get_user_data(
            user.id
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
        "📺 Find events and available UK TV channels.\n"
        "\n"
        "Select a sport below:"
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
        "/start — Open the main menu\n"
        "/help — Show this help\n"
        "\n"
        "Use the buttons to browse sports, "
        "events and UK TV information."
    )

    await update.message.reply_text(
        text,
        reply_markup=main_keyboard(),
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACKS
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
        text = (
            "🏆 *SPORTPULSE*\n"
            "\n"
            "Select a sport:"
        )

        await query.edit_message_text(
            text,
            reply_markup=main_keyboard(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # FOOTBALL
    # --------------------------------------------------------

    if data == "sport:football":
        text = (
            "⚽ *FOOTBALL*\n"
            "\n"
            "Choose a competition:"
        )

        await query.edit_message_text(
            text,
            reply_markup=football_keyboard(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # RUGBY
    # --------------------------------------------------------

    if data == "sport:rugby":
        text = (
            "🏉 *RUGBY*\n"
            "\n"
            "Choose a competition:"
        )

        await query.edit_message_text(
            text,
            reply_markup=rugby_keyboard(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # LEAGUES
    # --------------------------------------------------------

    if data.startswith("league:"):
        sport_key = data.split(
            ":",
            1,
        )[1]

        await show_sport_events(
            query,
            sport_key,
            0,
        )

        return

    # --------------------------------------------------------
    # SPORTS
    # --------------------------------------------------------

    if data.startswith("sport:"):
        sport_key = data.split(
            ":",
            1,
        )[1]

        if sport_key == "rugby":
            return

        await show_sport_events(
            query,
            sport_key,
            0,
        )

        return

    # --------------------------------------------------------
    # DATES
    # --------------------------------------------------------

    if data.startswith("date:"):
        parts = data.split(":")

        if len(parts) != 3:
            return

        sport_key = parts[1]

        try:
            offset = int(parts[2])
        except ValueError:
            offset = 0

        await show_sport_events(
            query,
            sport_key,
            offset,
        )

        return

    # --------------------------------------------------------
    # DAY SHORTCUTS
    # --------------------------------------------------------

    if data.startswith("day:"):
        try:
            offset = int(
                data.split(":")[1]
            )
        except ValueError:
            offset = 0

        date = uk_date(offset)

        events = get_premier_league(
            date
        )

        text = build_events_text(
            events,
            date,
            "Premier League",
        )

        await query.edit_message_text(
            text,
            reply_markup=event_keyboard(
                "premier",
                offset,
            ),
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

        if not teams:
            text = (
                "🔔 *MY ALERTS*\n"
                "\n"
                "You don't have any team alerts "
                "set up yet."
            )
        else:
            text = (
                "🔔 *MY ALERTS*\n"
                "\n"
                + "\n".join(
                    f"• {team}"
                    for team in teams
                )
            )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🔙 Main Menu",
                            callback_data="home",
                        )
                    ]
                ]
            ),
            parse_mode="Markdown",
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
        "Starting SportPulse bot..."
    )

    application = (
        Application.builder()
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
        "SportPulse bot is running."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


if __name__ == "__main__":
    main()
