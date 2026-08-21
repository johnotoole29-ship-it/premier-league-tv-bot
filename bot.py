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

UK_TIMEZONE = ZoneInfo("Europe/London")

SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"

MAX_TELEGRAM_LENGTH = 4000


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
                "🏀 Basketball",
                callback_data="basketball",
            ),
        ],

        [
            InlineKeyboardButton(
                "🎾 Tennis",
                callback_data="tennis",
            ),
            InlineKeyboardButton(
                "🎯 Darts",
                callback_data="darts",
            ),
        ],

        [
            InlineKeyboardButton(
                "🏎️ Formula 1",
                callback_data="f1",
            ),
            InlineKeyboardButton(
                "🥊 Combat",
                callback_data="combat",
            ),
        ],

        [
            InlineKeyboardButton(
                "🏌️ Golf",
                callback_data="golf",
            ),
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# FOOTBALL MENU
# ============================================================

def football_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "🏆 Premier League",
                callback_data="premier_league",
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
                "🔙 Back",
                callback_data="back",
            ),
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# LEAGUE MENU
# ============================================================

def league_menu(prefix, back_callback):

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 Today",
                callback_data=f"{prefix}_today",
            ),
        ],

        [
            InlineKeyboardButton(
                "➡️ Next 7 Days",
                callback_data=f"{prefix}_next7",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data=back_callback,
            ),
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# RUGBY MENU
# ============================================================

def rugby_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "🏉 Rugby Union",
                callback_data="rugby_union",
            ),
        ],

        [
            InlineKeyboardButton(
                "🏉 Super League",
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
                "🔙 Back",
                callback_data="back",
            ),
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# GENERIC SPORT MENU
# ============================================================

def sport_menu(sport, back_callback="back"):

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 Today",
                callback_data=f"today_{sport}",
            ),
        ],

        [
            InlineKeyboardButton(
                "➡️ Next 7 Days",
                callback_data=f"next7_{sport}",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data=back_callback,
            ),
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# COMBAT MENU
# ============================================================

def combat_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "🥊 UFC",
                callback_data="ufc",
            ),
        ],

        [
            InlineKeyboardButton(
                "🥊 Boxing",
                callback_data="boxing",
            ),
        ],

        [
            InlineKeyboardButton(
                "🤼 WWE",
                callback_data="wwe",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back",
            ),
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# UPCOMING EVENTS MENU
# ============================================================

def upcoming_menu(sport, back_callback):

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 Upcoming Events",
                callback_data=f"{sport}_upcoming",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data=back_callback,
            ),
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# UK DATE
# ============================================================

def get_uk_date():

    return datetime.now(
        UK_TIMEZONE
    ).strftime("%Y-%m-%d")


# ============================================================
# DISPLAY DATE
# ============================================================

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


# ============================================================
# THESPORTSDB REQUEST
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
# GET EVENTS FOR DAY
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


# ============================================================
# PREMIER LEAGUE
# ============================================================

def get_premier_league_matches(date):

    return get_events_for_day(
        date,
        sport="Soccer",
        league="English Premier League",
    )


# ============================================================
# CHAMPIONSHIP
# ============================================================

def get_championship_matches(date):

    return get_events_for_day(
        date,
        sport="Soccer",
        league="English League Championship",
    )


# ============================================================
# RUGBY UNION
# ============================================================

def get_rugby_union_events(date):

    return get_events_for_day(
        date,
        sport="Rugby",
    )


# ============================================================
# SUPER LEAGUE
# ============================================================

def get_super_league_events(date):

    return get_events_for_day(
        date,
        sport="Rugby",
        league="Super League",
    )


# ============================================================
# NRL
# ============================================================

def get_nrl_events(date):

    return get_events_for_day(
        date,
        sport="Rugby",
        league="NRL",
    )


# ============================================================
# GENERIC SPORT EVENTS
# ============================================================

def get_sport_events(
    date,
    sport,
):

    return get_events_for_day(
        date,
        sport=sport,
    )


# ============================================================
# TV CHANNELS
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

        event_id = broadcast.get("idEvent")

        if not event_id:
            continue

        channel = (
            broadcast.get("strChannel")
            or broadcast.get("strEvent")
        )

        country = (
            broadcast.get("strCountry")
            or ""
        )

        if not channel:
            continue

        item = {
            "channel": channel.strip(),
            "country": country.strip(),
        }

        tv_by_event.setdefault(
            str(event_id),
            [],
        ).append(item)

    return tv_by_event


# ============================================================
# CLEAN TV CHANNELS
# ============================================================

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
# UK CHANNEL CHECK
# ============================================================

def is_uk_channel(item):

    country = (
        item.get(
            "country",
            "",
        ).lower()
    )

    channel = (
        item.get(
            "channel",
            "",
        ).lower()
    )

    uk_words = [

        "united kingdom",
        "uk",
        "england",
        "britain",

        "sky sports",
        "tnt sports",
        "bbc",
        "itv",
        "channel 4",
        "channel 5",
        "premier sports",

    ]

    for word in uk_words:

        if word in country:
            return True

        if word in channel:
            return True

    return False


# ============================================================
# FORMAT TV CHANNELS
# ============================================================

def format_tv_channels(
    event,
    tv_by_event,
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

    channels = clean_tv_channels(
        channels
    )

    if not channels:

        return "📺 TV information unavailable"

    uk_channels = []
    international_channels = []

    for item in channels:

        if is_uk_channel(item):

            uk_channels.append(item)

        else:

            international_channels.append(item)

    lines = []

    # UK CHANNELS FIRST

    if uk_channels:

        uk_names = []

        for item in uk_channels[:3]:

            channel = item["channel"]

            if channel not in uk_names:

                uk_names.append(channel)

        lines.append(
            "🇬🇧 " + " • ".join(uk_names)
        )

    # INTERNATIONAL CHANNELS

    if international_channels:

        international_names = []

        for item in international_channels[:5]:

            channel = item["channel"]
            country = item["country"]

            if country:

                text = (
                    f"{channel} ({country})"
                )

            else:

                text = channel

            international_names.append(text)

        lines.append(
            "🌍 " + " • ".join(
                international_names
            )
        )

    return "\n".join(lines)

# ============================================================
# MATCH TIME - CONVERT TO UK TIME
# ============================================================

def format_match_time(event):

    event_date = event.get("dateEvent")
    event_time = event.get("strTime")

    if not event_date or not event_time:
        return "Time TBC"

    try:

        # Remove anything after seconds, if present
        clean_time = event_time[:8]

        # TheSportsDB times are treated as UTC
        utc_datetime = datetime.strptime(
            f"{event_date} {clean_time}",
            "%Y-%m-%d %H:%M:%S",
        ).replace(
            tzinfo=ZoneInfo("UTC")
        )

        # Convert to UK time automatically
        uk_datetime = utc_datetime.astimezone(
            UK_TIMEZONE
        )

        return uk_datetime.strftime("%H:%M")

    except Exception as error:

        logger.error(
            "Could not convert match time: %s",
            error,
        )

        return event_time[:5]


# ============================================================
# EVENT NAME
# ============================================================

def get_event_name(event):

    home_team = (
        event.get("strHomeTeam")
        or ""
    )

    away_team = (
        event.get("strAwayTeam")
        or ""
    )

    if home_team and away_team:

        return (
            f"{home_team} vs {away_team}"
        )

    return (
        event.get("strEvent")
        or event.get("strEventAlternate")
        or "Event details unavailable"
    )


# ============================================================
# EVENT BLOCK
# ============================================================

def create_event_block(
    event,
    tv_by_event,
    icon="⚽",
):

    event_name = get_event_name(
        event
    )

    event_time = format_match_time(
        event
    )

    tv = format_tv_channels(
        event,
        tv_by_event,
    )

    return (
        f"🕒 **{event_time}**\n"
        f"{icon} **{event_name}**\n"
        f"{tv}"
    )


# ============================================================
# SORT EVENTS
# ============================================================

def sort_events(events):

    return sorted(
        events,
        key=lambda event: (
            event.get(
                "dateEvent"
            )
            or "9999-99-99",

            event.get(
                "strTime"
            )
            or "99:99",
        )
    )


# ============================================================
# BUILD TODAY MESSAGE
# ============================================================

def build_today_message(
    title,
    events,
    date,
    icon="⚽",
):

    if not events:

        return (
            f"{icon} **{title.upper()}**\n\n"
            f"📅 **{format_display_date(date)}**\n\n"
            "No events found today."
        )

    tv_by_event = (
        get_tv_channels_for_date(date)
    )

    events = sort_events(events)

    message = (
        f"{icon} **{title.upper()}**\n\n"
        f"📅 **{format_display_date(date)}**\n\n"
    )

    for index, event in enumerate(events):

        message += create_event_block(
            event,
            tv_by_event,
            icon,
        )

        if index < len(events) - 1:

            message += (
                "\n\n──────────────\n\n"
            )

    return message


# ============================================================
# BUILD NEXT 7 DAYS MESSAGE
# ============================================================

def build_next_7_days_message(
    title,
    get_events_function,
    icon="⚽",
):

    start = datetime.now(
        UK_TIMEZONE
    ).date()

    all_events = []

    tv_cache = {}

    for day_number in range(7):

        current_day = (
            start
            + timedelta(days=day_number)
        )

        date = current_day.strftime(
            "%Y-%m-%d"
        )

        events = get_events_function(
            date
        )

        if events:

            all_events.extend(events)

            tv_cache[date] = (
                get_tv_channels_for_date(date)
            )

    if not all_events:

        return (
            f"{icon} **{title.upper()}**\n\n"
            "➡️ **NEXT 7 DAYS**\n\n"
            "No upcoming events found."
        )

    all_events = sort_events(
        all_events
    )

    message = (
        f"{icon} **{title.upper()}**\n\n"
        "➡️ **NEXT 7 DAYS**\n\n"
    )

    current_date = None

    for event in all_events:

        event_date = event.get(
            "dateEvent"
        )

        if event_date != current_date:

            if current_date is not None:

                message += "\n"

            current_date = event_date

            message += (
                f"📅 **{format_display_date(event_date)}**"
                "\n\n"
            )

        message += create_event_block(
            event,
            tv_cache.get(
                event_date,
                {},
            ),
            icon,
        )

        message += (
            "\n\n──────────────\n\n"
        )

    return message.rstrip()


# ============================================================
# UPCOMING EVENTS
# ============================================================

def get_upcoming_events_by_sport(
    sport_name,
    days=14,
):

    start = datetime.now(
        UK_TIMEZONE
    ).date()

    all_events = []

    for day_number in range(days):

        current_day = (
            start
            + timedelta(days=day_number)
        )

        date = current_day.strftime(
            "%Y-%m-%d"
        )

        events = get_sport_events(
            date,
            sport_name,
        )

        all_events.extend(events)

    return sort_events(
        all_events
    )


# ============================================================
# SPLIT LONG TELEGRAM MESSAGES
# ============================================================

async def send_long_message(
    query,
    text,
    reply_markup=None,
):

    if len(text) <= MAX_TELEGRAM_LENGTH:

        await query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        return

    chunks = []

    current_chunk = ""

    lines = text.split("\n")

    for line in lines:

        if (
            len(current_chunk)
            + len(line)
            + 1
            > MAX_TELEGRAM_LENGTH
        ):

            chunks.append(
                current_chunk
            )

            current_chunk = ""

        current_chunk += (
            line + "\n"
        )

    if current_chunk:

        chunks.append(
            current_chunk
        )

    await query.edit_message_text(
        chunks[0],
        parse_mode="Markdown",
    )

    for chunk in chunks[1:]:

        await query.message.reply_text(
            chunk,
            parse_mode="Markdown",
        )

    if reply_markup:

        await query.message.reply_text(
            "⬇️ Continue using the menu:",
            reply_markup=reply_markup,
        )


# ============================================================
# START COMMAND
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(

        "🔥 **SportPulseAlerts**\n\n"
        "Select a sport:",

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


    # ========================================================
    # BACK
    # ========================================================

    if data == "back":

        await query.edit_message_text(

            "🔥 **SportPulseAlerts**\n\n"
            "Select a sport:",

            reply_markup=main_menu(),

            parse_mode="Markdown",
        )

        return


    # ========================================================
    # MAIN SPORT MENUS
    # ========================================================

    if data == "football":

        await query.edit_message_text(

            "⚽ **FOOTBALL**\n\n"
            "Choose a competition:",

            reply_markup=football_menu(),

            parse_mode="Markdown",
        )

        return


    if data == "rugby":

        await query.edit_message_text(

            "🏉 **RUGBY**\n\n"
            "Choose a competition:",

            reply_markup=rugby_menu(),

            parse_mode="Markdown",
        )

        return


    if data == "combat":

        await query.edit_message_text(

            "🥊 **COMBAT SPORTS**\n\n"
            "Choose a sport:",

            reply_markup=combat_menu(),

            parse_mode="Markdown",
        )

        return


    # ========================================================
    # FOOTBALL COMPETITIONS
    # ========================================================

    if data == "premier_league":

        await query.edit_message_text(

            "⚽ **PREMIER LEAGUE**\n\n"
            "Choose an option:",

            reply_markup=league_menu(
                "premier",
                "football",
            ),

            parse_mode="Markdown",
        )

        return


    if data == "championship":

        await query.edit_message_text(

            "⚽ **CHAMPIONSHIP**\n\n"
            "Choose an option:",

            reply_markup=league_menu(
                "championship",
                "football",
            ),

            parse_mode="Markdown",
        )

        return


    # ========================================================
    # RUGBY COMPETITIONS
    # ========================================================

    if data == "rugby_union":

        await query.edit_message_text(

            "🏉 **RUGBY UNION**\n\n"
            "Choose an option:",

            reply_markup=league_menu(
                "rugby_union",
                "rugby",
            ),

            parse_mode="Markdown",
        )

        return


    if data == "super_league":

        await query.edit_message_text(

            "🏉 **SUPER LEAGUE**\n\n"
            "Choose an option:",

            reply_markup=league_menu(
                "super_league",
                "rugby",
            ),

            parse_mode="Markdown",
        )

        return


    if data == "nrl":

        await query.edit_message_text(

            "🇦🇺 **NRL**\n\n"
            "Choose an option:",

            reply_markup=league_menu(
                "nrl",
                "rugby",
            ),

            parse_mode="Markdown",
        )

        return


    # ========================================================
    # GENERIC SPORT MENUS
    # ========================================================

    generic_sports = {

        "cricket": (
            "🏏 CRICKET",
            "Cricket",
            "🏏",
        ),

        "basketball": (
            "🏀 BASKETBALL",
            "Basketball",
            "🏀",
        ),

        "tennis": (
            "🎾 TENNIS",
            "Tennis",
            "🎾",
        ),

        "darts": (
            "🎯 DARTS",
            "Darts",
            "🎯",
        ),

        "f1": (
            "🏎️ FORMULA 1",
            "Motorsport",
            "🏎️",
        ),

    }


    if data in generic_sports:

        title, _, icon = generic_sports[data]

        await query.edit_message_text(

            f"{icon} **{title}**\n\n"
            "Choose an option:",

            reply_markup=sport_menu(data),

            parse_mode="Markdown",
        )

        return


    # ========================================================
    # COMBAT MENUS
    # ========================================================

    if data == "ufc":

        await query.edit_message_text(

            "🥊 **UFC**\n\n"
            "View upcoming events:",

            reply_markup=upcoming_menu(
                "ufc",
                "combat",
            ),

            parse_mode="Markdown",
        )

        return


    if data == "boxing":

        await query.edit_message_text(

            "🥊 **BOXING**\n\n"
            "View upcoming events:",

            reply_markup=upcoming_menu(
                "boxing",
                "combat",
            ),

            parse_mode="Markdown",
        )

        return


    if data == "wwe":

        await query.edit_message_text(

            "🤼 **WWE**\n\n"
            "View upcoming events:",

            reply_markup=upcoming_menu(
                "wwe",
                "combat",
            ),

            parse_mode="Markdown",
        )

        return


    if data == "golf":

        await query.edit_message_text(

            "🏌️ **GOLF**\n\n"
            "View upcoming events:",

            reply_markup=upcoming_menu(
                "golf",
                "back",
            ),

            parse_mode="Markdown",
        )

        return


    # ========================================================
    # PREMIER LEAGUE TODAY
    # ========================================================

    if data == "premier_today":

        date = get_uk_date()

        events = get_premier_league_matches(
            date
        )

        message = build_today_message(

            "Premier League",
            events,
            date,
            "⚽",

        )

        await send_long_message(
            query,
            message,
            league_menu(
                "premier",
                "football",
            ),
        )

        return


    # ========================================================
    # PREMIER LEAGUE NEXT 7 DAYS
    # ========================================================

    if data == "premier_next7":

        message = build_next_7_days_message(

            "Premier League",
            get_premier_league_matches,
            "⚽",

        )

        await send_long_message(
            query,
            message,
            league_menu(
                "premier",
                "football",
            ),
        )

        return


    # ========================================================
    # CHAMPIONSHIP TODAY
    # ========================================================

    if data == "championship_today":

        date = get_uk_date()

        events = get_championship_matches(
            date
        )

        message = build_today_message(

            "Championship",
            events,
            date,
            "⚽",

        )

        await send_long_message(
            query,
            message,
            league_menu(
                "championship",
                "football",
            ),
        )

        return


    # ========================================================
    # CHAMPIONSHIP NEXT 7 DAYS
    # ========================================================

    if data == "championship_next7":

        message = build_next_7_days_message(

            "Championship",
            get_championship_matches,
            "⚽",

        )

        await send_long_message(
            query,
            message,
            league_menu(
                "championship",
                "football",
            ),
        )

        return


    # ========================================================
    # RUGBY CONFIG
    # ========================================================

    rugby_events = {

        "rugby_union": (
            "Rugby Union",
            get_rugby_union_events,
            "🏉",
        ),

        "super_league": (
            "Super League",
            get_super_league_events,
            "🏉",
        ),

        "nrl": (
            "NRL",
            get_nrl_events,
            "🇦🇺",
        ),

    }


    # ========================================================
    # RUGBY TODAY / NEXT 7
    # ========================================================

    for prefix, details in rugby_events.items():

        title, event_function, icon = details

        if data == f"{prefix}_today":

            date = get_uk_date()

            events = event_function(
                date
            )

            message = build_today_message(

                title,
                events,
                date,
                icon,

            )

            await send_long_message(

                query,
                message,
                league_menu(
                    prefix,
                    "rugby",
                ),

            )

            return


        if data == f"{prefix}_next7":

            message = build_next_7_days_message(

                title,
                event_function,
                icon,

            )

            await send_long_message(

                query,
                message,
                league_menu(
                    prefix,
                    "rugby",
                ),

            )

            return


    # ========================================================
    # GENERIC SPORT TODAY / NEXT 7
    # ========================================================

    sport_config = {

        "cricket": (
            "Cricket",
            "Cricket",
            "🏏",
        ),

        "basketball": (
            "Basketball",
            "Basketball",
            "🏀",
        ),

        "tennis": (
            "Tennis",
            "Tennis",
            "🎾",
        ),

        "darts": (
            "Darts",
            "Darts",
            "🎯",
        ),

        "f1": (
            "Formula 1",
            "Motorsport",
            "🏎️",
        ),

    }


    for prefix, details in sport_config.items():

        title, sport_name, icon = details

        if data == f"today_{prefix}":

            date = get_uk_date()

            events = get_sport_events(
                date,
                sport_name,
            )

            message = build_today_message(

                title,
                events,
                date,
                icon,

            )

            await send_long_message(

                query,
                message,
                sport_menu(prefix),

            )

            return


        if data == f"next7_{prefix}":

            def event_function(
                date,
                selected_sport=sport_name,
            ):

                return get_sport_events(
                    date,
                    selected_sport,
                )

            message = build_next_7_days_message(

                title,
                event_function,
                icon,

            )

            await send_long_message(

                query,
                message,
                sport_menu(prefix),

            )

            return


    # ========================================================
    # UPCOMING UFC
    # ========================================================

    if data == "ufc_upcoming":

        events = get_upcoming_events_by_sport(
            "Fighting"
        )

        message = build_upcoming_message(
            "UFC",
            events,
            "🥊",
        )

        await send_long_message(

            query,
            message,
            upcoming_menu(
                "ufc",
                "combat",
            ),

        )

        return


    # ========================================================
    # UPCOMING BOXING
    # ========================================================

    if data == "boxing_upcoming":

        events = get_upcoming_events_by_sport(
            "Boxing"
        )

        message = build_upcoming_message(
            "Boxing",
            events,
            "🥊",
        )

        await send_long_message(

            query,
            message,
            upcoming_menu(
                "boxing",
                "combat",
            ),

        )

        return


    # ========================================================
    # UPCOMING WWE
    # ========================================================

    if data == "wwe_upcoming":

        events = get_upcoming_events_by_sport(
            "Wrestling"
        )

        message = build_upcoming_message(
            "WWE",
            events,
            "🤼",
        )

        await send_long_message(

            query,
            message,
            upcoming_menu(
                "wwe",
                "combat",
            ),

        )

        return


    # ========================================================
    # UPCOMING GOLF
    # ========================================================

    if data == "golf_upcoming":

        events = get_upcoming_events_by_sport(
            "Golf"
        )

        message = build_upcoming_message(
            "Golf",
            events,
            "🏌️",
        )

        await send_long_message(

            query,
            message,
            upcoming_menu(
                "golf",
                "back",
            ),

        )

        return


# ============================================================
# BUILD UPCOMING MESSAGE
# ============================================================

def build_upcoming_message(
    title,
    events,
    icon,
):

    if not events:

        return (
            f"{icon} **{title.upper()}**\n\n"
            "No upcoming events found."
        )

    message = (
        f"{icon} **{title.upper()}**\n\n"
        "📅 **UPCOMING EVENTS**\n\n"
    )

    current_date = None

    for event in events[:30]:

        event_date = (
            event.get(
                "dateEvent"
            )
        )

        if event_date != current_date:

            current_date = event_date

            message += (
                f"📅 **{format_display_date(event_date)}**\n\n"
            )

        event_time = format_match_time(
            event
        )

        event_name = get_event_name(
            event
        )

        venue = (
            event.get("strVenue")
            or ""
        )

        message += (
            f"🕒 **{event_time}**\n"
            f"{icon} **{event_name}**"
        )

        if venue:

            message += (
                f"\n📍 {venue}"
            )

        message += (
            "\n\n──────────────\n\n"
        )

    return message.rstrip()


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context,
):

    logger.exception(
        "Exception while handling update:",
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
        "SportPulseAlerts Bot is running..."
    )

    application.run_polling()


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":
    main()
