import os
import logging
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes
)


# Load keys from .env
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
FOOTBALL_API_KEY = os.getenv("FOOTBALL_API_KEY")

# TheSportsDB free key
SPORTSDB_API_KEY = "123"

# UK timezone
UK_TIMEZONE = ZoneInfo("Europe/London")


# Verified UK TV selections
OFFICIAL_TV = {
    (
        "2026-08-21",
        "arsenal",
        "coventry city"
    ): "Sky Sports Premier League",

    (
        "2026-08-22",
        "hull city",
        "manchester united"
    ): "TNT Sports",

    (
        "2026-08-22",
        "brentford",
        "tottenham hotspur"
    ): "Sky Sports Premier League",
}


# Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)


def clean_team_name(name):

    name = name.lower()

    for ending in [
        " fc",
        " afc"
    ]:
        if name.endswith(ending):
            name = name[:-len(ending)]

    return name.strip()


def get_official_tv_channel(
    home,
    away,
    match_day
):

    key = (
        match_day,
        clean_team_name(home),
        clean_team_name(away)
    )

    return OFFICIAL_TV.get(key)


def get_tv_channel(
    home,
    away,
    match_day
):

    # Check verified TV selections first
    official_channel = get_official_tv_channel(
        home,
        away,
        match_day
    )

    if official_channel:

        print(
            "Verified TV channel:",
            official_channel
        )

        return official_channel

    try:

        # Create event name for TheSportsDB
        event_name = (
            f"{home.replace(' FC', '').replace(' AFC', '')}"
            f"_vs_"
            f"{away.replace(' FC', '').replace(' AFC', '')}"
        )

        search_url = (
            "https://www.thesportsdb.com/"
            "api/v1/json/"
            f"{SPORTSDB_API_KEY}/"
            "searchevents.php"
        )

        response = requests.get(
            search_url,
            params={
                "e": event_name,
                "d": match_day
            },
            timeout=10
        )

        events = response.json().get(
            "event"
        )

        if not events:
            return "Premier League Football"

        event_id = events[0].get(
            "idEvent"
        )

        if not event_id:
            return "Premier League Football"

        # Look up TV channels
        tv_url = (
            "https://www.thesportsdb.com/"
            "api/v1/json/"
            f"{SPORTSDB_API_KEY}/"
            "lookuptv.php"
        )

        tv_response = requests.get(
            tv_url,
            params={
                "id": event_id
            },
            timeout=10
        )

        tv_channels = tv_response.json().get(
            "tvevent"
        )

        if not tv_channels:
            return "Premier League Football"

        uk_channels = []

        for channel in tv_channels:

            channel_name = channel.get(
                "strChannel",
                ""
            )

            country = channel.get(
                "strCountry",
                ""
            ).lower()

            if not channel_name:
                continue

            if country in [
                "united kingdom",
                "uk",
                "england",
                "great britain"
            ]:

                uk_channels.append(
                    channel_name
                )

        if uk_channels:

            # Remove duplicate channels
            uk_channels = list(
                dict.fromkeys(
                    uk_channels
                )
            )

            return ", ".join(
                uk_channels
            )

        # No UK TV channel found
        return "Premier League Football"

    except Exception as error:

        print(
            "TV lookup error:",
            error
        )

        return "Premier League Football"


async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(
        "⚽ PREMIER LEAGUE TV BOT\n\n"
        "See today's Premier League matches "
        "and where they are showing.\n\n"
        "Type:\n"
        "/today"
    )


async def today(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    # REAL UK DATE
    today_date = datetime.now(
        UK_TIMEZONE
    ).date()

    print(
        "Looking for matches on:",
        today_date
    )

    # Get Premier League matches
    url = (
        "https://api.football-data.org/"
        "v4/competitions/PL/matches"
    )

    headers = {
        "X-Auth-Token": FOOTBALL_API_KEY
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:

            print(
                "Football API error:",
                response.status_code
            )

            await update.message.reply_text(
                "❌ I couldn't get today's matches."
            )

            return

        matches = response.json().get(
            "matches",
            []
        )

        today_matches = []

        # Find only matches happening today
        for match in matches:

            match_date = (
                datetime.fromisoformat(
                    match["utcDate"].replace(
                        "Z",
                        "+00:00"
                    )
                ).astimezone(
                    UK_TIMEZONE
                )
            )

            if match_date.date() == today_date:

                today_matches.append(
                    (
                        match,
                        match_date
                    )
                )

        # Sort matches by kick-off time
        today_matches.sort(
            key=lambda item: item[1]
        )

        # No matches today
        if not today_matches:

            await update.message.reply_text(
                "⚽ PREMIER LEAGUE TODAY\n\n"
                f"📅 "
                f"{today_date.strftime('%A %d %B %Y')}\n\n"
                "😴 There are no Premier League "
                "games today."
            )

            return

        # Start building the message
        message = (
            "⚽ PREMIER LEAGUE TODAY\n\n"
            f"📅 "
            f"{today_date.strftime('%A %d %B %Y')}"
        )

        # Add each match
        for match, match_date in today_matches:

            home = match[
                "homeTeam"
            ]["name"]

            away = match[
                "awayTeam"
            ]["name"]

            match_day = match[
                "utcDate"
            ][:10]

            tv_channel = get_tv_channel(
                home,
                away,
                match_day
            )

            message += (
                "\n\n"
                f"⚽ {home} vs {away}\n"
                f"🕒 "
                f"{match_date.strftime('%H:%M')}\n"
                f"📺 {tv_channel}"
            )

        await update.message.reply_text(
            message
        )

    except Exception as error:

        print(
            "Error:",
            error
        )

        await update.message.reply_text(
            "❌ Something went wrong. "
            "Please try again."
        )


def main():

    if not TELEGRAM_TOKEN:

        print(
            "ERROR: TELEGRAM_TOKEN is missing!"
        )

        return

    if not FOOTBALL_API_KEY:

        print(
            "ERROR: FOOTBALL_API_KEY is missing!"
        )

        return

    print(
        "⚽ Premier League TV bot is starting..."
    )

    app = ApplicationBuilder().token(
        TELEGRAM_TOKEN
    ).build()

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "today",
            today
        )
    )

    print(
        "🤖 Bot is running!"
    )

    app.run_polling()


if __name__ == "__main__":
    main()