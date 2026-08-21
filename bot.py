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

MAX_MESSAGE_LENGTH = 4000


# ============================================================
# THE SPORTDB LEAGUE IDS
# ============================================================

PREMIER_LEAGUE_ID = "4328"
CHAMPIONSHIP_ID = "4329"

SUPER_LEAGUE_ID = "4415"
NRL_ID = "4416"

FORMULA_1_ID = "4370"

UFC_ID = "4443"
BOXING_ID = "4445"
WWE_ID = "4444"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# CONFIG CHECK
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
# FOOTBALL LEAGUE MENU
# ============================================================

def football_league_menu(
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
# COMBAT EVENT MENU
# ============================================================

def combat_event_menu(
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
                "📅 Today",
                callback_data="today_golf",
            )
        ],

        [
            InlineKeyboardButton(
                "➡️ Next 7 Days",
                callback_data="next7_golf",
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
    ).date()


# ============================================================
# UK DATE STRING
# ============================================================

def get_uk_date_string():

    return get_uk_date().strftime(
        "%Y-%m-%d"
    )


# ============================================================
# DISPLAY DATE
# ============================================================

def format_display_date(
    date_string
):

    if not date_string:
        return "Date TBC"

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
# EVENTS FOR DAY
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
# TV CHANNELS FOR DATE
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

        channel = item.get(
            "channel",
            "",
        )

        country = item.get(
            "country",
            "",
        )

        key = (
            channel.lower().strip(),
            country.lower().strip(),
        )

        if key in seen:
            continue

        seen.add(key)
        cleaned.append(item)

    return cleaned


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

        return (
            "📺 TV: Not currently listed"
        )

    lines = [
        "📺 TV:"
    ]

    for item in channels[:10]:

        channel = item.get(
            "channel",
            "Unknown",
        )

        country = item.get(
            "country",
            "",
        )

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

    event_time = (
        event.get("strTime")
        or event.get("strEventTime")
    )

    if not event_time:

        return "Time TBC"

    try:

        return event_time[:5]

    except Exception:

        return str(event_time)


# ============================================================
# EVENT NAME
# ============================================================

def get_event_name(
    event
):

    home = (
        event.get(
            "strHomeTeam"
        )
        or event.get(
            "strHomeTeamShort"
        )
    )

    away = (
        event.get(
            "strAwayTeam"
        )
        or event.get(
            "strAwayTeamShort"
        )
    )

    if home and away:

        return f"{home} vs {away}"

    return (
        event.get(
            "strEvent"
        )
        or "Event"
    )


# ============================================================
# EVENT BLOCK
# ============================================================

def create_event_block(
    event,
    tv_by_event,
    show_tv=True,
):

    event_name = get_event_name(
        event
    )

    time = format_match_time(
        event
    )

    lines = [
        f"🕒 **{time}**",
        f"🏆 **{event_name}**",
    ]

    if show_tv:

        lines.append(
            format_tv_channels(
                event,
                tv_by_event,
            )
        )

    lines.append("")

    return "\n".join(lines)


# ============================================================
# SORT EVENTS
# ============================================================

def sort_events(
    events
):

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
            or event.get(
                "strEventTime"
            )
            or "99:99",
        ),
    )


# ============================================================
# REMOVE DUPLICATES
# ============================================================

def remove_duplicate_events(
    events
):

    seen = set()
    result = []

    for event in events:

        event_id = event.get(
            "idEvent"
        )

        if event_id:

            key = str(
                event_id
            )

        else:

            key = (
                event.get(
                    "dateEvent"
                ),
                event.get(
                    "strTime"
                ),
                event.get(
                    "strEvent"
                ),
            )

        if key in seen:
            continue

        seen.add(key)
        result.append(event)

    return result


# ============================================================
# GENERIC TODAY
# ============================================================

def get_today_events(
    title,
    sport=None,
    league_id=None,
    emoji="🏆",
):

    date = get_uk_date_string()

    events = get_events_for_day(
        date=date,
        sport=sport,
        league_id=league_id,
    )

    if not events:

        return (
            f"{emoji} **{title}**\n\n"
            f"📅 {format_display_date(date)}\n\n"
            "No events found."
        )

    events = remove_duplicate_events(
        events
    )

    events = sort_events(
        events
    )

    tv_by_event = get_tv_channels_for_date(
        date
    )

    message = (
        f"{emoji} **{title}**\n\n"
        f"📅 **{format_display_date(date)}**\n\n"
    )

    for event in events:

        message += create_event_block(
            event,
            tv_by_event,
        )

    return message


# ============================================================
# GENERIC NEXT 7 DAYS
# ============================================================

def get_next_7_days_events(
    title,
    sport=None,
    league_id=None,
    emoji="🏆",
    show_tv=True,
    rugby_union_only=False,
):

    start_date = get_uk_date()

    all_events = []
    tv_cache = {}

    for day_number in range(7):

        current_date = (
            start_date
            + timedelta(
                days=day_number
            )
        )

        date_string = current_date.strftime(
            "%Y-%m-%d"
        )

        events = get_events_for_day(
            date=date_string,
            sport=sport,
            league_id=league_id,
        )

        # ----------------------------------------------------
        # Rugby Union filter
        # ----------------------------------------------------

        if rugby_union_only:

            filtered = []

            for event in events:

                league_name = (
                    event.get(
                        "strLeague"
                    )
                    or ""
                ).lower()

                # Keep union competitions.
                # Remove obvious rugby-league competitions.
                if (
                    "league" not in league_name
                    and "nrl" not in league_name
                ):

                    filtered.append(
                        event
                    )

            events = filtered

        if events:

            all_events.extend(
                events
            )

        if show_tv:

            tv_cache[date_string] = (
                get_tv_channels_for_date(
                    date_string
                )
            )

    all_events = remove_duplicate_events(
        all_events
    )

    all_events = sort_events(
        all_events
    )

    if not all_events:

        return (
            f"{emoji} **{title}**\n\n"
            "➡️ **NEXT 7 DAYS**\n\n"
            "No events found."
        )

    message = (
        f"{emoji} **{title}**\n\n"
        "➡️ **NEXT 7 DAYS**\n\n"
    )

    current_date = None

    for event in all_events:

        event_date = event.get(
            "dateEvent"
        )

        if event_date != current_date:

            current_date = event_date

            message += (
                f"📅 **{format_display_date(event_date)}**\n\n"
            )

        tv_data = tv_cache.get(
            event_date,
            {},
        )

        message += create_event_block(
            event,
            tv_data,
            show_tv=show_tv,
        )

    return message


# ============================================================
# FOOTBALL
# ============================================================

def get_premier_league_today():

    return get_today_events(
        title="PREMIER LEAGUE",
        sport="Soccer",
        league_id=PREMIER_LEAGUE_ID,
        emoji="⚽",
    )


def get_premier_league_next7():

    return get_next_7_days_events(
        title="PREMIER LEAGUE",
        sport="Soccer",
        league_id=PREMIER_LEAGUE_ID,
        emoji="⚽",
    )


def get_championship_today():

    return get_today_events(
        title="CHAMPIONSHIP",
        sport="Soccer",
        league_id=CHAMPIONSHIP_ID,
        emoji="⚽",
    )


def get_championship_next7():

    return get_next_7_days_events(
        title="CHAMPIONSHIP",
        sport="Soccer",
        league_id=CHAMPIONSHIP_ID,
        emoji="⚽",
    )


# ============================================================
# RUGBY
# ============================================================

def get_rugby_union_today():

    return get_today_events(
        title="RUGBY UNION",
        sport="Rugby",
        emoji="🏉",
    )


def get_rugby_union_next7():

    return get_next_7_days_events(
        title="RUGBY UNION",
        sport="Rugby",
        emoji="🏉",
        rugby_union_only=True,
    )


def get_super_league_today():

    return get_today_events(
        title="SUPER LEAGUE",
        sport="Rugby",
        league_id=SUPER_LEAGUE_ID,
        emoji="🏉",
    )


def get_super_league_next7():

    return get_next_7_days_events(
        title="SUPER LEAGUE",
        sport="Rugby",
        league_id=SUPER_LEAGUE_ID,
        emoji="🏉",
    )


def get_nrl_today():

    return get_today_events(
        title="NRL",
        sport="Rugby",
        league_id=NRL_ID,
        emoji="🇦🇺",
    )


def get_nrl_next7():

    return get_next_7_days_events(
        title="NRL",
        sport="Rugby",
        league_id=NRL_ID,
        emoji="🇦🇺",
    )


# ============================================================
# CRICKET
# ============================================================

def get_cricket_today():

    return get_today_events(
        title="CRICKET",
        sport="Cricket",
        emoji="🏏",
    )


def get_cricket_next7():

    return get_next_7_days_events(
        title="CRICKET",
        sport="Cricket",
        emoji="🏏",
    )


# ============================================================
# BASKETBALL
# ============================================================

def get_basketball_today():

    return get_today_events(
        title="BASKETBALL",
        sport="Basketball",
        emoji="🏀",
    )


def get_basketball_next7():

    return get_next_7_days_events(
        title="BASKETBALL",
        sport="Basketball",
        emoji="🏀",
    )


# ============================================================
# TENNIS
# ============================================================

def get_tennis_today():

    return get_today_events(
        title="TENNIS",
        sport="Tennis",
        emoji="🎾",
    )


def get_tennis_next7():

    return get_next_7_days_events(
        title="TENNIS",
        sport="Tennis",
        emoji="🎾",
    )


# ============================================================
# DARTS
# ============================================================

def get_darts_today():

    return get_today_events(
        title="DARTS",
        sport="Darts",
        emoji="🎯",
    )


def get_darts_next7():

    return get_next_7_days_events(
        title="DARTS",
        sport="Darts",
        emoji="🎯",
    )


# ============================================================
# FORMULA 1
# ============================================================

def get_f1_today():

    return get_today_events(
        title="FORMULA 1",
        sport="Motorsport",
        league_id=FORMULA_1_ID,
        emoji="🏎️",
    )


def get_f1_next7():

    return get_next_7_days_events(
        title="FORMULA 1",
        sport="Motorsport",
        league_id=FORMULA_1_ID,
        emoji="🏎️",
    )


# ============================================================
# UFC
# ============================================================

def get_ufc_today():

    return get_today_events(
        title="UFC",
        sport="Fighting",
        league_id=UFC_ID,
        emoji="🥊",
    )


def get_ufc_next7():

    return get_next_7_days_events(
        title="UFC",
        sport="Fighting",
        league_id=UFC_ID,
        emoji="🥊",
    )


# ============================================================
# BOXING
# ============================================================

def get_boxing_today():

    return get_today_events(
        title="BOXING",
        sport="Fighting",
        league_id=BOXING_ID,
        emoji="🥊",
    )


def get_boxing_next7():

    return get_next_7_days_events(
        title="BOXING",
        sport="Fighting",
        league_id=BOXING_ID,
        emoji="🥊",
    )


# ============================================================
# WWE
# ============================================================

def get_wwe_today():

    return get_today_events(
        title="WWE",
        sport="Fighting",
        league_id=WWE_ID,
        emoji="🤼",
    )


def get_wwe_next7():

    return get_next_7_days_events(
        title="WWE",
        sport="Fighting",
        league_id=WWE_ID,
        emoji="🤼",
    )


# ============================================================
# GOLF
# ============================================================

def get_golf_today():

    return get_today_events(
        title="GOLF",
        sport="Golf",
        emoji="🏌️",
    )


def get_golf_next7():

    return get_next_7_days_events(
        title="GOLF",
        sport="Golf",
        emoji="🏌️",
    )


# ============================================================
# SAFE TELEGRAM SEND
# ============================================================

async def send_long_message(
    chat,
    text,
    reply_markup=None,
):

    if len(text) <= MAX_MESSAGE_LENGTH:

        await chat.send_message(
            text=text,
            parse_mode="Markdown",
            reply_markup=reply_markup,
        )

        return

    parts = []

    remaining = text

    while len(remaining) > MAX_MESSAGE_LENGTH:

        split_at = remaining.rfind(
            "\n",
            0,
            MAX_MESSAGE_LENGTH,
        )

        if split_at == -1:

            split_at = MAX_MESSAGE_LENGTH

        parts.append(
            remaining[:split_at]
        )

        remaining = remaining[
            split_at:
        ].lstrip()

    if remaining:

        parts.append(
            remaining
        )

    for index, part in enumerate(parts):

        markup = (
            reply_markup
            if index == len(parts) - 1
            else None
        )

        await chat.send_message(
            text=part,
            parse_mode="Markdown",
            reply_markup=markup,
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
        parse_mode="Markdown",
        reply_markup=main_menu(),
    )


# ============================================================
# SHOW MENU
# ============================================================

async def show_menu(
    query,
    text,
    keyboard,
):

    await query.edit_message_text(
        text=text,
        parse_mode="Markdown",
        reply_markup=keyboard,
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

    # --------------------------------------------------------
    # MAIN MENU
    # --------------------------------------------------------

    if data == "back":

        await show_menu(
            query,
            "🔥 **SportPulseAlerts**\n\n"
            "Select a sport:",
            main_menu(),
        )

        return

    # --------------------------------------------------------
    # FOOTBALL
    # --------------------------------------------------------

    if data == "football":

        await show_menu(
            query,
            "⚽ **FOOTBALL**\n\n"
            "Select a competition:",
            football_menu(),
        )

        return

    if data == "premier_league":

        await show_menu(
            query,
            "⚽ **PREMIER LEAGUE**\n\n"
            "Select an option:",
            football_league_menu(
                "premier_league"
            ),
        )

        return

    if data == "championship":

        await show_menu(
            query,
            "⚽ **CHAMPIONSHIP**\n\n"
            "Select an option:",
            football_league_menu(
                "championship"
            ),
        )

        return

    # --------------------------------------------------------
    # RUGBY
    # --------------------------------------------------------

    if data == "rugby":

        await show_menu(
            query,
            "🏉 **RUGBY**\n\n"
            "Select a competition:",
            rugby_menu(),
        )

        return

    if data == "rugby_union":

        await show_menu(
            query,
            "🏉 **RUGBY UNION**\n\n"
            "Select an option:",
            rugby_competition_menu(
                "rugby_union"
            ),
        )

        return

    if data == "rugby_league":

        await show_menu(
            query,
            "🏉 **SUPER LEAGUE**\n\n"
            "Select an option:",
            rugby_competition_menu(
                "rugby_league"
            ),
        )

        return

    if data == "nrl":

        await show_menu(
            query,
            "🇦🇺 **NRL**\n\n"
            "Select an option:",
            rugby_competition_menu(
                "nrl"
            ),
        )

        return

    # --------------------------------------------------------
    # CRICKET
    # --------------------------------------------------------

    if data == "cricket":

        await show_menu(
            query,
            "🏏 **CRICKET**\n\n"
            "Select an option:",
            sport_menu(
                "cricket"
            ),
        )

        return

    # --------------------------------------------------------
    # BASKETBALL
    # --------------------------------------------------------

    if data == "basketball":

        await show_menu(
            query,
            "🏀 **BASKETBALL**\n\n"
            "Select an option:",
            sport_menu(
                "basketball"
            ),
        )

        return

    # --------------------------------------------------------
    # TENNIS
    # --------------------------------------------------------

    if data == "tennis":

        await show_menu(
            query,
            "🎾 **TENNIS**\n\n"
            "Select an option:",
            sport_menu(
                "tennis"
            ),
        )

        return

    # --------------------------------------------------------
    # DARTS
    # --------------------------------------------------------

    if data == "darts":

        await show_menu(
            query,
            "🎯 **DARTS**\n\n"
            "Select an option:",
            sport_menu(
                "darts"
            ),
        )

        return

    # --------------------------------------------------------
    # F1
    # --------------------------------------------------------

    if data == "f1":

        await show_menu(
            query,
            "🏎️ **FORMULA 1**\n\n"
            "Select an option:",
            sport_menu(
                "f1"
            ),
        )

        return

    # --------------------------------------------------------
    # COMBAT
    # --------------------------------------------------------

    if data == "combat":

        await show_menu(
            query,
            "🥊 **COMBAT SPORTS**\n\n"
            "Select a competition:",
            combat_menu(),
        )

        return

    if data == "ufc":

        await show_menu(
            query,
            "🥊 **UFC**\n\n"
            "Select an option:",
            combat_event_menu(
                "ufc"
            ),
        )

        return

    if data == "boxing":

        await show_menu(
            query,
            "🥊 **BOXING**\n\n"
            "Select an option:",
            combat_event_menu(
                "boxing"
            ),
        )

        return

    if data == "wwe":

        await show_menu(
            query,
            "🤼 **WWE**\n\n"
            "Select an option:",
            combat_event_menu(
                "wwe"
            ),
        )

        return

    # --------------------------------------------------------
    # GOLF
    # --------------------------------------------------------

    if data == "golf":

        await show_menu(
            query,
            "🏌️ **GOLF**\n\n"
            "Select an option:",
            golf_menu(),
        )

        return

    # --------------------------------------------------------
    # FOOTBALL TODAY
    # --------------------------------------------------------

    if data == "today_premier_league":

        text = get_premier_league_today()

        await send_long_message(
            query.message.chat,
            text,
            football_league_menu(
                "premier_league"
            ),
        )

        return

    if data == "next7_premier_league":

        text = get_premier_league_next7()

        await send_long_message(
            query.message.chat,
            text,
            football_league_menu(
                "premier_league"
            ),
        )

        return

    if data == "today_championship":

        text = get_championship_today()

        await send_long_message(
            query.message.chat,
            text,
            football_league_menu(
                "championship"
            ),
        )

        return

    if data == "next7_championship":

        text = get_championship_next7()

        await send_long_message(
            query.message.chat,
            text,
            football_league_menu(
                "championship"
            ),
        )

        return

    # --------------------------------------------------------
    # RUGBY
    # --------------------------------------------------------

    if data == "today_rugby_union":

        text = get_rugby_union_today()

        await send_long_message(
            query.message.chat,
            text,
            rugby_competition_menu(
                "rugby_union"
            ),
        )

        return

    if data == "next7_rugby_union":

        text = get_rugby_union_next7()

        await send_long_message(
            query.message.chat,
            text,
            rugby_competition_menu(
                "rugby_union"
            ),
        )

        return

    if data == "today_rugby_league":

        text = get_super_league_today()

        await send_long_message(
            query.message.chat,
            text,
            rugby_competition_menu(
                "rugby_league"
            ),
        )

        return

    if data == "next7_rugby_league":

        text = get_super_league_next7()

        await send_long_message(
            query.message.chat,
            text,
            rugby_competition_menu(
                "rugby_league"
            ),
        )

        return

    if data == "today_nrl":

        text = get_nrl_today()

        await send_long_message(
            query.message.chat,
            text,
            rugby_competition_menu(
                "nrl"
            ),
        )

        return

    if data == "next7_nrl":

        text = get_nrl_next7()

        await send_long_message(
            query.message.chat,
            text,
            rugby_competition_menu(
                "nrl"
            ),
        )

        return

    # --------------------------------------------------------
    # CRICKET
    # --------------------------------------------------------

    if data == "today_cricket":

        text = get_cricket_today()

        await send_long_message(
            query.message.chat,
            text,
            sport_menu("cricket"),
        )

        return

    if data == "next7_cricket":

        text = get_cricket_next7()

        await send_long_message(
            query.message.chat,
            text,
            sport_menu("cricket"),
        )

        return

    # --------------------------------------------------------
    # BASKETBALL
    # --------------------------------------------------------

    if data == "today_basketball":

        text = get_basketball_today()

        await send_long_message(
            query.message.chat,
            text,
            sport_menu("basketball"),
        )

        return

    if data == "next7_basketball":

        text = get_basketball_next7()

        await send_long_message(
            query.message.chat,
            text,
            sport_menu("basketball"),
        )

        return

    # --------------------------------------------------------
    # TENNIS
    # --------------------------------------------------------

    if data == "today_tennis":

        text = get_tennis_today()

        await send_long_message(
            query.message.chat,
            text,
            sport_menu("tennis"),
        )

        return

    if data == "next7_tennis":

        text = get_tennis_next7()

        await send_long_message(
            query.message.chat,
            text,
            sport_menu("tennis"),
        )

        return

    # --------------------------------------------------------
    # DARTS
    # --------------------------------------------------------

    if data == "today_darts":

        text = get_darts_today()

        await send_long_message(
            query.message.chat,
            text,
            sport_menu("darts"),
        )

        return

    if data == "next7_darts":

        text = get_darts_next7()

        await send_long_message(
            query.message.chat,
            text,
            sport_menu("darts"),
        )

        return

    # --------------------------------------------------------
    # F1
    # --------------------------------------------------------

    if data == "today_f1":

        text = get_f1_today()

        await send_long_message(
            query.message.chat,
            text,
            sport_menu("f1"),
        )

        return

    if data == "next7_f1":

        text = get_f1_next7()

        await send_long_message(
            query.message.chat,
            text,
            sport_menu("f1"),
        )

        return

    # --------------------------------------------------------
    # UFC
    # --------------------------------------------------------

    if data == "today_ufc":

        text = get_ufc_today()

        await send_long_message(
            query.message.chat,
            text,
            combat_event_menu("ufc"),
        )

        return

    if data == "next7_ufc":

        text = get_ufc_next7()

        await send_long_message(
            query.message.chat,
            text,
            combat_event_menu("ufc"),
        )

        return

    # --------------------------------------------------------
    # BOXING
    # --------------------------------------------------------

    if data == "today_boxing":

        text = get_boxing_today()

        await send_long_message(
            query.message.chat,
            text,
            combat_event_menu("boxing"),
        )

        return

    if data == "next7_boxing":

        text = get_boxing_next7()

        await send_long_message(
            query.message.chat,
            text,
            combat_event_menu("boxing"),
        )

        return

    # --------------------------------------------------------
    # WWE
    # --------------------------------------------------------

    if data == "today_wwe":

        text = get_wwe_today()

        await send_long_message(
            query.message.chat,
            text,
            combat_event_menu("wwe"),
        )

        return

    if data == "next7_wwe":

        text = get_wwe_next7()

        await send_long_message(
            query.message.chat,
            text,
            combat_event_menu("wwe"),
        )

        return

    # --------------------------------------------------------
    # GOLF
    # --------------------------------------------------------

    if data == "today_golf":

        text = get_golf_today()

        await send_long_message(
            query.message.chat,
            text,
            golf_menu(),
        )

        return

    if data == "next7_golf":

        text = get_golf_next7()

        await send_long_message(
            query.message.chat,
            text,
            golf_menu(),
        )

        return


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Telegram error: %s",
        context.error,
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
        "SportPulseAlerts is running..."
    )

    application.run_polling()


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":
    main()
