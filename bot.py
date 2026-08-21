```python
import os
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)


# ============================================================
# SETUP
# ============================================================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# You can leave this as 123 for now.
# Later, if you get your own TheSportsDB key, add:
# SPORTSDB_API_KEY=your_key
# to Northflank Environment Variables.
SPORTSDB_API_KEY = os.getenv("SPORTSDB_API_KEY", "123")

if not TELEGRAM_TOKEN:
    raise ValueError("ERROR: TELEGRAM_TOKEN is missing")


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

UK_TZ = ZoneInfo("Europe/London")

SPORTSDB_BASE_URL = (
    f"https://www.thesportsdb.com/api/v1/json/"
    f"{SPORTSDB_API_KEY}"
)


# ============================================================
# SPORTS
# ============================================================

SPORTS = {
    "football": {
        "title": "⚽ Football",
        "api_sport": "Soccer",
    },
    "f1": {
        "title": "🏎 Formula 1",
        "api_sport": "Motorsport",
    },
    "basketball": {
        "title": "🏀 Basketball",
        "api_sport": "Basketball",
    },
    "nfl": {
        "title": "🏈 American Football",
        "api_sport": "American Football",
    },
    "rugby": {
        "title": "🏉 Rugby",
        "api_sport": "Rugby",
    },
    "tennis": {
        "title": "🎾 Tennis",
        "api_sport": "Tennis",
    },
    "darts": {
        "title": "🎯 Darts",
        "api_sport": "Darts",
    },
}


# ============================================================
# API
# ============================================================

def get_events_for_day(sport_name, date_value):
    """
    Get events for one sport on one date.
    """

    url = f"{SPORTSDB_BASE_URL}/eventsday.php"

    params = {
        "d": date_value.strftime("%Y-%m-%d"),
        "s": sport_name,
    }

    try:
        response = requests.get(
            url,
            params=params,
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()

        events = data.get("events")

        if not events:
            return []

        return events

    except Exception as error:
        logger.error(
            "TheSportsDB request failed: %s",
            error,
        )

        return []


def get_today_events(sport_key):
    """
    Get today's events.
    """

    sport = SPORTS[sport_key]

    today = datetime.now(UK_TZ).date()

    return get_events_for_day(
        sport["api_sport"],
        today,
    )


def get_upcoming_events(sport_key, days=7):
    """
    Get upcoming events for the next 7 days.
    """

    sport = SPORTS[sport_key]

    today = datetime.now(UK_TZ).date()

    all_events = []

    for day_number in range(days + 1):

        event_date = today + timedelta(days=day_number)

        events = get_events_for_day(
            sport["api_sport"],
            event_date,
        )

        if events:
            all_events.extend(events)

    # Remove duplicate events
    unique_events = {}

    for event in all_events:

        event_id = event.get("idEvent")

        if event_id:
            unique_events[event_id] = event
        else:
            event_name = event.get("strEvent", "")
            event_date = event.get("dateEvent", "")
            unique_events[
                f"{event_name}-{event_date}"
            ] = event

    return list(unique_events.values())


# ============================================================
# EVENT FORMATTING
# ============================================================

def format_event_time(event):

    event_time = event.get("strTime")

    if not event_time:
        return "Time TBC"

    try:

        event_date = event.get("dateEvent")

        if event_date:

            event_datetime = datetime.strptime(
                f"{event_date} {event_time}",
                "%Y-%m-%d %H:%M:%S",
            )

            return event_datetime.strftime("%H:%M")

        return event_time[:5]

    except Exception:
        return event_time[:5]


def format_event(event):

    home_team = event.get("strHomeTeam")
    away_team = event.get("strAwayTeam")

    event_name = event.get("strEvent")

    league = event.get("strLeague")

    event_date = event.get("dateEvent")

    event_time = format_event_time(event)

    text = ""

    if home_team and away_team:

        text += f"🏟 *{home_team} vs {away_team}*\n"

    elif event_name:

        text += f"🏟 *{event_name}*\n"

    else:

        text += "🏟 *Event details unavailable*\n"

    if league:

        text += f"🏆 {league}\n"

    if event_date:

        try:

            formatted_date = datetime.strptime(
                event_date,
                "%Y-%m-%d",
            ).strftime("%a %d %b")

            text += f"📅 {formatted_date}\n"

        except Exception:

            text += f"📅 {event_date}\n"

    text += f"🕒 {event_time}\n"

    return text


def format_events(
    sport_key,
    events,
    heading,
):
    """
    Turn events into a Telegram message.
    """

    sport = SPORTS[sport_key]

    if not events:

        return (
            f"{sport['title']} - *{heading}*\n\n"
            "📭 No fixtures found right now."
        )

    # Sort events by date and time
    events.sort(
        key=lambda event: (
            event.get("dateEvent") or "",
            event.get("strTime") or "",
        )
    )

    text = (
        f"{sport['title']} - *{heading}*\n\n"
    )

    # Telegram messages have a size limit.
    # Show up to 15 fixtures.
    for event in events[:15]:

        text += format_event(event)
        text += "\n"

    if len(events) > 15:

        text += (
            f"📋 Showing the first 15 of "
            f"{len(events)} fixtures."
        )

    return text


# ============================================================
# MENUS
# ============================================================

def main_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "⚽ Football",
                callback_data="sport:football",
            ),
            InlineKeyboardButton(
                "🏎 Formula 1",
                callback_data="sport:f1",
            ),
        ],
        [
            InlineKeyboardButton(
                "🏀 Basketball",
                callback_data="sport:basketball",
            ),
            InlineKeyboardButton(
                "🏈 NFL",
                callback_data="sport:nfl",
            ),
        ],
        [
            InlineKeyboardButton(
                "🏉 Rugby",
                callback_data="sport:rugby",
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
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def sport_menu(sport_key):

    keyboard = [
        [
            InlineKeyboardButton(
                "📅 Today",
                callback_data=f"today:{sport_key}",
            ),
            InlineKeyboardButton(
                "📆 Next 7 Days",
                callback_data=f"next:{sport_key}",
            ),
        ],
        [
            InlineKeyboardButton(
                "⬅️ Main Menu",
                callback_data="main",
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


def loading_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="main",
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# START
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🏆 *SPORTS TV BOT*\n\n"
        "Choose a sport:",
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

    await update.message.reply_text(
        "⏳ Loading today's football fixtures...",
    )

    events = get_today_events("football")

    text = format_events(
        "football",
        events,
        "Today's Matches",
    )

    await update.message.reply_text(
        text,
        reply_markup=sport_menu("football"),
        parse_mode="Markdown",
    )


# ============================================================
# /SPORTS
# ============================================================

async def sports_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🏆 *SPORTS TV BOT*\n\n"
        "Choose a sport:",
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

    choice = query.data


    # --------------------------------------------------------
    # MAIN MENU
    # --------------------------------------------------------

    if choice == "main":

        await query.edit_message_text(
            "🏆 *SPORTS TV BOT*\n\n"
            "Choose a sport:",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )

        return


    # --------------------------------------------------------
    # SPORT MENU
    # --------------------------------------------------------

    if choice.startswith("sport:"):

        sport_key = choice.split(":")[1]

        if sport_key not in SPORTS:

            await query.edit_message_text(
                "❌ Sport not found.",
                reply_markup=main_menu(),
            )

            return

        sport = SPORTS[sport_key]

        await query.edit_message_text(
            f"{sport['title']}\n\n"
            "Choose an option:",
            reply_markup=sport_menu(sport_key),
        )

        return


    # --------------------------------------------------------
    # TODAY
    # --------------------------------------------------------

    if choice.startswith("today:"):

        sport_key = choice.split(":")[1]

        if sport_key not in SPORTS:

            return

        sport = SPORTS[sport_key]

        await query.edit_message_text(
            f"⏳ Loading {sport['title']} fixtures...",
            reply_markup=loading_menu(),
        )

        events = get_today_events(sport_key)

        text = format_events(
            sport_key,
            events,
            "Today's Fixtures",
        )

        await query.edit_message_text(
            text,
            reply_markup=sport_menu(sport_key),
            parse_mode="Markdown",
        )

        return


    # --------------------------------------------------------
    # NEXT 7 DAYS
    # --------------------------------------------------------

    if choice.startswith("next:"):

        sport_key = choice.split(":")[1]

        if sport_key not in SPORTS:

            return

        sport = SPORTS[sport_key]

        await query.edit_message_text(
            f"⏳ Loading upcoming {sport['title']} fixtures...",
            reply_markup=loading_menu(),
        )

        events = get_upcoming_events(
            sport_key,
            days=7,
        )

        text = format_events(
            sport_key,
            events,
            "Next 7 Days",
        )

        await query.edit_message_text(
            text,
            reply_markup=sport_menu(sport_key),
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
        "Exception while handling an update:",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    application = (
        ApplicationBuilder()
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
        CommandHandler(
            "sports",
            sports_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            button_handler,
        )
    )

    application.add_error_handler(
        error_handler
    )

    print("Sports TV Bot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()
```
