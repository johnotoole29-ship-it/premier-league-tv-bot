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
# CONFIG & SECURITY
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SPORTSDB_API_KEY = os.getenv("SPORTSDB_API_KEY")

SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"

UK_TIMEZONE = ZoneInfo("Europe/London")

# Group/topic lock
ALLOWED_CHAT_ID = "3988874271"
ALLOWED_TOPIC_ID = "10394"


# ============================================================
# SUPPORTED CHANNELS
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


# ============================================================
# SPORT CATEGORIES
# ============================================================

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

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN is missing from Bunny.net."
    )

if not SPORTSDB_API_KEY:
    raise RuntimeError(
        "SPORTSDB_API_KEY is missing from Bunny.net."
    )


# ============================================================
# BUNNY HEALTH SERVER
# ============================================================

class HealthCheckHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-type",
            "text/plain",
        )

        self.end_headers()

        self.wfile.write(
            b"MatchDay Hub is running."
        )

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
        "Health server running on port %s",
        port,
    )

    server.serve_forever()


# ============================================================
# SPORTSDB REQUEST
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
            timeout=15,
        )

        response.raise_for_status()

        return response.json()

    except requests.RequestException as error:

        logger.error(
            "SportsDB request error: %s",
            error,
        )

        return None

    except ValueError as error:

        logger.error(
            "SportsDB JSON error: %s",
            error,
        )

        return None


# ============================================================
# DATE HELPERS
# ============================================================

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

def fetch_events(
    date_value,
    category,
):

    meta = CATEGORIES.get(
        category
    )

    if not meta:
        return []

    data = sportsdb_get(
        "eventsday.php",
        {
            "d": date_string(date_value),
            "s": meta["sport"],
        },
    )

    if not data:
        return []

    events = data.get("events")

    if not isinstance(
        events,
        list,
    ):
        return []

    filtered = []

    for event in events:

        league_id = str(
            event.get(
                "idLeague",
                "",
            )
        )

        league_name = str(
            event.get("strLeague")
            or ""
        ).strip().lower()

        event_name = str(
            event.get("strEvent")
            or ""
        ).strip().lower()

        combined = (
            league_name
            + " "
            + event_name
        )


        # ====================================================
        # PREMIER LEAGUE - ENGLAND ONLY
        # ====================================================

        if category == "football_prem":

            if (
                league_id == "4328"
                or league_name == "english premier league"
            ):

                filtered.append(
                    event
                )


        # ====================================================
        # CHAMPIONSHIP - ENGLAND ONLY
        # ====================================================

        elif category == "football_champ":

            if (
                league_id == "4329"
                or league_name == "english league championship"
                or league_name == "efl championship"
            ):

                filtered.append(
                    event
                )


        # ====================================================
        # NRL
        # ====================================================

        elif category == "nrl":

            if (
                league_id == "4416"
                or "nrl" in combined
                or "national rugby league" in combined
            ):

                filtered.append(
                    event
                )


        # ====================================================
        # SUPER LEAGUE
        # ====================================================

        elif category == "superleague":

            if (
                league_id == "4415"
                or "super league" in combined
            ):

                filtered.append(
                    event
                )


        # ====================================================
        # RUGBY UNION
        # ====================================================

        elif category == "union":

            if (
                league_id not in [
                    "4415",
                    "4416",
                ]
                and "super league" not in combined
                and "nrl" not in combined
                and "national rugby league" not in combined
            ):

                filtered.append(
                    event
                )


        # ====================================================
        # UFC
        # ====================================================

        elif category == "ufc":

            if (
                league_id == "4443"
                or "ufc" in combined
                or "ultimate fighting championship" in combined
            ):

                filtered.append(
                    event
                )


        # ====================================================
        # BOXING
        # ====================================================

        elif category == "boxing":

            if (
                league_id == "4445"
                or "boxing" in combined
            ):

                filtered.append(
                    event
                )


        # ====================================================
        # WWE
        # ====================================================

        elif category == "wwe":

            if (
                league_id == "4444"
                or "wwe" in combined
                or "world wrestling entertainment" in combined
            ):

                filtered.append(
                    event
                )


        # ====================================================
        # GOLF & DARTS
        # ====================================================

        elif category in [
            "golf",
            "darts",
        ]:

            filtered.append(
                event
            )


    return filtered[:15]


# ============================================================
# TV CHANNELS
# ============================================================

def get_tv_channels(
    date_value,
    sport,
):

    data = sportsdb_get(
        "eventstv.php",
        {
            "d": date_string(date_value),
            "s": sport,
        },
    )

    tv_dict = {}

    if not data:
        return tv_dict

    broadcasts = (
        data.get("tvevents")
        or data.get("events")
        or []
    )

    if not isinstance(
        broadcasts,
        list,
    ):
        return tv_dict

    for broadcast in broadcasts:

        event_id = str(
            broadcast.get("idEvent")
            or broadcast.get("id")
            or ""
        )

        channel = (
            broadcast.get("strChannel")
            or broadcast.get("strName")
            or ""
        ).strip()

        country = (
            broadcast.get("strCountry")
            or broadcast.get("strLocation")
            or "Intl"
        ).strip()

        if not event_id:
            continue

        if not channel:
            continue

        channel_lower = (
            channel.lower()
        )

        supported = any(
            supported_channel
            in channel_lower
            for supported_channel
            in MY_CHANNELS
        )

        if not supported:
            continue

        tv_dict.setdefault(
            event_id,
            [],
        )

        entry = (
            f"{country}: {channel}"
        )

        if entry not in tv_dict[event_id]:

            tv_dict[event_id].append(
                entry
            )

    return tv_dict


# ============================================================
# UK TIME CONVERSION
# ============================================================

def parse_uk_time(
    event
):

    fallback = datetime(
        2099,
        12,
        31,
        tzinfo=UK_TIMEZONE,
    )

    date_value = (
        event.get("dateEvent")
        or event.get("dateEventLocal")
    )

    time_value = (
        event.get("strTime")
        or event.get("strEventTime")
    )

    if not date_value:
        return fallback

    try:

        time_string = (
            str(time_value)[:8]
            if time_value
            else "00:00:00"
        )

        if len(time_string) == 5:

            time_string += ":00"

        utc_datetime = datetime.strptime(
            f"{date_value} {time_string}",
            "%Y-%m-%d %H:%M:%S",
        )

        utc_datetime = (
            utc_datetime.replace(
                tzinfo=timezone.utc
            )
        )

        return utc_datetime.astimezone(
            UK_TIMEZONE
        )

    except Exception as error:

        logger.warning(
            "Unable to parse time: %s",
            error,
        )

        return fallback


# ============================================================
# HOME PAGE
# ============================================================

def build_home_page():

    now_uk = datetime.now(
        UK_TIMEZONE
    )

    today = now_uk.date()

    text = (
        "⚡ <b>MATCHDAY HUB</b>\n"
        "<i>Fixture & Broadcast Guide</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "🏟️ <b>MAIN DASHBOARD</b>\n\n"
        f"📅 <b>Date:</b> "
        f"{now_uk.strftime('%A %d %B %Y')}\n"
        f"⏰ <b>Time:</b> "
        f"{now_uk.strftime('%H:%M')} UK\n\n"
        "<i>Select a sport below.</i>"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚽ Football Hub",
                    callback_data="menu:football",
                )
            ],

            [
                InlineKeyboardButton(
                    "🏉 Rugby Hub",
                    callback_data="menu:rugby",
                ),

                InlineKeyboardButton(
                    "🥊 Combat Hub",
                    callback_data="menu:combat",
                ),
            ],

            [
                InlineKeyboardButton(
                    "⛳ Golf",
                    callback_data=(
                        f"date:"
                        f"{date_string(today)}:"
                        f"golf"
                    ),
                ),

                InlineKeyboardButton(
                    "🎯 Darts",
                    callback_data=(
                        f"date:"
                        f"{date_string(today)}:"
                        f"darts"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(
                    "📺 Supported Channels",
                    callback_data="menu:channels",
                )
            ],
        ]
    )

    return (
        text,
        keyboard,
    )


# ============================================================
# FOOTBALL MENU
# ============================================================

def build_football_menu():

    today = date_string(
        datetime.now(
            UK_TIMEZONE
        ).date()
    )

    text = (
        "⚽ <b>FOOTBALL HUB</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<i>Select a competition:</i>"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏆 Premier League",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"football_prem"
                    ),
                )
            ],

            [
                InlineKeyboardButton(
                    "📈 Championship",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"football_champ"
                    ),
                )
            ],

            [
                InlineKeyboardButton(
                    "⬅️ Main Menu",
                    callback_data="menu:home",
                )
            ],
        ]
    )

    return (
        text,
        keyboard,
    )


# ============================================================
# RUGBY MENU
# ============================================================

def build_rugby_menu():

    today = date_string(
        datetime.now(
            UK_TIMEZONE
        ).date()
    )

    text = (
        "🏉 <b>RUGBY HUB</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<i>Select a competition:</i>"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🦘 NRL",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"nrl"
                    ),
                ),

                InlineKeyboardButton(
                    "🇬🇧 Super League",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"superleague"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(
                    "🏉 Rugby Union",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"union"
                    ),
                )
            ],

            [
                InlineKeyboardButton(
                    "⬅️ Main Menu",
                    callback_data="menu:home",
                )
            ],
        ]
    )

    return (
        text,
        keyboard,
    )


# ============================================================
# COMBAT MENU
# ============================================================

def build_combat_menu():

    today = date_string(
        datetime.now(
            UK_TIMEZONE
        ).date()
    )

    text = (
        "🥊 <b>COMBAT SPORTS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "<i>Select a category:</i>"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🥋 UFC",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"ufc"
                    ),
                ),

                InlineKeyboardButton(
                    "🥊 Boxing",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"boxing"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(
                    "🤼 WWE",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"wwe"
                    ),
                )
            ],

            [
                InlineKeyboardButton(
                    "⬅️ Main Menu",
                    callback_data="menu:home",
                )
            ],
        ]
    )

    return (
        text,
        keyboard,
    )


# ============================================================
# CHANNELS PAGE
# ============================================================

def build_channels_page():

    lines = [
        "📺 <b>SUPPORTED CHANNELS</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
    ]

    for channel in MY_CHANNELS:

        lines.append(
            f"• {html.escape(channel.title())}"
        )

    lines.append("")

    lines.append(
        "<i>The bot only displays these "
        "broadcasters when SportsDB has them listed.</i>"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⬅️ Main Menu",
                    callback_data="menu:home",
                )
            ]
        ]
    )

    return (
        "\n".join(lines),
        keyboard,
    )


# ============================================================
# FIXTURES PAGE
# ============================================================

def build_fixtures_page(
    date_value,
   
