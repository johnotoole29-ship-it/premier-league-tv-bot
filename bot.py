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
    MessageHandler,
    ContextTypes,
    filters,
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
        "Add your TheSportsDB Premium API key."
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

            return json.load(file)

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


def get_uk_date():

    return uk_now().strftime(
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


def format_event_datetime(
    event
):

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

        clean_time = time_string[:8]

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


def format_match_time(
    event
):

    event_time = (
        event.get("strTime")
        or event.get("strEventTime")
    )

    if not event_time:
        return "TBC"

    return event_time[:5]


# ============================================================
# THE SPORTS DB
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

    return data.get(
        "events"
    ) or []


def get_sport_events(
    date,
    sport,
):

    return get_events_for_day(
        date,
        sport=sport,
    )


# ============================================================
# LEAGUE FILTER
# ============================================================

def event_matches_keywords(
    event,
    keywords,
):

    league = (
        event.get("strLeague")
        or ""
    ).lower()

    event_name = (
        event.get("strEvent")
        or ""
    ).lower()

    combined = (
        league
        + " "
        + event_name
    )

    return any(
        keyword.lower() in combined
        for keyword in keywords
    )


def get_filtered_events(
    date,
    sport,
    keywords=None,
):

    events = get_sport_events(
        date,
        sport,
    )

    if not keywords:
        return events

    filtered = [
        event
        for event in events
        if event_matches_keywords(
            event,
            keywords,
        )
    ]

    return filtered


# ============================================================
# SPORTS
# ============================================================

def get_premier_league(
    date
):

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
            event.get("strLeague")
            or ""
        ).lower()
    ]


def get_championship(
    date
):

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
        if (
            "championship"
            in (
                event.get("strLeague")
                or ""
            ).lower()
        )
    ]


def get_rugby_union(
    date
):

    events = get_sport_events(
        date,
        "Rugby",
    )

    return [
        event
        for event in events
        if not any(
            x in (
                event.get("strLeague")
                or ""
            ).lower()
            for x in [
                "super league",
                "nrl",
                "national rugby league",
            ]
        )
    ]


def get_super_league(
    date
):

    events = get_sport_events(
        date,
        "Rugby",
    )

    return [
        event
        for event in events
        if (
            "super league"
            in (
                event.get("strLeague")
                or ""
            ).lower()
        )
    ]


def get_nrl(
    date
):

    events = get_sport_events(
        date,
        "Rugby",
    )

    results = []

    for event in events:

        league = (
            event.get("strLeague")
            or ""
        ).lower()

        event_name = (
            event.get("strEvent")
            or ""
        ).lower()

        if (
            "nrl" in league
            or "national rugby league" in league
            or "nrl" in event_name
        ):

            results.append(event)

    return results


# ============================================================
# TV BROADCASTS
# ============================================================

def get_tv_channels_for_date(
    date
):

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

        item = {
            "channel": str(channel).strip(),
            "country": str(country).strip(),
        }

        tv_by_event.setdefault(
            str(event_id),
            [],
        ).append(item)

    return tv_by_event


def get_tv_for_event(
    event
):

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
                    "channel": str(channel).strip(),
                    "country": str(country).strip(),
                }
            )

    return clean_tv_channels(
        results
    )


def clean_tv_channels(
    channels
):

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
# UK TV DETECTION
# ============================================================

def is_uk_channel(
    item
):

    country = (
        item.get("country")
        or ""
    ).lower().strip()

    uk_names = [
        "united kingdom",
        "uk",
        "england",
        "scotland",
        "wales",
        "northern ireland",
        "great britain",
    ]

    if country in uk_names:
        return True

    channel = (
        item.get("channel")
        or ""
    ).lower()

    uk_channel_words = [
        "sky sports",
        "sky sport",
        "bbc",
        "itv",
        "tnt sports",
        "premier sports",
        "channel 4",
        "channel five",
        "viaplay uk",
    ]

    return any(
        word in channel
        for word in uk_channel_words
    )


# ============================================================
# TV FORMATTING
# ============================================================

def get_event_channels(
    event,
    tv_by_event
):

    event_id = str(
        event.get(
            "idEvent",
            "",
        )
    )

    channels = tv_by_event.get(
        event_id,
        [],
    )

    if not channels:

        channels = get_tv_for_event(
            event
        )

    return clean_tv_channels(
        channels
    )


def format_uk_tv(
    event,
    tv_by_event
):

    channels = get_event_channels(
        event,
        tv_by_event,
    )

    uk_channels = [
        item
        for item in channels
        if is_uk_channel(item)
    ]

    if not uk_channels:

        return (
            "🇬🇧 **UK TV**\n"
            "• Not currently listed"
        )

    lines = [
        "🇬🇧 **UK TV**"
    ]

    for item in uk_channels[:6]:

        lines.append(
            f"• {item['channel']}"
        )

    return "\n".join(lines)


def format_worldwide_tv(
    event,
    tv_by_event
):

    channels = get_event_channels(
        event,
        tv_by_event,
    )

    worldwide = [
        item
        for item in channels
        if not is_uk_channel(item)
    ]

    if not worldwide:

        return (
            "🌍 **Worldwide TV**\n"
            "• No international listings currently available."
        )

    grouped = {}

    for item in worldwide:

        country = (
            item.get("country")
            or "International"
        )

        grouped.setdefault(
            country,
            [],
        ).append(
            item["channel"]
        )

    lines = [
        "🌍 **WORLDWIDE TV**",
        "",
    ]

    for country, channels_list in grouped.items():

        lines.append(
            f"🌎 **{country}**"
        )

        for channel in channels_list[:5]:

            lines.append(
                f"• {channel}"
            )

        lines.append("")

    return "\n".join(
        lines
    ).strip()


# ============================================================
# MATCH CARD
# ============================================================

def get_event_title(
    event
):

    home = (
        event.get("strHomeTeam")
        or "Home Team"
    )

    away = (
        event.get("strAwayTeam")
        or "Away Team"
    )

    return (
        f"{home} vs {away}"
    )


def create_match_card(
    event,
    tv_by_event,
    show_date=True,
):

    date = (
        event.get("dateEvent")
        or get_uk_date()
    )

    time = format_match_time(
        event
    )

    home = (
        event.get("strHomeTeam")
        or "Home Team"
    )

    away = (
        event.get("strAwayTeam")
        or "Away Team"
    )

    league = (
        event.get("strLeague")
        or ""
    )

    venue = (
        event.get("strVenue")
        or ""
    )

    location = (
        event.get("strCountry")
        or ""
    )

    lines = []

    lines.append(
        "━━━━━━━━━━━━━━━━━━━━"
    )

    if show_date:

        lines.append(
            f"📅 **{format_display_date(date)}**"
        )

    lines.append(
        f"🕒 **{time}**"
    )

    lines.append(
        f"⚽ **{home}**"
    )

    lines.append(
        "        **VS**"
    )

    lines.append(
        f"⚽ **{away}**"
    )

    if league:

        lines.append(
            f"🏆 {league}"
        )

    if venue:

        venue_line = (
            f"📍 {venue}"
        )

        if location:

            venue_line += (
                f" · {location}"
            )

        lines.append(
            venue_line
        )

    lines.append("")

    lines.append(
        format_uk_tv(
            event,
            tv_by_event,
        )
    )

    channels = get_event_channels(
        event,
        tv_by_event,
    )

    worldwide_count = len(
        [
            item
            for item in channels
            if not is_uk_channel(item)
        ]
    )

    if worldwide_count:

        lines.append("")

        lines.append(
            f"🌍 **{worldwide_count} international "
            f"broadcaster"
            f"{'s' if worldwide_count != 1 else ''} available**"
        )

    lines.append(
        "━━━━━━━━━━━━━━━━━━━━"
    )

    return "\n".join(
        lines
    )


# ============================================================
# FIXTURE KEYBOARDS
# ============================================================

def match_buttons(
    event
):

    event_id = event.get(
        "idEvent"
    )

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🌍 Worldwide TV",
                    callback_data=f"worldwide:{event_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔔 Alert Me",
                    callback_data=f"alert:{event_id}",
                ),
                InlineKeyboardButton(
                    "❤️ Follow",
                    callback_data=f"follow:{event_id}",
                ),
            ],
        ]
    )


# ============================================================
# MAIN MENU
# ============================================================

def main_menu():

    keyboard = [

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
                "🎯 Darts",
                callback_data="darts",
            ),
            InlineKeyboardButton(
                "🏎️ Formula 1",
                callback_data="f1",
            ),
        ],

        [
            InlineKeyboardButton(
                "🏌️ Golf",
                callback_data="golf",
            ),
            InlineKeyboardButton(
                "🥊 Combat",
                callback_data="combat",
            ),
        ],

        [
            InlineKeyboardButton(
                "📺 On TV Now",
                callback_data="tv_now",
            ),
        ],

        [
            InlineKeyboardButton(
                "⏱️ Starting Soon",
                callback_data="starting_soon",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔎 Search",
                callback_data="search",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔔 My Alerts",
                callback_data="my_alerts",
            ),
            InlineKeyboardButton(
                "❤️ My Teams",
                callback_data="my_teams",
            ),
        ],

        [
            InlineKeyboardButton(
                "💎 Premium",
                callback_data="premium",
            ),
            InlineKeyboardButton(
                "ℹ️ Help",
                callback_data="help",
            ),
        ],
    ]

    return InlineKeyboardMarkup(
        keyboard
    )


# ============================================================
# HOME TEXT
# ============================================================

def home_text():
    return (
        "🔥 **SPORT PULSE ALERTS**\n\n"
        "👉 Select a sport to get started.\n\n"
        "📺 Find fixtures, TV channels and upcoming events.\n\n"
        "🌍 Use Worldwide Channels to see international broadcasts."
    )
