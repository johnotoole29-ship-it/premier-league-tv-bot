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

    if (
        not data
        or not isinstance(
            data.get("events"),
            list,
        )
    ):
        return []

    filtered = []

    for event in data["events"]:

        league_id = str(
            event.get(
                "idLeague",
                "",
            )
        )

        league_name = str(
            event.get("strLeague")
            or ""
        ).lower()

        event_name = str(
            event.get("strEvent")
            or ""
        ).lower()

        combined = (
            league_name
            + " "
            + event_name
        )

        # Premier League
        if category == "football_prem":

            if (
                league_id == "4328"
                or "english premier league" in league_name
            ):
                filtered.append(
                    event
                )

        # Championship
        elif category == "football_champ":

            if (
                league_id == "4329"
                or "championship" in league_name
            ):
                filtered.append(
                    event
                )

        # NRL
        elif category == "nrl":

            if (
                league_id == "4416"
                or "nrl" in combined
                or "national rugby league" in combined
            ):
                filtered.append(
                    event
                )

        # Super League
        elif category == "superleague":

            if (
                league_id == "4415"
                or "super league" in combined
            ):
                filtered.append(
                    event
                )

        # Rugby Union
        elif category == "union":

            if (
                league_id not in [
                    "4415",
                    "4416",
                ]
                and "nrl" not in combined
                and "national rugby league" not in combined
                and "super league" not in combined
            ):
                filtered.append(
                    event
                )

        # UFC
        elif category == "ufc":

            if (
                league_id == "4443"
                or "ufc" in combined
                or "ultimate fighting championship" in combined
            ):
                filtered.append(
                    event
                )

        # Boxing
        elif category == "boxing":

            if (
                league_id == "4445"
                or "boxing" in combined
            ):
                filtered.append(
                    event
                )

        # WWE
        elif category == "wwe":

            if (
                league_id == "4444"
                or "wwe" in combined
                or "world wrestling entertainment" in combined
            ):
                filtered.append(
                    event
                )

        # Golf / Darts
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

        if not event_id or not channel:
            continue

        channel_lower = (
            channel.lower()
        )

        is_available = any(
            my_channel in channel_lower
            for my_channel in MY_CHANNELS
        )

        if not is_available:
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
# TIME PARSING
# ============================================================

def parse_uk_time(event):

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
            "Could not parse event time: %s",
            error,
        )

        return fallback


# ============================================================
# UI - HOME PAGE
# ============================================================

def build_home_page():

    now_uk = datetime.now(
        UK_TIMEZONE
    )

    text = (
        "⚡ <b>MATCHDAY HUB</b>\n"
        "<i>Premium Fixture & Broadcast Guide</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🏟️ <b>MAIN DASHBOARD</b>\n"
        f"📅 <b>Date:</b> {now_uk.strftime('%A, %d %b %Y')}\n"
        f"⏰ <b>Time:</b> {now_uk.strftime('%H:%M')} UK\n\n"
        "<i>Select a category below to access live match "
        "data and broadcast feeds.</i>"
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
                        f"{date_string(now_uk.date())}:"
                        f"golf"
                    ),
                ),
                InlineKeyboardButton(
                    "🎯 Darts",
                    callback_data=(
                        f"date:"
                        f"{date_string(now_uk.date())}:"
                        f"darts"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "⚙️ Supported App Channels",
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
# UI - FOOTBALL MENU
# ============================================================

def build_football_menu():

    today = date_string(
        datetime.now(
            UK_TIMEZONE
        ).date()
    )

    text = (
        "⚽ <b>FOOTBALL HUB</b>\n"
        "<i>Select a league below:</i>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏆 Premier League",
                    callback_data=(
                        f"date:{today}:football_prem"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "📈 Championship",
                    callback_data=(
                        f"date:{today}:football_champ"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back to Main Menu",
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
# UI - RUGBY MENU
# ============================================================

def build_rugby_menu():

    today = date_string(
        datetime.now(
            UK_TIMEZONE
        ).date()
    )

    text = (
        "🏉 <b>RUGBY HUB</b>\n"
        "<i>Select a league or code below:</i>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🦘 NRL",
                    callback_data=(
                        f"date:{today}:nrl"
                    ),
                ),
                InlineKeyboardButton(
                    "🇬🇧 Super League",
                    callback_data=(
                        f"date:{today}:superleague"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "🏉 Rugby Union",
                    callback_data=(
                        f"date:{today}:union"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back to Main Menu",
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
# UI - COMBAT MENU
# ============================================================

def build_combat_menu():

    today = date_string(
        datetime.now(
            UK_TIMEZONE
        ).date()
    )

    text = (
        "🥊 <b>COMBAT SPORTS HUB</b>\n"
        "<i>Select an organisation below:</i>\n"
        "━━━━━━━━━━━━━━━━━━━━"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🥋 UFC",
                    callback_data=(
                        f"date:{today}:ufc"
                    ),
                ),
                InlineKeyboardButton(
                    "🥊 Boxing",
                    callback_data=(
                        f"date:{today}:boxing"
                    ),
                ),
            ],
            [
                InlineKeyboardButton(
                    "🤼 WWE",
                    callback_data=(
                        f"date:{today}:wwe"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "⬅️ Back to Main Menu",
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
# UI - CHANNELS PAGE
# ============================================================

def build_channels_page():

    channel_list = ", ".join(
        f"<b>{html.escape(channel.title())}</b>"
        for channel in MY_CHANNELS
    )

    text = (
        "⚙️ <b>SYSTEM CONFIGURATION</b>\n"
        "<i>Supported Broadcast Feeds</i>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "The system is configured to show matches from "
        "the following networks when TheSportsDB lists them:\n\n"
        f"<blockquote>{channel_list}</blockquote>\n\n"
        "<i>Other broadcasters are filtered out from this view.</i>"
    )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⬅️ Back to Main Menu",
                    callback_data="menu:home",
                )
            ]
        ]
    )

    return (
        text,
        keyboard,
    )


# ============================================================
# UI - FIXTURES PAGE
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
            "❌ <b>Error:</b> Unknown category.",
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Back",
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
        f"{meta['icon']} <b>{meta['title'].upper()} FIXTURES</b>\n"
        f"📅 <b>{pretty_date(date_value)}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    keyboard_buttons = []

    if not events:

        text += (
            f"<blockquote>"
            f"❌ <i>No {html.escape(meta['title'])} events "
            f"scheduled for this date.</i>"
            f"</blockquote>\n"
        )

    else:

        text += (
            "<i>Tap an event below to open Match Center "
            "and view available broadcasts.</i>\n\n"
        )

        for event in events:

            home = html.escape(
                str(
                    event.get("strHomeTeam")
                    or ""
                )
            )

            away = html.escape(
                str(
                    event.get("strAwayTeam")
                    or ""
                )
            )

            if (
                not home
                or not away
                or home == "None"
                or away == "None"
            ):

                match_title = html.escape(
                    str(
                        event.get("strEvent")
                        or "TBA Event"
                    )
                )

            else:

                match_title = (
                    f"{home} vs {away}"
                )

            event_time = parse_uk_time(
                event
            )

            time_text = (
                event_time.strftime("%H:%M")
                if event_time.year != 2099
                else "TBC"
            )

            event_id = str(
                event.get(
                    "idEvent",
                    "",
                )
            )

            if not event_id:
                continue

            button_text = (
                f"[{time_text}] "
                f"{html.unescape(match_title)}"
            )

            if len(button_text) > 40:

                button_text = (
                    button_text[:37]
                    + "..."
                )

            keyboard_buttons.append(
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

    today = date_string(
        datetime.now(
            UK_TIMEZONE
        ).date()
    )

    previous_day = date_string(
        date_value
        - timedelta(days=1)
    )

    next_day = date_string(
        date_value
        + timedelta(days=1)
    )

    back_target = "menu:home"

    if category in [
        "football_prem",
        "football_champ",
    ]:

        back_target = (
            "menu:football"
        )

    elif category in [
        "nrl",
        "superleague",
        "union",
    ]:

        back_target = (
            "menu:rugby"
        )

    elif category in [
        "ufc",
        "boxing",
        "wwe",
    ]:

        back_target = (
            "menu:combat"
        )

    keyboard_buttons.append(
        [
            InlineKeyboardButton(
                "⬅️ Prev Day",
                callback_data=(
                    f"date:"
                    f"{previous_day}:"
                    f"{category}"
                ),
            ),
            InlineKeyboardButton(
                "📅 Today",
                callback_data=(
                    f"date:"
                    f"{today}:"
                    f"{category}"
                ),
            ),
            InlineKeyboardButton(
                "Next Day ➡️",
                callback_data=(
                    f"date:"
                    f"{next_day}:"
                    f"{category}"
                ),
            ),
        ]
    )

    keyboard_buttons.append(
        [
            InlineKeyboardButton(
                "🔄 Refresh List",
                callback_data=(
                    f"date:"
                    f"{date_string(date_value)}:"
                    f"{category}"
                ),
            ),
            InlineKeyboardButton(
                "⬅️ Back",
                callback_data=back_target,
            ),
        ]
    )

    return (
        text,
        InlineKeyboardMarkup(
            keyboard_buttons
        ),
    )


# ============================================================
# UI - MATCH DETAILS
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
            "❌ <b>Error:</b> Unknown category.",
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "⬅️ Back",
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
            event
            for event in events
            if str(
                event.get("idEvent")
            ) == str(event_id)
        ),
        None,
    )

    if not event:

        text = (
            "❌ <i>Match data is no longer available.</i>"
        )

        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Back to Matches",
                        callback_data=(
                            f"date:"
                            f"{date_string(date_value)}:"
                            f"{category}"
                        ),
                    )
                ]
            ]
        )

        return (
            text,
            keyboard,
        )

    home = html.escape(
        str(
            event.get("strHomeTeam")
            or ""
        )
    )

    away = html.escape(
        str(
            event.get("strAwayTeam")
            or ""
        )
    )

    if (
        not home
        or not away
        or home == "None"
        or away == "None"
    ):

        match_title = html.escape(
            str(
                event.get("strEvent")
                or "TBA Event"
            )
        )

    else:

        match_title = (
            f"{home} vs {away}"
        )

    event_time = parse_uk_time(
        event
    )

    time_text = (
        event_time.strftime("%H:%M")
        if event_time.year != 2099
        else "TBC"
    )

    tv_data = get_tv_channels(
        date_value,
        meta["sport"],
    )

    channels = tv_data.get(
        str(event_id),
        [],
    )

    text = (
        f"{meta['icon']} <b>MATCH CENTER</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"🏆 <b>Event:</b> {match_title}\n"
        f"📅 <b>Date:</b> {pretty_date(date_value)}\n"
        f"⏰ <b>Start:</b> {time_text} UK\n\n"
    )

    if not channels:

        text += (
            "<blockquote>"
            "📺 <i>No supported app feeds are currently "
            "listed for this event.</i>"
            "</blockquote>"
        )

    else:

        channel_text = "\n".join(
            f"• {html.escape(channel)}"
            for channel in channels
        )

        text += (
            "📺 <b>Supported Broadcast Feeds:</b>\n"
            f"<blockquote>{channel_text}</blockquote>"
        )

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "⬅️ Back to Matches",
                    callback_data=(
                        f"date:"
                        f"{date_string(date_value)}:"
                        f"{category}"
                    ),
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 Main Menu",
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
# /START HANDLER
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat = update.effective_chat
    message = update.effective_message

    # --------------------------------------------------------
    # GROUP CHAT - TOPIC LOCKED
    # --------------------------------------------------------

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

        # Keep your existing comparison logic
        is_correct_group = (
            chat_id.endswith(
                ALLOWED_CHAT_ID
            )
        )

        is_correct_topic = (
            thread_id
            == ALLOWED_TOPIC_ID
        )

        if (
            is_correct_group
            and is_correct_topic
        ):

            bot_info = (
                await context.bot.get_me()
            )

            bot_username = (
                bot_info.username
            )

            group_text = (
                "⚡ <b>MATCHDAY HUB</b>\n"
                "<i>Live Fixtures & TV Guide</i>\n"
                "━━━━━━━━━━━━━━━━━━━━\n"
                "To keep the group chat clean, match browsing "
                "is handled in a private session.\n\n"
                "👉 Tap below to launch your personal dashboard:"
            )

            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🚀 Open Match Center",
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

    # --------------------------------------------------------
    # PRIVATE CHAT
    # --------------------------------------------------------

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

    query = update.callback_query

    await query.answer()

    data = query.data or ""

    try:

        # HOME
        if data == "menu:home":

            text, keyboard = (
                build_home_page()
            )

            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            return

        # FOOTBALL MENU
        if data == "menu:football":

            text, keyboard = (
                build_football_menu()
            )

            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            return

        # RUGBY MENU
        if data == "menu:rugby":

            text, keyboard = (
                build_rugby_menu()
            )

            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            return

        # COMBAT MENU
        if data == "menu:combat":

            text, keyboard = (
                build_combat_menu()
            )

            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            return

        # CHANNELS PAGE
        if data in [
            "view_channels",
            "menu:channels",
        ]:

            text, keyboard = (
                build_channels_page()
            )

            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            return

        # DATE VIEW
        if data.startswith(
            "date:"
        ):

            parts = data.split(
                ":",
                2,
            )

            if len(parts) != 3:

                logger.error(
                    "Bad date callback: %s",
                    data,
                )

                return

            date_text = parts[1]
            category = parts[2]

            target_date = datetime.strptime(
                date_text,
                "%Y-%m-%d",
            ).date()

            text, keyboard = (
                build_fixtures_page(
                    target_date,
                    category,
                )
            )

            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            return

        # MATCH VIEW
        if data.startswith(
            "match:"
        ):

            parts = data.split(
                ":",
                3,
            )

            if len(parts) != 4:

                logger.error(
                    "Bad match callback: %s",
                    data,
                )

                return

            event_id = parts[1]
            date_text = parts[2]
            category = parts[3]

            target_date = datetime.strptime(
                date_text,
                "%Y-%m-%d",
            ).date()

            text, keyboard = (
                build_match_details_page(
                    event_id,
                    target_date,
                    category,
                )
            )

            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            return

        # UNKNOWN CALLBACK
        logger.warning(
            "Unknown callback: %s",
            data,
        )

        await query.edit_message_text(
            "⚠️ <b>Unknown menu option.</b>",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏠 Main Menu",
                            callback_data="menu:home",
                        )
                    ]
                ]
            ),
            parse_mode="HTML",
        )

    except Exception as error:

        logger.exception(
            "UI Error: %s",
            error,
        )

        await query.edit_message_text(
            "❌ <b>Something went wrong.</b>\n\n"
            "Please return to the main menu and try again.",
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🏠 Main Menu",
                            callback_data="menu:home",
                        )
                    ]
                ]
            ),
            parse_mode="HTML",
        )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context,
):

    logger.exception(
        "Telegram error: %s",
        context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "Starting MatchDay Hub..."
    )

    # Start Bunny health server
    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True,
    )

    health_thread.start()

    # Start Telegram bot
    application = (
        Application
        .builder()
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
        CallbackQueryHandler(
            button_handler
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "MatchDay Hub is online."
    )

    application.run_polling(
        drop_pending_updates=True
    )


# ============================================================
# RUN
# ============================================================

if __name__ == "__main__":

    main()
