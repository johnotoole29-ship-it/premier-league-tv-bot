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
        "TELEGRAM_TOKEN is missing. "
        "Add it to your Bunny.net environment variables."
    )

if not SPORTSDB_API_KEY:
    raise RuntimeError(
        "SPORTSDB_API_KEY is missing. "
        "Add your TheSportsDB Premium API key."
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
                "🏎️ F1",
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
            )
        ],

        [
            InlineKeyboardButton(
                "🏆 Championship",
                callback_data="championship",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back",
            )
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# PREMIER LEAGUE MENU
# ============================================================

def premier_league_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 Today",
                callback_data="football_today",
            )
        ],

        [
            InlineKeyboardButton(
                "➡️ Next 7 Days",
                callback_data="football_next7",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Football",
                callback_data="football",
            )
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# CHAMPIONSHIP MENU
# ============================================================

def championship_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 Today",
                callback_data="championship_today",
            )
        ],

        [
            InlineKeyboardButton(
                "➡️ Next 7 Days",
                callback_data="championship_next7",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Football",
                callback_data="football",
            )
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
            )
        ],

        [
            InlineKeyboardButton(
                "🏉 Super League",
                callback_data="rugby_league",
            )
        ],

        [
            InlineKeyboardButton(
                "🇦🇺 NRL",
                callback_data="nrl",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back",
            )
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# RUGBY COMPETITION MENU
# ============================================================

def rugby_competition_menu(
    competition
):

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 Today",
                callback_data=f"today_{competition}",
            )
        ],

        [
            InlineKeyboardButton(
                "➡️ Next 7 Days",
                callback_data=f"next7_{competition}",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Rugby",
                callback_data="rugby",
            )
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# GENERIC SPORT MENU
# ============================================================

def sport_menu(
    sport
):

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 Today",
                callback_data=f"today_{sport}",
            )
        ],

        [
            InlineKeyboardButton(
                "➡️ Next 7 Days",
                callback_data=f"next7_{sport}",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back",
            )
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

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back",
            )
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# UFC MENU
# ============================================================

def ufc_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 Upcoming Events",
                callback_data="ufc_upcoming",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Combat",
                callback_data="combat",
            )
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# BOXING MENU
# ============================================================

def boxing_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 Upcoming Events",
                callback_data="boxing_upcoming",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Combat",
                callback_data="combat",
            )
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# WWE MENU
# ============================================================

def wwe_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 Upcoming Events",
                callback_data="wwe_upcoming",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Combat",
                callback_data="combat",
            )
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# GOLF MENU
# ============================================================

def golf_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "🏌️ Upcoming Events",
                callback_data="golf_events",
            )
        ],

        [
            InlineKeyboardButton(
                "🔙 Back",
                callback_data="back",
            )
        ],

    ]

    return InlineKeyboardMarkup(keyboard)


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


# ============================================================
# THESPORTSDB REQUEST
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
            "TheSportsDB request failed: %s",
            error,
        )

        return None

    except ValueError as error:

        logger.error(
            "Invalid JSON returned by TheSportsDB: %s",
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

def get_premier_league_matches(
    date
):

    return get_events_for_day(
        date,
        sport="Soccer",
        league="English Premier League",
    )


# ============================================================
# CHAMPIONSHIP
# ============================================================

def get_championship_matches(
    date
):

    return get_events_for_day(
        date,
        sport="Soccer",
        league="English League Championship",
    )


# ============================================================
# TV CHANNELS
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

        event_id = broadcast.get(
            "idEvent"
        )

        if not event_id:
            continue

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

        if not channel:
            continue

        item = {
            "channel": channel,
            "country": country,
        }

        tv_by_event.setdefault(
            str(event_id),
            [],
        ).append(item)

    return tv_by_event


# ============================================================
# CLEAN TV CHANNELS
# ============================================================

def clean_tv_channels(
    channels
):

    seen = set()
    cleaned = []

    for item in channels:

        key = (
            item["channel"].lower(),
            item["country"].lower(),
        )

        if key in seen:
            continue

        seen.add(key)
        cleaned.append(item)

    return cleaned


# ============================================================
# FORMAT TV
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

        return (
            "📺 TV: Not currently listed"
        )

    lines = [
        "📺 TV:"
    ]

    for item in channels[:8]:

        channel = item["channel"]
        country = item["country"]

        if country:

            lines.append(
                f"• {channel} ({country})"
            )

        else:

            lines.append(
                f"• {channel}"
            )

    return "\n".join(lines)


# ============================================================
# MATCH TIME
# ============================================================

def format_match_time(
    event
):

    event_time = event.get(
        "strTime"
    )

    if not event_time:

        return "Time TBC"

    return event_time[:5]


# ============================================================
# MATCH BLOCK
# ============================================================

def create_match_block(
    event,
    tv_by_event,
):

    home_team = (
        event.get(
            "strHomeTeam"
        )
        or event.get(
            "strHomeTeamShort"
        )
        or "Home Team"
    )

    away_team = (
        event.get(
            "strAwayTeam"
        )
        or event.get(
            "strAwayTeamShort"
        )
        or "Away Team"
    )

    time = format_match_time(
        event
    )

    tv = format_tv_channels(
        event,
        tv_by_event,
    )

    return (
        f"🕒 **{time}**\n"
        f"🏆 **{home_team} vs {away_team}**\n"
        f"{tv}\n"
    )


# ============================================================
# FOOTBALL TODAY
# ============================================================

def get_football_today():

    date = get_uk_date()

    matches = get_premier_league_matches(
        date
    )

    if not matches:

        return (
            "⚽ **PREMIER LEAGUE**\n\n"
            f"📅 {format_display_date(date)}\n\n"
            "No Premier League matches found."
        )

    tv_by_event = get_tv_channels_for_date(
        date
    )

    matches = sorted(
        matches,
        key=lambda event: (
            event.get(
                "strTime"
            )
            or "99:99"
        )
    )

    message = (
        "⚽ **PREMIER LEAGUE**\n\n"
        f"📅 {format_display_date(date)}\n\n"
    )

    for event in matches:

        message += (
            create_match_block(
                event,
                tv_by_event,
            )
            + "\n"
        )

    return message


# ============================================================
# PREMIER LEAGUE NEXT 7 DAYS
# ============================================================

def get_football_next_7_days():

    start = datetime.now(
        UK_TIMEZONE
    ).date()

    all_matches = []

    tv_cache = {}

    for day_number in range(7):

        date = (
            start
            + timedelta(
                days=day_number
            )
        ).strftime(
            "%Y-%m-%d"
        )

        matches = get_premier_league_matches(
            date
        )

        if matches:

            all_matches.extend(
                matches
            )

        tv_cache[date] = (
            get_tv_channels_for_date(
                date
            )
        )

    if not all_matches:

        return (
            "⚽ **PREMIER LEAGUE**\n\n"
            "➡️ **NEXT 7 DAYS**\n\n"
            "No Premier League matches found."
        )

    all_matches = sorted(
        all_matches,
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

    message = (
        "⚽ **PREMIER LEAGUE**\n\n"
        "➡️ **NEXT 7 DAYS**\n\n"
    )

    current_date = None

    for event in all_matches:

        event_date = event.get(
            "dateEvent"
        )

        if event_date != current_date:

            current_date = event_date

            message += (
                f"📅 **{format_display_date(event_date)}**\n\n"
            )

        message += (
            create_match_block(
                event,
                tv_cache.get(
                    event_date,
                    {},
                ),
            )
            + "\n"
        )

    return message


# ============================================================
# CHAMPIONSHIP TODAY
# ============================================================

def get_championship_today():

    date = get_uk_date()

    matches = get_championship_matches(
        date
    )

    if not matches:

        return (
            "⚽ **CHAMPIONSHIP**\n\n"
            f"📅 {format_display_date(date)}\n\n"
            "No Championship matches found."
        )

    tv_by_event = get_tv_channels_for_date(
        date
    )

    matches = sorted(
        matches,
        key=lambda event: (
            event.get(
                "strTime"
            )
            or "99:99"
        )
    )

    message = (
        "⚽ **CHAMPIONSHIP**\n\n"
        f"📅 {format_display_date(date)}\n\n"
    )

    for event in matches:

        message += (
            create_match_block(
                event,
                tv_by_event,
            )
            + "\n"
        )

    return message


# ============================================================
# CHAMPIONSHIP NEXT 7 DAYS
# ============================================================

def get_championship_next_7_days():

    start = datetime.now(
        UK_TIMEZONE
    ).date()

    all_matches = []

    tv_cache = {}

    for day_number in range(7):

        date = (
            start
            + timedelta(
                days=day_number
            )
        ).strftime(
            "%Y-%m-%d"
        )

        matches = get_championship_matches(
            date
        )

        if matches:

            all_matches.extend(
                matches
            )

        tv_cache[date] = (
            get_tv_channels_for_date(
                date
            )
        )

    if not all_matches:

        return (
            "⚽ **CHAMPIONSHIP**\n\n"
            "➡️ **NEXT 7 DAYS**\n\n"
            "No Championship matches found."
        )

    all_matches = sorted(
        all_matches,
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

    message = (
        "⚽ **CHAMPIONSHIP**\n\n"
        "➡️ **NEXT 7 DAYS**\n\n"
    )

    current_date = None

    for event in all_matches:

        event_date = event.get(
            "dateEvent"
        )

        if event_date != current_date:

            current_date = event_date

            message += (
                f"📅 **{format_display_date(event_date)}**\n\n"
            )

        message += (
            create_match_block(
                event,
                tv_cache.get(
                    event_date,
                    {},
                ),
            )
            + "\n"
        )

    return message


# ============================================================
# RUGBY UNION FILTER
# ============================================================

def filter_rugby_union(
    events
):

    results = []

    for event in events:

        league = (
            event.get(
                "strLeague",
                "",
            )
            or ""
        ).lower()

        event_name = (
            event.get(
                "strEvent",
                "",
            )
            or ""
        ).lower()

        combined = (
            league
            + " "
            + event_name
        )

        if "nrl" in combined:
            continue

        if "super league" in combined:
            continue

        if "rugby league" in combined:
            continue

        if (
            "rugby union" in combined
            or "premiership rugby" in combined
            or "six nations" in combined
            or "rugby championship" in combined
            or "rugby world cup" in combined
            or "world rugby" in combined
        ):
            results.append(event)

    return results


# ============================================================
# SUPER LEAGUE ONLY
# ============================================================

def filter_super_league(
    events
):

    results = []

    for event in events:

        league = (
            event.get(
                "strLeague",
                "",
            )
            or ""
        ).lower()

        event_name = (
            event.get(
                "strEvent",
                "",
            )
            or ""
        ).lower()

        combined = (
            league
            + " "
            + event_name
        )

        if "nrl" in combined:
            continue

        if "super league" in combined:

            results.append(event)

    return results


# ============================================================
# NRL ONLY
# ============================================================

def filter_nrl(
    events
):

    results = []

    for event in events:

        league = (
            event.get(
                "strLeague",
                "",
            )
            or ""
        ).lower()

        event_name = (
            event.get(
                "strEvent",
                "",
            )
            or ""
        ).lower()

        combined = (
            league
            + " "
            + event_name
        )

        if (
            "nrl" in combined
            or "national rugby league" in combined
        ):

            results.append(event)

    return results


# ============================================================
# F1 FILTER
# ============================================================

def filter_f1(
    events
):

    results = []

    for event in events:

        league = (
            event.get(
                "strLeague",
                "",
            )
            or ""
        ).lower()

        event_name = (
            event.get(
                "strEvent",
                "",
            )
            or ""
        ).lower()

        combined = (
            league
            + " "
            + event_name
        )

        if (
            "formula 1" in combined
            or "formula one" in combined
        ):

            results.append(event)

    return results


# ============================================================
# GENERIC SPORT EVENTS
# ============================================================

def get_generic_sport_matches(
    sport_key,
    days=1,
):

    start = datetime.now(
        UK_TIMEZONE
    ).date()

    all_events = []

    for offset in range(days):

        date = (
            start
            + timedelta(
                days=offset
            )
        ).strftime(
            "%Y-%m-%d"
        )

        if sport_key == "basketball":

            events = get_events_for_day(
                date,
                sport="Basketball",
            )

        elif sport_key == "cricket":

            events = get_events_for_day(
                date,
                sport="Cricket",
            )

        elif sport_key == "tennis":

            events = get_events_for_day(
                date,
                sport="Tennis",
            )

        elif sport_key == "darts":

            events = get_events_for_day(
                date,
                sport="Darts",
            )

        elif sport_key == "f1":

            raw_events = get_events_for_day(
                date,
                sport="Motorsport",
            )

            events = filter_f1(
                raw_events
            )

        elif sport_key in (
            "rugby_union",
            "rugby_league",
            "nrl",
        ):

            raw_events = get_events_for_day(
                date,
                sport="Rugby",
            )

            if sport_key == "rugby_union":

                events = filter_rugby_union(
                    raw_events
                )

            elif sport_key == "rugby_league":

                events = filter_super_league(
                    raw_events
                )

            else:

                events = filter_nrl(
                    raw_events
                )

        else:

            events = []

        for event in events:

            if not event.get(
                "dateEvent"
            ):

                event["dateEvent"] = date

            all_events.append(
                event
            )

    return all_events


# ============================================================
# GENERIC SPORT MESSAGE
# ============================================================

def create_generic_sport_message(
    sport_key,
    days,
):

    names = {

        "basketball":
            "🏀 **BASKETBALL**",

        "cricket":
            "🏏 **CRICKET**",

        "tennis":
            "🎾 **TENNIS**",

        "darts":
            "🎯 **DARTS**",

        "f1":
            "🏎️ **FORMULA 1**",

        "rugby_union":
            "🏉 **RUGBY UNION**",

        "rugby_league":
            "🏉 **SUPER LEAGUE**",

        "nrl":
            "🇦🇺 **NRL**",

    }

    title = names.get(
        sport_key,
        "🏆 **SPORT**",
    )

    events = get_generic_sport_matches(
        sport_key,
        days,
    )

    if not events:

        if days == 1:

            return (
                f"{title}\n\n"
                f"📅 {format_display_date(get_uk_date())}\n\n"
                "No matches/events found."
            )

        return (
            f"{title}\n\n"
            "➡️ **NEXT 7 DAYS**\n\n"
            "No matches/events found."
        )

    tv_cache = {}

    for event in events:

        event_date = event.get(
            "dateEvent"
        )

        if event_date not in tv_cache:

            tv_cache[event_date] = (
                get_tv_channels_for_date(
                    event_date
                )
            )

    events = sorted(
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

    message = (
        f"{title}\n\n"
    )

    if days > 1:

        message += (
            "➡️ **NEXT 7 DAYS**\n\n"
        )

    current_date = None

    for event in events:

        event_date = event.get(
            "dateEvent"
        )

        if event_date != current_date:

            current_date = event_date

            message += (
                f"📅 **{format_display_date(event_date)}**\n\n"
            )

        message += (
            create_match_block(
                event,
                tv_cache.get(
                    event_date,
                    {},
                ),
            )
            + "\n"
        )

    return message


# ============================================================
# START
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
# TODAY COMMAND
# ============================================================

async def today_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = get_football_today()

    await update.message.reply_text(
        message,
        reply_markup=premier_league_menu(),
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
    # FOOTBALL
    # ========================================================

    if data == "football":

        await query.edit_message_text(
            "⚽ **FOOTBALL**\n\n"
            "Choose a competition:",
            reply_markup=football_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # PREMIER LEAGUE
    # ========================================================

    if data == "premier_league":

        await query.edit_message_text(
            "🏆 **PREMIER LEAGUE**\n\n"
            "Choose an option:",
            reply_markup=premier_league_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # CHAMPIONSHIP
    # ========================================================

    if data == "championship":

        await query.edit_message_text(
            "🏆 **CHAMPIONSHIP**\n\n"
            "Choose an option:",
            reply_markup=championship_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # RUGBY
    # ========================================================

    if data == "rugby":

        await query.edit_message_text(
            "🏉 **RUGBY**\n\n"
            "Choose a competition:",
            reply_markup=rugby_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # RUGBY UNION
    # ========================================================

    if data == "rugby_union":

        await query.edit_message_text(
            "🏉 **RUGBY UNION**\n\n"
            "Choose an option:",
            reply_markup=rugby_competition_menu(
                "rugby_union"
            ),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # SUPER LEAGUE
    # ========================================================

    if data == "rugby_league":

        await query.edit_message_text(
            "🏉 **SUPER LEAGUE**\n\n"
            "🇬🇧 Super League fixtures only.",
            reply_markup=rugby_competition_menu(
                "rugby_league"
            ),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # NRL
    # ========================================================

    if data == "nrl":

        await query.edit_message_text(
            "🇦🇺 **NRL**\n\n"
            "Australian NRL fixtures only.",
            reply_markup=rugby_competition_menu(
                "nrl"
            ),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # BASKETBALL
    # ========================================================

    if data == "basketball":

        await query.edit_message_text(
            "🏀 **BASKETBALL**\n\n"
            "Choose an option:",
            reply_markup=sport_menu(
                "basketball"
            ),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # CRICKET
    # ========================================================

    if data == "cricket":

        await query.edit_message_text(
            "🏏 **CRICKET**\n\n"
            "Choose an option:",
            reply_markup=sport_menu(
                "cricket"
            ),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # TENNIS
    # ========================================================

    if data == "tennis":

        await query.edit_message_text(
            "🎾 **TENNIS**\n\n"
            "Choose an option:",
            reply_markup=sport_menu(
                "tennis"
            ),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # DARTS
    # ========================================================

    if data == "darts":

        await query.edit_message_text(
            "🎯 **DARTS**\n\n"
            "Choose an option:",
            reply_markup=sport_menu(
                "darts"
            ),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # F1
    # ========================================================

    if data == "f1":

        await query.edit_message_text(
            "🏎️ **FORMULA 1**\n\n"
            "Choose an option:",
            reply_markup=sport_menu(
                "f1"
            ),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # COMBAT
    # ========================================================

    if data == "combat":

        await query.edit_message_text(
            "🥊 **COMBAT SPORTS**\n\n"
            "Choose a sport:",
            reply_markup=combat_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # UFC
    # ========================================================

    if data == "ufc":

        await query.edit_message_text(
            "🥊 **UFC**\n\n"
            "Upcoming UFC events will appear here.",
            reply_markup=ufc_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # BOXING
    # ========================================================

    if data == "boxing":

        await query.edit_message_text(
            "🥊 **BOXING**\n\n"
            "Upcoming boxing events will appear here.",
            reply_markup=boxing_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # WWE
    # ========================================================

    if data == "wwe":

        await query.edit_message_text(
            "🤼 **WWE**\n\n"
            "Upcoming WWE events will appear here.",
            reply_markup=wwe_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # GOLF
    # ========================================================

    if data == "golf":

        await query.edit_message_text(
            "🏌️ **GOLF**\n\n"
            "Upcoming golf events will appear here.",
            reply_markup=golf_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # UFC UPCOMING
    # ========================================================

    if data == "ufc_upcoming":

        await query.edit_message_text(
            "🥊 **UFC**\n\n"
            "⏳ UFC event data will be connected next.",
            reply_markup=ufc_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # BOXING UPCOMING
    # ========================================================

    if data == "boxing_upcoming":

        await query.edit_message_text(
            "🥊 **BOXING**\n\n"
            "⏳ Boxing event data will be connected next.",
            reply_markup=boxing_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # WWE UPCOMING
    # ========================================================

    if data == "wwe_upcoming":

        await query.edit_message_text(
            "🤼 **WWE**\n\n"
            "⏳ WWE event data will be connected next.",
            reply_markup=wwe_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # GOLF EVENTS
    # ========================================================

    if data == "golf_events":

        await query.edit_message_text(
            "🏌️ **GOLF**\n\n"
            "⏳ Golf event data will be connected next.",
            reply_markup=golf_menu(),
            parse_mode="Markdown",
        )

        return


    # ========================================================
    # PREMIER LEAGUE TODAY
    # ========================================================

    if data == "football_today":

        await query.edit_message_text(
            "⏳ Loading Premier League fixtures..."
        )

        try:

            message = get_football_today()

            await query.edit_message_text(
                message,
                reply_markup=premier_league_menu(),
                parse_mode="Markdown",
            )

        except Exception:

            logger.exception(
                "Premier League today error"
            )

            await query.edit_message_text(
                "❌ Unable to load Premier League fixtures.",
                reply_markup=premier_league_menu(),
            )

        return


    # ========================================================
    # PREMIER LEAGUE NEXT 7
    # ========================================================

    if data == "football_next7":

        await query.edit_message_text(
            "⏳ Loading the next 7 days..."
        )

        try:

            message = get_football_next_7_days()

            await query.edit_message_text(
                message,
                reply_markup=premier_league_menu(),
                parse_mode="Markdown",
            )

        except Exception:

            logger.exception(
                "Premier League next 7 error"
            )

            await query.edit_message_text(
                "❌ Unable to load the next 7 days.",
                reply_markup=premier_league_menu(),
            )

        return


    # ========================================================
    # CHAMPIONSHIP TODAY
    # ========================================================

    if data == "championship_today":

        await query.edit_message_text(
            "⏳ Loading Championship fixtures..."
        )

        try:

            message = get_championship_today()

            await query.edit_message_text(
                message,
                reply_markup=championship_menu(),
                parse_mode="Markdown",
            )

        except Exception:

            logger.exception(
                "Championship today error"
            )

            await query.edit_message_text(
                "❌ Unable to load Championship fixtures.",
                reply_markup=championship_menu(),
            )

        return


    # ========================================================
    # CHAMPIONSHIP NEXT 7
    # ========================================================

    if data == "championship_next7":

        await query.edit_message_text(
            "⏳ Loading Championship fixtures..."
        )

        try:

            message = get_championship_next_7_days()

            await query.edit_message_text(
                message,
                reply_markup=championship_menu(),
                parse_mode="Markdown",
            )

        except Exception:

            logger.exception(
                "Championship next 7 error"
            )

            await query.edit_message_text(
                "❌ Unable to load Championship fixtures.",
                reply_markup=championship_menu(),
            )

        return


    # ========================================================
    # GENERIC TODAY
    # ========================================================

    if data.startswith("today_"):

        sport_key = data.replace(
            "today_",
            "",
            1,
        )

        if sport_key in (
            "rugby_union",
            "rugby_league",
            "nrl",
        ):

            keyboard = rugby_competition_menu(
                sport_key
            )

        else:

            keyboard = sport_menu(
                sport_key
            )

        await query.edit_message_text(
            "⏳ Loading fixtures..."
        )

        try:

            message = create_generic_sport_message(
                sport_key,
                1,
            )

            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

        except Exception:

            logger.exception(
                "Sport today error"
            )

            await query.edit_message_text(
                "❌ Unable to load fixtures.",
                reply_markup=keyboard,
            )

        return


    # ========================================================
    # GENERIC NEXT 7
    # ========================================================

    if data.startswith("next7_"):

        sport_key = data.replace(
            "next7_",
            "",
            1,
        )

        if sport_key in (
            "rugby_union",
            "rugby_league",
            "nrl",
        ):

            keyboard = rugby_competition_menu(
                sport_key
            )

        else:

            keyboard = sport_menu(
                sport_key
            )

        await query.edit_message_text(
            "⏳ Loading the next 7 days..."
        )

        try:

            message = create_generic_sport_message(
                sport_key,
                7,
            )

            await query.edit_message_text(
                message,
                reply_markup=keyboard,
                parse_mode="Markdown",
            )

        except Exception:

            logger.exception(
                "Sport next 7 error"
            )

            await query.edit_message_text(
                "❌ Unable to load the next 7 days.",
                reply_markup=keyboard,
            )

        return


    # ========================================================
    # UNKNOWN BUTTON
    # ========================================================

    await query.edit_message_text(
        "❌ Unknown option.",
        reply_markup=main_menu(),
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Telegram error: %s",
        context.error,
        exc_info=context.error,
    )


# ============================================================
# START BOT
# ============================================================

def main():

    logger.info(
        "Starting SportPulseAlerts..."
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
            "today",
            today_command,
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
        "SportPulseAlerts is running..."
    )

    application.run_polling(
        allowed_updates=Update.ALL_TYPES
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
