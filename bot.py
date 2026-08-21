import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


# ============================================================
# CONFIGURATION
# ============================================================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

UK_TIMEZONE = ZoneInfo("Europe/London")

API_BASE = (
    "https://www.thesportsdb.com/api/v1/json/"
    f"{FOOTBALL_API_KEY}"
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
# CHECK API KEYS
# ============================================================

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN is missing from environment variables."
    )

if not FOOTBALL_API_KEY:
    raise RuntimeError(
        "FOOTBALL_API_KEY is missing from environment variables."
    )


# ============================================================
# SPORTS
# ============================================================

SPORTS = {
    "football": {
        "name": "⚽ Football",
        "sport": "Soccer",
    },
    "basketball": {
        "name": "🏀 Basketball",
        "sport": "Basketball",
    },
    "nfl": {
        "name": "🏈 NFL",
        "sport": "American Football",
    },
    "rugby": {
        "name": "🏉 Rugby",
        "sport": "Rugby",
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
        "name": "🏎️ F1",
        "sport": "Motorsport",
    },
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
                "🏈 NFL",
                callback_data="nfl",
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
                "📅 Today's Premier League Games",
                callback_data="football_today",
            )
        ],

        [
            InlineKeyboardButton(
                "➡️ Next 7 Days",
                callback_data="football_upcoming",
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

def sport_menu(sport_key):

    keyboard = [

        [
            InlineKeyboardButton(
                "📅 Today",
                callback_data=f"{sport_key}_today",
            )
        ],

        [
            InlineKeyboardButton(
                "➡️ Next 7 Days",
                callback_data=f"{sport_key}_upcoming",
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
# GET CURRENT UK DATE
# ============================================================

def get_uk_date():

    return datetime.now(
        UK_TIMEZONE
    ).strftime("%Y-%m-%d")


# ============================================================
# FORMAT DATE FOR TELEGRAM
# ============================================================

def format_date(date_string):

    try:

        date_obj = datetime.strptime(
            date_string,
            "%Y-%m-%d"
        )

        return date_obj.strftime(
            "%A %d %B %Y"
        )

    except Exception:

        return date_string


# ============================================================
# FORMAT TIME
# ============================================================

def format_event_time(event):

    timestamp = event.get("strTimestamp")

    if timestamp:

        try:

            timestamp = timestamp.replace(
                "Z",
                "+00:00"
            )

            dt = datetime.fromisoformat(timestamp)

            if dt.tzinfo is None:
                dt = dt.replace(
                    tzinfo=ZoneInfo("UTC")
                )

            uk_time = dt.astimezone(
                UK_TIMEZONE
            )

            return uk_time.strftime(
                "%H:%M"
            )

        except Exception as error:

            logger.warning(
                f"Timestamp error: {error}"
            )

    # Fallback to strTime

    time_value = event.get("strTime")

    if time_value:

        try:

            return time_value[:5]

        except Exception:
            pass

    return "TBC"


# ============================================================
# GET UK LOCAL DATE FOR EVENT
# ============================================================

def get_event_uk_date(event):

    timestamp = event.get("strTimestamp")

    if timestamp:

        try:

            timestamp = timestamp.replace(
                "Z",
                "+00:00"
            )

            dt = datetime.fromisoformat(timestamp)

            if dt.tzinfo is None:
                dt = dt.replace(
                    tzinfo=ZoneInfo("UTC")
                )

            uk_time = dt.astimezone(
                UK_TIMEZONE
            )

            return uk_time.strftime(
                "%Y-%m-%d"
            )

        except Exception:
            pass

    return event.get(
        "dateEvent",
        get_uk_date()
    )


# ============================================================
# GET EVENTS FOR ONE DAY
# ============================================================

def get_events_for_day(
    date,
    sport=None,
    league_id=None,
):

    url = f"{API_BASE}/eventsday.php"

    params = {
        "d": date,
    }

    if sport:
        params["s"] = sport

    if league_id:
        params["l"] = league_id

    try:

        response = requests.get(
            url,
            params=params,
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        events = data.get(
            "events"
        )

        if not events:
            return []

        return events

    except requests.RequestException as error:

        logger.error(
            f"TheSportsDB request failed: {error}"
        )

        return []

    except Exception as error:

        logger.error(
            f"Error getting events: {error}"
        )

        return []


# ============================================================
# GET PREMIER LEAGUE MATCHES
# ============================================================

def get_premier_league_matches(date):

    return get_events_for_day(
        date=date,
        league_id=PREMIER_LEAGUE_ID,
    )


# ============================================================
# GET TV LISTINGS FOR A DAY
# ============================================================

def get_tv_events_for_day(date):

    url = f"{API_BASE}/eventstv.php"

    params = {
        "d": date,
    }

    try:

        response = requests.get(
            url,
            params=params,
            timeout=20,
        )

        response.raise_for_status()

        data = response.json()

        tv_events = data.get(
            "tvevents"
        )

        if not tv_events:
            return []

        return tv_events

    except Exception as error:

        logger.error(
            f"Error getting TV listings: {error}"
        )

        return []


# ============================================================
# GET TV CHANNELS FOR EVENT
# ============================================================

def get_tv_channels(event, tv_events=None):

    event_id = str(
        event.get(
            "idEvent",
            ""
        )
    )

    channels = []

    # --------------------------------------------------------
    # First use the TV schedule for the day.
    # This is much more efficient.
    # --------------------------------------------------------

    if tv_events:

        for tv in tv_events:

            tv_event_id = str(
                tv.get(
                    "idEvent",
                    ""
                )
            )

            if tv_event_id != event_id:
                continue

            channel = tv.get(
                "strChannel"
            )

            country = tv.get(
                "strCountry"
            )

            if not channel:
                continue

            item = {
                "channel": channel,
                "country": country or "Unknown",
            }

            if item not in channels:

                channels.append(item)

    # --------------------------------------------------------
    # If nothing was found, try the individual event TV API.
    # --------------------------------------------------------

    if not channels and event_id:

        url = f"{API_BASE}/lookuptv.php"

        try:

            response = requests.get(
                url,
                params={
                    "id": event_id
                },
                timeout=20,
            )

            response.raise_for_status()

            data = response.json()

            tv_channels = data.get(
                "tvevent"
            )

            if not tv_channels:

                tv_channels = data.get(
                    "tvchannels"
                )

            if tv_channels:

                for tv in tv_channels:

                    channel = tv.get(
                        "strChannel"
                    )

                    country = tv.get(
                        "strCountry"
                    )

                    if channel:

                        item = {
                            "channel": channel,
                            "country": country or "Unknown",
                        }

                        if item not in channels:

                            channels.append(item)

        except Exception as error:

            logger.warning(
                f"TV lookup failed for event {event_id}: {error}"
            )

    return channels


# ============================================================
# FORMAT TV CHANNELS
# ============================================================

def format_tv_channels(channels):

    if not channels:

        return "📺 TV: Not currently listed"

    lines = []

    # Show maximum 12 listings so Telegram messages
    # don't become enormous.

    for item in channels[:12]:

        channel = item["channel"]
        country = item["country"]

        lines.append(
            f"📺 {channel} ({country})"
        )

    if len(channels) > 12:

        lines.append(
            f"➕ {len(channels) - 12} more listings"
        )

    return "\n".join(lines)


# ============================================================
# CREATE EVENT TEXT
# ============================================================

def create_event_text(
    event,
    tv_events=None,
):

    home_team = event.get(
        "strHomeTeam",
        "Home Team"
    )

    away_team = event.get(
        "strAwayTeam",
        "Away Team"
    )

    match_time = format_event_time(
        event
    )

    channels = get_tv_channels(
        event,
        tv_events,
    )

    tv_text = format_tv_channels(
        channels
    )

    return (
        f"🕒 **{match_time}**\n"
        f"⚽ **{home_team} vs {away_team}**\n"
        f"{tv_text}\n"
    )


# ============================================================
# CREATE FOOTBALL MESSAGE
# ============================================================

def create_football_message(
    date,
    matches,
    tv_events=None,
):

    if not matches:

        return (
            "⚽ **PREMIER LEAGUE**\n\n"
            f"📅 **{format_date(date)}**\n\n"
            "No Premier League matches found."
        )

    # Sort by UK time

    matches = sorted(
        matches,
        key=lambda event: (
            get_event_uk_date(event),
            format_event_time(event)
        )
    )

    message = (
        "⚽ **PREMIER LEAGUE**\n\n"
        f"📅 **{format_date(date)}**\n\n"
    )

    for event in matches:

        # Make sure an event crossing midnight
        # is displayed under its actual UK date.

        message += (
            create_event_text(
                event,
                tv_events,
            )
            + "\n"
        )

    return message


# ============================================================
# CREATE GENERIC SPORT MESSAGE
# ============================================================

def create_sport_message(
    sport_name,
    date,
    events,
    tv_events=None,
):

    if not events:

        return (
            f"{sport_name}\n\n"
            f"📅 **{format_date(date)}**\n\n"
            "No events found."
        )

    events = sorted(
        events,
        key=lambda event: (
            get_event_uk_date(event),
            format_event_time(event)
        )
    )

    message = (
        f"{sport_name}\n\n"
        f"📅 **{format_date(date)}**\n\n"
    )

    for event in events:

        home_team = event.get(
            "strHomeTeam"
        )

        away_team = event.get(
            "strAwayTeam"
        )

        event_name = event.get(
            "strEvent"
        )

        # Some sports have teams.
        # Others, such as F1, may not.

        if home_team and away_team:

            title = (
                f"{home_team} vs {away_team}"
            )

        elif event_name:

            title = event_name

        else:

            title = "Event"

        match_time = format_event_time(
            event
        )

        channels = get_tv_channels(
            event,
            tv_events,
        )

        tv_text = format_tv_channels(
            channels
        )

        message += (
            f"🕒 **{match_time}**\n"
            f"🏟️ **{title}**\n"
            f"{tv_text}\n\n"
        )

    return message


# ============================================================
# GET UPCOMING EVENTS FOR NEXT 7 DAYS
# ============================================================

def get_next_7_days_events(
    sport_key
):

    today = datetime.now(
        UK_TIMEZONE
    ).date()

    all_events = []

    sport_config = SPORTS[
        sport_key
    ]

    sport_name = sport_config[
        "sport"
    ]

    for day_number in range(7):

        current_date = (
            today
            + timedelta(
                days=day_number
            )
        )

        date_string = current_date.strftime(
            "%Y-%m-%d"
        )

        if sport_key == "football":

            events = get_premier_league_matches(
                date_string
            )

        else:

            events = get_events_for_day(
                date=date_string,
                sport=sport_name,
            )

        if not events:
            continue

        tv_events = get_tv_events_for_day(
            date_string
        )

        for event in events:

            event["_uk_date"] = (
                get_event_uk_date(event)
            )

            event["_tv_events"] = (
                tv_events
            )

            all_events.append(
                event
            )

    return all_events


# ============================================================
# CREATE NEXT 7 DAYS MESSAGE
# ============================================================

def create_next_7_days_message(
    sport_key,
    events,
):

    sport_name = SPORTS[
        sport_key
    ]["name"]

    if not events:

        return (
            f"{sport_name}\n\n"
            "📅 **Next 7 Days**\n\n"
            "No events found."
        )

    # Group events by UK date

    grouped = {}

    for event in events:

        date = event.get(
            "_uk_date"
        )

        if not date:
            date = get_event_uk_date(
                event
            )

        if date not in grouped:

            grouped[date] = []

        grouped[date].append(
            event
        )

    message = (
        f"{sport_name}\n\n"
        "📅 **NEXT 7 DAYS**\n"
    )

    for date in sorted(grouped.keys()):

        message += (
            f"\n━━━━━━━━━━━━━━\n"
            f"📅 **{format_date(date)}**\n"
            f"━━━━━━━━━━━━━━\n\n"
        )

        day_events = sorted(
            grouped[date],
            key=lambda event: format_event_time(
                event
            )
        )

        for event in day_events:

            tv_events = event.get(
                "_tv_events",
                []
            )

            if sport_key == "football":

                message += (
                    create_event_text(
                        event,
                        tv_events,
                    )
                    + "\n"
                )

            else:

                home_team = event.get(
                    "strHomeTeam"
                )

                away_team = event.get(
                    "strAwayTeam"
                )

                event_name = event.get(
                    "strEvent",
                    "Event"
                )

                if home_team and away_team:

                    title = (
                        f"{home_team} vs {away_team}"
                    )

                else:

                    title = event_name

                match_time = format_event_time(
                    event
                )

                channels = get_tv_channels(
                    event,
                    tv_events,
                )

                tv_text = format_tv_channels(
                    channels
                )

                message += (
                    f"🕒 **{match_time}**\n"
                    f"🏟️ **{title}**\n"
                    f"{tv_text}\n\n"
                )

    return message


# ============================================================
# /start
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    text = (
        "🔥 **SportPulseAlerts**\n\n"
        "Your sports fixture and TV guide.\n\n"
        "Select a sport below:"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


# ============================================================
# /today
# ============================================================

async def today_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    date = get_uk_date()

    matches = get_premier_league_matches(
        date
    )

    tv_events = get_tv_events_for_day(
        date
    )

    message = create_football_message(
        date,
        matches,
        tv_events,
    )

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
    # MAIN SPORTS
    # --------------------------------------------------------

    if data in SPORTS:

        sport = SPORTS[
            data
        ]

        if data == "football":

            await query.edit_message_text(
                "⚽ **FOOTBALL**\n\n"
                "What would you like to see?",
                reply_markup=football_menu(),
                parse_mode="Markdown",
            )

        else:

            await query.edit_message_text(
                f"{sport['name']}\n\n"
                "What would you like to see?",
                reply_markup=sport_menu(data),
                parse_mode="Markdown",
            )

        return

    # --------------------------------------------------------
    # FOOTBALL TODAY
    # --------------------------------------------------------

    if data == "football_today":

        date = get_uk_date()

        matches = get_premier_league_matches(
            date
        )

        tv_events = get_tv_events_for_day(
            date
        )

        message = create_football_message(
            date,
            matches,
            tv_events,
        )

        await query.edit_message_text(
            message,
            reply_markup=football_menu(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # FOOTBALL NEXT 7 DAYS
    # --------------------------------------------------------

    if data == "football_upcoming":

        await query.edit_message_text(
            "⏳ **Loading Premier League fixtures...**\n\n"
            "Checking the next 7 days and TV listings.",
            parse_mode="Markdown",
        )

        events = get_next_7_days_events(
            "football"
        )

        message = create_next_7_days_message(
            "football",
            events,
        )

        await query.edit_message_text(
            message,
            reply_markup=football_menu(),
            parse_mode="Markdown",
        )

        return

    # --------------------------------------------------------
    # GENERIC SPORT TODAY
    # --------------------------------------------------------

    for sport_key in SPORTS:

        if data == f"{sport_key}_today":

            if sport_key == "football":
                continue

            date = get_uk_date()

            sport_name = SPORTS[
                sport_key
            ]["sport"]

            events = get_events_for_day(
                date=date,
                sport=sport_name,
            )

            tv_events = get_tv_events_for_day(
                date
            )

            message = create_sport_message(
                SPORTS[sport_key]["name"],
                date,
                events,
                tv_events,
            )

            await query.edit_message_text(
                message,
                reply_markup=sport_menu(
                    sport_key
                ),
                parse_mode="Markdown",
            )

            return

    # --------------------------------------------------------
    # GENERIC SPORT NEXT 7 DAYS
    # --------------------------------------------------------

    for sport_key in SPORTS:

        if data == f"{sport_key}_upcoming":

            await query.edit_message_text(
                "⏳ **Loading...**\n\n"
                "Checking the next 7 days and TV listings.",
                parse_mode="Markdown",
            )

            events = get_next_7_days_events(
                sport_key
            )

            message = create_next_7_days_message(
                sport_key,
                events,
            )

            await query.edit_message_text(
                message,
                reply_markup=sport_menu(
                    sport_key
                ),
                parse_mode="Markdown",
            )

            return

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


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE,
):

    logger.error(
        "Telegram error:",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print(
        "SportPulseAlerts is starting..."
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
        drop_pending_updates=True
    )


# ============================================================
# START BOT
# ============================================================

if __name__ == "__main__":

    main()
