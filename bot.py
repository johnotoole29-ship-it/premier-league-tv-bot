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
# SPORTS BOT
# FIXTURES • TV • LIVE SPORT
# ============================================================


# ============================================================
# CONFIG
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SPORTSDB_API_KEY = os.getenv("SPORTSDB_API_KEY")

SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"

UK_TIMEZONE = ZoneInfo("Europe/London")

# Telegram group/topic lock
ALLOWED_CHAT_ID = "3988874271"
ALLOWED_TOPIC_ID = "10394"


# ============================================================
# SUPPORTED TV / STREAMING CHANNELS
# ============================================================

MY_CHANNELS = [
    "sky sports",
    "sky sport",
    "tnt sports",
    "amazon prime",
    "prime video",
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
    "hub premier",
    "supersport",
    "monomax",
    "usa network",
    "peacock",
    "nbc",
]


# ============================================================
# SPORTS / LEAGUE CATEGORIES
# ============================================================

CATEGORIES = {

    # --------------------------------------------------------
    # FOOTBALL
    # --------------------------------------------------------

    "football_prem": {
        "icon": "🏴",
        "title": "Premier League",
        "sport": "Soccer",
        "league_id": "4328",
    },

    "football_champ": {
        "icon": "🏴",
        "title": "Championship",
        "sport": "Soccer",
        "league_id": "4329",
    },

    "football_laliga": {
        "icon": "🇪🇸",
        "title": "La Liga",
        "sport": "Soccer",
        "league_id": "4335",
    },

    "football_seriea": {
        "icon": "🇮🇹",
        "title": "Serie A",
        "sport": "Soccer",
        "league_id": "4332",
    },

    "football_bundesliga": {
        "icon": "🇩🇪",
        "title": "Bundesliga",
        "sport": "Soccer",
        "league_id": "4331",
    },

    "football_ligue1": {
        "icon": "🇫🇷",
        "title": "Ligue 1",
        "sport": "Soccer",
        "league_id": "4334",
    },

    # --------------------------------------------------------
    # RUGBY
    # --------------------------------------------------------

    "nrl": {
        "icon": "🦘",
        "title": "NRL",
        "sport": "Rugby",
        "league_id": "4416",
    },

    "superleague": {
        "icon": "🇬🇧",
        "title": "Super League",
        "sport": "Rugby",
        "league_id": "4415",
    },

    "union": {
        "icon": "🏉",
        "title": "Rugby Union",
        "sport": "Rugby",
        "league_id": None,
    },

    # --------------------------------------------------------
    # COMBAT
    # --------------------------------------------------------

    "ufc": {
        "icon": "🥋",
        "title": "UFC",
        "sport": "Fighting",
        "league_id": None,
    },

    "boxing": {
        "icon": "🥊",
        "title": "Boxing",
        "sport": "Fighting",
        "league_id": None,
    },

    "wwe": {
        "icon": "🤼",
        "title": "WWE",
        "sport": "Fighting",
        "league_id": None,
    },

    # --------------------------------------------------------
    # OTHER SPORTS
    # --------------------------------------------------------

    "golf": {
        "icon": "⛳",
        "title": "Golf",
        "sport": "Golf",
        "league_id": None,
    },

    "darts": {
        "icon": "🎯",
        "title": "Darts",
        "sport": "Darts",
        "league_id": None,
    },
}


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format=(
        "%(asctime)s - "
        "%(name)s - "
        "%(levelname)s - "
        "%(message)s"
    ),
    level=logging.INFO,
)

logger = logging.getLogger("SportsBot")


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
# BUNNY.NET HEALTH SERVER
# ============================================================

class HealthCheckHandler(BaseHTTPRequestHandler):

    def do_GET(self):

        self.send_response(200)

        self.send_header(
            "Content-Type",
            "text/plain",
        )

        self.end_headers()

        self.wfile.write(
            b"Sports Bot is running."
        )

    def log_message(self, format, *args):
        pass


def start_health_server():

    port = int(
        os.getenv(
            "PORT",
            "8080",
        )
    )

    try:

        server = HTTPServer(
            (
                "0.0.0.0",
                port,
            ),
            HealthCheckHandler,
        )

        logger.info(
            "Health server listening on port %s",
            port,
        )

        server.serve_forever()

    except Exception as error:

        logger.exception(
            "Health server error: %s",
            error,
        )


# ============================================================
# SPORTSDB API
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
            "SportsDB returned invalid JSON: %s",
            error,
        )

        return None


# ============================================================
# DATE HELPERS
# ============================================================

def date_string(
    date_value,
):

    return date_value.strftime(
        "%Y-%m-%d"
    )


def pretty_date(
    date_value,
):

    return date_value.strftime(
        "%A %d %B %Y"
    )


# ============================================================
# UK TIME CONVERSION
# ============================================================

def parse_uk_time(
    event,
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
            str(time_value).strip()
            if time_value
            else "00:00:00"
        )

        time_string = time_string[:8]

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
            "Could not parse event time: %s",
            error,
        )

        return fallback


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
            "d": date_string(
                date_value
            ),
            "s": meta["sport"],
        },
    )

    if not data:
        return []

    events = data.get(
        "events"
    )

    if not isinstance(
        events,
        list,
    ):
        return []

    filtered = []

    for event in events:

        league_id = str(
            event.get(
                "idLeague"
            )
            or ""
        )

        league_name = str(
            event.get(
                "strLeague"
            )
            or ""
        ).strip().lower()

        event_name = str(
            event.get(
                "strEvent"
            )
            or ""
        ).strip().lower()

        combined = (
            league_name
            + " "
            + event_name
        )

        # ====================================================
        # FOOTBALL
        # ====================================================

        if category == "football_prem":

            if league_id == "4328":
                filtered.append(
                    event
                )

        elif category == "football_champ":

            if league_id == "4329":
                filtered.append(
                    event
                )

        elif category == "football_laliga":

            if league_id == "4335":
                filtered.append(
                    event
                )

        elif category == "football_seriea":

            if league_id == "4332":
                filtered.append(
                    event
                )

        elif category == "football_bundesliga":

            if league_id == "4331":
                filtered.append(
                    event
                )

        elif category == "football_ligue1":

            if league_id == "4334":
                filtered.append(
                    event
                )

        # ====================================================
        # RUGBY LEAGUE
        # ====================================================

        elif category == "nrl":

            if (
                league_id == "4416"
                or "national rugby league" in combined
                or "nrl" in combined
            ):

                filtered.append(
                    event
                )

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

            excluded_terms = [
                "super league",
                "national rugby league",
                "nrl",
            ]

            is_rugby_league = any(
                term in combined
                for term in excluded_terms
            )

            if (
                league_id not in [
                    "4415",
                    "4416",
                ]
                and not is_rugby_league
            ):

                filtered.append(
                    event
                )

        # ====================================================
        # UFC
        # ====================================================

        elif category == "ufc":

            if (
                "ufc" in combined
                or
                "ultimate fighting championship"
                in combined
            ):

                filtered.append(
                    event
                )

        # ====================================================
        # BOXING
        # ====================================================

        elif category == "boxing":

            if "boxing" in combined:

                filtered.append(
                    event
                )

        # ====================================================
        # WWE
        # ====================================================

        elif category == "wwe":

            if (
                "wwe" in combined
                or
                "world wrestling entertainment"
                in combined
            ):

                filtered.append(
                    event
                )

        # ====================================================
        # GOLF / DARTS
        # ====================================================

        elif category in [
            "golf",
            "darts",
        ]:

            filtered.append(
                event
            )

    return filtered[:20]


# ============================================================
# TV CHANNEL DATA
# ============================================================

def get_tv_channels(
    date_value,
    sport,
):

    data = sportsdb_get(
        "eventstv.php",
        {
            "d": date_string(
                date_value
            ),
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
            broadcast.get(
                "idEvent"
            )
            or broadcast.get(
                "id"
            )
            or ""
        )

        channel = str(
            broadcast.get(
                "strChannel"
            )
            or broadcast.get(
                "strName"
            )
            or ""
        ).strip()

        country = str(
            broadcast.get(
                "strCountry"
            )
            or broadcast.get(
                "strLocation"
            )
            or "International"
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

        if entry not in tv_dict[
            event_id
        ]:

            tv_dict[
                event_id
            ].append(
                entry
            )

    return tv_dict


# ============================================================
# PREMIUM PRIVATE HOME PAGE
# ============================================================

def build_home_page():

    now_uk = datetime.now(
        UK_TIMEZONE
    )

    today = now_uk.date()

    text = (
        "🏟️ <b>SPORTS BOT</b>\n"
        "<b>YOUR MATCHDAY CENTRE</b>\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "⚡ <b>LIVE SPORTS DIRECTORY</b>\n"
        "\n"
        f"📅 {now_uk.strftime('%A %d %B %Y')}\n"
        f"🕒 {now_uk.strftime('%H:%M')} UK\n"
        "\n"
        "📺 Fixtures • TV • Streaming\n"
        "🌍 Major leagues & sports\n"
        "🇬🇧 All times shown in UK time\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "<b>👇 CHOOSE YOUR SPORT</b>"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⚽ FOOTBALL",
                    callback_data="menu:football",
                )
            ],

            [
                InlineKeyboardButton(
                    "🏉 RUGBY",
                    callback_data="menu:rugby",
                ),

                InlineKeyboardButton(
                    "🥊 COMBAT",
                    callback_data="menu:combat",
                ),
            ],

            [
                InlineKeyboardButton(
                    "⛳ GOLF",
                    callback_data=(
                        f"date:"
                        f"{date_string(today)}:"
                        f"golf"
                    ),
                ),

                InlineKeyboardButton(
                    "🎯 DARTS",
                    callback_data=(
                        f"date:"
                        f"{date_string(today)}:"
                        f"darts"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(
                    "📺 TV & STREAMING GUIDE",
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
# FOOTBALL HUB
# ============================================================

def build_football_menu():

    today = date_string(
        datetime.now(
            UK_TIMEZONE
        ).date()
    )

    text = (
        "⚽ <b>FOOTBALL CENTRE</b>\n"
        "<i>Europe's major leagues</i>\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "🏆 <b>SELECT A COMPETITION</b>\n"
        "\n"
        "Choose a league to view fixtures, "
        "UK kick-off times and available broadcasters."
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏴 Premier League",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"football_prem"
                    ),
                ),

                InlineKeyboardButton(
                    "🏴 Championship",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"football_champ"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(
                    "🇪🇸 La Liga",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"football_laliga"
                    ),
                ),

                InlineKeyboardButton(
                    "🇮🇹 Serie A",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"football_seriea"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(
                    "🇩🇪 Bundesliga",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"football_bundesliga"
                    ),
                ),

                InlineKeyboardButton(
                    "🇫🇷 Ligue 1",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"football_ligue1"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(
                    "🏠 MAIN MENU",
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
# RUGBY HUB
# ============================================================

def build_rugby_menu():

    today = date_string(
        datetime.now(
            UK_TIMEZONE
        ).date()
    )

    text = (
        "🏉 <b>RUGBY CENTRE</b>\n"
        "<i>League & Union</i>\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "🏆 <b>SELECT A COMPETITION</b>"
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
                    "🇬🇧 SUPER LEAGUE",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"superleague"
                    ),
                ),
            ],

            [
                InlineKeyboardButton(
                    "🏉 RUGBY UNION",
                    callback_data=(
                        f"date:"
                        f"{today}:"
                        f"union"
                    ),
                )
            ],

            [
                InlineKeyboardButton(
                    "🏠 MAIN MENU",
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
# COMBAT HUB
# ============================================================

def build_combat_menu():

    today = date_string(
        datetime.now(
            UK_TIMEZONE
        ).date()
    )

    text = (
        "🥊 <b>COMBAT CENTRE</b>\n"
        "<i>Fight nights & major events</i>\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        "🔥 <b>SELECT A CATEGORY</b>"
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
                    "🥊 BOXING",
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
                    "🏠 MAIN MENU",
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
# SUPPORTED CHANNELS PAGE
# ============================================================

def build_channels_page():

    lines = [
        "📺 <b>TV & STREAMING GUIDE</b>",
        "<i>Supported broadcast partners</i>",
        "",
        "━━━━━━━━━━━━━━━━━━━━",
        "",
        "🌍 <b>AVAILABLE NETWORKS</b>",
        "",
    ]

    for channel in MY_CHANNELS:

        lines.append(
            f"• {html.escape(channel.title())}"
        )

    lines.extend(
        [
            "",
            "━━━━━━━━━━━━━━━━━━━━",
            "",
            "ℹ️ <i>Channels appear against an event "
            "when broadcast information is available "
            "from the fixture data provider.</i>",
        ]
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏠 MAIN MENU",
                    callback_data="menu:home",
                )
            ]
        ]
    )

    return (
        "\n".join(
            lines
        ),
        keyboard,
    )


# ============================================================
# FIXTURE LIST
# ============================================================

def build_fixtures_page(
    date_value,
    category,
):

    meta = CATEGORIES.get(
        category
    )

    if not meta:

        return (
            "❌ <b>Unknown category.</b>",
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏠 MAIN MENU",
                            callback_data="menu:home",
                        )
                    ]
                ]
            ),
        )

    events = fetch_events(
        date_value,
        category,
    )

    events.sort(
        key=parse_uk_time
    )

    text = (
        f"{meta['icon']} "
        f"<b>{html.escape(meta['title'].upper())}</b>\n"
        "<i>Fixture Centre</i>\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        f"📅 <b>{pretty_date(date_value)}</b>\n"
        "\n"
    )

    buttons = []

    if not events:

        text += (
            "📭 <b>NO FIXTURES FOUND</b>\n\n"
            f"No {html.escape(meta['title'])} "
            "events are currently listed for this date.\n\n"
            "Use the navigation below to check another day."
        )

    else:

        text += (
            f"⚡ <b>{len(events)} EVENT"
            f"{'S' if len(events) != 1 else ''} FOUND</b>\n\n"
            "<i>Select a fixture to open its Match Centre "
            "and view broadcast information.</i>"
        )

        for event in events:

            home = str(
                event.get(
                    "strHomeTeam"
                )
                or ""
            ).strip()

            away = str(
                event.get(
                    "strAwayTeam"
                )
                or ""
            ).strip()

            event_name = str(
                event.get(
                    "strEvent"
                )
                or "Event"
            ).strip()

            if home and away:

                title = (
                    f"{home} vs {away}"
                )

            else:

                title = event_name

            event_time = parse_uk_time(
                event
            )

            if event_time.year == 2099:

                time_text = "TBC"

            else:

                time_text = (
                    event_time.strftime(
                        "%H:%M"
                    )
                )

            event_id = str(
                event.get(
                    "idEvent"
                )
                or ""
            )

            if not event_id:
                continue

            button_text = (
                f"⚡ {time_text}  |  {title}"
            )

            if len(button_text) > 52:

                button_text = (
                    button_text[:49]
                    + "..."
                )

            buttons.append(
                [
                    InlineKeyboardButton(
                        button_text,
                        callback_data=(
                            f"match:"
                            f"{event_id}:"
                            f"{date_string(date_value)}:"
                            f"{category}"
                        ),
                    )
                ]
            )

    today = datetime.now(
        UK_TIMEZONE
    ).date()

    previous_day = (
        date_value
        - timedelta(
            days=1
        )
    )

    next_day = (
        date_value
        + timedelta(
            days=1
        )
    )

    football_categories = [
        "football_prem",
        "football_champ",
        "football_laliga",
        "football_seriea",
        "football_bundesliga",
        "football_ligue1",
    ]

    rugby_categories = [
        "nrl",
        "superleague",
        "union",
    ]

    combat_categories = [
        "ufc",
        "boxing",
        "wwe",
    ]

    if category in football_categories:

        back_target = (
            "menu:football"
        )

    elif category in rugby_categories:

        back_target = (
            "menu:rugby"
        )

    elif category in combat_categories:

        back_target = (
            "menu:combat"
        )

    else:

        back_target = (
            "menu:home"
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "◀️ PREV",
                callback_data=(
                    f"date:"
                    f"{date_string(previous_day)}:"
                    f"{category}"
                ),
            ),

            InlineKeyboardButton(
                "📅 TODAY",
                callback_data=(
                    f"date:"
                    f"{date_string(today)}:"
                    f"{category}"
                ),
            ),

            InlineKeyboardButton(
                "NEXT ▶️",
                callback_data=(
                    f"date:"
                    f"{date_string(next_day)}:"
                    f"{category}"
                ),
            ),
        ]
    )

    buttons.append(
        [
            InlineKeyboardButton(
                "🔄 REFRESH",
                callback_data=(
                    f"date:"
                    f"{date_string(date_value)}:"
                    f"{category}"
                ),
            ),

            InlineKeyboardButton(
                "⬅️ BACK",
                callback_data=back_target,
            ),
        ]
    )

    return (
        text,
        InlineKeyboardMarkup(
            buttons
        ),
    )


# ============================================================
# MATCH CENTRE
# ============================================================

def build_match_details_page(
    event_id,
    date_value,
    category,
):

    meta = CATEGORIES.get(
        category
    )

    if not meta:

        return (
            "❌ <b>Unknown category.</b>",
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏠 MAIN MENU",
                            callback_data="menu:home",
                        )
                    ]
                ]
            ),
        )

    events = fetch_events(
        date_value,
        category,
    )

    event = next(
        (
            item
            for item in events
            if str(
                item.get(
                    "idEvent"
                )
            ) == str(
                event_id
            )
        ),
        None,
    )

    if not event:

        return (
            "❌ <b>EVENT UNAVAILABLE</b>\n\n"
            "This fixture is no longer available "
            "from the data provider.",
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ BACK TO FIXTURES",
                            callback_data=(
                                f"date:"
                                f"{date_string(date_value)}:"
                                f"{category}"
                            ),
                        )
                    ]
                ]
            ),
        )

    home = str(
        event.get(
            "strHomeTeam"
        )
        or ""
    ).strip()

    away = str(
        event.get(
            "strAwayTeam"
        )
        or ""
    ).strip()

    event_name = str(
        event.get(
            "strEvent"
        )
        or "Event"
    ).strip()

    if home and away:

        title = (
            f"{home} vs {away}"
        )

    else:

        title = event_name

    event_time = parse_uk_time(
        event
    )

    if event_time.year == 2099:

        time_text = "TBC"

    else:

        time_text = (
            event_time.strftime(
                "%H:%M"
            )
        )

    venue = str(
        event.get(
            "strVenue"
        )
        or ""
    ).strip()

    tv_data = get_tv_channels(
        date_value,
        meta["sport"],
    )

    channels = tv_data.get(
        str(
            event_id
        ),
        [],
    )

    text = (
        "🏟️ <b>MATCH CENTRE</b>\n"
        f"<i>{html.escape(meta['title'])}</i>\n"
        "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
        f"{meta['icon']} <b>{html.escape(title)}</b>\n"
        "\n"
        f"📅 <b>{pretty_date(date_value)}</b>\n"
        f"🕒 <b>{time_text} UK</b>\n"
    )

    if venue:

        text += (
            f"📍 {html.escape(venue)}\n"
        )

    text += (
        "\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "\n"
    )

    if channels:

        text += (
            "📺 <b>WHERE TO WATCH</b>\n\n"
        )

        for channel in channels:

            text += (
                f"▸ {html.escape(channel)}\n"
            )

    else:

        text += (
            "📺 <b>WHERE TO WATCH</b>\n\n"
            "Broadcast information is not currently "
            "available on a supported channel."
        )

    keyboard_rows = [
        [
            InlineKeyboardButton(
                "⬅️ BACK TO FIXTURES",
                callback_data=(
                    f"date:"
                    f"{date_string(date_value)}:"
                    f"{category}"
                ),
            )
        ]
    ]

    if category.startswith(
        "football_"
    ):

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    "⚽ FOOTBALL CENTRE",
                    callback_data="menu:football",
                )
            ]
        )

    elif category in [
        "nrl",
        "superleague",
        "union",
    ]:

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    "🏉 RUGBY CENTRE",
                    callback_data="menu:rugby",
                )
            ]
        )

    elif category in [
        "ufc",
        "boxing",
        "wwe",
    ]:

        keyboard_rows.append(
            [
                InlineKeyboardButton(
                    "🥊 COMBAT CENTRE",
                    callback_data="menu:combat",
                )
            ]
        )

    keyboard_rows.append(
        [
            InlineKeyboardButton(
                "🏠 MAIN MENU",
                callback_data="menu:home",
            )
        ]
    )

    return (
        text,
        InlineKeyboardMarkup(
            keyboard_rows
        ),
    )


# ============================================================
# /START HANDLER
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat = update.effective_chat
    message = update.effective_message

    if not chat or not message:
        return

    # ========================================================
    # GROUP MODE
    # ========================================================

    if chat.type in [
        "group",
        "supergroup",
    ]:

        chat_id = str(
            chat.id
        )

        thread_id = (
            str(
                message.message_thread_id
            )
            if message.message_thread_id
            else None
        )

        correct_group = (
            chat_id.endswith(
                ALLOWED_CHAT_ID
            )
        )

        correct_topic = (
            thread_id
            == ALLOWED_TOPIC_ID
        )

        if (
            correct_group
            and correct_topic
        ):

            bot_info = (
                await context.bot.get_me()
            )

            bot_username = (
                bot_info.username
            )

            # =================================================
            # PREMIUM GROUP LANDING CARD
            # =================================================

            group_text = (
                "🏟️ <b>SPORTS BOT</b>\n"
                "<b>FIXTURES • TV • LIVE SPORT</b>\n"
                "\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "\n"
                "⚡ <b>YOUR MATCHDAY COMPANION</b>\n"
                "\n"
                "⚽ Premier League & Championship\n"
                "🌍 La Liga • Serie A • Bundesliga • Ligue 1\n"
                "🏉 Rugby • 🥊 Combat • ⛳ Golf • 🎯 Darts\n"
                "📺 TV & streaming broadcast listings\n"
                "🕒 All fixtures shown in UK local time\n"
                "\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "\n"
                "🔒 <b>PRIVATE MATCH CENTRE</b>\n"
                "\n"
                "Your fixtures and TV guide are delivered "
                "privately, keeping the group clean and "
                "uncluttered.\n"
                "\n"
                "📩 <b>Tap below and Sports Bot will send "
                "you a private message.</b>\n"
                "\n"
                "👇 <b>OPEN YOUR MATCH CENTRE</b>"
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⚡ LAUNCH SPORTS BOT ⚡",
                            url=(
                                f"https://t.me/"
                                f"{bot_username}"
                                f"?start=open"
                            ),
                        )
                    ]
                ]
            )

            await message.reply_text(
                group_text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

        return

    # ========================================================
    # PRIVATE MODE
    # ========================================================

    if chat.type == "private":

        text, keyboard = (
            build_home_page()
        )

        await message.reply_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )


# ============================================================
# BUTTON HANDLER
# ============================================================

async def button_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = (
        update.callback_query
    )

    if not query:
        return

    await query.answer()

    data = (
        query.data
        or ""
    )

    try:

        # ====================================================
        # HOME
        # ====================================================

        if data == "menu:home":

            text, keyboard = (
                build_home_page()
            )

        # ====================================================
        # FOOTBALL
        # ====================================================

        elif data == "menu:football":

            text, keyboard = (
                build_football_menu()
            )

        # ====================================================
        # RUGBY
        # ====================================================

        elif data == "menu:rugby":

            text, keyboard = (
                build_rugby_menu()
            )

        # ====================================================
        # COMBAT
        # ====================================================

        elif data == "menu:combat":

            text, keyboard = (
                build_combat_menu()
            )

        # ====================================================
        # CHANNEL GUIDE
        # ====================================================

        elif data == "menu:channels":

            text, keyboard = (
                build_channels_page()
            )

        # ====================================================
        # FIXTURE DATE
        # ====================================================

        elif data.startswith(
            "date:"
        ):

            parts = data.split(
                ":",
                2,
            )

            if len(parts) != 3:

                raise ValueError(
                    f"Invalid date callback: {data}"
                )

            date_text = parts[1]
            category = parts[2]

            target_date = (
                datetime.strptime(
                    date_text,
                    "%Y-%m-%d",
                ).date()
            )

            text, keyboard = (
                build_fixtures_page(
                    target_date,
                    category,
                )
            )

        # ====================================================
        # MATCH CENTRE
        # ====================================================

        elif data.startswith(
            "match:"
        ):

            parts = data.split(
                ":",
                3,
            )

            if len(parts) != 4:

                raise ValueError(
                    f"Invalid match callback: {data}"
                )

            event_id = (
                parts[1]
            )

            date_text = (
                parts[2]
            )

            category = (
                parts[3]
            )

            target_date = (
                datetime.strptime(
                    date_text,
                    "%Y-%m-%d",
                ).date()
            )

            text, keyboard = (
                build_match_details_page(
                    event_id,
                    target_date,
                    category,
                )
            )

        # ====================================================
        # UNKNOWN CALLBACK
        # ====================================================

        else:

            text = (
                "⚠️ <b>OPTION UNAVAILABLE</b>\n\n"
                "Please return to the main dashboard."
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏠 MAIN MENU",
                            callback_data="menu:home",
                        )
                    ]
                ]
            )

        await query.edit_message_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML",
        )

    except Exception as error:

        logger.exception(
            "Button handler error: %s",
            error,
        )

        try:

            await query.edit_message_text(
                "❌ <b>SPORTS BOT ERROR</b>\n\n"
                "Something went wrong while loading "
                "this section.\n\n"
                "Please return to the main dashboard.",
                reply_markup=InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                "🏠 MAIN MENU",
                                callback_data="menu:home",
                            )
                        ]
                    ]
                ),
                parse_mode="HTML",
            )

        except Exception as secondary_error:

            logger.error(
                "Could not display fallback error: %s",
                secondary_error,
            )


# ============================================================
# GLOBAL ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context,
):

    logger.error(
        "Telegram error: %s",
        context.error,
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "Starting Sports Bot..."
    )

    # Bunny health endpoint
    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True,
    )

    health_thread.start()

    # Telegram application
    application = (
        Application
        .builder()
        .token(
            TELEGRAM_TOKEN
        )
        .build()
    )

    # /start
    application.add_handler(
        CommandHandler(
            "start",
            start,
        )
    )

    # Inline buttons
    application.add_handler(
        CallbackQueryHandler(
            button_handler
        )
    )

    # Global error handler
    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Sports Bot is online."
    )

    application.run_polling(
        drop_pending_updates=True
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":
    main()
