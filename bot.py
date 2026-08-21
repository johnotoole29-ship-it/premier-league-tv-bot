import os
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import requests

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

MAX_MESSAGE_LENGTH = 4000


# ============================================================
# EXACT THESPORTSDB LEAGUE IDS
# ============================================================

LEAGUES = {
    "premier": "4328",
    "championship": "4329",

    "super_league": "4415",
    "nrl": "4416",

    "f1": "4370",

    "ufc": "4443",
    "wwe": "4444",
    "boxing": "4445",
}


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
# HOME TEXT
# ============================================================

HOME_TEXT = (
    "🔥 **SPORT PULSE ALERTS**\n\n"
    "Your sports hub for fixtures, upcoming events "
    "and worldwide TV channels.\n\n"
    "👇 **Select a sport to get started**"
)


# ============================================================
# MENU HELPERS
# ============================================================

def navigation_row(back_callback="home"):

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
                "🏌️ Golf",
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
                "💎 Premium",
                callback_data="premium",
            ),

            InlineKeyboardButton(
                "ℹ️ Help",
                callback_data="help",
            ),
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


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

        navigation_row("home"),

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

        navigation_row("home"),

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

        navigation_row("home"),

    ])


# ============================================================
# TODAY / NEXT 7 MENU
# ============================================================

def league_menu(prefix, back_callback):

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

        navigation_row(back_callback),

    ])


def sport_menu(prefix, back_callback="home"):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📅 Today",
                callback_data=f"today_{prefix}",
            )
        ],

        [
            InlineKeyboardButton(
                "➡️ Next 7 Days",
                callback_data=f"next7_{prefix}",
            )
        ],

        navigation_row(back_callback),

    ])


# ============================================================
# UPCOMING MENU
# ============================================================

def upcoming_menu(prefix, back_callback):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "📅 Upcoming Events",
                callback_data=f"{prefix}_upcoming",
            )
        ],

        navigation_row(back_callback),

    ])


# ============================================================
# RESULTS MENU
# ============================================================

def results_menu(back_callback, worldwide_callback):

    return InlineKeyboardMarkup([

        [
            InlineKeyboardButton(
                "🌍 Show Worldwide Channels",
                callback_data=worldwide_callback,
            )
        ],

        navigation_row(back_callback),

    ])


# ============================================================
# UK DATE
# ============================================================

def get_uk_date():

    return datetime.now(
        UK_TIMEZONE
    ).strftime(
        "%Y-%m-%d"
    )


# ============================================================
# DISPLAY DATE
# ============================================================

def format_display_date(date_string):

    try:

        return datetime.strptime(
            date_string,
            "%Y-%m-%d",
        ).strftime(
            "%A %d %B %Y"
        )

    except Exception:

        return date_string or "Date TBC"


# ============================================================
# UK EVENT TIME
# ============================================================

def format_event_time(event):

    timestamp = event.get(
        "strTimestamp"
    )

    if timestamp:

        try:

            value = timestamp.replace(
                "Z",
                "+00:00",
            )

            event_datetime = datetime.fromisoformat(
                value
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

            clean_time = (
                event_time
                .split("+")[0]
                .split("Z")[0]
            )

            clean_time = clean_time[:8]

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


    return "Time TBC"


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
# EVENTS BY DAY
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


    return data.get(
        "events"
    ) or []


# ============================================================
# EXACT LEAGUE LOOKUPS
# ============================================================

def get_premier_league_matches(date):

    return get_events_for_day(
        date,
        league_id=LEAGUES["premier"],
    )


def get_championship_matches(date):

    return get_events_for_day(
        date,
        league_id=LEAGUES["championship"],
    )


def get_super_league_events(date):

    return get_events_for_day(
        date,
        league_id=LEAGUES["super_league"],
    )


def get_nrl_events(date):

    return get_events_for_day(
        date,
        league_id=LEAGUES["nrl"],
    )


def get_f1_events(date):

    return get_events_for_day(
        date,
        league_id=LEAGUES["f1"],
    )


def get_ufc_events(date):

    return get_events_for_day(
        date,
        league_id=LEAGUES["ufc"],
    )


def get_boxing_events(date):

    return get_events_for_day(
        date,
        league_id=LEAGUES["boxing"],
    )


def get_wwe_events(date):

    return get_events_for_day(
        date,
        league_id=LEAGUES["wwe"],
    )


# ============================================================
# RUGBY UNION
# ============================================================

def get_rugby_union_events(date):

    events = get_events_for_day(
        date,
        sport="Rugby",
    )

    excluded_leagues = {

        "English Rugby League Super League",

        "Australian National Rugby League",

    }

    return [

        event

        for event in events

        if event.get(
            "strLeague"
        ) not in excluded_leagues

    ]


# ============================================================
# GENERIC SPORTS
# ============================================================

def get_cricket_events(date):

    return get_events_for_day(
        date,
        sport="Cricket",
    )


def get_tennis_events(date):

    return get_events_for_day(
        date,
        sport="Tennis",
    )


def get_darts_events(date):

    return get_events_for_day(
        date,
        sport="Darts",
    )


def get_golf_events(date):

    return get_events_for_day(
        date,
        sport="Golf",
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

        event_id = broadcast.get(
            "idEvent"
        )

        channel = (

            broadcast.get(
                "strChannel"
            )

            or broadcast.get(
                "strEvent"
            )

        )

        country = (
            broadcast.get(
                "strCountry"
            )
            or ""
        )


        if not event_id or not channel:

            continue


        tv_by_event.setdefault(
            str(event_id),
            [],
        ).append({

            "channel": channel,

            "country": country,

        })


    return tv_by_event


# ============================================================
# WORLDWIDE TV CHANNELS
# ============================================================

def get_worldwide_channels(events):

    channels_by_date = {}

    tv_cache = {}


    for event in events:

        event_date = event.get(
            "dateEvent"
        )

        if not event_date:

            continue


        if event_date not in tv_cache:

            tv_cache[event_date] = (
                get_tv_channels_for_date(
                    event_date
                )
            )


        event_id = str(
            event.get(
                "idEvent"
            )
            or ""
        )


        channels = tv_cache[
            event_date
        ].get(
            event_id,
            [],
        )


        if channels:

            channels_by_date.setdefault(
                event_date,
                [],
            ).extend(
                channels
            )


    return channels_by_date


def build_worldwide_message(events):

    channels_by_date = (
        get_worldwide_channels(
            events
        )
    )


    if not channels_by_date:

        return (
            "🌍 **WORLDWIDE TV CHANNELS**\n\n"
            "No worldwide TV information is currently available."
        )


    lines = [

        "🌍 **WORLDWIDE TV CHANNELS**",

        "",

    ]


    for event_date in sorted(
        channels_by_date
    ):

        lines.append(
            f"📅 **{format_display_date(event_date)}**"
        )

        lines.append("")


        grouped = {}


        for item in channels_by_date[
            event_date
        ]:

            country = (
                item["country"]
                or "International"
            )

            grouped.setdefault(
                country,
                [],
            ).append(
                item["channel"]
            )


        for country in sorted(
            grouped
        ):

            unique_channels = []


            for channel in grouped[country]:

                if channel not in unique_channels:

                    unique_channels.append(
                        channel
                    )


            lines.append(
                f"🌍 **{country}**"
            )


            for channel in unique_channels[:20]:

                lines.append(
                    f"• {channel}"
                )


            lines.append("")


    return "\n".join(
        lines
    ).strip()


# ============================================================
# EVENT FORMATTING
# ============================================================

def event_title(event):

    if event.get(
        "strEvent"
    ):

        return event.get(
            "strEvent"
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


    return f"{home} vs {away}"


def event_location(event):

    parts = []


    for value in [

        event.get("strVenue"),

        event.get("strCity"),

        event.get("strCountry"),

    ]:

        if value and value not in parts:

            parts.append(value)


    return " • ".join(parts)


def build_event_block(
    event,
    icon,
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


    return "\n".join(
        lines
    )


def sort_events(events):

    return sorted(

        events,

        key=lambda event: (

            event.get(
                "dateEvent"
            )
            or "9999-99-99",

            event.get(
                "strTimestamp"
            )
            or "",

            event.get(
                "strTime"
            )
            or "99:99",

        ),

    )


# ============================================================
# TODAY MESSAGE
# ============================================================

def build_today_message(
    title,
    events,
    date,
    icon,
):

    lines = [

        f"{icon} **{title.upper()}**",

        "",

        f"📅 **{format_display_date(date)}**",

        "",

    ]


    if not events:

        lines.append(
            "No events found."
        )

        return "\n".join(
            lines
        )


    for event in sort_events(
        events
    ):

        lines.append(
            build_event_block(
                event,
                icon,
            )
        )

        lines.append("")


    return "\n".join(
        lines
    ).strip()


# ============================================================
# NEXT 7 DAYS
# ============================================================

def build_next_7_days_message(
    title,
    event_function,
    icon,
):

    start = datetime.now(
        UK_TIMEZONE
    ).date()


    all_events = []


    for day_number in range(7):

        date = (

            start

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


    for event in sort_events(
        all_events
    ):

        event_date = event.get(
            "dateEvent"
        )


        if event_date != current_date:

            current_date = event_date


            lines.append(

                f"📅 **{format_display_date(event_date)}**"

            )

            lines.append("")


        lines.append(

            build_event_block(
                event,
                icon,
            )

        )

        lines.append("")


    return "\n".join(
        lines
    ).strip()


# ============================================================
# LONG TELEGRAM MESSAGE
# ============================================================

def split_message(
    text,
    limit=MAX_MESSAGE_LENGTH,
):

    if len(text) <= limit:

        return [text]


    chunks = []

    current = ""


    for line in text.splitlines(
        keepends=True
    ):

        if len(current) + len(line) > limit:

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

    "premier": (
        "Premier League",
        get_premier_league_matches,
        "⚽",
        "football",
    ),

    "championship": (
        "Championship",
        get_championship_matches,
        "⚽",
        "football",
    ),

    "rugby_union": (
        "Rugby Union",
        get_rugby_union_events,
        "🏉",
        "rugby",
    ),

    "super_league": (
        "Super League",
        get_super_league_events,
        "🏉",
        "rugby",
    ),

    "nrl": (
        "NRL",
        get_nrl_events,
        "🇦🇺",
        "rugby",
    ),

    "cricket": (
        "Cricket",
        get_cricket_events,
        "🏏",
        "home",
    ),

    "tennis": (
        "Tennis",
        get_tennis_events,
        "🎾",
        "home",
    ),

    "darts": (
        "Darts",
        get_darts_events,
        "🎯",
        "home",
    ),

    "f1": (
        "Formula 1",
        get_f1_events,
        "🏎️",
        "home",
    ),

}


UPCOMING_CONFIG = {

    "ufc": (
        "UFC",
        get_ufc_events,
        "🥊",
        "combat",
    ),

    "boxing": (
        "Boxing",
        get_boxing_events,
        "🥊",
        "combat",
    ),

    "wwe": (
        "WWE",
        get_wwe_events,
        "🤼",
        "combat",
    ),

    "golf": (
        "Golf",
        get_golf_events,
        "🏌️",
        "home",
    ),

}


# ============================================================
# WORLDWIDE EVENT LOOKUP
# ============================================================

def get_events_for_scope(scope):

    if scope.startswith(
        "worldwide_"
    ):

        scope = scope.replace(
            "worldwide_",
            "",
            1,
        )


    if scope.endswith(
        "_today"
    ):

        prefix = scope[:-6]

        if prefix in SPORT_CONFIG:

            event_function = SPORT_CONFIG[
                prefix
            ][1]

            return event_function(
                get_uk_date()
            )


    if scope.endswith(
        "_next7"
    ):

        prefix = scope[:-6]

        if prefix in SPORT_CONFIG:

            event_function = SPORT_CONFIG[
                prefix
            ][1]

            events = []

            start = datetime.now(
                UK_TIMEZONE
            ).date()


            for day_number in range(7):

                date = (

                    start

                    + timedelta(
                        days=day_number
                    )

                ).strftime(
                    "%Y-%m-%d"
                )


                events.extend(
                    event_function(
                        date
                    )
                )


            return events


    if scope.endswith(
        "_upcoming"
    ):

        prefix = scope[:-9]

        if prefix in UPCOMING_CONFIG:

            event_function = UPCOMING_CONFIG[
                prefix
            ][1]

            events = []

            start = datetime.now(
                UK_TIMEZONE
            ).date()


            for day_number in range(7):

                date = (

                    start

                    + timedelta(
                        days=day_number
                    )

                ).strftime(
                    "%Y-%m-%d"
                )


                events.extend(
                    event_function(
                        date
                    )
                )


            return events


    return []


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


    # ========================================================
    # HOME
    # ========================================================

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
    # FOOTBALL
    # ========================================================

    if data == "premier":

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
    # RUGBY
    # ========================================================

    rugby_titles = {

        "rugby_union":
            "🏉 **RUGBY UNION**",

        "super_league":
            "🏉 **SUPER LEAGUE**",

        "nrl":
            "🇦🇺 **NRL**",

    }


    if data in rugby_titles:

        await query.edit_message_text(

            f"{rugby_titles[data]}\n\n"
            "Choose an option:",

            reply_markup=league_menu(
                data,
                "rugby",
            ),

            parse_mode="Markdown",

        )

        return


    # ========================================================
    # GENERIC SPORTS
    # ========================================================

    generic_titles = {

        "cricket":
            "🏏 **CRICKET**",

        "tennis":
            "🎾 **TENNIS**",

        "darts":
            "🎯 **DARTS**",

        "f1":
            "🏎️ **FORMULA 1**",

    }


    if data in generic_titles:

        await query.edit_message_text(

            f"{generic_titles[data]}\n\n"
            "Choose an option:",

            reply_markup=sport_menu(
                data
            ),

            parse_mode="Markdown",

        )

        return


    # ========================================================
    # COMBAT
    # ========================================================

    combat_titles = {

        "ufc":
            "🥊 **UFC**",

        "boxing":
            "🥊 **BOXING**",

        "wwe":
            "🤼 **WWE**",

    }


    if data in combat_titles:

        await query.edit_message_text(

            f"{combat_titles[data]}\n\n"
            "Choose an option:",

            reply_markup=upcoming_menu(
                data,
                "combat",
            ),

            parse_mode="Markdown",

        )

        return


    # ========================================================
    # GOLF
    # ========================================================

    if data == "golf":

        await query.edit_message_text(

            "🏌️ **GOLF**\n\n"
            "Choose an option:",

            reply_markup=upcoming_menu(
                "golf",
                "home",
            ),

            parse_mode="Markdown",

        )

        return


    # ========================================================
    # TODAY / NEXT 7 RESULTS
    # ========================================================

    for prefix, details in SPORT_CONFIG.items():

        title = details[0]

        event_function = details[1]

        icon = details[2]

        back_callback = details[3]


        today_callbacks = [

            f"{prefix}_today",

            f"today_{prefix}",

        ]


        next7_callbacks = [

            f"{prefix}_next7",

            f"next7_{prefix}",

        ]


        if data in today_callbacks:

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

                results_menu(

                    back_callback,

                    f"worldwide_{prefix}_today",

                ),

            )

            return


        if data in next7_callbacks:

            message = build_next_7_days_message(

                title,

                event_function,

                icon,

            )


            await send_long_message(

                query,

                message,

                results_menu(

                    back_callback,

                    f"worldwide_{prefix}_next7",

                ),

            )

            return


    # ========================================================
    # UPCOMING EVENTS
    # ========================================================

    for prefix, details in UPCOMING_CONFIG.items():

        title = details[0]

        event_function = details[1]

        icon = details[2]

        back_callback = details[3]


        if data == f"{prefix}_upcoming":

            message = build_next_7_days_message(

                title,

                event_function,

                icon,

            )


            await send_long_message(

                query,

                message,

                results_menu(

                    back_callback,

                    f"worldwide_{prefix}_upcoming",

                ),

            )

            return


    # ========================================================
    # WORLDWIDE CHANNELS
    # ========================================================

    if data.startswith(
        "worldwide_"
    ):

        events = get_events_for_scope(
            data
        )


        message = build_worldwide_message(
            events
        )


        clean_scope = data.replace(
            "worldwide_",
            "",
            1,
        )


        if clean_scope.startswith(
            (
                "premier",
                "championship",
            )
        ):

            back_callback = "football"


        elif clean_scope.startswith(
            (
                "rugby_union",
                "super_league",
                "nrl",
            )
        ):

            back_callback = "rugby"


        elif clean_scope.startswith(
            (
                "ufc",
                "boxing",
                "wwe",
            )
        ):

            back_callback = "combat"


        else:

            back_callback = "home"


        await send_long_message(

            query,

            message,

            InlineKeyboardMarkup([

                navigation_row(
                    back_callback
                ),

            ]),

        )

        return


    # ========================================================
    # MY ALERTS
    # ========================================================

    if data == "my_alerts":

        await query.edit_message_text(

            "🔔 **MY ALERTS**\n\n"
            "Coming soon.\n\n"
            "This will let you choose teams, sports "
            "and live alerts.",

            reply_markup=InlineKeyboardMarkup([

                navigation_row(
                    "home"
                ),

            ]),

            parse_mode="Markdown",

        )

        return


    # ========================================================
    # MY TEAMS
    # ========================================================

    if data == "my_teams":

        await query.edit_message_text(

            "⭐ **MY TEAMS**\n\n"
            "Coming soon.\n\n"
            "You will be able to save favourite teams "
            "and quickly view their fixtures.",

            reply_markup=InlineKeyboardMarkup([

                navigation_row(
                    "home"
                ),

            ]),

            parse_mode="Markdown",

        )

        return


    # ========================================================
    # PREMIUM
    # ========================================================

    if data == "premium":

        await query.edit_message_text(

            "💎 **SPORT PULSE PREMIUM**\n\n"

            "Premium features coming soon:\n\n"

            "🔔 Live alerts\n"
            "⭐ Favourite team alerts\n"
            "🏎️ F1 alerts\n"
            "🥊 UFC & boxing alerts\n"
            "📺 Worldwide TV channels\n"
            "⚡ Faster notifications",

            reply_markup=InlineKeyboardMarkup([

                navigation_row(
                    "home"
                ),

            ]),

            parse_mode="Markdown",

        )

        return


    # ========================================================
    # HELP
    # ========================================================

    if data == "help":

        await query.edit_message_text(

            "ℹ️ **HELP**\n\n"

            "Choose a sport, then choose a competition "
            "or event type.\n\n"

            "You can view:\n\n"

            "📅 Today's events\n"
            "➡️ Next 7 days\n"
            "🌍 Worldwide TV channels\n\n"

            "More features are coming soon.",

            reply_markup=InlineKeyboardMarkup([

                navigation_row(
                    "home"
                ),

            ]),

            parse_mode="Markdown",

        )

        return


    # ========================================================
    # FALLBACK
    # ========================================================

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

        "Exception while handling update:",

        exc_info=context.error,

    )


# ============================================================
# MAIN
# ============================================================

def main():

    application = (

        Application.builder()

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

        CallbackQueryHandler(
            button_handler
        )

    )


    application.add_error_handler(
        error_handler
    )


    print(
        "Sport Pulse Alerts Bot is running..."
    )


    application.run_polling()


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":

    main()
