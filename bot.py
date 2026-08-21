import os
import json
import logging
import asyncio
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
# SPORT PULSE ALERTS
# COMPLETE BOT.PY
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
    "SportPulseAlerts"
)


# ============================================================
# STARTUP CHECK
# ============================================================

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN is missing. "
        "Add it to Bunny.net Environment Variables."
    )

if not SPORTSDB_API_KEY:
    raise RuntimeError(
        "SPORTSDB_API_KEY is missing. "
        "Add your TheSportsDB API key to Bunny.net."
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

        if not isinstance(data, dict):

            return {
                "users": {}
            }

        data.setdefault(
            "users",
            {}
        )

        return data

    except Exception:

        logger.exception(
            "Could not load data"
        )

        return {
            "users": {}
        }


def save_data():

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                DATA,
                file,
                indent=2,
                ensure_ascii=False,
            )

    except Exception:

        logger.exception(
            "Could not save data"
        )


DATA = load_data()


def get_user(user_id):

    user_id = str(user_id)

    if user_id not in DATA["users"]:

        DATA["users"][user_id] = {
            "teams": [],
            "alerts": [],
        }

        save_data()

    return DATA["users"][user_id]


# ============================================================
# TIME FUNCTIONS
# ============================================================

def uk_now():

    return datetime.now(
        UK_TIMEZONE
    )


def today_string():

    return uk_now().strftime(
        "%Y-%m-%d"
    )


def display_date(date_string):

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


def event_datetime(event):

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

        clean_time = str(
            time_value
        )[:8]

        if len(clean_time) == 5:

            clean_time += ":00"

        value = datetime.strptime(
            f"{date_value} {clean_time}",
            "%Y-%m-%d %H:%M:%S",
        )

        return value.replace(
            tzinfo=UK_TIMEZONE
        )

    except Exception:

        return None


def event_time(event):

    event_date = event_datetime(
        event
    )

    if not event_date:

        return "TBC"

    return event_date.strftime(
        "%H:%M"
    )


# ============================================================
# SPORTSDB API
# ============================================================

def sportsdb_request(
    endpoint,
    params=None,
):

    url = (
        f"{SPORTSDB_BASE}/"
        f"{SPORTSDB_API_KEY}/"
        f"{endpoint}"
    )

    try:

        logger.info(
            "SportsDB: %s %s",
            endpoint,
            params,
        )

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
            "SportsDB JSON error: %s",
            error,
        )

        return None


async def sportsdb_request_async(
    endpoint,
    params=None,
):

    return await asyncio.to_thread(
        sportsdb_request,
        endpoint,
        params,
    )


# ============================================================
# EVENTS FOR A DAY
# ============================================================

async def get_events_day(
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

    data = await sportsdb_request_async(
        "eventsday.php",
        params,
    )

    if not data:

        return []

    return (
        data.get("events")
        or []
    )


# ============================================================
# TV FOR A DAY
# ============================================================

async def get_tv_day(
    date,
    sport=None,
    country=None,
):

    params = {
        "d": date,
    }

    if sport:

        params["s"] = sport

    if country:

        params["a"] = country

    data = await sportsdb_request_async(
        "eventstv.php",
        params,
    )

    if not data:

        return []

    return (
        data.get("tvevents")
        or data.get("events")
        or []
    )


# ============================================================
# SINGLE EVENT
# ============================================================

async def lookup_event(
    event_id
):

    data = await sportsdb_request_async(
        "lookupevent.php",
        {
            "id": event_id,
        },
    )

    if not data:

        return None

    events = (
        data.get("events")
        or []
    )

    if not events:

        return None

    return events[0]


# ============================================================
# EVENT TV
# ============================================================

async def lookup_event_tv(
    event_id
):

    data = await sportsdb_request_async(
        "lookuptv.php",
        {
            "id": event_id,
        },
    )

    if not data:

        return []

    return (
        data.get("tvevents")
        or data.get("events")
        or []
    )


# ============================================================
# SPORTS
# ============================================================

SPORTS = {

    "football": {
        "name": "⚽ Football",
        "sport": "Soccer",
    },

    "rugby": {
        "name": "🏉 Rugby",
        "sport": "Rugby",
    },

    "cricket": {
        "name": "🏏 Cricket",
        "sport": "Cricket",
    },

    "tennis": {
        "name": "🎾 Tennis",
        "sport": "Tennis",
    },

    "darts": {
        "name": "🎯 Darts",
        "sport": "Darts",
    },

    "f1": {
        "name": "🏎️ Formula 1",
        "sport": "Motorsport",
        "keywords": [
            "formula 1",
            "formula one",
            "f1",
        ],
    },

    "golf": {
        "name": "🏌️ Golf",
        "sport": "Golf",
    },

    "combat": {
        "name": "🥊 Combat",
        "sport": "Fighting",
    },
}


# ============================================================
# SPORT FILTERING
# ============================================================

def event_search_text(
    event
):

    league = (
        event.get("strLeague")
        or ""
    )

    name = (
        event.get("strEvent")
        or ""
    )

    home = (
        event.get("strHomeTeam")
        or ""
    )

    away = (
        event.get("strAwayTeam")
        or ""
    )

    return (
        f"{league} "
        f"{name} "
        f"{home} "
        f"{away}"
    ).lower()


def filter_special_sport(
    events,
    sport_key,
):

    settings = SPORTS[
        sport_key
    ]

    keywords = settings.get(
        "keywords"
    )

    if not keywords:

        return events

    filtered = []

    for event in events:

        text = event_search_text(
            event
        )

        if any(
            keyword in text
            for keyword in keywords
        ):

            filtered.append(
                event
            )

    return filtered


async def get_sport_events(
    date,
    sport_key,
):

    settings = SPORTS[
        sport_key
    ]

    sport_name = settings[
        "sport"
    ]

    events = await get_events_day(
        date,
        sport=sport_name,
    )

    events = filter_special_sport(
        events,
        sport_key,
    )

    events.sort(
        key=lambda event: (
            event_datetime(event)
            or datetime.max.replace(
                tzinfo=UK_TIMEZONE
            )
        )
    )

    return events


# ============================================================
# TV CLEANING
# ============================================================

UK_COUNTRIES = {
    "united kingdom",
    "uk",
    "england",
    "scotland",
    "wales",
    "northern ireland",
    "great britain",
}


UK_CHANNEL_WORDS = [
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


def get_channel_name(
    item
):

    return (
        item.get("strChannel")
        or item.get("channel")
        or item.get("strName")
        or "Unknown channel"
    ).strip()


def get_channel_country(
    item
):

    return (
        item.get("strCountry")
        or item.get("country")
        or "International"
    ).strip()


def is_uk_channel(
    item
):

    country = (
        get_channel_country(item)
        .lower()
        .strip()
    )

    if country in UK_COUNTRIES:

        return True

    channel = (
        get_channel_name(item)
        .lower()
    )

    return any(
        word in channel
        for word in UK_CHANNEL_WORDS
    )


def clean_channels(
    channels
):

    seen = set()
    result = []

    for item in channels:

        name = get_channel_name(
            item
        )

        country = get_channel_country(
            item
        )

        key = (
            name.lower(),
            country.lower(),
        )

        if key in seen:

            continue

        seen.add(key)

        result.append({
            "strChannel": name,
            "strCountry": country,
        })

    return result


# ============================================================
# TV MAP
# ============================================================

async def build_tv_map(
    date
):

    listings = await get_tv_day(
        date
    )

    result = {}

    for listing in listings:

        event_id = (
            listing.get("idEvent")
            or listing.get("id")
        )

        if not event_id:

            continue

        key = str(
            event_id
        )

        result.setdefault(
            key,
            []
        )

        result[key].append(
            listing
        )

    for key in result:

        result[key] = clean_channels(
            result[key]
        )

    return result


async def get_event_channels(
    event
):

    event_id = event.get(
        "idEvent"
    )

    if not event_id:

        return []

    channels = await lookup_event_tv(
        event_id
    )

    return clean_channels(
        channels
    )


# ============================================================
# MAIN MENU
# ============================================================

def main_menu():

    keyboard = [

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
                "🎯 Darts",
                callback_data="sport:darts",
            ),
            InlineKeyboardButton(
                "🏎️ Formula 1",
                callback_data="sport:f1",
            ),
        ],

        [
            InlineKeyboardButton(
                "🏌️ Golf",
                callback_data="sport:golf",
            ),
            InlineKeyboardButton(
                "🥊 Combat",
                callback_data="sport:combat",
            ),
        ],

        [
            InlineKeyboardButton(
                "📺 On TV Now",
                callback_data="tvnow",
            ),
        ],

        [
            InlineKeyboardButton(
                "⏱️ Starting Soon",
                callback_data="starting",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔔 My Alerts",
                callback_data="alerts",
            ),
            InlineKeyboardButton(
                "❤️ My Teams",
                callback_data="teams",
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
# BACK BUTTON
# ============================================================

def home_button():

    return [
        [
            InlineKeyboardButton(
                "⬅️ Back to Sports",
                callback_data="home",
            )
        ]
    ]


# ============================================================
# SPORT NAVIGATION
# ============================================================

def sport_navigation(
    sport_key,
    date,
):

    return [

        [
            InlineKeyboardButton(
                "◀️ Previous Day",
                callback_data=(
                    f"day:{sport_key}:{date}:-1"
                ),
            ),

            InlineKeyboardButton(
                "Next Day ▶️",
                callback_data=(
                    f"day:{sport_key}:{date}:1"
                ),
            ),
        ],

        [
            InlineKeyboardButton(
                "⬅️ Sports",
                callback_data="home",
            )
        ],

    ]


# ============================================================
# EVENT BUTTON
# ============================================================

def event_button(
    event_id,
    sport_key,
    date,
):

    return InlineKeyboardButton(
        "📺 Open Match",
        callback_data=(
            f"event:{event_id}:"
            f"{sport_key}:{date}"
        ),
    )


# ============================================================
# HOME TEXT
# ============================================================

def home_text():

    now = uk_now().strftime(
        "%H:%M"
    )

    return (
        "🔥 *SPORT PULSE ALERTS*\n\n"
        f"🇬🇧 UK TIME: *{now}*\n\n"
        "Choose a sport below.\n\n"
        "📺 UK TV listings\n"
        "🌍 Worldwide broadcasters\n"
        "🔔 Match alerts\n"
        "❤️ Follow teams\n"
        "📅 Previous / Next Day"
    )


# ============================================================
# SPORT HEADER
# ============================================================

def sport_header(
    sport_key,
    date,
    count,
):

    name = SPORTS[
        sport_key
    ]["name"]

    word = (
        "fixture"
        if count == 1
        else "fixtures"
    )

    return (
        f"📅 *{display_date(date)}*\n"
        f"{name}\n\n"
        f"📋 {count} {word}"
    )


# ============================================================
# MATCH CARD
# ============================================================

def make_match_card(
    event,
    channels,
):

    date_value = (
        event.get("dateEvent")
        or "Date TBC"
    )

    formatted_date = (
        display_date(date_value)
    )

    time_value = event_time(
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

    lines = [

        "━━━━━━━━━━━━━━━━━━━━",

        f"📅 *{formatted_date}*",

        f"🕒 *{time_value} UK*",

        "",

        f"⚽ *{home}*",

        "        *VS*",

        f"⚽ *{away}*",

    ]

    if league:

        lines.append(
            f"\n🏆 {league}"
        )

    if venue:

        lines.append(
            f"📍 {venue}"
        )

    lines.append("")

    channels = clean_channels(
        channels
    )

    uk_channels = [
        channel
        for channel in channels
        if is_uk_channel(channel)
    ]

    international = [
        channel
        for channel in channels
        if not is_uk_channel(channel)
    ]

    lines.append(
        "🇬🇧 *UK TV*"
    )

    if uk_channels:

        for channel in uk_channels[:8]:

            lines.append(
                f"• {get_channel_name(channel)}"
            )

    else:

        lines.append(
            "• TBC / not currently listed"
        )

    if international:

        lines.append("")

        count = len(
            international
        )

        lines.append(
            f"🌍 *{count} international "
            f"broadcaster"
            f"{'' if count == 1 else 's'} "
            f"available*"
        )

    lines.append(
        "━━━━━━━━━━━━━━━━━━━━"
    )

    return "\n".join(
        lines
    )


# ============================================================
# EVENT DETAIL BUTTONS
# ============================================================

def event_buttons(
    event_id,
    sport_key,
    date,
):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🌍 Worldwide TV",
                callback_data=(
                    f"world:{event_id}:"
                    f"{sport_key}:{date}"
                ),
            )
        ],

        [
            InlineKeyboardButton(
                "🔔 Alert Me",
                callback_data=(
                    f"alert:{event_id}:"
                    f"{sport_key}:{date}"
                ),
            ),

            InlineKeyboardButton(
                "❤️ Follow",
                callback_data=(
                    f"follow:{event_id}:"
                    f"{sport_key}:{date}"
                ),
            ),
        ],

        [
            InlineKeyboardButton(
                "⬅️ Back to Fixtures",
                callback_data=(
                    f"dayback:{sport_key}:{date}"
                ),
            )
        ],

    ])


# ============================================================
# SHOW SPORT
# ============================================================

async def show_sport(
    query,
    sport_key,
    date,
):

    logger.info(
        "Loading %s for %s",
        sport_key,
        date,
    )

    events = await get_sport_events(
        date,
        sport_key,
    )

    if not events:

        text = (
            f"📅 *{display_date(date)}*\n"
            f"{SPORTS[sport_key]['name']}\n\n"
            "⚠️ *No fixtures found for this date.*\n\n"
            "Use Previous Day or Next Day "
            "to check another date."
        )

        keyboard = InlineKeyboardMarkup(
            sport_navigation(
                sport_key,
                date,
            )
        )

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=keyboard,
        )

        return

    tv_map = await build_tv_map(
        date
    )

    lines = [
        sport_header(
            sport_key,
            date,
            len(events),
        ),
        "",
    ]

    buttons = []

    for index, event in enumerate(
        events[:20],
        start=1,
    ):

        event_id = event.get(
            "idEvent"
        )

        home = (
            event.get(
                "strHomeTeam"
            )
            or "Home"
        )

        away = (
            event.get(
                "strAwayTeam"
            )
            or "Away"
        )

        lines.append(
            f"*{index}. "
            f"{event_time(event)}* — "
            f"{home} vs {away}"
        )

        channels = tv_map.get(
            str(event_id),
            [],
        )

        uk = [
            channel
            for channel in channels
            if is_uk_channel(channel)
        ]

        if uk:

            names = [
                get_channel_name(
                    channel
                )
                for channel in uk[:3]
            ]

            lines.append(
                "📺 UK TV: "
                + ", ".join(names)
            )

        else:

            lines.append(
                "📺 UK TV: TBC"
            )

        lines.append("")

        if event_id:

            buttons.append([
                InlineKeyboardButton(
                    (
                        f"📺 "
                        f"{event_time(event)} "
                        f"{home} v {away}"
                    )[:60],
                    callback_data=(
                        f"event:{event_id}:"
                        f"{sport_key}:{date}"
                    ),
                )
            ])

    text = "\n".join(
        lines
    )

    if len(text) > 3900:

        short_lines = [
            sport_header(
                sport_key,
                date,
                len(events),
            ),
            "",
        ]

        for index, event in enumerate(
            events[:20],
            start=1,
        ):

            short_lines.append(
                f"*{index}. "
                f"{event_time(event)}* — "
                f"{event.get('strHomeTeam', 'Home')} "
                f"vs "
                f"{event.get('strAwayTeam', 'Away')}"
            )

        text = "\n".join(
            short_lines
        )

    buttons.extend(
        sport_navigation(
            sport_key,
            date,
        )
    )

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
    )


# ============================================================
# SHOW EVENT
# ============================================================

async def show_event(
    query,
    event_id,
    sport_key,
    date,
):

    event = await lookup_event(
        event_id
    )

    if not event:

        await query.answer(
            "Event not found.",
            show_alert=True,
        )

        return

    channels = await get_event_channels(
        event
    )

    text = make_match_card(
        event,
        channels,
    )

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=event_buttons(
            event_id,
            sport_key,
            date,
        ),
    )


# ============================================================
# WORLDWIDE TV
# ============================================================

async def show_worldwide(
    query,
    event_id,
    sport_key,
    date,
):

    event = await lookup_event(
        event_id
    )

    if not event:

        await query.answer(
            "Event not found.",
            show_alert=True,
        )

        return

    channels = await get_event_channels(
        event
    )

    worldwide = [
        channel
        for channel in channels
        if not is_uk_channel(channel)
    ]

    if not worldwide:

        text = (
            "🌍 *WORLDWIDE TV*\n\n"
            "No international TV listings "
            "are currently available."
        )

    else:

        grouped = {}

        for channel in worldwide:

            country = get_channel_country(
                channel
            )

            grouped.setdefault(
                country,
                [],
            )

            grouped[country].append(
                get_channel_name(
                    channel
                )
            )

        lines = [
            "🌍 *WORLDWIDE TV*",
            "",
        ]

        for country, names in grouped.items():

            lines.append(
                f"🌎 *{country}*"
            )

            for name in names[:10]:

                lines.append(
                    f"• {name}"
                )

            lines.append("")

        text = "\n".join(
            lines
        ).strip()

    keyboard = InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "⬅️ Back to Match",
                callback_data=(
                    f"event:{event_id}:"
                    f"{sport_key}:{date}"
                ),
            )
        ],

        [
            InlineKeyboardButton(
                "⬅️ Back to Fixtures",
                callback_data=(
                    f"dayback:{sport_key}:{date}"
                ),
            )
        ],

    ])

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


# ============================================================
# ALERT
# ============================================================

async def save_alert(
    query,
    user_id,
    event_id,
):

    event = await lookup_event(
        event_id
    )

    if not event:

        await query.answer(
            "Event not found.",
            show_alert=True,
        )

        return

    data = get_user(
        user_id
    )

    event_id = str(
        event_id
    )

    if event_id not in data["alerts"]:

        data["alerts"].append(
            event_id
        )

        save_data()

        await query.answer(
            "🔔 Alert saved!",
            show_alert=True,
        )

    else:

        await query.answer(
            "🔔 Alert already saved.",
            show_alert=True,
        )


# ============================================================
# FOLLOW TEAM
# ============================================================

async def follow_team(
    query,
    user_id,
    event_id,
):

    event = await lookup_event(
        event_id
    )

    if not event:

        await query.answer(
            "Event not found.",
            show_alert=True,
        )

        return

    team = (
        event.get("strHomeTeam")
        or event.get("strAwayTeam")
    )

    if not team:

        await query.answer(
            "Team unavailable.",
            show_alert=True,
        )

        return

    data = get_user(
        user_id
    )

    if team not in data["teams"]:

        data["teams"].append(
            team
        )

        save_data()

        await query.answer(
            f"❤️ Following {team}",
            show_alert=True,
        )

    else:

        await query.answer(
            f"❤️ Already following {team}",
            show_alert=True,
        )


# ============================================================
# MY ALERTS
# ============================================================

async def show_alerts(
    query,
    user_id,
):

    data = get_user(
        user_id
    )

    if not data["alerts"]:

        text = (
            "🔔 *MY ALERTS*\n\n"
            "You have no saved alerts.\n\n"
            "Open a fixture and press "
            "*🔔 Alert Me*."
        )

        await query.edit_message_text(
            text=text,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(
                home_button()
            ),
        )

        return

    lines = [
        "🔔 *MY ALERTS*",
        "",
    ]

    valid_alerts = []

    for event_id in data["alerts"][:30]:

        event = await lookup_event(
            event_id
        )

        if not event:

            continue

        valid_alerts.append(
            event_id
        )

        lines.append(
            f"🕒 *{event_time(event)}* — "
            f"{event.get('strHomeTeam', 'Home')} "
            f"vs "
            f"{event.get('strAwayTeam', 'Away')}"
        )

    data["alerts"] = valid_alerts

    save_data()

    if len(lines) == 2:

        lines.append(
            "No active events found."
        )

    await query.edit_message_text(
        text="\n".join(lines),
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            home_button()
        ),
    )


# ============================================================
# MY TEAMS
# ============================================================

async def show_teams(
    query,
    user_id,
):

    data = get_user(
        user_id
    )

    if not data["teams"]:

        text = (
            "❤️ *MY TEAMS*\n\n"
            "You are not following any teams.\n\n"
            "Open a fixture and press "
            "*❤️ Follow*."
        )

    else:

        lines = [
            "❤️ *MY TEAMS*",
            "",
        ]

        for team in data["teams"]:

            lines.append(
                f"• {team}"
            )

        text = "\n".join(
            lines
        )

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            home_button()
        ),
    )


# ============================================================
# ON TV NOW
# ============================================================

async def show_tv_now(
    query,
):

    now = uk_now()

    date = today_string()

    listings = await get_tv_day(
        date,
        country="United Kingdom",
    )

    events = {}

    for listing in listings:

        if not is_uk_channel(
            listing
        ):

            continue

        event_id = (
            listing.get("idEvent")
        )

        if not event_id:

            continue

        dt = event_datetime(
            listing
        )

        if not dt:

            continue

        if (
            now - timedelta(hours=2)
            <= dt
            <= now + timedelta(hours=2)
        ):

            events.setdefault(
                str(event_id),
                listing,
            )

    rows = list(
        events.values()
    )

    rows.sort(
        key=lambda item: (
            event_datetime(item)
            or datetime.max.replace(
                tzinfo=UK_TIMEZONE
            )
        )
    )

    if not rows:

        text = (
            "📺 *ON TV NOW*\n\n"
            "Nothing currently listed "
            "on UK TV in the surrounding "
            "2-hour window."
        )

        keyboard = InlineKeyboardMarkup(
            home_button()
        )

    else:

        lines = [
            "📺 *ON TV NOW*",
            "",
        ]

        buttons = []

        for item in rows[:20]:

            event_id = item.get(
                "idEvent"
            )

            name = (
                item.get("strEvent")
                or "Sports event"
            )

            channel = (
                item.get("strChannel")
                or "TV TBC"
            )

            dt = event_datetime(
                item
            )

            time_text = (
                dt.strftime("%H:%M")
                if dt
                else "TBC"
            )

            lines.append(
                f"🕒 *{time_text}* — {name}"
            )

            lines.append(
                f"📺 {channel}"
            )

            lines.append("")

            if event_id:

                buttons.append([

                    InlineKeyboardButton(
                        (
                            f"📺 {time_text} "
                            f"{name}"
                        )[:60],
                        callback_data=(
                            f"event:{event_id}:"
                            f"football:{date}"
                        ),
                    )

                ])

        buttons.append([
            InlineKeyboardButton(
                "⬅️ Sports",
                callback_data="home",
            )
        ])

        text = "\n".join(
            lines
        )

        keyboard = InlineKeyboardMarkup(
            buttons
        )

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


# ============================================================
# STARTING SOON
# ============================================================

async def show_starting(
    query,
):

    now = uk_now()

    events = {}

    for day_offset in range(
        0,
        2,
    ):

        day = (
            now
            + timedelta(
                days=day_offset
            )
        ).strftime(
            "%Y-%m-%d"
        )

        for sport_key in SPORTS:

            found = await get_sport_events(
                day,
                sport_key,
            )

            for event in found:

                event_id = event.get(
                    "idEvent"
                )

                if event_id:

                    events[
                        str(event_id)
                    ] = event

    upcoming = []

    for event in events.values():

        dt = event_datetime(
            event
        )

        if not dt:

            continue

        if (
            now
            <= dt
            <= now + timedelta(
                hours=6
            )
        ):

            upcoming.append(
                event
            )

    upcoming.sort(
        key=lambda event: (
            event_datetime(event)
            or datetime.max.replace(
                tzinfo=UK_TIMEZONE
            )
        )
    )

    if not upcoming:

        text = (
            "⏱️ *STARTING SOON*\n\n"
            "No events found in the "
            "next 6 hours."
        )

        keyboard = InlineKeyboardMarkup(
            home_button()
        )

    else:

        lines = [
            "⏱️ *STARTING SOON*",
            "",
        ]

        buttons = []

        for event in upcoming[:20]:

            event_id = event.get(
                "idEvent"
            )

            home = (
                event.get(
                    "strHomeTeam"
                )
                or "Home"
            )

            away = (
                event.get(
                    "strAwayTeam"
                )
                or "Away"
            )

            sport = (
                event.get(
                    "strSport"
                )
                or "Sport"
            )

            lines.append(
                f"🕒 *{event_time(event)}* — "
                f"{home} vs {away}"
            )

            lines.append(
                f"   {sport}"
            )

            lines.append("")

            if event_id:

                buttons.append([

                    InlineKeyboardButton(
                        (
                            f"📺 "
                            f"{event_time(event)} "
                            f"{home} v {away}"
                        )[:60],
                        callback_data=(
                            f"event:{event_id}:"
                            f"football:{today_string()}"
                        ),
                    )

                ])

        buttons.append([
            InlineKeyboardButton(
                "⬅️ Sports",
                callback_data="home",
            )
        ])

        text = "\n".join(
            lines
        )

        keyboard = InlineKeyboardMarkup(
            buttons
        )

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


# ============================================================
# HELP
# ============================================================

async def show_help(
    query,
):

    text = (
        "ℹ️ *SPORT PULSE ALERTS*\n\n"

        "⚽ *Football*\n"
        "🏉 *Rugby*\n"
        "🏏 *Cricket*\n"
        "🎾 *Tennis*\n"
        "🎯 *Darts*\n"
        "🏎️ *Formula 1*\n"
        "🏌️ *Golf*\n"
        "🥊 *Combat*\n\n"

        "📅 Use Previous Day / Next Day "
        "to browse dates.\n\n"

        "📺 Open a fixture to see TV.\n"
        "🌍 Worldwide TV shows international "
        "broadcasters.\n"
        "🔔 Alert Me saves an event.\n"
        "❤️ Follow saves a team.\n\n"

        "🇬🇧 All times are UK time."
    )

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            home_button()
        ),
    )


# ============================================================
# PREMIUM
# ============================================================

async def show_premium(
    query,
):

    text = (
        "💎 *PREMIUM*\n\n"
        "Premium features are coming soon.\n\n"
        "The main fixture and TV system "
        "is available now."
    )

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(
            home_button()
        ),
    )


# ============================================================
# CALLBACK ROUTER
# ============================================================

async def callback_router(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    data = query.data or ""

    user_id = query.from_user.id

    try:

        # ----------------------------------------------------
        # HOME
        # ----------------------------------------------------

        if data == "home":

            await query.edit_message_text(
                text=home_text(),
                parse_mode="Markdown",
                reply_markup=main_menu(),
            )

            return


        # ----------------------------------------------------
        # SPORT
        # ----------------------------------------------------

        if data.startswith(
            "sport:"
        ):

            sport_key = data.split(
                ":",
                1,
            )[1]

            if sport_key not in SPORTS:

                await query.edit_message_text(
                    "⚠️ Sport not available.",
                    reply_markup=InlineKeyboardMarkup(
                        home_button()
                    ),
                )

                return

            await show_sport(
                query,
                sport_key,
                today_string(),
            )

            return


        # ----------------------------------------------------
        # PREVIOUS / NEXT DAY
        # ----------------------------------------------------

        if data.startswith(
            "day:"
        ):

            parts = data.split(
                ":"
            )

            if len(parts) != 4:

                return

            sport_key = parts[1]

            current_date = parts[2]

            direction = int(
                parts[3]
            )

            base_date = datetime.strptime(
                current_date,
                "%Y-%m-%d",
            )

            new_date = (
                base_date
                + timedelta(
                    days=direction
                )
            ).strftime(
                "%Y-%m-%d"
            )

            await show_sport(
                query,
                sport_key,
                new_date,
            )

            return


        # ----------------------------------------------------
        # BACK TO FIXTURES
        # ----------------------------------------------------

        if data.startswith(
            "dayback:"
        ):

            parts = data.split(
                ":"
            )

            sport_key = parts[1]

            date = parts[2]

            await show_sport(
                query,
                sport_key,
                date,
            )

            return


        # ----------------------------------------------------
        # EVENT
        # ----------------------------------------------------

        if data.startswith(
            "event:"
        ):

            parts = data.split(
                ":"
            )

            if len(parts) < 4:

                return

            event_id = parts[1]

            sport_key = parts[2]

            date = parts[3]

            await show_event(
                query,
                event_id,
                sport_key,
                date,
            )

            return


        # ----------------------------------------------------
        # WORLDWIDE TV
        # ----------------------------------------------------

        if data.startswith(
            "world:"
        ):

            parts = data.split(
                ":"
            )

            event_id = parts[1]

            sport_key = parts[2]

            date = parts[3]

            await show_worldwide(
                query,
                event_id,
                sport_key,
                date,
            )

            return


        # ----------------------------------------------------
        # ALERT
        # ----------------------------------------------------

        if data.startswith(
            "alert:"
        ):

            parts = data.split(
                ":"
            )

            event_id = parts[1]

            await save_alert(
                query,
                user_id,
                event_id,
            )

            return


        # ----------------------------------------------------
        # FOLLOW
        # ----------------------------------------------------

        if data.startswith(
            "follow:"
        ):

            parts = data.split(
                ":"
            )

            event_id = parts[1]

            await follow_team(
                query,
                user_id,
                event_id,
            )

            return


        # ----------------------------------------------------
        # TV NOW
        # ----------------------------------------------------

        if data == "tvnow":

            await show_tv_now(
                query
            )

            return


        # ----------------------------------------------------
        # STARTING SOON
        # ----------------------------------------------------

        if data == "starting":

            await show_starting(
                query
            )

            return


        # ----------------------------------------------------
        # ALERTS
        # ----------------------------------------------------

        if data == "alerts":

            await show_alerts(
                query,
                user_id,
            )

            return


        # ----------------------------------------------------
        # TEAMS
        # ----------------------------------------------------

        if data == "teams":

            await show_teams(
                query,
                user_id,
            )

            return


        # ----------------------------------------------------
        # HELP
        # ----------------------------------------------------

        if data == "help":

            await show_help(
                query
            )

            return


        # ----------------------------------------------------
        # PREMIUM
        # ----------------------------------------------------

        if data == "premium":

            await show_premium(
                query
            )

            return


        # ----------------------------------------------------
        # UNKNOWN
        # ----------------------------------------------------

        await query.edit_message_text(
            text=(
                "⚠️ Unknown menu option.\n\n"
                "Please return to the main menu."
            ),
            reply_markup=InlineKeyboardMarkup(
                home_button()
            ),
        )

    except Exception:

        logger.exception(
            "Callback error: %s",
            data,
        )

        try:

            await query.edit_message_text(
                text=(
                    "⚠️ *Something went wrong.*\n\n"
                    "The API may be temporarily "
                    "unavailable. Please try again."
                ),
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(
                    home_button()
                ),
            )

        except Exception:

            pass


# ============================================================
# /START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        text=home_text(),
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


# ============================================================
# /HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        text=(
            "ℹ️ *SPORT PULSE ALERTS*\n\n"
            "Press /start to open the main menu."
        ),
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context,
):

    logger.exception(
        "Unhandled bot error: %s",
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

    application.add_handler(
        CommandHandler(
            "help",
            help_command,
        )
    )

    # ALL inline buttons go through one router.
    application.add_handler(
        CallbackQueryHandler(
            callback_router
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Bot is online."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
