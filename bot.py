import os
import logging
from datetime import datetime
from zoneinfo import ZoneInfo

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

# =========================
# LOAD ENVIRONMENT VARIABLES
# =========================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# TheSportsDB test/development key
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY", "123")

UK_TIMEZONE = ZoneInfo("Europe/London")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger(__name__)


# =========================
# TV CHANNEL DATA
# =========================

OFFICIAL_TV = {
    ("2026-08-21", "arsenal", "coventry city"):
        "Sky Sports Premier League",

    ("2026-08-22", "hull city", "manchester united"):
        "TNT Sports",

    ("2026-08-22", "brentford", "tottenham hotspur"):
        "Sky Sports Premier League",
}


# =========================
# MAIN MENU
# =========================

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


# =========================
# FOOTBALL MENU
# =========================

def football_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "🏴 Premier League",
                callback_data="premier_league"
            )
        ],
        [
            InlineKeyboardButton(
                "🇪🇺 Champions League",
                callback_data="champions_league"
            )
        ],
        [
            InlineKeyboardButton(
                "🇪🇸 La Liga",
                callback_data="la_liga"
            ),
            InlineKeyboardButton(
                "🇮🇹 Serie A",
                callback_data="serie_a"
            ),
        ],
        [
            InlineKeyboardButton(
                "🇩🇪 Bundesliga",
                callback_data="bundesliga"
            )
        ],
        [
            InlineKeyboardButton(
                "⬅️ Back to Sports",
                callback_data="main_menu"
            )
        ],
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# BACK BUTTON
# =========================

def back_menu():
    keyboard = [
        [
            InlineKeyboardButton(
                "⬅️ Back to Sports",
                callback_data="main_menu"
            )
        ]
    ]

    return InlineKeyboardMarkup(keyboard)


# =========================
# START COMMAND
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):

    text = (
        "🏆 *WELCOME TO SPORTS TV BOT*\n\n"
        "Find upcoming sports events and TV information.\n\n"
        "Choose a sport below 👇"
    )

    await update.message.reply_text(
        text,
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


# =========================
# CALLBACK BUTTON HANDLER
# =========================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    query = update.callback_query
    await query.answer()

    choice = query.data

    # -------------------------
    # MAIN MENU
    # -------------------------

    if choice == "main_menu":

        await query.edit_message_text(
            "🏆 *SPORTS TV BOT*\n\nChoose a sport 👇",
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )

    # -------------------------
    # FOOTBALL
    # -------------------------

    elif choice == "football":

        await query.edit_message_text(
            "⚽ *FOOTBALL*\n\nChoose a competition 👇",
            reply_markup=football_menu(),
            parse_mode="Markdown",
        )

    # -------------------------
    # PREMIER LEAGUE
    # -------------------------

    elif choice == "premier_league":

        text = (
            "⚽ *PREMIER LEAGUE*\n\n"
            "Upcoming matches and TV channels will appear here.\n\n"
            "📺 UK TV coverage included where available."
        )

        await query.edit_message_text(
            text,
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # -------------------------
    # CHAMPIONS LEAGUE
    # -------------------------

    elif choice == "champions_league":

        await query.edit_message_text(
            "🇪🇺 *CHAMPIONS LEAGUE*\n\n"
            "Upcoming Champions League fixtures will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # -------------------------
    # LA LIGA
    # -------------------------

    elif choice == "la_liga":

        await query.edit_message_text(
            "🇪🇸 *LA LIGA*\n\n"
            "Upcoming La Liga fixtures will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # -------------------------
    # SERIE A
    # -------------------------

    elif choice == "serie_a":

        await query.edit_message_text(
            "🇮🇹 *SERIE A*\n\n"
            "Upcoming Serie A fixtures will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # -------------------------
    # BUNDESLIGA
    # -------------------------

    elif choice == "bundesliga":

        await query.edit_message_text(
            "🇩🇪 *BUNDESLIGA*\n\n"
            "Upcoming Bundesliga fixtures will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # -------------------------
    # FORMULA 1
    # -------------------------

    elif choice == "f1":

        await query.edit_message_text(
            "🏎️ *FORMULA 1*\n\n"
            "🏁 Next race information will appear here.\n\n"
            "Future update: race date, start time and UK TV channel.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # -------------------------
    # BASKETBALL
    # -------------------------

    elif choice == "basketball":

        await query.edit_message_text(
            "🏀 *BASKETBALL*\n\n"
            "Choose from upcoming NBA and other major basketball events in a future update.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # -------------------------
    # NFL
    # -------------------------

    elif choice == "nfl":

        await query.edit_message_text(
            "🏈 *NFL*\n\n"
            "Upcoming NFL games and UK TV channels will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # -------------------------
    # RUGBY
    # -------------------------

    elif choice == "rugby":

        await query.edit_message_text(
            "🏉 *RUGBY*\n\n"
            "Upcoming rugby fixtures and TV coverage will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # -------------------------
    # TENNIS
    # -------------------------

    elif choice == "tennis":

        await query.edit_message_text(
            "🎾 *TENNIS*\n\n"
            "Upcoming tennis tournaments and UK TV coverage will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )

    # -------------------------
    # DARTS
    # -------------------------

    elif choice == "darts":

        await query.edit_message_text(
            "🎯 *DARTS*\n\n"
            "Upcoming darts events and UK TV coverage will appear here.",
            reply_markup=back_menu(),
            parse_mode="Markdown",
        )


# =========================
# ERROR HANDLER
# =========================

async def error_handler(
    update: object,
    context: ContextTypes.DEFAULT_TYPE
):

    logger.error(
        "Exception while handling an update:",
        exc_info=context.error,
    )


# =========================
# MAIN
# =========================

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
        CommandHandler("start", start)
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
