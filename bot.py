import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# TheSportsDB free development key
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
# OFFICIAL TV CHANNEL DATA
#
# Add verified UK TV channels here when known.
# Format:
# (date, home team, away team): channel
# ============================================================

OFFICIAL_TV = {
    ("2026-08-21", "arsenal", "coventry city"):
        "Sky Sports Premier League",

    ("2026-08-22", "hull city", "manchester united"):
        "TNT Sports",

    ("2026-08-22", "brentford", "tottenham hotspur"):
        "Sky Sports Premier League",
}


# ============================================================
# MAIN MENU
# ============================================================

def main_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "⚽ Football",
                callback_data="football"
            ),
            InlineKeyboardButton(
                "🏎️ Formula 1",
                callback_data="f1"
            ),
        ],
        [
            InlineKeyboardButton(
                "🏀 Basketball",
                callback_data="basketball"
            ),
            InlineKeyboardButton(
                "🏈 NFL",
                callback_data="nfl"
            ),
        ],
        [
            InlineKeyboardButton(
                "🏉 Rugby",
                callback_data="rugby"
            ),
            InlineKeyboardButton(
                "🎾 Tennis",
                callback_data="tennis"
            ),
        ],
        [
            InlineKeyboardButton(
                "🎯 Darts",
                callback_data="darts"
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
                callback_data="today"
            ),
        ],
        [
            InlineKeyboardButton(
                "🔜 Upcoming Premier League Games",
                callback_data="upcoming"
            ),
        ],
        [
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data="back"
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# BACK BUTTON
# ============================================================

def back_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "⬅️ Back to Sports",
                callback_data="back"
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
# GET TV CHANNEL
# ============================================================

def get_tv_channel(date, home_team, away_team):
    key = (
        date,
        home_team.lower().strip(),
        away_team.lower().strip(),
    )

    return OFFICIAL_TV.get(key, "TV channel not yet confirmed")


# ============================================================
# GET PREMIER LEAGUE MATCHES
# ============================================================

def get_premier_league_matches(date):
    url = (
        f"https://www.thesportsdb.com/api/v1/json/"
        f"{FOOTBALL_API_KEY}/eventsday.php"
    )

    params = {
        "d": date,
        "s": "Soccer",
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

        premier_league_games = []

        for event in events:
            league = event.get("strLeague", "")

            if "Premier League" in league:
                premier_league_games.append(event)

        return premier_league_games

    except Exception as error:
        logger.error(
            f"Error getting football matches: {error}"
        )

        return None


# ============================================================
# FORMAT MATCH TIME
# ============================================================

def format_match_time(event):
    time = event.get("strTime")

    if not time:
        return "Time TBC"

    try:
        return time[:5]
    except Exception:
        return "Time TBC"


# ============================================================
# CREATE FOOTBALL MESSAGE
# ============================================================

def create_matches_message(date, matches):
    if not matches:
        return (
            "⚽ *PREMIER LEAGUE*\n\n"
            f"📅 {date}\n\n"
            "No Premier League matches found."
        )

    message = (
        "⚽ *PREMIER LEAGUE*\n\n"
        f"📅 {date}\n\n"
    )

    for event in matches:
        home_team = event.get(
            "strHomeTeam",
            "Home Team"
        )

        away_team = event.get(
            "strAwayTeam",
            "Away Team"
        )

        match_time = format_match_time(event)

        channel = get_tv_channel(
            date,
            home_team,
            away_team,
        )

        message += (
            f"🕐 *{match_time}*\n"
            f"⚽ {home_team} vs {away_team}\n"
            f"📺 {channel}\n\n"
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
        "🏆 *SPORTS TV BOT*\n\n"
        "Choose a sport:",
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
    date = get_uk_date()

    matches = get_premier_league_matches(date)

    if matches is None:
        await update.message.reply_text(
            "❌ I couldn't get today's matches right now.\n\n"
            "Please try again in a moment."
        )
        return

    message = create_matches_message(
        date,
        matches,
    )

    await update.message.reply_text(
        message,
        reply_markup=football_menu(),
        parse_mode="Markdown",
    )


# ============================================================
# UPCOMING MATCHES
# ============================================================

async def upcoming_matches(
    query,
):
    await query.edit_message_text(
        "🔜 *UPCOMING PREMIER LEAGUE MATCHES*\n\n"
        "This feature is coming next.",
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

    choice = query.data

    # --------------------------------------------------------
    # MAIN MENU
    # --------------------------------------------------------

    if choice == "back":
        await query.edit_message_text(
            "🏆 *SPORTS TV BOT*\n\n"
            "Choose a sport:",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )

    # --------------------------------------------------------
    # FOOTBALL
    # --------------------------------------------------------

    elif choice == "football":
        await query.edit_message_text(
            "⚽ *FOOTBALL*\n\n"
            "Choose an option:",
            reply_markup=football_menu(),
            parse_mode="Markdown",
        )

    # --------------------------------------------------------
    # TODAY'S PREMIER LEAGUE MATCHES
    # --------------------------------------------------------

    elif choice == "today":
        date = get_uk_date()

        await query.edit_message_text(
            "⏳ Getting today's Premier League matches..."
        )

        matches = get_premier_league_matches(date)

        if matches is None:
            await query.edit_message_text(
                "❌ I couldn't get today's matches.\n\n"
                "Please try again later.",
                reply_markup=football_menu(),
            )

            return

        message = create_matches_message(
            date,
            matches,
        )

        await query.edit_message_text(
            message,
            reply_markup=football_menu(),
            parse_mode="Markdown",
        )

    # --------------------------------------------------------
    # UPCOMING FOOTBALL
    # --------------------------------------------------------

    elif choice == "upcoming":
        await upcoming_matches(query)

    # --------------------------------------------------------
    # FORMULA 1
    # --------------------------------------------------------

    elif choice == "f1":
        await query.edit_message_text(
            "🏎️ *FORMULA 1*\n\n"
            "Upcoming F1 races and UK TV coverage "
            "will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # --------------------------------------------------------
    # BASKETBALL
    # --------------------------------------------------------

    elif choice == "basketball":
        await query.edit_message_text(
            "🏀 *BASKETBALL*\n\n"
            "Upcoming basketball games and UK TV "
            "coverage will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # --------------------------------------------------------
    # NFL
    # --------------------------------------------------------

    elif choice == "nfl":
        await query.edit_message_text(
            "🏈 *NFL*\n\n"
            "Upcoming NFL games and UK TV coverage "
            "will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # --------------------------------------------------------
    # RUGBY
    # --------------------------------------------------------

    elif choice == "rugby":
        await query.edit_message_text(
            "🏉 *RUGBY*\n\n"
            "Upcoming rugby matches and UK TV coverage "
            "will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # --------------------------------------------------------
    # TENNIS
    # --------------------------------------------------------

    elif choice == "tennis":
        await query.edit_message_text(
            "🎾 *TENNIS*\n\n"
            "Upcoming tennis tournaments and UK TV "
            "coverage will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # --------------------------------------------------------
    # DARTS
    # --------------------------------------------------------

    elif choice == "darts":
        await query.edit_message_text(
            "🎯 *DARTS*\n\n"
            "Upcoming darts events and UK TV coverage "
            "will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )


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

    if not TELEGRAM_TOKEN:
        raise ValueError(
            "ERROR: TELEGRAM_TOKEN is missing!"
        )

    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    # Commands
    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        CommandHandler("today", today_command)
    )

    # Button clicks
    application.add_handler(
        CallbackQueryHandler(button_handler)
    )

    # Errors
    application.add_error_handler(
        error_handler
    )

    print("Sports TV Bot is running...")

    application.run_polling()


# ============================================================
# RUN BOT
# ============================================================

if __name__ == "__main__":
    main()
