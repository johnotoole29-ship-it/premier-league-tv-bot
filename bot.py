import os
import json
import logging
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

logger = logging.getLogger("SportPulse")


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
# DATA
# ============================================================

def load_data():

    try:

        if not os.path.exists(DATA_FILE):
            return {"users": {}}

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            data = json.load(file)

        if "users" not in data:
            data["users"] = {}

        return data

    except Exception as error:

        logger.error(
            "Could not load data: %s",
            error,
        )

        return {"users": {}}


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

    user = DATA["users"][user_id]

    user.setdefault("teams", [])
    user.setdefault("alerts", [])

    return user


# ============================================================
# TIME
# ============================================================

def uk_now():

    return datetime.now(
        UK_TIMEZONE
    )


def get_uk_date():

    return uk_now().strftime(
        "%Y-%m-%d"
    )


def format_display_date(date_string):

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


def format_match_time(event):

    value = (
        event.get("strTime")
        or event.get("strEventTime")
        or ""
    )

    if not value:
        return "TBC"

    return value[:5]


def event_datetime(event):

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

        time_string = time_string[:8]

        if len(time_string) == 5:
            time_string += ":00"

        value = datetime.strptime(
            f"{date_string} {time_string}",
            "%Y-%m-%d %H:%M:%S",
        )

        return value.replace(
            tzinfo=UK_TIMEZONE
        )

    except Exception:

        return None


# ============================================================
# SPORTS DB
# ============================================================

def sportsdb_get(endpoint, params=None):

    url = (
        f"{SPORTSDB_BASE}/"
        f"{SPORTSDB_API_KEY}/"
        f"{endpoint}"
    )

    logger.info(
        "SportsDB request: %s params=%s",
        endpoint,
        params,
    )

    try:

        response = requests.get(
            url,
            params=params or {},
            timeout=20,
        )

        logger.info(
            "SportsDB response: %s",
            response.status_code,
        )

        response.raise_for_status()

        data = response.json()

        return data

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
# EVENT FETCHING
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

    return (
        data.get("events")
        or []
    )


def get_sport_events(
    date,
    sport,
):

    return get_events_for_day(
        date,
        sport=sport,
    )


# ============================================================
# FOOTBALL
# ============================================================

def get_premier_league(date):

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


def get_championship(date):

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


def get_all_football(date):

    return get_sport_events(
        date,
        "Soccer",
    )


# ============================================================
# OTHER SPORTS
# ============================================================

def get_rugby(date):

    return get_sport_events(
        date,
        "Rugby",
    )


def get_cricket(date):

    return get_sport_events(
        date,
        "Cricket",
    )


def get_tennis(date):

    return get_sport_events(
        date,
        "Tennis",
    )


def get_darts(date):

    return get_sport_events(
        date,
        "Darts",
    )


def get_formula1(date):

    return get_sport_events(
        date,
        "Formula 1",
    )


def get_golf(date):

    return get_sport_events(
        date,
        "Golf",
    )


def get_combat(date):

    events = get_sport_events(
        date,
        "Fighting",
    )

    if events:
        return events

    events = get_sport_events(
        date,
        "Boxing",
    )

    return events


# ============================================================
# TV
# ============================================================

def get_tv_channels_for_date(date):

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

        item = {
            "channel": str(channel).strip(),
            "country": str(country).strip(),
        }

        tv_by_event.setdefault(
            str(event_id),
            [],
        ).append(item)

    return tv_by_event


def clean_tv_channels(channels):

    seen = set()
    cleaned = []

    for item in channels:

        channel = str(
            item.get("channel", "")
        ).strip()

        country = str(
            item.get("country", "")
        ).strip()

        if not channel:
            continue

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


def get_tv_for_event(event):

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


def get_event_channels(
    event,
    tv_by_event=None,
):

    event_id = str(
        event.get(
            "idEvent",
            "",
        )
    )

    channels = []

    if tv_by_event:
        channels = tv_by_event.get(
            event_id,
            [],
        )

    if not channels:
        channels = get_tv_for_event(
            event
        )

    return clean_tv_channels(
        channels
    )


# ============================================================
# UK TV
# ============================================================

def is_uk_channel(item):

    country = (
        item.get("country")
        or ""
    ).lower().strip()

    uk_names = [
        "united kingdom",
        "uk",
        "england",
        "scotland",
        "wales",
        "northern ireland",
        "great britain",
    ]

    if country in uk_names:
        return True

    channel = (
        item.get("channel")
        or ""
    ).lower()

    uk_words = [
        "sky sports",
        "sky sport",
        "bbc",
        "itv",
        "tnt sports",
        "premier sports",
        "channel 4",
        "channel five",
        "viaplay uk",
    ]

    return any(
        word in channel
        for word in uk_words
    )


def format_uk_tv(
    event,
    tv_by_event=None,
):

    channels = get_event_channels(
        event,
        tv_by_event,
    )

    uk_channels = [
        item
        for item in channels
        if is_uk_channel(item)
    ]

    if not uk_channels:

        return (
            "🇬🇧 **UK TV**\n"
            "• Not currently listed"
        )

    lines = [
        "🇬🇧 **UK TV**"
    ]

    for item in uk_channels[:6]:

        lines.append(
            f"• {item['channel']}"
        )

    return "\n".join(
        lines
    )


def format_worldwide_tv(
    event,
    tv_by_event=None,
):

    channels = get_event_channels(
        event,
        tv_by_event,
    )

    worldwide = [
        item
        for item in channels
        if not is_uk_channel(item)
    ]

    if not worldwide:

        return (
            "🌍 **WORLDWIDE TV**\n\n"
            "No international listings "
            "are currently available."
        )

    grouped = {}

    for item in worldwide:

        country = (
            item.get("country")
            or "International"
        )

        grouped.setdefault(
            country,
            [],
        ).append(
            item["channel"]
        )

    lines = [
        "🌍 **WORLDWIDE TV**",
        "",
    ]

    for country, channels in grouped.items():

        lines.append(
            f"🌎 **{country}**"
        )

        for channel in channels[:5]:

            lines.append(
                f"• {channel}"
            )

        lines.append("")

    return "\n".join(
        lines
    ).strip()


# ============================================================
# MATCH CARD
# ============================================================

def get_event_title(event):

    home = (
        event.get("strHomeTeam")
        or "Home Team"
    )

    away = (
        event.get("strAwayTeam")
        or "Away Team"
    )

    return (
        f"{home} vs {away}"
    )


def create_match_card(
    event,
    tv_by_event=None,
    show_date=True,
):

    date = (
        event.get("dateEvent")
        or get_uk_date()
    )

    time = format_match_time(
        event
    )

    home = (
        event.get("strHomeTeam")
        or "Home Team"
    )

    away = (
        event.get("strAwayTeam")
        or "Away Team"
    )

    league = (
        event.get("strLeague")
        or ""
    )

    venue = (
        event.get("strVenue")
        or ""
    )

    country = (
        event.get("strCountry")
        or ""
    )

    lines = []

    lines.append(
        "━━━━━━━━━━━━━━━━━━━━"
    )

    if show_date:

        lines.append(
            f"📅 **{format_display_date(date)}**"
        )

    lines.append(
        f"🕒 **{time} UK**"
    )

    lines.append(
        f"⚽ **{home}**"
    )

    lines.append(
        "        **VS**"
    )

    lines.append(
        f"⚽ **{away}**"
    )

    if league:

        lines.append(
            f"🏆 {league}"
        )

    if venue:

        venue_line = f"📍 {venue}"

        if country:
            venue_line += f" · {country}"

        lines.append(
            venue_line
        )

    lines.append("")

    lines.append(
        format_uk_tv(
            event,
            tv_by_event,
        )
    )

    channels = get_event_channels(
        event,
        tv_by_event,
    )

    worldwide = [
        item
        for item in channels
        if not is_uk_channel(item)
    ]

    if worldwide:

        lines.append("")

        lines.append(
            f"🌍 **{len(worldwide)} international "
            f"broadcaster"
            f"{'s' if len(worldwide) != 1 else ''} available**"
        )

    lines.append(
        "━━━━━━━━━━━━━━━━━━━━"
    )

    return "\n".join(lines)


# ============================================================
# BUTTONS
# ============================================================

def match_buttons(event):

    event_id = event.get(
        "idEvent"
    )

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🌍 Worldwide TV",
                    callback_data=f"worldwide:{event_id}",
                ),
            ],
            [
                InlineKeyboardButton(
                    "🔔 Alert Me",
                    callback_data=f"alert:{event_id}",
                ),
                InlineKeyboardButton(
                    "❤️ Follow",
                    callback_data=f"follow:{event_id}",
                ),
            ],
        ]
    )


def back_button():

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏠 Main Menu",
                    callback_data="home",
                )
            ]
        ]
    )


# ============================================================
# MAIN MENU
# ============================================================

def main_menu():

    keyboard = [

        [
            InlineKeyboardButton(
                "⚽ Football",
                callback_data="football",
            ),
            InlineKeyboardButton(
                "🏉 Rugby",
                callback_data="rugby",
            ),
        ],

        [
            InlineKeyboardButton(
                "🏏 Cricket",
                callback_data="cricket",
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
            InlineKeyboardButton(
                "🏎️ Formula 1",
                callback_data="f1",
            ),
        ],

        [
            InlineKeyboardButton(
                "🏌️ Golf",
                callback_data="golf",
            ),
            InlineKeyboardButton(
                "🥊 Combat",
                callback_data="combat",
            ),
        ],

        [
            InlineKeyboardButton(
                "📺 On TV Now",
                callback_data="tv_now",
            ),
        ],

        [
            InlineKeyboardButton(
                "⏱️ Starting Soon",
                callback_data="starting_soon",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔎 Search",
                callback_data="search",
            ),
        ],

        [
            InlineKeyboardButton(
                "🔔 My Alerts",
                callback_data="my_alerts",
            ),
            InlineKeyboardButton(
                "❤️ My Teams",
                callback_data="my_teams",
            ),
        ],

        [
            InlineKeyboardButton(
                "💎 Premium",
                callback_data="premium",
            ),
            InlineKeyboardButton(
                "ℹ️ Help",
                callback_data="help",
            ),
        ],
    ]

    return InlineKeyboardMarkup(
        keyboard
    )


# ============================================================
# HOME
# ============================================================

def home_text():

    return (
        "🔥 **SPORT PULSE ALERTS**\n\n"
        "Choose a sport below to see upcoming fixtures.\n\n"
        "📺 Find UK TV channels\n"
        "🌍 See worldwide broadcasters\n"
        "🔔 Set match alerts\n"
        "❤️ Follow your favourite teams\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🇬🇧 **Times shown in UK time**"
    )


# ============================================================
# SEND EVENTS
# ============================================================

async def send_events(
    query,
    title,
    events,
):

    if not events:

        await query.edit_message_text(
            f"{title}\n\n"
            "⚡ **No fixtures found.**\n\n"
            "TheSportsDB currently has no "
            "events listed for this date.",
            reply_markup=back_button(),
            parse_mode="Markdown",
        )

        return

    events = sorted(
        events,
        key=lambda event: (
            event_datetime(event)
            or datetime.max.replace(
                tzinfo=UK_TIMEZONE
            )
        ),
    )

    tv_by_event = get_tv_channels_for_date(
        get_uk_date()
    )

    text = (
        f"🔥 **{title}**\n\n"
    )

    buttons = []

    for event in events[:12]:

        home = (
            event.get("strHomeTeam")
            or "Home"
        )

        away = (
            event.get("strAwayTeam")
            or "Away"
        )

        time = format_match_time(
            event
        )

        text += (
            f"🕒 **{time}**  "
            f"{home} vs {away}\n"
        )

        event_id = event.get(
            "idEvent"
        )

        if event_id:

            buttons.append(
                [
                    InlineKeyboardButton(
                        f"📺 {home} vs {away}",
                        callback_data=f"event:{event_id}",
                    )
                ]
            )

    text += (
        "\nSelect a fixture for full details "
        "and TV information."
    )

    buttons.append(
        [
            InlineKeyboardButton(
                "🏠 Main Menu",
                callback_data="home",
            )
        ]
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
        parse_mode="Markdown",
    )


# ============================================================
# FOOTBALL MENU
# ============================================================

async def football_menu(query):

    keyboard = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "🏆 Premier League",
                    callback_data="premier_league",
                )
            ],
            [
                InlineKeyboardButton(
                    "🏆 Championship",
                    callback_data="championship",
                )
            ],
            [
                InlineKeyboardButton(
                    "⚽ All Football",
                    callback_data="all_football",
                )
            ],
            [
                InlineKeyboardButton(
                    "🏠 Main Menu",
                    callback_data="home",
                )
            ],
        ]
    )

    await query.edit_message_text(
        "⚽ **FOOTBALL**\n\n"
        "Choose a competition:",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )


# ============================================================
# SPORT CALLBACKS
# ============================================================

async def show_sport(
    query,
    sport_name,
    getter,
):

    today = get_uk_date()

    tomorrow = (
        uk_now()
        + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    events = getter(today)

    if not events:

        events = getter(tomorrow)

    await send_events(
        query,
        sport_name,
        events,
    )


# ============================================================
# EVENT DETAILS
# ============================================================

async def show_event_details(
    query,
    event_id,
):

    today = get_uk_date()

    events = []

    for date in [
        today,
        (
            uk_now()
            + timedelta(days=1)
        ).strftime("%Y-%m-%d"),
        (
            uk_now()
            - timedelta(days=1)
        ).strftime("%Y-%m-%d"),
    ]:

        data = sportsdb_get(
            "lookupevent.php",
            {
                "id": event_id,
            },
        )

        if data:

            events = (
                data.get("events")
                or []
            )

        if events:
            break

    if not events:

        await query.edit_message_text(
            "⚠️ **Fixture not found.**",
            reply_markup=back_button(),
            parse_mode="Markdown",
        )

        return

    event = events[0]

    tv_by_event = get_tv_channels_for_date(
        event.get(
            "dateEvent",
            today,
        )
    )

    text = create_match_card(
        event,
        tv_by_event,
        show_date=True,
    )

    await query.edit_message_text(
        text,
        reply_markup=match_buttons(
            event
        ),
        parse_mode="Markdown",
    )


# ============================================================
# WORLDWIDE TV
# ============================================================

async def worldwide_tv(
    query,
    event_id,
):

    data = sportsdb_get(
        "lookupevent.php",
        {
            "id": event_id,
        },
    )

    events = (
        data.get("events", [])
        if data
        else []
    )

    if not events:

        await query.answer(
            "Fixture not found.",
            show_alert=True,
        )

        return

    event = events[0]

    text = format_worldwide_tv(
        event
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "⬅️ Back to Fixture",
                        callback_data=f"event:{event_id}",
                    )
                ],
                [
                    InlineKeyboardButton(
                        "🏠 Main Menu",
                        callback_data="home",
                    )
                ],
            ]
        ),
        parse_mode="Markdown",
    )


# ============================================================
# ALERTS
# ============================================================

async def set_alert(
    query,
    user_id,
    event_id,
):

    user = get_user_data(
        user_id
    )

    event_id = str(
        event_id
    )

    if event_id not in user["alerts"]:

        user["alerts"].append(
            event_id
        )

        save_data(DATA)

        await query.answer(
            "🔔 Alert added!",
            show_alert=True,
        )

    else:

        await query.answer(
            "🔔 You already have an alert for this fixture.",
            show_alert=True,
        )


async def my_alerts(
    query,
    user_id,
):

    user = get_user_data(
        user_id
    )

    alerts = user.get(
        "alerts",
        [],
    )

    if not alerts:

        await query.edit_message_text(
            "🔔 **MY ALERTS**\n\n"
            "You don't have any match alerts yet.\n\n"
            "Open a fixture and press "
            "**🔔 Alert Me**.",
            reply_markup=back_button(),
            parse_mode="Markdown",
        )

        return

    text = (
        "🔔 **MY ALERTS**\n\n"
    )

    shown = 0

    for event_id in alerts[:10]:

        data = sportsdb_get(
            "lookupevent.php",
            {
                "id": event_id,
            },
        )

        events = (
            data.get("events", [])
            if data
            else []
        )

        if not events:
            continue

        event = events[0]

        text += (
            f"• {get_event_title(event)}\n"
            f"  🕒 {format_match_time(event)}\n"
            f"  📅 {event.get('dateEvent', 'TBC')}\n\n"
        )

        shown += 1

    if shown == 0:

        text += (
            "No current fixtures found."
        )

    await query.edit_message_text(
        text,
        reply_markup=back_button(),
        parse_mode="Markdown",
    )


# ============================================================
# FOLLOW TEAMS
# ============================================================

async def follow_event(
    query,
    user_id,
    event_id,
):

    data = sportsdb_get(
        "lookupevent.php",
        {
            "id": event_id,
        },
    )

    events = (
        data.get("events", [])
        if data
        else []
    )

    if not events:

        await query.answer(
            "Fixture not found.",
            show_alert=True,
        )

        return

    event = events[0]

    home = event.get(
        "strHomeTeam"
    )

    away = event.get(
        "strAwayTeam"
    )

    user = get_user_data(
        user_id
    )

    teams = user["teams"]

    added = []

    for team in [home, away]:

        if team and team not in teams:

            teams.append(team)
            added.append(team)

    save_data(DATA)

    if added:

        await query.answer(
            "❤️ Following: "
            + ", ".join(added),
            show_alert=True,
        )

    else:

        await query.answer(
            "❤️ You're already following these teams.",
            show_alert=True,
        )


async def my_teams(
    query,
    user_id,
):

    user = get_user_data(
        user_id
    )

    teams = user.get(
        "teams",
        [],
    )

    if not teams:

        await query.edit_message_text(
            "❤️ **MY TEAMS**\n\n"
            "You aren't following any teams yet.\n\n"
            "Open a fixture and press "
            "**❤️ Follow**.",
            reply_markup=back_button(),
            parse_mode="Markdown",
        )

        return

    text = (
        "❤️ **MY TEAMS**\n\n"
    )

    for team in teams:

        text += f"• {team}\n"

    await query.edit_message_text(
        text,
        reply_markup=back_button(),
        parse_mode="Markdown",
    )


# ============================================================
# TV NOW
# ============================================================

async def tv_now(
    query,
):

    date = get_uk_date()

    events = get_events_for_day(
        date
    )

    if not events:

        await query.edit_message_text(
            "📺 **ON TV NOW**\n\n"
            "⚡ No events are currently listed.",
            reply_markup=back_button(),
            parse_mode="Markdown",
        )

        return

    tv_by_event = get_tv_channels_for_date(
        date
    )

    now = uk_now()

    active = []

    for event in events:

        event_time = event_datetime(
            event
        )

        if not event_time:
            continue

        if (
            event_time
            <= now
            <= event_time + timedelta(
                hours=3
            )
        ):

            channels = get_event_channels(
                event,
                tv_by_event,
            )

            if channels:
                active.append(
                    event
                )

    if not active:

        await query.edit_message_text(
            "📺 **ON TV NOW**\n\n"
            "No live/ongoing events with "
            "TV listings were found right now.",
            reply_markup=back_button(),
            parse_mode="Markdown",
        )

        return

    buttons = []

    text = (
        "📺 **ON TV NOW**\n\n"
    )

    for event in active[:12]:

        text += (
            f"🕒 **{format_match_time(event)}** "
            f"{get_event_title(event)}\n"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    f"📺 {get_event_title(event)}",
                    callback_data=f"event:{event.get('idEvent')}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "🏠 Main Menu",
                callback_data="home",
            )
        ]
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
        parse_mode="Markdown",
    )


# ============================================================
# STARTING SOON
# ============================================================

async def starting_soon(
    query,
):

    today = get_uk_date()

    tomorrow = (
        uk_now()
        + timedelta(days=1)
    ).strftime("%Y-%m-%d")

    events = (
        get_events_for_day(today)
        + get_events_for_day(tomorrow)
    )

    now = uk_now()

    upcoming = []

    for event in events:

        event_time = event_datetime(
            event
        )

        if not event_time:
            continue

        minutes = (
            event_time - now
        ).total_seconds() / 60

        if 0 <= minutes <= 180:

            upcoming.append(
                event
            )

    upcoming.sort(
        key=lambda event:
        event_datetime(event)
        or datetime.max.replace(
            tzinfo=UK_TIMEZONE
        )
    )

    if not upcoming:

        await query.edit_message_text(
            "⏱️ **STARTING SOON**\n\n"
            "No fixtures are starting "
            "within the next 3 hours.",
            reply_markup=back_button(),
            parse_mode="Markdown",
        )

        return

    text = (
        "⏱️ **STARTING SOON**\n\n"
    )

    buttons = []

    for event in upcoming[:12]:

        text += (
            f"🕒 **{format_match_time(event)}** "
            f"{get_event_title(event)}\n"
        )

        buttons.append(
            [
                InlineKeyboardButton(
                    f"📺 {get_event_title(event)}",
                    callback_data=f"event:{event.get('idEvent')}",
                )
            ]
        )

    buttons.append(
        [
            InlineKeyboardButton(
                "🏠 Main Menu",
                callback_data="home",
            )
        ]
    )

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(
            buttons
        ),
        parse_mode="Markdown",
    )


# ============================================================
# HELP
# ============================================================

async def help_menu(query):

    await query.edit_message_text(
        "ℹ️ **SPORT PULSE HELP**\n\n"
        "⚽ Choose a sport to view fixtures.\n"
        "📺 Open a fixture to see UK TV listings.\n"
        "🌍 Worldwide TV shows international broadcasters.\n"
        "🔔 Alert Me saves a match alert.\n"
        "❤️ Follow saves the teams.\n"
        "⏱️ Starting Soon shows events beginning shortly.\n"
        "📺 On TV Now shows events currently being broadcast.\n\n"
        "🇬🇧 All times are shown in UK time.",
        reply_markup=back_button(),
        parse_mode="Markdown",
    )


# ============================================================
# PREMIUM
# ============================================================

async def premium_menu(query):

    await query.edit_message_text(
        "💎 **SPORT PULSE PREMIUM**\n\n"
        "Premium features coming soon.\n\n"
        "🚀 More alerts\n"
        "📺 Advanced TV listings\n"
        "❤️ More followed teams\n"
        "🌍 Enhanced worldwide coverage\n"
        "⚡ Faster fixture updates",
        reply_markup=back_button(),
        parse_mode="Markdown",
    )


# ============================================================
# SEARCH
# ============================================================

async def search_menu(query):

    await query.edit_message_text(
        "🔎 **SEARCH**\n\n"
        "Use the command:\n\n"
        "`/search Arsenal`\n\n"
        "to search for a team.",
        reply_markup=back_button(),
        parse_mode="Markdown",
    )


async def search_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    if not context.args:

        await update.message.reply_text(
            "🔎 Use:\n\n"
            "`/search Arsenal`",
            parse_mode="Markdown",
        )

        return

    search_text = " ".join(
        context.args
    )

    data = sportsdb_get(
        "searchteams.php",
        {
            "t": search_text,
        },
    )

    teams = (
        data.get("teams", [])
        if data
        else []
    )

    if not teams:

        await update.message.reply_text(
            f"🔎 No teams found for **{search_text}**.",
            parse_mode="Markdown",
        )

        return

    text = (
        f"🔎 **SEARCH RESULTS**\n\n"
    )

    for team in teams[:10]:

        text += (
            f"⚽ **{team.get('strTeam', 'Unknown')}**\n"
            f"🏆 {team.get('strLeague', 'Unknown')}\n\n"
        )

    await update.message.reply_text(
        text,
        parse_mode="Markdown",
    )


# ============================================================
# CALLBACK HANDLER
# ============================================================

async def callback_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    query = update.callback_query

    await query.answer()

    data = query.data

    user_id = query.from_user.id


    # --------------------------------------------------------
    # HOME
    # --------------------------------------------------------

    if data == "home":

        await query.edit_message_text(
            home_text(),
            reply_markup=main_menu(),
            parse_mode="Markdown",
        )

        return


    # --------------------------------------------------------
    # FOOTBALL
    # --------------------------------------------------------

    if data == "football":

        await football_menu(
            query
        )

        return


    if data == "premier_league":

        await show_sport(
            query,
            "PREMIER LEAGUE",
            get_premier_league,
        )

        return


    if data == "championship":

        await show_sport(
            query,
            "CHAMPIONSHIP",
            get_championship,
        )

        return


    if data == "all_football":

        await show_sport(
            query,
            "FOOTBALL",
            get_all_football,
        )

        return


    # --------------------------------------------------------
    # SPORTS
    # --------------------------------------------------------

    if data == "rugby":

        await show_sport(
            query,
            "RUGBY",
            get_rugby,
        )

        return


    if data == "cricket":

        await show_sport(
            query,
            "CRICKET",
            get_cricket,
        )

        return


    if data == "tennis":

        await show_sport(
            query,
            "TENNIS",
            get_tennis,
        )

        return


    if data == "darts":

        await show_sport(
            query,
            "DARTS",
            get_darts,
        )

        return


    if data == "f1":

        await show_sport(
            query,
            "FORMULA 1",
            get_formula1,
        )

        return


    if data == "golf":

        await show_sport(
            query,
            "GOLF",
            get_golf,
        )

        return


    if data == "combat":

        await show_sport(
            query,
            "COMBAT SPORTS",
            get_combat,
        )

        return


    # --------------------------------------------------------
    # TV
    # --------------------------------------------------------

    if data == "tv_now":

        await tv_now(
            query
        )

        return


    if data == "starting_soon":

        await starting_soon(
            query
        )

        return


    # --------------------------------------------------------
    # SEARCH
    # --------------------------------------------------------

    if data == "search":

        await search_menu(
            query
        )

        return


    # --------------------------------------------------------
    # ALERTS
    # --------------------------------------------------------

    if data == "my_alerts":

        await my_alerts(
            query,
            user_id,
        )

        return


    if data == "my_teams":

        await my_teams(
            query,
            user_id,
        )

        return


    # --------------------------------------------------------
    # PREMIUM
    # --------------------------------------------------------

    if data == "premium":

        await premium_menu(
            query
        )

        return


    # --------------------------------------------------------
    # HELP
    # --------------------------------------------------------

    if data == "help":

        await help_menu(
            query
        )

        return


    # --------------------------------------------------------
    # EVENT
    # --------------------------------------------------------

    if data.startswith("event:"):

        event_id = data.split(
            ":",
            1,
        )[1]

        await show_event_details(
            query,
            event_id,
        )

        return


    # --------------------------------------------------------
    # WORLDWIDE
    # --------------------------------------------------------

    if data.startswith("worldwide:"):

        event_id = data.split(
            ":",
            1,
        )[1]

        await worldwide_tv(
            query,
            event_id,
        )

        return


    # --------------------------------------------------------
    # ALERT
    # --------------------------------------------------------

    if data.startswith("alert:"):

        event_id = data.split(
            ":",
            1,
        )[1]

        await set_alert(
            query,
            user_id,
            event_id,
        )

        return


    # --------------------------------------------------------
    # FOLLOW
    # --------------------------------------------------------

    if data.startswith("follow:"):

        event_id = data.split(
            ":",
            1,
        )[1]

        await follow_event(
            query,
            user_id,
            event_id,
        )

        return


# ============================================================
# START COMMAND
# ============================================================

async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
):

    get_user_data(
        update.effective_user.id
    )

    await update.message.reply_text(
        home_text(),
        reply_markup=main_menu(),
        parse_mode="Markdown",
    )


# ============================================================
# ERROR HANDLER
# ============================================================

async def error_handler(
    update,
    context,
):

    logger.error(
        "Bot error: %s",
        context.error,
        exc_info=context.error,
    )


# ============================================================
# MAIN
# ============================================================

def main():

    logger.info(
        "Starting Sport Pulse bot..."
    )

    application = (
        Application.builder()
        .token(TELEGRAM_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler(
            "start",
            start_command,
        )
    )

    application.add_handler(
        CommandHandler(
            "search",
            search_command,
        )
    )

    application.add_handler(
        CallbackQueryHandler(
            callback_handler
        )
    )

    application.add_error_handler(
        error_handler
    )

    logger.info(
        "Sport Pulse bot is online."
    )

    application.run_polling(
        drop_pending_updates=True
    )


if __name__ == "__main__":
    main()
