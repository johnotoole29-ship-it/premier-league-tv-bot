```python
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
# ENVIRONMENT VARIABLES
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
# UK TV CHANNELS
# ============================================================

OFFICIAL_TV = {
    (
        "2026-08-21",
        "arsenal",
        "coventry city",
    ): "Sky Sports Premier League",

    (
        "2026-08-22",
        "hull city",
        "manchester united",
    ): "TNT Sports",

    (
        "2026-08-22",
        "brentford",
        "tottenham hotspur",
    ): "Sky Sports Premier League",
}


# ============================================================
# FALLBACK FIXTURES
#
# Used if TheSportsDB does not return fixtures.
# ============================================================

FALLBACK_FIXTURES = {
    "2026-08-21": [
        {
            "strHomeTeam": "Arsenal",
            "strAwayTeam": "Coventry City",
            "strTime": "20:00:00",
            "strLeague": "English Premier League",
        }
    ],

    "2026-08-22": [
        {
            "strHomeTeam": "Hull City",
            "strAwayTeam": "Manchester United",
            "strTime": "12:30:00",
            "strLeague": "English Premier League",
        },
        {
            "strHomeTeam": "Ipswich Town",
            "strAwayTeam": "Sunderland",
            "strTime": "15:00:00",
            "strLeague": "English Premier League",
        },
        {
            "strHomeTeam": "Nottingham Forest",
            "strAwayTeam": "Leeds United",
            "strTime": "15:00:00",
            "strLeague": "English Premier League",
        },
        {
            "strHomeTeam": "Everton",
            "strAwayTeam": "Crystal Palace",
            "strTime": "15:00:00",
            "strLeague": "English Premier League",
        },
        {
            "strHomeTeam": "Brentford",
            "strAwayTeam": "Tottenham Hotspur",
            "strTime": "17:30:00",
            "strLeague": "English Premier League",
        },
    ],
}


# ============================================================
# MAIN SPORTS MENU
# ============================================================

def main_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "⚽ Football",
                callback_data="football",
            ),
            InlineKeyboardButton(
                "🏎️ Formula 1",
                callback_data="f1",
            ),
        ],
        [
            InlineKeyboardButton(
                "🏀 Basketball",
                callback_data="basketball",
            ),
            InlineKeyboardButton(
                "🏈 NFL",
                callback_data="nfl",
            ),
        ],
        [
            InlineKeyboardButton(
                "🏉 Rugby",
                callback_data="rugby",
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
                callback_data="today",
            ),
        ],
        [
            InlineKeyboardButton(
                "🔜 Upcoming Premier League Games",
                callback_data="upcoming",
            ),
        ],
        [
            InlineKeyboardButton(
                "⬅️ Back to Sports",
                callback_data="back",
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# BACK MENU
# ============================================================

def back_menu():

    keyboard = [
        [
            InlineKeyboardButton(
                "⬅️ Back to Sports",
                callback_data="back",
            ),
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# ============================================================
# GET UK DATE
# ============================================================

def get_uk_date():

    return datetime.now(
        UK_TIMEZONE
    ).strftime("%Y-%m-%d")


# ============================================================
# GET TV CHANNEL
# ============================================================

def get_tv_channel(
    date,
    home_team,
    away_team,
):

    key = (
        date,
        home_team.lower().strip(),
        away_team.lower().strip(),
    )

    return OFFICIAL_TV.get(
        key,
        "Premiership folder",
    )


# ============================================================
# GET PREMIER LEAGUE MATCHES
# ============================================================

def get_premier_league_matches(date):

    url = (
        "https://www.thesportsdb.com/api/v1/json/"
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

        events = data.get(
            "events",
            [],
        )

        premier_league_games = []

        for event in events:

            league = event.get(
                "strLeague",
                "",
            )

            if (
                "Premier League" in league
                or "English Premier League" in league
            ):

                premier_league_games.append(
                    event
                )

        # If TheSportsDB found games, use them
        if premier_league_games:

            return premier_league_games

        # Otherwise use our fallback fixtures
        return FALLBACK_FIXTURES.get(
            date,
            [],
        )

    except Exception as error:

        logger.error(
            "Error getting football matches: %s",
            error,
        )

        # If API fails, still use fallback fixtures
        return FALLBACK_FIXTURES.get(
            date,
            [],
        )


# ============================================================
# FORMAT MATCH TIME
# ============================================================

def format_match_time(event):

    match_time = event.get(
        "strTime"
    )

    if not match_time:

        return "Time TBC"

    return match_time[:5]


# ============================================================
# FORMAT DATE FOR DISPLAY
# ============================================================

def format_display_date(date):

    try:

        date_object = datetime.strptime(
            date,
            "%Y-%m-%d",
        )

        return date_object.strftime(
            "%A %-d %B %Y"
        )

    except Exception:

        return date


# ============================================================
# CREATE MATCH MESSAGE
# ============================================================

def create_matches_message(
    date,
    matches,
):

    display_date = format_display_date(
        date
    )

    if not matches:

        return (
            "⚽ *PREMIER LEAGUE TODAY*\n\n"
            f"📅 {display_date}\n\n"
            "😴 There are no Premier League games today."
        )

    message = (
        "⚽ *PREMIER LEAGUE TODAY*\n\n"
        f"📅 {display_date}\n\n"
    )

    for event in matches:

        home_team = event.get(
            "strHomeTeam",
            "Home Team",
        )

        away_team = event.get(
            "strAwayTeam",
            "Away Team",
        )

        match_time = format_match_time(
            event
        )

        channel = get_tv_channel(
            date,
            home_team,
            away_team,
        )

        message += (
            f"⚽ {home_team} vs {away_team}\n"
            f"🕒 {match_time}\n"
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
        "Choose a sport below 👇",
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

    matches = get_premier_league_matches(
        date
    )

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

async def upcoming_matches(query):

    await query.edit_message_text(
        "🔜 *UPCOMING PREMIER LEAGUE MATCHES*\n\n"
        "This section will show upcoming matches next.",
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


    # BACK TO MAIN MENU

    if choice == "back":

        await query.edit_message_text(
            "🏆 *SPORTS TV BOT*\n\n"
            "Choose a sport below 👇",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )


    # FOOTBALL

    elif choice == "football":

        await query.edit_message_text(
            "⚽ *FOOTBALL*\n\n"
            "Choose an option below 👇",
            reply_markup=football_menu(),
            parse_mode="Markdown",
        )


    # TODAY

    elif choice == "today":

        date = get_uk_date()

        await query.edit_message_text(
            "⏳ Getting today's Premier League matches..."
        )

        matches = get_premier_league_matches(
            date
        )

        message = create_matches_message(
            date,
            matches,
        )

        await query.edit_message_text(
            message,
            reply_markup=football_menu(),
            parse_mode="Markdown",
        )


    # UPCOMING

    elif choice == "upcoming":

        await upcoming_matches(
            query
        )


    # FORMULA 1

    elif choice == "f1":

        await query.edit_message_text(
            "🏎️ *FORMULA 1*\n\n"
            "F1 races and TV coverage will be added here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )


    # BASKETBALL

    elif choice == "basketball":

        await query.edit_message_text(
            "🏀 *BASKETBALL*\n\n"
            "Basketball games and TV coverage will be added here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )


    # NFL

    elif choice == "nfl":

        await query.edit_message_text(
            "🏈 *NFL*\n\n"
            "NFL games and TV coverage will be added here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )


    # RUGBY

    elif choice == "rugby":

        await query.edit_message_text(
            "🏉 *RUGBY*\n\n"
            "Rugby fixtures and TV coverage will be added here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )


    # TENNIS

    elif choice == "tennis":

        await query.edit_message_text(
            "🎾 *TENNIS*\n\n"
            "Tennis events and TV coverage will be added here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )


    # DARTS

    elif choice == "darts":

        await query.edit_message_text(
            "🎯 *DARTS*\n\n"
            "Darts events and TV coverage will be added here.",
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
        "Sports TV Bot is running..."
    )


    application.run_polling()


# ============================================================
# RUN BOT
# ============================================================

if __name__ == "__main__":
    main()
```
