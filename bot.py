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
                            "🏠 Main Menu",
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
        f"📅 <b>{pretty_date(date_value)}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )

    keyboard_buttons = []

    if not events:

        text += (
            "<blockquote>"
            f"❌ No {html.escape(meta['title'])} "
            "events scheduled for this date."
            "</blockquote>"
        )

    else:

        text += (
            "<i>Tap an event to open Match Center "
            "and view TV channels.</i>\n\n"
        )

        for event in events:

            home = str(
                event.get("strHomeTeam")
                or ""
            ).strip()

            away = str(
                event.get("strAwayTeam")
                or ""
            ).strip()

            event_name = str(
                event.get("strEvent")
                or ""
            ).strip()

            if home and away:

                match_title = (
                    f"{home} vs {away}"
                )

            elif event_name:

                match_title = event_name

            else:

                match_title = "TBA Event"

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
                    "idEvent",
                    "",
                )
            )

            if not event_id:
                continue

            button_text = (
                f"[{time_text}] "
                f"{match_title}"
            )

            if len(button_text) > 48:

                button_text = (
                    button_text[:45]
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

    today = datetime.now(
        UK_TIMEZONE
    ).date()

    previous_day = (
        date_value
        - timedelta(days=1)
    )

    next_day = (
        date_value
        + timedelta(days=1)
    )

    back_target = (
        "menu:home"
    )

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
                "⬅️ Prev",
                callback_data=(
                    f"date:"
                    f"{date_string(previous_day)}:"
                    f"{category}"
                ),
            ),

            InlineKeyboardButton(
                "📅 Today",
                callback_data=(
                    f"date:"
                    f"{date_string(today)}:"
                    f"{category}"
                ),
            ),

            InlineKeyboardButton(
                "Next ➡️",
                callback_data=(
                    f"date:"
                    f"{date_string(next_day)}:"
                    f"{category}"
                ),
            ),
        ]
    )

    keyboard_buttons.append(
        [
            InlineKeyboardButton(
                "🔄 Refresh",
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
# MATCH DETAILS PAGE
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
                            "🏠 Main Menu",
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
                item.get("idEvent")
            ) == str(event_id)
        ),
        None,
    )

    if not event:

        return (
            "❌ <b>Event data is no longer available.</b>",
            InlineKeyboardMarkup(
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
            ),
        )

    home = str(
        event.get("strHomeTeam")
        or ""
    ).strip()

    away = str(
        event.get("strAwayTeam")
        or ""
    ).strip()

    event_name = str(
        event.get("strEvent")
        or ""
    ).strip()

    if home and away:

        match_title = (
            f"{home} vs {away}"
        )

    elif event_name:

        match_title = event_name

    else:

        match_title = "TBA Event"

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
        f"🏆 <b>Event:</b> "
        f"{html.escape(match_title)}\n"
        f"📅 <b>Date:</b> "
        f"{pretty_date(date_value)}\n"
        f"⏰ <b>Start:</b> "
        f"{time_text} UK\n\n"
    )

    if channels:

        text += (
            "📺 <b>Supported Broadcasts</b>\n\n"
        )

        for channel in channels:

            text += (
                f"• {html.escape(channel)}\n"
            )

    else:

        text += (
            "<blockquote>"
            "📺 No supported broadcaster is "
            "currently listed for this event."
            "</blockquote>"
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
# START COMMAND
# ============================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    chat = update.effective_chat
    message = update.effective_message

    # ========================================================
    # GROUP / TOPIC MODE
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

            text = (
                "⚡ <b>MATCHDAY HUB</b>\n"
                "<i>Fixtures & TV Guide</i>\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                "Use the private Match Center "
                "to browse fixtures and channels."
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
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

        return


    # ========================================================
    # PRIVATE CHAT
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

    query = update.callback_query

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

            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            return


        # ====================================================
        # FOOTBALL
        # ====================================================

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


        # ====================================================
        # RUGBY
        # ====================================================

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


        # ====================================================
        # COMBAT
        # ====================================================

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


        # ====================================================
        # CHANNELS
        # ====================================================

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


        # ====================================================
        # DATE PAGE
        # ====================================================

        if data.startswith(
            "date:"
        ):

            parts = data.split(
                ":",
                2,
            )

            if len(parts) != 3:

                logger.error(
                    "Invalid date callback: %s",
                    data,
                )

                return

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

            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            return


        # ====================================================
        # MATCH PAGE
        # ====================================================

        if data.startswith(
            "match:"
        ):

            parts = data.split(
                ":",
                3,
            )

            if len(parts) != 4:

                logger.error(
                    "Invalid match callback: %s",
                    data,
                )

                return

            event_id = parts[1]
            date_text = parts[2]
            category = parts[3]

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

            await query.edit_message_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML",
            )

            return


        # ====================================================
        # UNKNOWN CALLBACK
        # ====================================================

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


    # ========================================================
    # UI ERROR
    # ========================================================

    except Exception as error:

        logger.exception(
            "UI Error: %s",
            error,
        )

        await query.edit_message_text(
            "❌ <b>Something went wrong.</b>\n\n"
            "Please return to the main menu "
            "and try again.",
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
        "Starting MatchDay Hub..."
    )

    health_thread = threading.Thread(
        target=start_health_server,
        daemon=True,
    )

    health_thread.start()

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
