import os
import logging
import threading
import html
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, HTTPServer

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
# CONFIG & SECURITY LOCKS
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SPORTSDB_API_KEY = os.getenv("SPORTSDB_API_KEY")

SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"
UK_TIMEZONE = ZoneInfo("Europe/London")

# The bot will only respond to group messages inside this exact topic
ALLOWED_CHAT_ID = "3988874271"
ALLOWED_TOPIC_ID = "10394"


# ============================================================
# MY APP CHANNELS & SPORT CATEGORIES
# ============================================================

MY_CHANNELS = [
    "sky sports",
    "tnt sports",
    "amazon prime",
    "stan sport",
    "fubo",
    "espn",
    "now prem",
    "now 4k",
    "star sports",
    "vidio",
    "coupang play",
    "astro",
    "bein sports",
    "sky sport",
    "hub premier",
    "supersport",
    "monomax",
    "usa network",
    "peacock",
    "nbc",
]

CATEGORIES = {
    "football_prem": {
        "icon": "⚽",
        "title": "Premier League",
        "sport": "Soccer",
    },
    "football_champ": {
        "icon": "⚽",
        "title": "Championship",
        "sport": "Soccer",
    },
    "nrl": {
        "icon": "🦘",
        "title": "NRL",
        "sport": "Rugby",
    },
    "superleague": {
        "icon": "🇬🇧",
        "title": "Super League",
        "sport": "Rugby",
    },
    "union": {
        "icon": "🏉",
        "title": "Rugby Union",
        "sport": "Rugby",
    },
    "ufc": {
        "icon": "🥋",
        "title": "UFC",
        "sport": "Fighting",
    },
    "boxing": {
        "icon": "🥊",
        "title": "Boxing",
        "sport": "Fighting",
    },
    "wwe": {
        "icon": "🤼",
        "title": "WWE",
        "sport": "Fighting",
    },
    "golf": {
        "icon": "⛳",
        "title": "Golf",
        "sport": "Golf",
    },
    "darts": {
        "icon": "🎯",
        "title": "Darts",
        "sport": "Darts",
    },
}


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)

logger = logging.getLogger("MatchDayHub")


# ============================================================
# CONFIG CHECK
# ============================================================

if not TELEGRAM_TOKEN or not SPORTSDB_API_KEY:
    raise RuntimeError(
        "Missing TELEGRAM_TOKEN or SPORTSDB_API_KEY. "
        "Check your Bunny.net environment variables."
    )


# ============================================================
# BUNNY.NET HEALTH CHECK SERVER
# ============================================================

class HealthCheckHandler(BaseHTTPRequestHandler):

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Bot is running and healthy!")

    def log_message(self, format, *args):
        pass


def start_health_server():

    port = int(
        os.getenv("PORT", 8080)
    )

    server = HTTPServer(
        ("0.0.0.0", port),
        HealthCheckHandler,
    )

    logger.info(
        "Health check server listening on port %s",
        port,
    )

    server.serve_forever()


# ============================================================
# API & DATA
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
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:

        logger.error(
            "SportsDB Request Error: %s",
            error,
        )

        return None

    except ValueError as error:

        logger.error(
            "SportsDB JSON Error: %s",
            error,
        )

        return None


def date_string(date_value):

    return date_value.strftime(
        "%Y-%m-%d"
    )


def pretty_date(date_value):

    return date_value.strftime(
        "%A %d %B %Y"
    )


# ============================================================
# EVENT FILTERING
# ============================================================

def fetch
