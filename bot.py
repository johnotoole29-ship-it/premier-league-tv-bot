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

SPORTSDB_API_KEY = (
    os.getenv("SPORTSDB_API_KEY")
    or os.getenv("FOOTBALL_API_KEY")
)

SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"

UK_TIMEZONE = ZoneInfo("Europe/London")

REQUEST_TIMEOUT = 20
MAX_MESSAGE_LENGTH = 3900


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# CHECK CONFIG
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
# LEAGUES
#
# Only use fixed IDs where we know the competition.
# ============================================================

LEAGUES = {

    "premier": {
        "id": "4328",
        "name": "Premier League",
        "icon": "⚽",
        "back": "football",
    },

    "championship": {
        "id": "4329",
        "name": "Championship",
        "icon": "⚽",
        "back": "football",
    },

}


# ============================================================
# HOME TEXT
# ============================================================

HOME_TEXT = (
    "🔥 **SPORT PULSE ALERTS**\n\n"
    "Fixtures • Events • TV Coverage\n\n"
    "👇 **Choose a sport**"
)


# ============================================================
# API REQUEST
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
            timeout=REQUEST_TIMEOUT,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:

        logger.error(
            "TheSportsDB request failed: %s",
            error,
        )

        return None

    except ValueError as error:

        logger.error(
            "Invalid JSON returned: %s",
            error,
        )

        return None


# ============================================================
# DATE / TIME
# ============================================================

def get_uk_date():

    return datetime.now(
        UK_TIMEZONE
    ).strftime(
        "%Y-%m-%d"
    )


def format_display_date(
    date_string,
):

    try:

        return datetime.strptime(
            date_string,
            "%Y-%m-%d",
        ).strftime(
            "%A %d %B"
        )

    except Exception:

        return date_string or "Date TBC"


def format_event_time(
    event,
):

    timestamp = event.get(
        "strTimestamp"
    )

    if timestamp:

        try:

            timestamp = timestamp.replace(
                "Z",
                "+00:00",
            )

            event_datetime = datetime.fromisoformat(
                timestamp
            )

            if event_datetime.tzinfo is None:

                event_datetime = event_datetime.replace(
                    tzinfo=timezone.utc
                )

            return event_datetime.astimezone(
                UK_TIMEZONE
            ).strftime(
                "%H:%M"
            )

        except Exception:

            pass


    event_date = event.get(
        "dateEvent"
    )

    event_time = event.get(
        "strTime"
    )


    if event_date and event_time:

        try:

            clean_time = event_time[:8]

            event_datetime = datetime.strptime(
                f"{event_date} {clean_time}",
                "%Y-%m-%d %H:%M:%S",
            )

            event_datetime = event_datetime.replace(
                tzinfo=timezone.utc
            )

            return event_datetime.astimezone(
                UK_TIMEZONE
            ).strftime(
                "%H:%M"
            )

        except Exception:

            pass


    if event_time:

        return event_time[:5]


    return "TBC"


# ============================================================
# NAVIGATION
# ============================================================

def nav_row(
    back_callback="home",
):

    return [

        InlineKeyboardButton(
            "◀️ Back",
            callback_data=back_callback,
        ),

        InlineKeyboardButton(
            "🏠 Home",
            callback_data="home",
        ),

    ]


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
                "🏎️ F1",
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
                "🔔 My Alerts",
                callback_data="my_alerts",
            ),

            InlineKeyboardButton(
                "⭐ My Teams",
                callback_data="my_teams",
            ),
        ],

        [
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
# FOOTBALL MENU
# ============================================================

def football_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🏆 Premier League",
                callback_data="premier",
            )
        ],

        [
            InlineKeyboardButton(
                "🏆 Championship",
                callback_data="championship",
            )
        ],

        nav_row("home"),

    ])


# ============================================================
# RUGBY MENU
# ============================================================

def rugby_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🏉 Rugby Union",
                callback_data="rugby_union",
            )
        ],

        [
            InlineKeyboardButton(
                "🏉 Super League",
                callback_data="super_league",
            )
        ],

        [
            InlineKeyboardButton(
                "🇦🇺 NRL",
                callback_data="nrl",
            )
        ],

        nav_row("home"),

    ])


# ============================================================
# COMBAT MENU
# ============================================================

def combat_menu():

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🥊 UFC",
                callback_data="ufc",
            )
        ],

        [
            InlineKeyboardButton(
                "🥊 Boxing",
                callback_data="boxing",
            )
        ],

        [
            InlineKeyboardButton(
                "🤼 WWE",
                callback_data="wwe",
            )
        ],

        nav_row("home"),

    ])


# ============================================================
# TODAY / NEXT 7 MENU
# ============================================================

def date_menu(
    prefix,
    back_callback,
):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📅 Today",
                callback_data=f"{prefix}_today",
            )
        ],

        [
            InlineKeyboardButton(
                "➡️ Next 7 Days",
                callback_data=f"{prefix}_next7",
            )
        ],

        nav_row(back_callback),

    ])


# ============================================================
# RESULTS MENU
# ============================================================

def results_menu(
    back_callback,
    worldwide_callback,
):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🌍 Show Worldwide Channels",
                callback_data=worldwide_callback,
            )
        ],

        nav_row(back_callback),

    ])


# ============================================================
# GET EVENTS BY DAY
# ============================================================

def get_events_for_day(
    date,
    sport=None,
    league_id=None,
):

    params = {
        "d": date,
    }

    if sport:

        params["s"] = sport

    if league_id:

        params["l"] = league_id


    data = sportsdb_get(
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
# FOOTBALL
# ============================================================

def get_premier_events(
    date,
):

    return get_events_for_day(
        date,
        sport="Soccer",
        league_id="4328",
    )


def get_championship_events(
    date,
):

    return get_events_for_day(
        date,
        sport="Soccer",
        league_id="4329",
    )


# ============================================================
# RUGBY
# ============================================================

def get_rugby_events(
    date,
):

    return get_events_for_day(
        date,
        sport="Rugby",
    )


def filter_super_league(
    events,
):

    keywords = [

        "super league",
        "betfred super league",

    ]

    return [

        event

        for event in events

        if any(

            keyword in (
                event.get("strLeague")
                or ""
            ).lower()

            for keyword in keywords

        )

    ]


def filter_nrl(
    events,
):

    return [

        event

        for event in events

        if "nrl" in (

            event.get("strLeague")
            or ""

        ).lower()

        or "national rugby league" in (

            event.get("strLeague")
            or ""

        ).lower()

    ]


def filter_rugby_union(
    events,
):

    excluded = [

        "super league",
        "nrl",
        "national rugby league",

    ]

    return [

        event

        for event in events

        if not any(

            word in (

                event.get("strLeague")
                or ""

            ).lower()

            for word in excluded

        )

    ]


def get_rugby_union_events(
    date,
):

    return filter_rugby_union(
        get_rugby_events(date)
    )


def get_super_league_events(
    date,
):

    return filter_super_league(
        get_rugby_events(date)
    )


def get_nrl_events(
    date,
):

    return filter_nrl(
        get_rugby_events(date)
    )


# ============================================================
# OTHER SPORTS
# ============================================================

def get_cricket_events(
    date,
):

    return get_events_for_day(
        date,
        sport="Cricket",
    )


def get_tennis_events(
    date,
):

    return get_events_for_day(
        date,
        sport="Tennis",
    )


def get_darts_events(
    date,
):

    return get_events_for_day(
        date,
        sport="Darts",
    )


def get_f1_events(
    date,
):

    events = get_events_for_day(
        date
    )

    return [

        event

        for event in events

        if "formula 1" in (

            event.get("strLeague")
            or ""

        ).lower()

        or event.get("strSport") == "Motorsport"

        and "f1" in (

            event.get("strEvent")
            or ""

        ).lower()

    ]


def get_golf_events(
    date,
):

    return get_events_for_day(
        date,
        sport="Golf",
    )


# ============================================================
# COMBAT SPORTS
# ============================================================

def get_fighting_events(
    date,
):

    return get_events_for_day(
        date,
        sport="Fighting",
    )


def get_ufc_events(
    date,
):

    events = get_fighting_events(
        date
    )

    return [

        event

        for event in events

        if "ufc" in (

            event.get("strLeague")
            or ""

        ).lower()

        or "ufc" in (

            event.get("strEvent")
            or ""

        ).lower()

    ]


def get_boxing_events(
    date,
):

    events = get_fighting_events(
        date
    )

    return [

        event

        for event in events

        if "boxing" in (

            event.get("strLeague")
            or ""

        ).lower()

        or "boxing" in (

            event.get("strEvent")
            or ""

        ).lower()

    ]


def get_wwe_events(
    date,
):

    events = get_events_for_day(
        date
    )

    return [

        event

        for event in events

        if "wwe" in (

            event.get("strLeague")
            or ""

        ).lower()

        or "wwe" in (

            event.get("strEvent")
            or ""

        ).lower()

    ]


# ============================================================
# CLEAN TV CHANNELS
# ============================================================

def clean_tv_channels(
    channels,
):

    seen = set()

    cleaned = []


    for item in channels:

        channel = (
            item.get("channel")
            or ""
        ).strip()

        country = (
            item.get("country")
            or ""
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

        cleaned.append({

            "channel": channel,

            "country": country,

        })


    return cleaned


# ============================================================
# LOOKUP TV FOR ONE EVENT
#
# This is the main TV lookup.
# ============================================================

def get_tv_channels_for_event(
    event_id,
):

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

        or data.get("tv")

        or []

    )


    channels = []


    for broadcast in broadcasts:

        channel = (

            broadcast.get("strChannel")

            or broadcast.get("strChannelName")

            or broadcast.get("strEvent")

            or ""

        )


        country = (

            broadcast.get("strCountry")

            or broadcast.get("strCountryName")

            or ""

        )


        if channel:

            channels.append({

                "channel": channel,

                "country": country,

            })


    return clean_tv_channels(
        channels
    )


# ============================================================
# DAILY TV LOOKUP
# ============================================================

def get_daily_tv_channels(
    date,
    country=None,
):

    params = {
        "d": date,
    }


    if country:

        params["a"] = country


    data = sportsdb_get(
        "eventstv.php",
        params,
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

        event_id = broadcast.get(
            "idEvent"
        )

        if not event_id:

            continue


        channel = (

            broadcast.get("strChannel")

            or broadcast.get("strChannelName")

            or broadcast.get("strEvent")

            or ""

        )


        country_name = (

            broadcast.get("strCountry")

            or broadcast.get("strCountryName")

            or ""

        )


        if not channel:

            continue


        tv_by_event.setdefault(

            str(event_id),

            []

        ).append({

            "channel": channel,

            "country": country_name,

        })


    for event_id in tv_by_event:

        tv_by_event[event_id] = (
            clean_tv_channels(
                tv_by_event[event_id]
            )
        )


    return tv_by_event


# ============================================================
# BUILD TV CACHE
#
# 1. UK TV listings
# 2. Worldwide daily listings
# ============================================================

def build_tv_cache(
    date,
):

    uk_tv = get_daily_tv_channels(
        date,
        country="United_Kingdom",
    )

    worldwide_tv = get_daily_tv_channels(
        date
    )

    return {

        "uk": uk_tv,

        "worldwide": worldwide_tv,

    }


# ============================================================
# GET CHANNELS FOR EVENT
#
# Priority:
#
# 1. lookuptv.php event lookup
# 2. UK daily TV listing
# 3. Worldwide daily TV listing
# ============================================================

def get_event_channels(
    event,
    tv_cache,
):

    event_id = str(
        event.get("idEvent")
        or ""
    )


    channels = get_tv_channels_for_event(
        event_id
    )


    uk_channels = (

        tv_cache.get("uk", {})

        .get(event_id, [])

    )


    worldwide_channels = (

        tv_cache.get("worldwide", {})

        .get(event_id, [])

    )


    combined = []

    combined.extend(
        uk_channels
    )

    combined.extend(
        channels
    )

    combined.extend(
        worldwide_channels
    )


    return clean_tv_channels(
        combined
    )


# ============================================================
# PRIORITISE UK CHANNELS
# ============================================================

def order_channels(
    channels,
):

    uk = []

    other = []


    uk_names = {

        "united kingdom",
        "uk",
        "england",
        "great britain",

    }


    for item in channels:

        country = (

            item.get("country")
            or ""

        ).strip().lower()


        channel = (

            item.get("channel")
            or ""

        ).lower()


        if (

            country in uk_names

            or "sky sports" in channel

            or "tnt sports" in channel

            or "bbc" in channel

            or "itv" in channel

            or "amazon prime" in channel

            or "discovery+" in channel

            or "channel 4" in channel

            or "channel 5" in channel

        ):

            uk.append(item)

        else:

            other.append(item)


    return clean_tv_channels(
        uk + other
    )


# ============================================================
# FORMAT CHANNELS UNDER EVENT
# ============================================================

def format_event_channels(
    event,
    tv_cache,
):

    channels = get_event_channels(
        event,
        tv_cache,
    )


    channels = order_channels(
        channels
    )


    if not channels:

        return (
            "📺 **TV:** Not currently listed"
        )


    display = []


    for item in channels[:5]:

        channel = item.get(
            "channel"
        )

        country = item.get(
            "country"
        )


        if country:

            display.append(
                f"{channel} ({country})"
            )

        else:

            display.append(
                channel
            )


    return (
        "📺 **TV:** "
        + " • ".join(display)
    )


# ============================================================
# EVENT TITLE
# ============================================================

def event_title(
    event,
):

    home = event.get(
        "strHomeTeam"
    )

    away = event.get(
        "strAwayTeam"
    )


    if home and away:

        return f"{home} vs {away}"


    return (

        event.get("strEvent")

        or event.get("strEventAlternate")

        or "Event"

    )


# ============================================================
# EVENT LOCATION
# ============================================================

def event_location(
    event,
):

    parts = []


    for value in [

        event.get("strVenue"),

        event.get("strCity"),

        event.get("strCountry"),

    ]:

        if value and value not in parts:

            parts.append(value)


    return " • ".join(
        parts
    )


# ============================================================
# EVENT BLOCK
# ============================================================

def build_event_block(
    event,
    icon,
    tv_cache,
):

    lines = [

        f"🕒 **{format_event_time(event)}**",

        f"{icon} **{event_title(event)}**",

    ]


    league = event.get(
        "strLeague"
    )

    location = event_location(
        event
    )


    if league:

        lines.append(
            f"🏆 {league}"
        )


    if location:

        lines.append(
            f"📍 {location}"
        )


    lines.append(

        format_event_channels(
            event,
            tv_cache,
        )

    )


    return "\n".join(
        lines
    )


# ============================================================
# SORT EVENTS
# ============================================================

def sort_events(
    events,
):

    return sorted(

        events,

        key=lambda event: (

            event.get("dateEvent")
            or "9999-99-99",

            event.get("strTimestamp")
            or "",

            event.get("strTime")
            or "99:99",

        ),

    )


# ============================================================
# BUILD TODAY MESSAGE
# ============================================================

def build_today_message(
    title,
    events,
    date,
    icon,
):

    tv_cache = build_tv_cache(
        date
    )


    lines = [

        f"{icon} **{title.upper()}**",

        "",

        f"📅 **{format_display_date(date)}**",

        "",

    ]


    if not events:

        lines.append(
            "No events found today."
        )

        return "\n".join(
            lines
        )


    for event in sort_events(events):

        lines.append(

            build_event_block(
                event,
                icon,
                tv_cache,
            )

        )

        lines.append(
            "━━━━━━━━━━━━━━"
        )

        lines.append("")


    return "\n".join(
        lines
    ).strip()


# ============================================================
# BUILD NEXT 7 DAYS
# ============================================================

def build_next_7_days_message(
    title,
    event_function,
    icon,
):

    start_date = datetime.now(
        UK_TIMEZONE
    ).date()


    all_events = []

    tv_caches = {}


    for day_number in range(7):

        date = (

            start_date

            + timedelta(
                days=day_number
            )

        ).strftime(
            "%Y-%m-%d"
        )


        events = event_function(
            date
        )


        if events:

            all_events.extend(
                events
            )


        tv_caches[date] = (
            build_tv_cache(
                date
            )
        )


    lines = [

        f"{icon} **{title.upper()}**",

        "",

        "➡️ **NEXT 7 DAYS**",

        "",

    ]


    if not all_events:

        lines.append(
            "No events found in the next 7 days."
        )

        return "\n".join(
            lines
        )


    current_date = None


    for event in sort_events(all_events):

        event_date = event.get(
            "dateEvent"
        )


        if event_date != current_date:

            current_date = event_date

            lines.append(

                f"📅 **{format_display_date(event_date)}**"

            )

            lines.append("")


        tv_cache = tv_caches.get(
            event_date,
            {

                "uk": {},
                "worldwide": {},

            },
        )


        lines.append(

            build_event_block(
                event,
                icon,
                tv_cache,
            )

        )

        lines.append(
            "━━━━━━━━━━━━━━"
        )

        lines.append("")


    return "\n".join(
        lines
    ).strip()


# ============================================================
# WORLDWIDE CHANNELS
# ============================================================

def build_worldwide_message(
    events,
):

    if not events:

        return (
            "🌍 **WORLDWIDE CHANNELS**\n\n"
            "No events found."
        )


    lines = [

        "🌍 **WORLDWIDE TV CHANNELS**",

        "",

    ]


    current_date = None


    tv_caches = {}


    for event in sort_events(events):

        event_date = event.get(
            "dateEvent"
        )


        if event_date not in tv_caches:

            tv_caches[event_date] = (
                build_tv_cache(
                    event_date
                )
            )


        if event_date != current_date:

            current_date = event_date

            lines.append(

                f"📅 **{format_display_date(event_date)}**"

            )

            lines.append("")


        lines.append(

            f"🏆 **{event_title(event)}**"

        )


        channels = get_event_channels(

            event,

            tv_caches[event_date],

        )


        channels = order_channels(
            channels
        )


        if not channels:

            lines.append(
                "📺 Not currently listed"
            )

        else:

            grouped = {}


            for item in channels:

                country = (

                    item.get("country")

                    or "International"

                )


                grouped.setdefault(
                    country,
                    []
                ).append(

                    item.get("channel")
                )


            for country, country_channels in grouped.items():

                unique = []


                for channel in country_channels:

                    if channel not in unique:

                        unique.append(
                            channel
                        )


                lines.append(
                    f"🌍 **{country}:** "
                    + ", ".join(unique[:10])
                )


        lines.append(
            "━━━━━━━━━━━━━━"
        )

        lines.append("")


    return "\n".join(
        lines
    ).strip()


# ============================================================
# SPLIT LONG TELEGRAM MESSAGES
# ============================================================

def split_message(
    text,
):

    if len(text) <= MAX_MESSAGE_LENGTH:

        return [text]


    chunks = []

    current = ""


    for line in text.splitlines(
        keepends=True
    ):

        if (

            len(current)
            + len(line)

            > MAX_MESSAGE_LENGTH

        ):

            if current:

                chunks.append(
                    current
                )

                current = ""


        current += line


    if current:

        chunks.append(
            current
        )


    return chunks


async def send_long_message(
    query,
    text,
    reply_markup,
):

    chunks = split_message(
        text
    )


    await query.edit_message_text(

        chunks[0],

        reply_markup=reply_markup,

        parse_mode="Markdown",

    )


    for chunk in chunks[1:]:

        await query.message.reply_text(

            chunk,

            parse_mode="Markdown",

        )


# ============================================================
# SPORT CONFIG
# ============================================================

SPORT_CONFIG = {

    "premier": {

        "name": "Premier League",

        "icon": "⚽",

        "function": get_premier_events,

        "back": "football",

    },

    "championship": {

        "name": "Championship",

        "icon": "⚽",

        "function": get_championship_events,

        "back": "football",

    },

    "rugby_union": {

        "name": "Rugby Union",

        "icon": "🏉",

        "function": get_rugby_union_events,

        "back": "rugby",

    },

    "super_league": {

        "name": "Super League",

        "icon": "🏉",

        "function": get_super_league_events,

        "back": "rugby",

    },

    "nrl": {

        "name": "NRL",

        "icon": "🇦🇺",

        "function": get_nrl_events,

        "back": "rugby",

    },

    "cricket": {

        "name": "Cricket",

        "icon": "🏏",

        "function": get_cricket_events,

        "back": "home",

    },

    "tennis": {

        "name": "Tennis",

        "icon": "🎾",

        "function": get_tennis_events,

        "back": "home",

    },

    "darts": {

        "name": "Darts",

        "icon": "🎯",

        "function": get_darts_events,

        "back": "home",

    },

    "f1": {

        "name": "Formula 1",

        "icon": "🏎️",

        "function": get_f1_events,

        "back": "home",

    },

    "golf": {

        "name": "Golf",

        "icon": "🏌️",

        "function": get_golf_events,

        "back": "home",

    },

    "ufc": {

        "name": "UFC",

        "icon": "🥊",

        "function": get_ufc_events,

        "back": "combat",

    },

    "boxing": {

        "name": "Boxing",

        "icon": "🥊",

        "function": get_boxing_events,

        "back": "combat",

    },

    "wwe": {

        "name": "WWE",

        "icon": "🤼",

        "function": get_wwe_events,

        "back": "combat",

    },

}


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(

        HOME_TEXT,

        reply_markup=main_menu(),

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

    data = query.data


    # HOME

    if data in (
        "home",
        "back",
    ):

        await query.edit_message_text(

            HOME_TEXT,

            reply_markup=main_menu(),

            parse_mode="Markdown",

        )

        return


    # FOOTBALL

    if data == "football":

        await query.edit_message_text(

            "⚽ **FOOTBALL**\n\n"
            "Choose a competition:",

            reply_markup=football_menu(),

            parse_mode="Markdown",

        )

        return


    # RUGBY

    if data == "rugby":

        await query.edit_message_text(

            "🏉 **RUGBY**\n\n"
            "Choose a competition:",

            reply_markup=rugby_menu(),

            parse_mode="Markdown",

        )

        return


    # COMBAT

    if data == "combat":

        await query.edit_message_text(

            "🥊 **COMBAT SPORTS**\n\n"
            "Choose a sport:",

            reply_markup=combat_menu(),

            parse_mode="Markdown",

        )

        return


    # LEAGUE / SPORT FOLDERS

    if data in SPORT_CONFIG:

        config = SPORT_CONFIG[data]

        await query.edit_message_text(

            f"{config['icon']} "
            f"**{config['name'].upper()}**\n\n"
            "Choose an option:",

            reply_markup=date_menu(

                data,

                config["back"],

            ),

            parse_mode="Markdown",

        )

        return


    # TODAY / NEXT 7

    for prefix, config in SPORT_CONFIG.items():

        if data == f"{prefix}_today":

            date = get_uk_date()

            events = config["function"](
                date
            )


            message = build_today_message(

                config["name"],

                events,

                date,

                config["icon"],

            )


            await send_long_message(

                query,

                message,

                results_menu(

                    prefix,

                    f"worldwide_{prefix}_today",

                ),

            )

            return


        if data == f"{prefix}_next7":

            message = build_next_7_days_message(

                config["name"],

                config["function"],

                config["icon"],

            )


            await send_long_message(

                query,

                message,

                results_menu(

                    prefix,

                    f"worldwide_{prefix}_next7",

                ),

            )

            return


    # WORLDWIDE TODAY / NEXT 7

    if data.startswith(
        "worldwide_"
    ):

        clean = data.replace(
            "worldwide_",
            "",
            1,
        )


        if clean.endswith("_today"):

            prefix = clean[:-6]


            if prefix in SPORT_CONFIG:

                config = SPORT_CONFIG[
                    prefix
                ]


                events = config["function"](
                    get_uk_date()
                )


                message = build_worldwide_message(
                    events
                )


                await send_long_message(

                    query,

                    message,

                    InlineKeyboardMarkup([

                        [
                            InlineKeyboardButton(
                                "◀️ Back",
                                callback_data=f"{prefix}_today",
                            ),

                            InlineKeyboardButton(
                                "🏠 Home",
                                callback_data="home",
                            ),

                        ]

                    ]),

                )

                return


        if clean.endswith("_next7"):

            prefix = clean[:-6]


            if prefix in SPORT_CONFIG:

                config = SPORT_CONFIG[
                    prefix
                ]

                start_date = datetime.now(
                    UK_TIMEZONE
                ).date()


                events = []


                for day_number in range(7):

                    date = (

                        start_date

                        + timedelta(
                            days=day_number
                        )

                    ).strftime(
                        "%Y-%m-%d"
                    )


                    events.extend(

                        config["function"](
                            date
                        )

                    )


                message = build_worldwide_message(
                    events
                )


                await send_long_message(

                    query,

                    message,

                    InlineKeyboardMarkup([

                        [
                            InlineKeyboardButton(
                                "◀️ Back",
                                callback_data=f"{prefix}_next7",
                            ),

                            InlineKeyboardButton(
                                "🏠 Home",
                                callback_data="home",
                            ),

                        ]

                    ]),

                )

                return


    # MY ALERTS

    if data == "my_alerts":

        await query.edit_message_text(

            "🔔 **MY ALERTS**\n\n"
            "This is where personalised alerts will go.\n\n"
            "⚽ Goals\n"
            "🏎️ F1 race alerts\n"
            "🏉 Rugby alerts\n"
            "🏏 Cricket alerts\n"
            "🥊 UFC / Boxing / WWE alerts\n\n"
            "Next step: choosing exactly which "
            "sports and teams you want alerts for.",

            reply_markup=InlineKeyboardMarkup([

                nav_row("home"),

            ]),

            parse_mode="Markdown",

        )

        return


    # MY TEAMS

    if data == "my_teams":

        await query.edit_message_text(

            "⭐ **MY TEAMS**\n\n"
            "Choose and save your favourite teams.\n\n"
            "This will later power quick fixtures "
            "and personalised alerts.",

            reply_markup=InlineKeyboardMarkup([

                nav_row("home"),

            ]),

            parse_mode="Markdown",

        )

        return


    # HELP

    if data == "help":

        await query.edit_message_text(

            "ℹ️ **SPORT PULSE ALERTS**\n\n"

            "Choose a sport and competition.\n\n"

            "You can view:\n\n"

            "📅 Today's events\n"
            "➡️ Next 7 days\n"
            "📍 Event locations\n"
            "📺 TV channels\n"
            "🇬🇧 UK channels prioritised\n"
            "🌍 Worldwide channels\n"
            "🔔 Future personalised alerts",

            reply_markup=InlineKeyboardMarkup([

                nav_row("home"),

            ]),

            parse_mode="Markdown",

        )

        return


    # FALLBACK

    await query.edit_message_text(

        HOME_TEXT,

        reply_markup=main_menu(),

        parse_mode="Markdown",

    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context,
):

    logger.exception(

        "Unhandled error",

        exc_info=context.error,

    )


# ============================================================
# MAIN
# ============================================================

def main():

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

        CallbackQueryHandler(
            button_handler
        )

    )


    application.add_error_handler(
        error_handler
    )


    print(
        "Sport Pulse Alerts is running..."
    )


    application.run_polling()


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
