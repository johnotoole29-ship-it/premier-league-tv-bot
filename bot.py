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
# CONFIGURATION
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# Your Premium TheSportsDB API key.
# On Bunny.net set:
# SPORTSDB_API_KEY=YOUR_PREMIUM_KEY
#
# FOOTBALL_API_KEY is also accepted for compatibility
# with your previous setup.

SPORTSDB_API_KEY = (
    os.getenv("SPORTSDB_API_KEY")
    or os.getenv("FOOTBALL_API_KEY")
)

UK_TIMEZONE = ZoneInfo("Europe/London")

SPORTSDB_BASE = (
    "https://www.thesportsdb.com/api/v1/json"
)

PREMIER_LEAGUE_ID = "4328"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# ============================================================
# CHECK CONFIGURATION
# ============================================================

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN is missing. "
        "Add it to your Bunny.net environment variables."
    )

if not SPORTSDB_API_KEY:
    raise RuntimeError(
        "SPORTSDB_API_KEY is missing. "
        "Add your Premium TheSportsDB API key "
        "to your Bunny.net environment variables."
    )


# ============================================================
# THE SPORT MENU
# ============================================================

SPORT_NAMES = {
    "football": "⚽ Football",
    "basketball": "🏀 Basketball",
    "cricket": "🏏 Cricket",
    "rugby": "🏉 Rugby",
    "tennis": "🎾 Tennis",
    "darts": "🎯 Darts",
    "f1": "🏎️ F1",
}


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
                "🏀 Basketball",
                callback_data="basketball",
            ),
        ],

        [
            InlineKeyboardButton(
                "🏏 Cricket",
                callback_data="cricket",
            ),
            InlineKeyboardButton(
                "🏉 Rugby",
                callback_data="rugby",
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
                "📅 Today's Premier League",
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
                "🔙 Back",
                callback_data="back",
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
                "🏉 Rugby League",
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
# GENERIC SPORT MENU
# ============================================================

def sport_menu(sport):

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
# RUGBY SUB-MENU ACTION
# ============================================================

def rugby_competition_menu(competition):

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
# UK DATE
# ============================================================

def get_uk_date():

    return datetime.now(
        UK_TIMEZONE
    ).strftime("%Y-%m-%d")


# ============================================================
# FORMAT DATE FOR TELEGRAM
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
# API REQUEST
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
            "TheSportsDB returned invalid JSON: %s",
            error,
        )

        return None


# ============================================================
# GET EVENTS FOR A DAY
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

    events = data.get(
        "events"
    )

    if not events:
        return []

    return events


# ============================================================
# FILTER PREMIER LEAGUE
# ============================================================

def get_premier_league_matches(date):

    return get_events_for_day(
        date,
        sport="Soccer",
        league_id=PREMIER_LEAGUE_ID,
    )


# ============================================================
# FILTER SPORT EVENTS
# ============================================================

def get_sport_matches(
    date,
    sport_name,
):

    events = get_events_for_day(
        date,
        sport=sport_name,
    )

    return events


# ============================================================
# RUGBY FILTERING
# ============================================================

def filter_rugby_events(
    events,
    competition,
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

        country = (
            event.get(
                "strCountry",
                "",
            )
            or ""
        ).lower()

        combined = (
            league
            + " "
            + event_name
            + " "
            + country
        )

        if competition == "rugby_union":

            # Rugby Union competitions generally
            # contain "union" in the league name,
            # but we also accept common major
            # union competitions.

            if (
                "union" in combined
                or "premiership rugby" in combined
                or "six nations" in combined
                or "rugby championship" in combined
                or "world cup" in combined
            ):
                results.append(event)

        elif competition == "rugby_league":

            if (
                "rugby league" in combined
                or "super league" in combined
                or "challenge cup" in combined
                or "championship" in combined
            ):
                results.append(event)

        elif competition == "nrl":

            if (
                "nrl" in combined
                or "national rugby league" in combined
            ):
                results.append(event)

    return results


# ============================================================
# F1 FILTER
# ============================================================

def filter_f1_events(events):

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
            or league == "formula 1"
        ):
            results.append(event)

    return results


# ============================================================
# GET TV CHANNELS
# ============================================================

def get_tv_channels_for_date(
    date,
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
            broadcast.get(
                "idEvent"
            )
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

        language = (
            broadcast.get(
                "strLanguage"
            )
            or ""
        )

        if not channel:
            continue

        item = {
            "channel": channel,
            "country": country,
            "language": language,
        }

        tv_by_event.setdefault(
            str(event_id),
            [],
        ).append(item)

    return tv_by_event


# ============================================================
# REMOVE DUPLICATE TV CHANNELS
# ============================================================

def clean_tv_channels(
    channels,
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
# FORMAT TV INFORMATION
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

    # Show up to 8 worldwide broadcasts
    # to keep Telegram messages readable.

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

    if len(channels) > 8:

        lines.append(
            f"• +{len(channels) - 8} more"
        )

    return "\n".join(lines)


# ============================================================
# FORMAT MATCH TIME
# ============================================================

def format_match_time(event):

    event_time = (
        event.get(
            "strTime"
        )
    )

    if not event_time:

        return "Time TBC"

    try:

        # TheSportsDB generally returns
        # HH:MM:SS. Display UK local time.

        time_part = event_time[:5]

        return time_part

    except Exception:

        return "Time TBC"


# ============================================================
# CREATE MATCH BLOCK
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
        f"⚽ **{home_team} vs {away_team}**\n"
        f"{tv}\n"
    )


# ============================================================
# CREATE DAILY MESSAGE
# ============================================================

def create_matches_message(
    date,
    matches,
    title,
):

    if not matches:

        return (
            f"{title}\n\n"
            f"📅 {format_display_date(date)}\n\n"
            "No matches found."
        )

    tv_by_event = get_tv_channels_for_date(
        date
    )

    # Sort by time

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
        f"{title}\n\n"
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
# GET FOOTBALL FOR TODAY
# ============================================================

def get_football_today():

    date = get_uk_date()

    matches = get_premier_league_matches(
        date
    )

    return create_matches_message(
        date,
        matches,
        "⚽ **PREMIER LEAGUE**",
    )


# ============================================================
# GET FOOTBALL NEXT 7 DAYS
# ============================================================

def get_football_next_7_days():

    start = datetime.now(
        UK_TIMEZONE
    ).date()

    all_matches = []

    dates = []

    for day_number in range(7):

        date = (
            start
            + timedelta(
                days=day_number
            )
        ).strftime(
            "%Y-%m-%d"
        )

        dates.append(date)

        matches = get_premier_league_matches(
            date
        )

        for event in matches:

            all_matches.append(
                event
            )

    if not all_matches:

        return (
            "⚽ **PREMIER LEAGUE**\n\n"
            "📅 Next 7 Days\n\n"
            "No Premier League matches found."
        )

    # Get TV listings for each date

    tv_cache = {}

    for date in dates:

        tv_cache[date] = (
            get_tv_channels_for_date(
                date
            )
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
                f"\n📅 **{format_display_date(event_date)}**\n\n"
            )

        tv_by_event = tv_cache.get(
            event_date,
            {}
        )

        message += (
            create_match_block(
                event,
                tv_by_event,
            )
            + "\n"
        )

    return message


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

        events = []

        if sport_key == "basketball":

            events = get_sport_matches(
                date,
                "Basketball",
            )

        elif sport_key == "cricket":

            events = get_sport_matches(
                date,
                "Cricket",
            )

        elif sport_key == "tennis":

            events = get_sport_matches(
                date,
                "Tennis",
            )

        elif sport_key == "darts":

            events = get_sport_matches(
                date,
                "Darts",
            )

        elif sport_key == "f1":

            raw_events = get_sport_matches(
                date,
                "Motorsport",
            )

            events = filter_f1_events(
                raw_events
            )

        elif sport_key in (
            "rugby_union",
            "rugby_league",
            "nrl",
        ):

            raw_events = get_sport_matches(
                date,
                "Rugby",
            )

            events = filter_rugby_events(
                raw_events,
                sport_key,
            )

        for event in events:

            # Store date explicitly because
            # some API responses can omit it.

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
        "basketball": "🏀 **BASKETBALL**",
        "cricket": "🏏 **CRICKET**",
        "tennis": "🎾 **TENNIS**",
        "darts": "🎯 **DARTS**",
        "f1": "🏎️ **FORMULA 1**",
        "rugby_union": "🏉 **RUGBY UNION**",
        "rugby_league": "🏉 **RUGBY LEAGUE**",
        "nrl": "🇦🇺 **NRL**",
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

    # Cache TV information by date

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
# /START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = (
        "🔥 **SportPulseAlerts**\n\n"
        "Select a sport:"
    )

    if update.message:

        await update.message.reply_text(
            message,
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )


# ============================================================
# /TODAY
# ============================================================

async def today_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    message = get_football_today()

    await update.message.reply_text(
        message,
        reply_markup=football_menu(),
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

    # --------------------------------------------------------
    # BACK
    # --------------------------------------------------------

    if data == "back":

        await query.edit_message_text(
            "🔥 **SportPulseAlerts**\n\n"
            "Select a sport:",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # MAIN SPORTS
    # --------------------------------------------------------

    if data == "football":

        await query.edit_message_text(
            "⚽ **FOOTBALL**\n\n"
            "What would you like to see?",
            reply_markup=football_menu(),
            parse_mode="Markdown",
        )

        return

    if data == "basketball":

        await query.edit_message_text(
            "🏀 **BASKETBALL**\n\n"
            "What would you like to see?",
            reply_markup=sport_menu(
                "basketball"
            ),
            parse_mode="Markdown",
        )

        return

    if data == "cricket":

        await query.edit_message_text(
            "🏏 **CRICKET**\n\n"
            "What would you like to see?",
            reply_markup=sport_menu(
                "cricket"
            ),
            parse_mode="Markdown",
        )

        return

    if data == "tennis":

        await query.edit_message_text(
            "🎾 **TENNIS**\n\n"
            "What would you like to see?",
            reply_markup=sport_menu(
                "tennis"
            ),
            parse_mode="Markdown",
        )

        return

    if data == "darts":

        await query.edit_message_text(
            "🎯 **DARTS**\n\n"
            "What would you like to see?",
            reply_markup=sport_menu(
                "darts"
            ),
            parse_mode="Markdown",
        )

        return

    if data == "f1":

        await query.edit_message_text(
            "🏎️ **FORMULA 1**\n\n"
            "What would you like to see?",
            reply_markup=sport_menu(
                "f1"
            ),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # RUGBY
    # --------------------------------------------------------

    if data == "rugby":

        await query.edit_message_text(
            "🏉 **RUGBY**\n\n"
            "Choose a competition:",
            reply_markup=rugby_menu(),
            parse_mode="Markdown",
        )

        return

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

    if data == "rugby_league":

        await query.edit_message_text(
            "🏉 **RUGBY LEAGUE**\n\n"
            "Choose an option:",
            reply_markup=rugby_competition_menu(
                "rugby_league"
            ),
            parse_mode="Markdown",
        )

        return

    if data == "nrl":

        await query.edit_message_text(
            "🇦🇺 **NRL**\n\n"
            "Choose an option:",
            reply_markup=rugby_competition_menu(
                "nrl"
            ),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # FOOTBALL TODAY
    # --------------------------------------------------------

    if data == "football_today":

        await query.edit_message_text(
            "⏳ Loading Premier League fixtures...",
        )

        try:

            message = get_football_today()

            await query.edit_message_text(
                message,
                reply_markup=football_menu(),
                parse_mode="Markdown",
            )

        except Exception as error:

            logger.exception(
                "Football today error"
            )

            await query.edit_message_text(
                "❌ Sorry, there was a problem "
                "getting the football fixtures.",
                reply_markup=football_menu(),
            )

        return

    # --------------------------------------------------------
    # FOOTBALL NEXT 7 DAYS
    # --------------------------------------------------------

    if data == "football_next7":

        await query.edit_message_text(
            "⏳ Loading the next 7 days...",
        )

        try:

            message = get_football_next_7_days()

            await query.edit_message_text(
                message,
                reply_markup=football_menu(),
                parse_mode="Markdown",
            )

        except Exception as error:

            logger.exception(
                "Football next 7 error"
            )

            await query.edit_message_text(
                "❌ Sorry, there was a problem "
                "getting the next 7 days.",
                reply_markup=football_menu(),
            )

        return

    # --------------------------------------------------------
    # GENERIC SPORT TODAY
    # --------------------------------------------------------

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
            "⏳ Loading fixtures...",
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

        except Exception as error:

            logger.exception(
                "Sport today error"
            )

            await query.edit_message_text(
                "❌ Sorry, there was a problem "
                "getting the fixtures.",
                reply_markup=keyboard,
            )

        return

    # --------------------------------------------------------
    # GENERIC SPORT NEXT 7 DAYS
    # --------------------------------------------------------

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
            "⏳ Loading the next 7 days...",
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

        except Exception as error:

            logger.exception(
                "Sport next 7 error"
            )

            await query.edit_message_text(
                "❌ Sorry, there was a problem "
                "getting the next 7 days.",
                reply_markup=keyboard,
            )

        return

    # --------------------------------------------------------
    # UNKNOWN BUTTON
    # --------------------------------------------------------

    await query.edit_message_text(
        "❌ Unknown option.",
        reply_markup=main_menu(),
    )


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
        Application.builder()
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
            "today",
            today_command,
        )
    )

    # Buttons

    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    # Errors

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
# START BOT
# ============================================================

if __name__ == "__main__":
    main()
