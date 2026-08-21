import os
import json
import logging
import asyncio
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
    MessageHandler,
    ContextTypes,
    filters,
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

DATA_FILE = "sportpulse_data.json"


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("SportPulseAlerts")


# ============================================================
# CONFIG CHECK
# ============================================================

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN is missing. "
        "Add it to Bunny.net environment variables."
    )

if not SPORTSDB_API_KEY:
    raise RuntimeError(
        "SPORTSDB_API_KEY is missing. "
        "Add your TheSportsDB API key."
    )


# ============================================================
# DATA STORAGE
# ============================================================

def load_data():

    try:

        if not os.path.exists(DATA_FILE):
            return {
                "users": {}
            }

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        data.setdefault(
            "users",
            {}
        )

        return data

    except Exception as error:

        logger.error(
            "Could not load data: %s",
            error,
        )

        return {
            "users": {}
        }


def save_data(data):

    try:

        with open(
            DATA_FILE,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                indent=2,
                ensure_ascii=False,
            )

    except Exception as error:

        logger.error(
            "Could not save data: %s",
            error,
        )


DATA = load_data()


def get_user_data(user_id):

    user_id = str(user_id)

    if user_id not in DATA["users"]:

        DATA["users"][user_id] = {
            "teams": [],
            "alerts": [],
        }

        save_data(DATA)

    return DATA["users"][user_id]


# ============================================================
# DATE / TIME
# ============================================================

def uk_now():

    return datetime.now(
        UK_TIMEZONE
    )


def uk_date(
    offset=0
):

    return (
        uk_now()
        + timedelta(days=offset)
    ).strftime(
        "%Y-%m-%d"
    )


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


def format_event_datetime(
    event
):

    date_string = (
        event.get("dateEvent")
        or event.get("dateEventLocal")
    )

    time_string = (
        event.get("strTime")
        or event.get("strEventTime")
        or "00:00:00"
    )

    if not date_string:
        return None

    try:

        clean_time = str(
            time_string
        )[:8]

        if len(clean_time) == 5:
            clean_time += ":00"

        naive = datetime.strptime(
            f"{date_string} {clean_time}",
            "%Y-%m-%d %H:%M:%S",
        )

        return naive.replace(
            tzinfo=UK_TIMEZONE
        )

    except Exception:

        return None


def format_match_time(
    event
):

    event_time = (
        event.get("strTime")
        or event.get("strEventTime")
    )

    if not event_time:
        return "TBC"

    return str(event_time)[:5]


# ============================================================
# THE SPORTS DB
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
            "SportsDB request failed: %s",
            error,
        )

        return None

    except ValueError as error:

        logger.error(
            "Invalid SportsDB JSON: %s",
            error,
        )

        return None


# ============================================================
# EVENTS
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


def get_sport_events(
    date,
    sport,
):

    return get_events_for_day(
        date,
        sport=sport,
    )


# ============================================================
# PREMIER LEAGUE
# ============================================================

def get_premier_league(
    date
):

    events = get_events_for_day(
        date,
        sport="Soccer",
        league="English Premier League",
    )

    if events:
        return events

    events = get_sport_events(
        date,
        "Soccer",
    )

    return [
        event
        for event in events
        if "premier league"
        in (
            event.get("strLeague")
            or ""
        ).lower()
    ]


# ============================================================
# CHAMPIONSHIP
# ============================================================

def get_championship(
    date
):

    events = get_events_for_day(
        date,
        sport="Soccer",
        league="English League Championship",
    )

    if events:
        return events

    events = get_sport_events(
        date,
        "Soccer",
    )

    return [
        event
        for event in events
        if "championship"
        in (
            event.get("strLeague")
            or ""
        ).lower()
    ]


# ============================================================
# RUGBY UNION
# ============================================================

def get_rugby_union(
    date
):

    events = get_sport_events(
        date,
        "Rugby",
    )

    excluded = [
        "super league",
        "nrl",
        "national rugby league",
    ]

    results = []

    for event in events:

        league = (
            event.get("strLeague")
            or ""
        ).lower()

        if not any(
            x in league
            for x in excluded
        ):

            results.append(event)

    return results


# ============================================================
# SUPER LEAGUE
# ============================================================

def get_super_league(
    date
):

    events = get_sport_events(
        date,
        "Rugby",
    )

    return [
        event
        for event in events
        if "super league"
        in (
            event.get("strLeague")
            or ""
        ).lower()
    ]


# ============================================================
# NRL
# ============================================================

def get_nrl(
    date
):

    events = get_sport_events(
        date,
        "Rugby",
    )

    results = []

    for event in events:

        league = (
            event.get("strLeague")
            or ""
        ).lower()

        name = (
            event.get("strEvent")
            or ""
        ).lower()

        if (
            "nrl" in league
            or "national rugby league" in league
            or "nrl" in name
        ):

            results.append(event)

    return results


# ============================================================
# SPORT MENU DATA
# ============================================================

def get_sport_events_for_menu(
    date,
    sport_key
):

    if sport_key == "premier":

        return get_premier_league(
            date
        )

    if sport_key == "championship":

        return get_championship(
            date
        )

    if sport_key == "rugby_union":

        return get_rugby_union(
            date
        )

    if sport_key == "super_league":

        return get_super_league(
            date
        )

    if sport_key == "nrl":

        return get_nrl(
            date
        )

    sport_name = {
        "football": "Soccer",
        "cricket": "Cricket",
        "tennis": "Tennis",
        "darts": "Darts",
        "f1": "Motorsport",
        "golf": "Golf",
        "combat": "Fighting",
    }.get(
        sport_key
    )

    if sport_name:

        return get_sport_events(
            date,
            sport_name,
        )

    return []


# ============================================================
# TV BROADCASTS
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

        event_id = (
            broadcast.get("idEvent")
            or broadcast.get("id")
        )

        if not event_id:
            continue

        channel = (
            broadcast.get("strChannel")
            or broadcast.get("strEvent")
            or broadcast.get("strName")
        )

        country = (
            broadcast.get("strCountry")
            or broadcast.get("strLocation")
            or ""
        )

        if not channel:
            continue

        tv_by_event.setdefault(
            str(event_id),
            [],
        ).append(
            {
                "channel": str(
                    channel
                ).strip(),

                "country": str(
                    country
                ).strip(),
            }
        )

    return tv_by_event


def get_tv_for_event(
    event
):

    event_id = event.get(
        "idEvent"
    )

    if not event_id:
        return []

    data = sportsdb_get(
        "lookuptv.php",
        {
            "id": event_id,
        },
    )

    if not data:
        return []

    broadcasts = (
        data.get("tvevents")
        or data.get("events")
        or []
    )

    results = []

    for broadcast in broadcasts:

        channel = (
            broadcast.get("strChannel")
            or broadcast.get("strEvent")
            or broadcast.get("strName")
        )

        country = (
            broadcast.get("strCountry")
            or broadcast.get("strLocation")
            or ""
        )

        if channel:

            results.append(
                {
                    "channel": str(
                        channel
                    ).strip(),

                    "country": str(
                        country
                    ).strip(),
                }
            )

    return clean_tv_channels(
        results
    )


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
            channel.lower(),
            country.lower(),
        )

        if key in seen:
            continue

        seen.add(key)

        cleaned.append(
            {
                "channel": channel,
                "country": country,
            }
        )

    return cleaned


# ============================================================
# UK TV
# ============================================================

def is_uk_channel(
    item
):

    country = (
        item.get("country")
        or ""
    ).lower().strip()

    uk_names = {
        "united kingdom",
        "uk",
        "england",
        "scotland",
        "wales",
        "northern ireland",
        "great britain",
    }

    if country in uk
