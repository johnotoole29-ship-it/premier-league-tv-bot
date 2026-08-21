import os
import logging
from datetime import datetime
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
# SETTINGS
# ============================================================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "123")

UK_TIMEZONE = ZoneInfo("Europe/London")

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)

# ============================================================
# FALLBACK MATCHES
# These are used if TheSportsDB does not return the fixture.
# ============================================================

FALLBACK_FIXTURES = {
    "2026-08-21": [
        {
            "home": "Arsenal",
            "away": "Coventry City",
            "time": "20:00",
            "channel": "Sky Sports Premier League",
        }
    ],
}

# ============================================================
# MAIN MENU
# ============================================================

def main_menu():
    keyboard = [
        [
            InlineKeyboardButton("⚽ Football", callback_data="football"),
            InlineKeyboardButton("🏎️ Formula 1", callback_data="f1"),
        ],
        [
            InlineKeyboardButton("🏀 Basketball", callback_data="basketball"),
            InlineKeyboardButton("🏈 NFL", callback_data="nfl"),
        ],
        [
            InlineKeyboardButton("🏉 Rugby", callback_data="rugby"),
            InlineKeyboardButton("🎾 Tennis", callback_data="tennis"),
        ],
        [
            InlineKeyboardButton("🎯 Darts", callback_data="darts"),
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
                "📅 Today's Matches",
                callback_data="today",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔜 Upcoming Matches",
                callback_data="upcoming",
            ),
        ],
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="back",
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# GET TODAY'S DATE IN UK
# ============================================================

def get_uk_date():
    return datetime.now(UK_TIMEZONE).strftime("%Y-%m-%d")


# ============================================================
# GET PREMIER LEAGUE MATCHES
# ============================================================

def get_matches(date):

    fallback = FALLBACK_FIXTURES.get(date, [])

    try:
        url = (
            "https://www.thesportsdb.com/api/v1/json/"
            f"{FOOTBALL_API_KEY}/eventsday.php"
        )

        response = requests.get(
            url,
            params={
                "d": date,
                "s": "Soccer",
            },
            timeout=15,
        )

        response.raise_for_status()

        data = response.json()
        events = data.get("events") or []

        matches = []

        for event in events:
            league = event.get("strLeague") or ""

            if "Premier League" in league:
                matches.append(
                    {
                        "home": event.get(
                            "strHomeTeam",
                            "Home Team",
                        ),
                        "away": event.get(
                            "strAwayTeam",
                            "Away Team",
                        ),
                        "time": (
                            event.get("strTime") or "Time TBC"
                        )[:5],
                        "channel": "TV channel TBC",
                    }
                )

        if matches:
            return matches

    except Exception as error:
        logger.error("Football API error: %s", error)

    return fallback


# ============================================================
# CREATE MATCH MESSAGE
# ============================================================

def create_match_message(date, matches):

    try:
        display_date = datetime.strptime(
            date,
            "%Y-%m-%d",
        ).strftime("%A %d %B %Y")

    except ValueError:
        display_date = date

    if not matches:
        return (
            "⚽ PREMIER LEAGUE\n\n"
            f"📅 {display_date}\n\n"
            "No Premier League matches found today."
        )

    message = (
        "⚽ PREMIER LEAGUE\n\n"
        f"📅 {display_date}\n\n"
    )

    for match in matches:
        message += (
            f"⚽ {match['home']} vs {match['away']}\n"
            f"🕒 {match['time']}\n"
            f"📺 {match['channel']}\n\n"
        )

    return message


# ============================================================
# START COMMAND
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    await update.message.reply_text(
        "🏆 SPORTS TV BOT\n\n"
        "Choose a sport below:",
        reply_markup=main_menu(),
    )


# ============================================================
# TODAY COMMAND
# ============================================================

async def today(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    date = get_uk_date()
    matches = get_matches(date)

    message = create_match_message(
        date,
        matches,
    )

    await update.message.reply_text(
        message,
        reply_markup=football_menu(),
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

    if choice == "back":

        await query.edit_message_text(
            "🏆 SPORTS TV BOT\n\n"
            "Choose a sport below:",
            reply_markup=main_menu(),
        )

    elif choice == "football":

        await query.edit_message_text(
            "⚽ FOOTBALL\n\n"
            "Choose an option:",
            reply_markup=football_menu(),
        )

    elif choice == "today":

        date = get_uk_date()
        matches = get_matches(date)

        message = create_match_message(
            date,
            matches,
        )

        await query.edit_message_text(
            message,
            reply_markup=football_menu(),
        )

    elif choice == "upcoming":

        await query.edit_message_text(
            "🔜 UPCOMING MATCHES\n\n"
            "Coming soon.",
            reply_markup=football_menu(),
        )

    elif choice == "f1":

        await query.edit_message_text(
            "🏎️ FORMULA 1\n\nComing soon.",
            reply_markup=main_menu(),
        )

    elif choice == "basketball":

        await query.edit_message_text(
            "🏀 BASKETBALL\n\nComing soon.",
            reply_markup=main_menu(),
        )

    elif choice == "nfl":

        await query.edit_message_text(
            "🏈 NFL\n\nComing soon.",
            reply_markup=main_menu(),
        )

    elif choice == "rugby":

        await query.edit_message_text(
            "🏉 RUGBY\n\nComing soon.",
            reply_markup=main_menu(),
        )

    elif choice == "tennis":

        await query.edit_message_text(
            "🎾 TENNIS\n\nComing soon.",
            reply_markup=main_menu(),
        )

    elif choice == "darts":

        await query.edit_message_text(
            "🎯 DARTS\n\nComing soon.",
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
        "Exception while handling update",
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    if not TELEGRAM_TOKEN:
        raise ValueError(
            "TELEGRAM_TOKEN is missing"
        )

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("today", today)
    )

    application.add_handler(
        CallbackQueryHandler(button_handler)
    )

    application.add_error_handler(
        error_handler
    )

    print("Sports TV Bot is running...")

    application.run_polling()


if __name__ == "__main__":
    main()
