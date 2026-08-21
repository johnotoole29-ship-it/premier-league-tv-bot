import os
import json
import logging
import html
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

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger("SportPulseAlerts")


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

            data = json.load(file)

        if "users" not in data:
            data["users"] = {}

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


def get_uk_date():

    return uk_now().strftime(
        "%Y-%m-%d"
    )


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


def change_date(
    date_string,
    days,
):

    try:

        date_object = datetime.strptime(
            date_string,
            "%Y-%m-%d",
        )

        new_date = (
            date_object
            + timedelta(days=days)
        )

        return new_date.strftime(
            "%Y-%m-%d"
        )

    except Exception:

        return get_uk_date()


def format_match_time(event):

    event_time = (
        event.get("strTime")
        or event.get("strEventTime")
        or event.get("strTimeLocal")
    )

    if not event_time:
        return "TBC"

    return str(event_time)[:5]


# ============================================================
# SPORTS DB REQUEST
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

    logger.info(
        "SportsDB request: %s",
        endpoint,
    )

    try:

        response = requests.get(
            url,
            params=params or {},
            timeout=25,
        )

        response.raise_for_status()

        data = response.json()

        if not isinstance(data, dict):

            logger.error(
                "SportsDB returned unexpected data."
            )

            return None

        return data

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
# EVENTS
# ============================================================

def get_events_for_day(
    date,
    sport=None,
    league=None,
):

    params = {
        "d": date
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

    return (
        data.get("events")
        or []
    )


# ============================================================
# SPORT DEFINITIONS
# ============================================================

SPORTS = {

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

    events = get_events_for_day(
        date,
        sport="Soccer",
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

    return [
        event
        for event in events
        if "championship"
        in (
            event.get("strLeague")
            or ""
        ).lower()
    ]


def get_all_football(date):

    return get_events_for_day(
        date,
        sport="Soccer",
    )


# ============================================================
# RUGBY
# ============================================================

def get_rugby(date):

    events = get_events_for_day(
        date,
        sport="Rugby",
    )

    return events


# ============================================================
# GENERIC SPORTS
# ============================================================

def get_generic_sport_events(
    date,
    sport,
):

    return get_events_for_day(
        date,
        sport=sport,
    )


# ============================================================
# TV BROADCASTS
# ============================================================

def normalise_tv_item(
    broadcast
):

    if not isinstance(
        broadcast,
        dict,
    ):
        return None

    channel = (
        broadcast.get("strChannel")
        or broadcast.get("strEvent")
        or broadcast.get("strName")
        or broadcast.get("strTVStation")
        or broadcast.get("strStation")
    )

    country = (
        broadcast.get("strCountry")
        or broadcast.get("strLocation")
        or broadcast.get("strLanguage")
        or ""
    )

    if not channel:
        return None

    return {
        "channel": str(channel).strip(),
        "country": str(country).strip(),
    }


def clean_tv_channels(
    channels
):

    seen = set()

    cleaned = []

    for item in channels:

        if not item:
            continue

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

        cleaned.append(
            {
                "channel": channel,
                "country": country,
            }
        )

    return cleaned


# ============================================================
# DAILY TV FEED
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

        item = normalise_tv_item(
            broadcast
        )

        if not item:
            continue

        tv_by_event.setdefault(
            str(event_id),
            [],
        ).append(item)

    for event_id in list(
        tv_by_event.keys()
    ):

        tv_by_event[event_id] = (
            clean_tv_channels(
                tv_by_event[event_id]
            )
        )

    logger.info(
        "Daily TV feed found %s events.",
        len(tv_by_event),
    )

    return tv_by_event


# ============================================================
# INDIVIDUAL EVENT TV
# ============================================================

def get_tv_for_event(
    event
):

    event_id = (
        event.get("idEvent")
        or event.get("id")
    )

    if not event_id:
        return []

    logger.info(
        "Looking up TV for event %s",
        event_id,
    )

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

    results = []

    for broadcast in broadcasts:

        item = normalise_tv_item(
            broadcast
        )

        if item:
            results.append(
                item
            )

    results = clean_tv_channels(
        results
    )

    logger.info(
        "TV lookup for %s returned %s channels.",
        event_id,
        len(results),
    )

    return results


# ============================================================
# EVENT TV
# ============================================================

def get_event_channels(
    event,
    tv_by_event=None,
):

    event_id = str(
        event.get(
            "idEvent",
            "",
        )
    )

    # --------------------------------------------------------
    # FIRST: individual event lookup
    # --------------------------------------------------------

    channels = get_tv_for_event(
        event
    )

    if channels:
        return channels

    # --------------------------------------------------------
    # SECOND: daily TV feed
    # --------------------------------------------------------

    if tv_by_event:

        channels = tv_by_event.get(
            event_id,
            [],
        )

        if channels:
            return clean_tv_channels(
                channels
            )

    # --------------------------------------------------------
    # NOTHING FOUND
    # --------------------------------------------------------

    return []


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

    uk_countries = [
        "united kingdom",
        "uk",
        "england",
        "scotland",
        "wales",
        "northern ireland",
        "great britain",
        "britain",
    ]

    if country in uk_countries:
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
        "channel 5",

        "viaplay uk",

        "bt sport",

    ]

    return any(
        word in channel
        for word in uk_channel_words
    )


# ============================================================
# TV DISPLAY
# ============================================================

def get_uk_channels(
    event,
    tv_by_event=None,
):

    channels = get_event_channels(
        event,
        tv_by_event,
    )

    return [
        item
        for item in channels
        if is_uk_channel(item)
    ]


def get_worldwide_channels(
    event,
    tv_by_event=None,
):

    channels = get_event_channels(
        event,
        tv_by_event,
    )

    return [
        item
        for item in channels
        if not is_uk_channel(item)
    ]


def format_uk_tv(
    event,
    tv_by_event=None,
):

    channels = get_uk_channels(
        event,
        tv_by_event,
    )

    if not channels:

        return (
            "📺 <b>UK TV:</b> TBC"
        )

    lines = [
        "📺 <b>UK TV:</b>"
    ]

    for item in channels[:8]:

        lines.append(
            f"• {html.escape(item['channel'])}"
        )

    return "\n".join(
        lines
    )


# ============================================================
# EVENT NAME
# ============================================================

def get_event_title(
    event
):

    home = (
        event.get("strHomeTeam")
        or event.get("strEvent")
        or "Home"
    )

    away = (
        event.get("strAwayTeam")
        or ""
    )

    if away:

        return (
            f"{home} vs {away}"
        )

    return str(home)


# ============================================================
# MATCH CARD
# ============================================================

def create_match_card(
    event,
    tv_by_event=None,
    show_date=True,
):

    date = (
        event.get("dateEvent")
        or event.get("dateEventLocal")
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
            f"📅 <b>{html.escape(format_display_date(date))}</b>"
        )

    lines.append(
        f"🕒 <b>{html.escape(time)} UK</b>"
    )

    lines.append(
        f"⚽ <b>{html.escape(home)}</b>"
    )

    lines.append(
        "        <b>VS</b>"
    )

    lines.append(
        f"⚽ <b>{html.escape(away)}</b>"
    )

    if league:

        lines.append(
            f"🏆 {html.escape(league)}"
        )

    if venue:

        venue_text = (
            f"📍 {venue}"
        )

        if location:

            venue_text += (
                f" · {location}"
            )

        lines.append(
            html.escape(
                venue_text
            )
        )

    lines.append("")

    lines.append(
        format_uk_tv(
            event,
            tv_by_event,
        )
    )

    worldwide = get_worldwide_channels(
        event,
        tv_by_event,
    )

    if worldwide:

        lines.append("")

        lines.append(
            f"🌍 <b>{len(worldwide)} international "
            f"broadcaster"
            f"{'s' if len(worldwide) != 1 else ''} available</b>"
        )

    lines.append(
        "━━━━━━━━━━━━━━━━━━━━"
    )

    return "\n".join(
        lines
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
        "🔥 <b>SPORT PULSE ALERTS</b>\n\n"
        "Your sports TV guide in one place.\n\n"
        "⚽ Football\n"
        "🏉 Rugby\n"
        "🏏 Cricket\n"
        "🎾 Tennis\n"
        "🎯 Darts\n"
        "🏎️ Formula 1\n"
        "🏌️ Golf\n"
        "🥊 Combat\n\n"
        "📺 Find what's on TV\n"
        "🔔 Set alerts\n"
        "❤️ Follow teams\n\n"
        "👇 <b>Select a sport</b>"
    )


# ============================================================
# SPORTS MENU
# ============================================================

def sports_menu():

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
                "⬅️ Main Menu",
                callback_data="main_menu",
            ),
    ]

    ]

    return InlineKeyboardMarkup(
        keyboard
    )


# ============================================================
# FOOTBALL MENU
# ============================================================

def football_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "🏆 Premier League",
                callback_data="football:premier",
            ),
        ],

        [
            InlineKeyboardButton(
                "🏆 Championship",
                callback_data="football:championship",
            ),
        ],

        [
            InlineKeyboardButton(
                "⚽ All Football",
                callback_data="football:all",
            ),
        ],

        [
            InlineKeyboardButton(
                "⬅️ Sports",
                callback_data="back_sports",
            ),
        ],

    ]

    return InlineKeyboardMarkup(
        keyboard
    )


# ============================================================
# FIXTURE KEYBOARD
# ============================================================

def fixture_keyboard(
    sport_key,
    date,
    event_id,
):

    return InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "🌍 Worldwide TV",
                    callback_data=(
                        f"tv:{event_id}"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(
                    "🔔 Alert Me",
                    callback_data=(
                        f"alert:{event_id}"
                    ),
                ),

                InlineKeyboardButton(
                    "❤️ Follow",
                    callback_data=(
                        f"follow:{event_id}"
                    ),
                ),
            ],

        ]

    )


# ============================================================
# DATE NAVIGATION
# ============================================================

def date_navigation(
    sport_key,
    date,
):

    previous_date = change_date(
        date,
        -1,
    )

    next_date = change_date(
        date,
        1,
    )

    return [

        [

            InlineKeyboardButton(
                "◀️ Previous Day",
                callback_data=(
                    f"day:{sport_key}:{previous_date}"
                ),
            ),

            InlineKeyboardButton(
                "Next Day ▶️",
                callback_data=(
                    f"day:{sport_key}:{next_date}"
                ),
            ),

        ],

        [

            InlineKeyboardButton(
                "⬅️ Sports",
                callback_data="back_sports",
            ),

        ],

    ]


# ============================================================
# FOOTBALL DATE NAVIGATION
# ============================================================

def football_date_navigation(
    category,
    date,
):

    previous_date = change_date(
        date,
        -1,
    )

    next_date = change_date(
        date,
        1,
    )

    return [

        [

            InlineKeyboardButton(
                "◀️ Previous Day",
                callback_data=(
                    f"fday:{category}:{previous_date}"
                ),
            ),

            InlineKeyboardButton(
                "Next Day ▶️",
                callback_data=(
                    f"fday:{category}:{next_date}"
                ),
            ),

        ],

        [

            InlineKeyboardButton(
                "⬅️ Football",
                callback_data="football",
            ),

        ],

    ]


# ============================================================
# DISPLAY FOOTBALL FIXTURES
# ============================================================

async def show_football(
    query,
    category,
    date,
):

    if category == "premier":

        events = get_premier_league(
            date
        )

        title = (
            "🏆 Premier League"
        )

    elif category == "championship":

        events = get_championship(
            date
        )

        title = (
            "🏆 Championship"
        )

    else:

        events = get_all_football(
            date
        )

        title = (
            "⚽ Football"
        )

    tv_by_event = (
        get_tv_channels_for_date(
            date
        )
    )

    header = (
        f"📅 <b>{html.escape(format_display_date(date))}</b>\n"
        f"🏆 <b>{html.escape(title)}</b>\n\n"
    )

    if not events:

        text = (
            header
            + "📭 <b>No fixtures found for this date.</b>\n\n"
            + "Try the next day."
        )

        keyboard = (
            football_date_navigation(
                category,
                date,
            )
        )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
            parse_mode="HTML",
        )

        return

    # Sort by time
    events.sort(
        key=lambda event: (
            event.get("strTime")
            or "99:99"
        )
    )

    # Store current view
    query.message.chat_id

    full_text = header

    buttons = []

    for index, event in enumerate(
        events[:20],
        start=1,
    ):

        full_text += (
            f"<b>{index}.</b> "
            f"{html.escape(get_event_title(event))}\n"
        )

        full_text += (
            f"🕒 {html.escape(format_match_time(event))} UK\n"
        )

        uk_channels = get_uk_channels(
            event,
            tv_by_event,
        )

        if uk_channels:

            names = ", ".join(
                item["channel"]
                for item in uk_channels[:4]
            )

            full_text += (
                f"📺 <b>UK TV:</b> "
                f"{html.escape(names)}\n"
            )

        else:

            full_text += (
                "📺 <b>UK TV:</b> TBC\n"
            )

        full_text += "\n"

        event_id = event.get(
            "idEvent"
        )

        if event_id:

            buttons.append(

                [

                    InlineKeyboardButton(
                        (
                            f"📺 "
                            f"{get_event_title(event)[:35]}"
                        ),
                        callback_data=(
                            f"match:{event_id}"
                        ),
                    ),

                ]

            )

    buttons.extend(
        football_date_navigation(
            category,
            date,
        )
    )

    await query.edit_message_text(
        full_text,
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
        parse_mode="HTML",
    )


# ============================================================
# DISPLAY GENERIC SPORT
# ============================================================

async def show_sport(
    query,
    sport_key,
    date,
):

    config = SPORTS.get(
        sport_key
    )

    if not config:

        await query.edit_message_text(
            "❌ Sport not found.",
            reply_markup=sports_menu(),
        )

        return

    events = get_generic_sport_events(
        date,
        config["sport"],
    )

    tv_by_event = (
        get_tv_channels_for_date(
            date
        )
    )

    header = (
        f"📅 <b>{html.escape(format_display_date(date))}</b>\n"
        f"{html.escape(config['name'])}\n\n"
    )

    if not events:

        text = (
            header
            + "📭 <b>No fixtures found for this date.</b>\n\n"
            + "Try the next day."
        )

        keyboard = date_navigation(
            sport_key,
            date,
        )

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(
                keyboard
            ),
            parse_mode="HTML",
        )

        return

    events.sort(
        key=lambda event: (
            event.get("strTime")
            or "99:99"
        )
    )

    full_text = header

    buttons = []

    for index, event in enumerate(
        events[:20],
        start=1,
    ):

        title = get_event_title(
            event
        )

        full_text += (
            f"<b>{index}.</b> "
            f"{html.escape(title)}\n"
        )

        full_text += (
            f"🕒 {html.escape(format_match_time(event))} UK\n"
        )

        uk_channels = get_uk_channels(
            event,
            tv_by_event,
        )

        if uk_channels:

            names = ", ".join(
                item["channel"]
                for item in uk_channels[:4]
            )

            full_text += (
                f"📺 <b>UK TV:</b> "
                f"{html.escape(names)}\n"
            )

        else:

            full_text += (
                "📺 <b>UK TV:</b> TBC\n"
            )

        full_text += "\n"

        event_id = event.get(
            "idEvent"
        )

        if event_id:

            buttons.append(

                [

                    InlineKeyboardButton(
                        (
                            f"📺 "
                            f"{title[:35]}"
                        ),
                        callback_data=(
                            f"match:{event_id}"
                        ),
                    ),

                ]

            )

    buttons.extend(
        date_navigation(
            sport_key,
            date,
        )
    )

    await query.edit_message_text(
        full_text,
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
        parse_mode="HTML",
    )


# ============================================================
# SHOW INDIVIDUAL MATCH
# ============================================================

async def show_match(
    query,
    event_id,
):

    logger.info(
        "Opening event %s",
        event_id,
    )

    data = sportsdb_get(
        "lookupevent.php",
        {
            "id": event_id,
        },
    )

    if not data:

        await query.answer(
            "Could not load this fixture.",
            show_alert=True,
        )

        return

    events = (
        data.get("events")
        or []
    )

    if not events:

        await query.answer(
            "Fixture not found.",
            show_alert=True,
        )

        return

    event = events[0]

    tv_by_event = {}

    channels = get_event_channels(
        event,
        tv_by_event,
    )

    tv_by_event[
        str(event_id)
    ] = channels

    text = create_match_card(
        event,
        tv_by_event,
        show_date=True,
    )

    keyboard = fixture_keyboard(
        "match",
        event.get(
            "dateEvent"
            or get_uk_date()
        ),
        event_id,
    )

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# WORLDWIDE TV
# ============================================================

async def show_worldwide_tv(
    query,
    event_id,
):

    data = sportsdb_get(
        "lookupevent.php",
        {
            "id": event_id,
        },
    )

    if not data:

        await query.answer(
            "Could not load event.",
            show_alert=True,
        )

        return

    events = (
        data.get("events")
        or []
    )

    if not events:

        await query.answer(
            "Event not found.",
            show_alert=True,
        )

        return

    event = events[0]

    channels = get_event_channels(
        event,
        {},
    )

    worldwide = [
        item
        for item in channels
        if not is_uk_channel(item)
    ]

    if not worldwide:

        text = (
            "🌍 <b>WORLDWIDE TV</b>\n\n"
            "No international listings are "
            "currently available for this event."
        )

    else:

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
            "🌍 <b>WORLDWIDE TV</b>",
            "",
            f"📺 <b>{len(worldwide)} "
            f"international broadcasters</b>",
            "",
        ]

        for country, channel_list in grouped.items():

            lines.append(
                f"🌎 <b>{html.escape(country)}</b>"
            )

            for channel in channel_list[:8]:

                lines.append(
                    f"• {html.escape(channel)}"
                )

            lines.append("")

        text = "\n".join(
            lines
        ).strip()

    keyboard = InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "⬅️ Back to Fixture",
                    callback_data=(
                        f"match:{event_id}"
                    ),
                ),
            ],

        ]

    )

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# ALERT
# ============================================================

async def add_alert(
    query,
    user_id,
    event_id,
):

    user = get_user_data(
        user_id
    )

    alerts = user.setdefault(
        "alerts",
        []
    )

    event_id = str(
        event_id
    )

    if event_id not in alerts:

        alerts.append(
            event_id
        )

        save_data(
            DATA
        )

        message = (
            "🔔 <b>Alert added!</b>\n\n"
            "I'll remember this fixture "
            "for your alerts."
        )

    else:

        alerts.remove(
            event_id
        )

        save_data(
            DATA
        )

        message = (
            "🔕 <b>Alert removed.</b>"
        )

    await query.answer(
        message.replace(
            "<b>",
            ""
        ).replace(
            "</b>",
            ""
        ),
        show_alert=True,
    )


# ============================================================
# FOLLOW TEAM
# ============================================================

async def follow_event(
    query,
    user_id,
    event_id,
):

    data = sportsdb_get(
        "lookupevent.php",
        {
            "id": event_id,
        },
    )

    if not data:

        await query.answer(
            "Could not load team.",
            show_alert=True,
        )

        return

    events = (
        data.get("events")
        or []
    )

    if not events:

        await query.answer(
            "Could not load team.",
            show_alert=True,
        )

        return

    event = events[0]

    home = (
        event.get("strHomeTeam")
        or ""
    )

    away = (
        event.get("strAwayTeam")
        or ""
    )

    user = get_user_data(
        user_id
    )

    teams = user.setdefault(
        "teams",
        []
    )

    added = []

    for team in [
        home,
        away,
    ]:

        if not team:
            continue

        if team not in teams:

            teams.append(
                team
            )

            added.append(
                team
            )

    save_data(
        DATA
    )

    if added:

        message = (
            "❤️ Following: "
            + ", ".join(
                added
            )
        )

    else:

        message = (
            "❤️ You're already "
            "following these teams."
        )

    await query.answer(
        message,
        show_alert=True,
    )


# ============================================================
# MY ALERTS
# ============================================================

async def show_my_alerts(
    query,
    user_id,
):

    user = get_user_data(
        user_id
    )

    alerts = user.get(
        "alerts",
        []
    )

    if not alerts:

        text = (
            "🔔 <b>MY ALERTS</b>\n\n"
            "You don't have any alerts yet.\n\n"
            "Open a fixture and press "
            "🔔 Alert Me."
        )

    else:

        lines = [
            "🔔 <b>MY ALERTS</b>",
            "",
            f"You have <b>{len(alerts)}</b> "
            "saved alert(s).",
            "",
        ]

        for event_id in alerts[:20]:

            data = sportsdb_get(
                "lookupevent.php",
                {
                    "id": event_id,
                },
            )

            events = (
                data.get("events", [])
                if data
                else []
            )

            if events:

                event = events[0]

                lines.append(
                    f"• {html.escape(get_event_title(event))}"
                )

            else:

                lines.append(
                    f"• Event {event_id}"
                )

        text = "\n".join(
            lines
        )

    keyboard = InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "⬅️ Main Menu",
                    callback_data="main_menu",
                ),
            ],

        ]

    )

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# MY TEAMS
# ============================================================

async def show_my_teams(
    query,
    user_id,
):

    user = get_user_data(
        user_id
    )

    teams = user.get(
        "teams",
        []
    )

    if not teams:

        text = (
            "❤️ <b>MY TEAMS</b>\n\n"
            "You're not following any teams yet.\n\n"
            "Open a fixture and press "
            "❤️ Follow."
        )

    else:

        lines = [
            "❤️ <b>MY TEAMS</b>",
            "",
        ]

        for team in teams:

            lines.append(
                f"• {html.escape(team)}"
            )

        text = "\n".join(
            lines
        )

    keyboard = InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "⬅️ Main Menu",
                    callback_data="main_menu",
                ),
            ],

        ]

    )

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# STARTING SOON
# ============================================================

async def show_starting_soon(
    query,
):

    today = get_uk_date()

    events = get_all_football(
        today
    )

    now = uk_now()

    upcoming = []

    for event in events:

        date_string = (
            event.get("dateEvent")
            or today
        )

        time_string = (
            event.get("strTime")
            or "00:00:00"
        )

        try:

            event_time = datetime.strptime(
                f"{date_string} {time_string[:8]}",
                "%Y-%m-%d %H:%M:%S",
            ).replace(
                tzinfo=UK_TIMEZONE
            )

        except Exception:

            continue

        difference = (
            event_time - now
        )

        if timedelta(
            minutes=0
        ) <= difference <= timedelta(
            hours=3
        ):

            upcoming.append(
                event
            )

    tv_by_event = (
        get_tv_channels_for_date(
            today
        )
    )

    if not upcoming:

        text = (
            "⏱️ <b>STARTING SOON</b>\n\n"
            "No football fixtures are "
            "starting within the next 3 hours."
        )

    else:

        lines = [
            "⏱️ <b>STARTING SOON</b>",
            "",
        ]

        for event in upcoming[:10]:

            title = get_event_title(
                event
            )

            lines.append(
                f"⚽ <b>{html.escape(title)}</b>"
            )

            lines.append(
                f"🕒 {html.escape(format_match_time(event))} UK"
            )

            uk_channels = get_uk_channels(
                event,
                tv_by_event,
            )

            if uk_channels:

                lines.append(
                    "📺 "
                    + html.escape(
                        uk_channels[0]["channel"]
                    )
                )

            else:

                lines.append(
                    "📺 UK TV: TBC"
                )

            lines.append("")

        text = "\n".join(
            lines
        )

    keyboard = InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "⬅️ Main Menu",
                    callback_data="main_menu",
                ),
            ],

        ]

    )

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# TV NOW
# ============================================================

async def show_tv_now(
    query,
):

    date = get_uk_date()

    events = get_all_football(
        date
    )

    tv_by_event = (
        get_tv_channels_for_date(
            date
        )
    )

    tv_events = []

    for event in events:

        channels = get_uk_channels(
            event,
            tv_by_event,
        )

        if channels:

            tv_events.append(
                (
                    event,
                    channels,
                )
            )

    if not tv_events:

        text = (
            "📺 <b>ON TV NOW</b>\n\n"
            "No UK TV football listings "
            "are currently available."
        )

    else:

        lines = [
            "📺 <b>ON TV TODAY</b>",
            "",
        ]

        for event, channels in tv_events[:15]:

            title = get_event_title(
                event
            )

            channel_names = ", ".join(
                item["channel"]
                for item in channels[:3]
            )

            lines.append(
                f"⚽ <b>{html.escape(title)}</b>"
            )

            lines.append(
                f"🕒 {html.escape(format_match_time(event))} UK"
            )

            lines.append(
                f"📺 {html.escape(channel_names)}"
            )

            lines.append("")

        text = "\n".join(
            lines
        )

    keyboard = InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "⬅️ Main Menu",
                    callback_data="main_menu",
                ),
            ],

        ]

    )

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# HELP
# ============================================================

async def show_help(
    query,
):

    text = (
        "ℹ️ <b>SPORT PULSE ALERTS</b>\n\n"
        "⚽ Choose a sport to see fixtures.\n\n"
        "📺 UK TV shows British broadcasters "
        "when available.\n\n"
        "🌍 Worldwide TV shows international "
        "broadcasters.\n\n"
        "🔔 Alert Me saves a fixture to your "
        "alerts.\n\n"
        "❤️ Follow saves the teams for you.\n\n"
        "📅 Previous/Next Day lets you browse "
        "the fixture calendar."
    )

    keyboard = InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "⬅️ Main Menu",
                    callback_data="main_menu",
                ),
            ],

        ]

    )

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# PREMIUM
# ============================================================

async def show_premium(
    query,
):

    text = (
        "💎 <b>PREMIUM</b>\n\n"
        "Premium features can be added here.\n\n"
        "🚀 More alerts\n"
        "📺 Advanced TV filtering\n"
        "❤️ Unlimited followed teams\n"
        "🔔 Advanced notifications\n"
        "🌍 More international coverage"
    )

    keyboard = InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "⬅️ Main Menu",
                    callback_data="main_menu",
                ),
            ],

        ]

    )

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# SEARCH
# ============================================================

async def show_search(
    query,
):

    text = (
        "🔎 <b>SEARCH</b>\n\n"
        "Send me a team name using the "
        "message box.\n\n"
        "Example:\n"
        "<code>Arsenal</code>\n\n"
        "Search functionality can then be "
        "expanded to fixtures and TV listings."
    )

    keyboard = InlineKeyboardMarkup(

        [

            [
                InlineKeyboardButton(
                    "⬅️ Main Menu",
                    callback_data="main_menu",
                ),
            ],

        ]

    )

    await query.edit_message_text(
        text,
        reply_markup=keyboard,
        parse_mode="HTML",
    )


# ============================================================
# MAIN CALLBACK HANDLER
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    data = query.data or ""

    user_id = query.from_user.id

    logger.info(
        "Callback: %s",
        data,
    )

    # --------------------------------------------------------
    # MAIN MENU
    # --------------------------------------------------------

    if data == "main_menu":

        await query.edit_message_text(
            home_text(),
            reply_markup=main_menu(),
            parse_mode="HTML",
        )

        return

    # --------------------------------------------------------
    # SPORTS MENU
    # --------------------------------------------------------

    if data == "back_sports":

        await query.edit_message_text(
            "🏆 <b>SPORTS</b>\n\n"
            "Choose a sport:",
            reply_markup=sports_menu(),
            parse_mode="HTML",
        )

        return

    # --------------------------------------------------------
    # FOOTBALL MENU
    # --------------------------------------------------------

    if data == "football":

        await query.edit_message_text(
            "⚽ <b>FOOTBALL</b>\n\n"
            "Choose a competition:",
            reply_markup=football_menu(),
            parse_mode="HTML",
        )

        return

    # --------------------------------------------------------
    # FOOTBALL CATEGORIES
    # --------------------------------------------------------

    if data.startswith(
        "football:"
    ):

        category = data.split(
            ":",
            1,
        )[1]

        await show_football(
            query,
            category,
            get_uk_date(),
        )

        return

    # --------------------------------------------------------
    # FOOTBALL DATE
    # --------------------------------------------------------

    if data.startswith(
        "fday:"
    ):

        parts = data.split(
            ":"
        )

        if len(parts) != 3:
            return

        category = parts[1]
        date = parts[2]

        await show_football(
            query,
            category,
            date,
        )

        return

    # --------------------------------------------------------
    # GENERIC SPORTS
    # --------------------------------------------------------

    if data in SPORTS:

        await show_sport(
            query,
            data,
            get_uk_date(),
        )

        return

    # --------------------------------------------------------
    # GENERIC SPORT DATE
    # --------------------------------------------------------

    if data.startswith(
        "day:"
    ):

        parts = data.split(
            ":"
        )

        if len(parts) != 3:
            return

        sport_key = parts[1]
        date = parts[2]

        await show_sport(
            query,
            sport_key,
            date,
        )

        return

    # --------------------------------------------------------
    # INDIVIDUAL MATCH
    # --------------------------------------------------------

    if data.startswith(
        "match:"
    ):

        event_id = data.split(
            ":",
            1,
        )[1]

        await show_match(
            query,
            event_id,
        )

        return

    # --------------------------------------------------------
    # WORLDWIDE TV
    # --------------------------------------------------------

    if data.startswith(
        "tv:"
    ):

        event_id = data.split(
            ":",
            1,
        )[1]

        await show_worldwide_tv(
            query,
            event_id,
        )

        return

    # --------------------------------------------------------
    # ALERT
    # --------------------------------------------------------

    if data.startswith(
        "alert:"
    ):

        event_id = data.split(
            ":",
            1,
        )[1]

        await add_alert(
            query,
            user_id,
            event_id,
        )

        return

    # --------------------------------------------------------
    # FOLLOW
    # --------------------------------------------------------

    if data.startswith(
        "follow:"
    ):

        event_id = data.split(
            ":",
            1,
        )[1]

        await follow_event(
            query,
            user_id,
            event_id,
        )

        return

    # --------------------------------------------------------
    # OTHER MENUS
    # --------------------------------------------------------

    if data == "tv_now":

        await show_tv_now(
            query
        )

        return

    if data == "starting_soon":

        await show_starting_soon(
            query
        )

        return

    if data == "my_alerts":

        await show_my_alerts(
            query,
            user_id,
        )

        return

    if data == "my_teams":

        await show_my_teams(
            query,
            user_id,
        )

        return

    if data == "premium":

        await show_premium(
            query
        )

        return

    if data == "help":

        await show_help(
            query
        )

        return

    if data == "search":

        await show_search(
            query
        )

        return

    # --------------------------------------------------------
    # UNKNOWN CALLBACK
    # --------------------------------------------------------

    logger.warning(
        "Unknown callback received: %s",
        data,
    )

    await query.edit_message_text(
        "⚠️ <b>Menu option unavailable.</b>\n\n"
        "Please return to the main menu.",
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "🏠 Main Menu",
                        callback_data="main_menu",
                    )
                ]
            ]
        ),
        parse_mode="HTML",
    )


# ============================================================
# /START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    get_user_data(
        update.effective_user.id
    )

    await update.message.reply_text(
        home_text(),
        reply_markup=main_menu(),
        parse_mode="HTML",
    )


# ============================================================
# /HELP
# ============================================================

async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "ℹ️ <b>SportPulseAlerts</b>\n\n"
        "Use /start to open the main menu.",
        parse_mode="HTML",
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Unhandled exception:",
        exc_info=context.error,
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
        CommandHandler(
            "help",
            help_command,
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
        "SportPulseAlerts is now running."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
