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
# CONFIG & TIMEZONE
# ============================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SPORTSDB_API_KEY = os.getenv("SPORTSDB_API_KEY")

SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"

# Note: Your container MUST have the 'tzdata' package installed 
# for ZoneInfo to work on Linux.
UK_TIMEZONE = ZoneInfo("Europe/London")


# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("SportPulse")


# ============================================================
# CHECK ENVIRONMENT VARIABLES
# ============================================================
# TEMPORARY DEBUG LINE
logger.info(f"DEBUG - Found Environment Keys: {list(os.environ.keys())}")

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
        # Suppress logging to keep console clean
        pass

def start_health_server():
    port = int(os.getenv("PORT", 8080))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info("Health check server listening on port %s", port)
    server.serve_forever()


# ============================================================
# SPORTSDB REQUEST
# ============================================================

def sportsdb_get(endpoint, params=None):
    url = f"{SPORTSDB_BASE}/{SPORTSDB_API_KEY}/{endpoint}"
    try:
        response = requests.get(url, params=params or {}, timeout=20)
        response.raise_for_status()
        return response.json()
    except (requests.RequestException, ValueError) as error:
        logger.error("SportsDB request failed: %s", error)
        return None


# ============================================================
# DATE & TIME HELPERS
# ============================================================

def uk_now():
    return datetime.now(UK_TIMEZONE)

def uk_date():
    return uk_now().date()

def date_string(date_value):
    return date_value.strftime("%Y-%m-%d")

def pretty_date(date_value):
    return date_value.strftime("%A %d %B %Y")

def event_datetime_uk(event):
    timestamp = event.get("strTimestamp")

    if timestamp:
        try:
            if str(timestamp).isdigit():
                utc_time = datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
                return utc_time.astimezone(UK_TIMEZONE)

            cleaned = str(timestamp).replace("Z", "+00:00")
            parsed = datetime.fromisoformat(cleaned)

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            return parsed.astimezone(UK_TIMEZONE)
        except Exception as error:
            logger.warning("Could not parse strTimestamp %s: %s", timestamp, error)

    date_value = event.get("dateEvent") or event.get("dateEventLocal")
    time_value = event.get("strTime") or event.get("strEventTime") or "00:00:00"

    if not date_value:
        return None

    try:
        clean_time = str(time_value)[:8]
        if len(clean_time) == 5:
            clean_time += ":00"

        utc_datetime = datetime.strptime(
            f"{date_value} {clean_time}",
            "%Y-%m-%d %H:%M:%S",
        ).replace(tzinfo=timezone.utc)
        return utc_datetime.astimezone(UK_TIMEZONE)
    except Exception as error:
        return None


# ============================================================
# DATA FETCHERS
# ============================================================

def get_football_events(date_value):
    data = sportsdb_get("eventsday.php", {"d": date_string(date_value), "s": "Soccer"})
    if not data:
        return []
    return data.get("events") or []

def get_premier_league_events(date_value):
    events = get_football_events(date_value)
    results = []
    for event in events:
        league = (event.get("strLeague") or "").lower()
        if "premier league" in league or "english premier league" in league:
            results.append(event)
    return results

def get_uk_tv(date_value):
    data = sportsdb_get("eventstv.php", {"d": date_string(date_value), "s": "Soccer", "a": "United_Kingdom"})
    if not data:
        return {}

    broadcasts = data.get("tvevents") or data.get("events") or []
    tv_by_event = {}

    for broadcast in broadcasts:
        event_id = broadcast.get("idEvent") or broadcast.get("id")
        if not event_id:
            continue

        channel = (broadcast.get("strChannel") or broadcast.get("strName") or "").strip()
        if not channel:
            continue

        event_key = str(event_id)
        tv_by_event.setdefault(event_key, [])

        if channel not in tv_by_event[event_key]:
            tv_by_event[event_key].append(channel)

    return tv_by_event


# ============================================================
# UI FORMATTING (WITH HTML ESCAPING)
# ============================================================

def uk_tv_text(event, tv_by_event):
    event_id = str(event.get("idEvent") or "")
    channels = tv_by_event.get(event_id, [])

    if not channels:
        return "📺 <b>UK TV:</b> TBC"

    lines = ["📺 <b>UK TV:</b>"]
    for channel in channels[:8]:
        # ESCAPE HTML: Fixes crashes when TV channels contain '&' (e.g. A&E)
        safe_channel = html.escape(channel)
        lines.append(f"• {safe_channel}")

    return "\n".join(lines)


def match_text(event, tv_by_event, number=None):
    # ESCAPE HTML: Fixes crashes when team names contain '&' (e.g. Brighton & Hove Albion)
    home = html.escape(event.get("strHomeTeam") or "Home")
    away = html.escape(event.get("strAwayTeam") or "Away")
    
    event_time = event_datetime_uk(event)
    time_text = event_time.strftime("%H:%M") if event_time else "TBC"

    prefix = f"{number}. " if number is not None else ""

    return (
        f"{prefix}🕒 <b>{time_text} UK</b>\n"
        f"⚽ <b>{home} vs {away}</b>\n"
        f"{uk_tv_text(event, tv_by_event)}"
    )


def fixtures_page(date_value, mode="premier"):
    if mode == "premier":
        events = get_premier_league_events(date_value)
        title = "🏆 Premier League"
    else:
        events = get_football_events(date_value)
        title = "⚽ Football"

    # BUG FIX: Use 2099 instead of datetime.max to prevent Linux OverflowErrors
    fallback_date = datetime(2099, 12, 31, tzinfo=UK_TIMEZONE)
    events.sort(key=lambda event: event_datetime_uk(event) or fallback_date)

    tv_by_event = get_uk_tv(date_value)

    text = f"📅 <b>{pretty_date(date_value)}</b>\n{title}\n\n"

    if not events:
        text += "❌ <b>No fixtures found.</b>\n\nTry the next day."
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⬅️ Previous Day", callback_data=f"day:{date_string(date_value - timedelta(days=1))}:{mode}"),
                InlineKeyboardButton("Next Day ➡️", callback_data=f"day:{date_string(date_value + timedelta(days=1))}:{mode}"),
            ],
            [InlineKeyboardButton("⬅️ Back", callback_data="home")],
        ])
        return text, keyboard

    display_events = events[:20]
    text += f"📋 <b>{len(events)} fixture{'s' if len(events) != 1 else ''}</b>\n\n"

    for index, event in enumerate(display_events, start=1):
        text += match_text(event, tv_by_event, index) + "\n\n"

    if len(events) > 20:
        text += f"ℹ️ Showing first 20 of {len(events)} fixtures.\n\n"

    keyboard = [
        [
            InlineKeyboardButton("⬅️ Previous Day", callback_data=f"day:{date_string(date_value - timedelta(days=1))}:{mode}"),
            InlineKeyboardButton("Next Day ➡️", callback_data=f"day:{date_string(date_value + timedelta(days=1))}:{mode}"),
        ],
        [InlineKeyboardButton("🌍 View Match TV", callback_data="tv_help")],
        [InlineKeyboardButton("⬅️ Back", callback_data="home")],
    ]
    return text, InlineKeyboardMarkup(keyboard)


# ============================================================
# BOT COMMANDS & HANDLERS
# ============================================================

def home_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Premier League", callback_data="premier_today")],
        [InlineKeyboardButton("⚽ All Football", callback_data="football_today")],
        [InlineKeyboardButton("📺 TV Channels", callback_data="tv_help")],
    ])

def home_text():
    return (
        "🔥 <b>SPORT PULSE ALERTS</b>\n\n"
        "⚽ Football fixtures and TV channels\n\n"
        "Choose an option below.\n\n"
        "🕒 All match times are shown in <b>UK time</b>."
    )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(home_text(), reply_markup=home_keyboard(), parse_mode="HTML")

async def show_fixtures(query, date_value, mode):
    await query.answer()
    try:
        await query.edit_message_text("⏳ <b>Loading fixtures and TV channels...</b>", parse_mode="HTML")
        text, keyboard = fixtures_page(date_value, mode)
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as error:
        logger.exception("Fixture error: %s", error)
        await query.edit_message_text(
            "❌ <b>Something went wrong.</b>\n\nPlease try again.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="home")]]),
            parse_mode="HTML",
        )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    if data == "home":
        await query.answer()
        await query.edit_message_text(home_text(), reply_markup=home_keyboard(), parse_mode="HTML")
        return

    if data == "premier_today":
        await show_fixtures(query, uk_date(), "premier")
        return

    if data == "football_today":
        await show_fixtures(query, uk_date(), "football")
        return

    if data.startswith("day:"):
        parts = data.split(":")
        if len(parts) == 3:
            try:
                selected_date = datetime.strptime(parts[1], "%Y-%m-%d").date()
                await show_fixtures(query, selected_date, parts[2])
            except ValueError:
                pass
        return

    if data == "tv_help":
        await query.answer()
        text = (
            "📺 <b>TV CHANNELS</b>\n\n"
            "The bot checks TheSportsDB's TV listings for each football fixture.\n\n"
            "If a UK broadcaster is listed, it appears directly underneath the match.\n\n"
            "If no UK broadcaster is currently listed, you will see:\n\n"
            "📺 <b>UK TV: TBC</b>\n\n"
            "Tap a match's TV button in future versions to see worldwide broadcasters."
        )
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="home")]]),
            parse_mode="HTML",
        )
        return

    await query.answer("This button is no longer available.")

async def error_handler(update, context):
    logger.exception("Telegram error:", exc_info=context.error)


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    # 1. Start the health check for Bunny.net
    threading.Thread(target=start_health_server, daemon=True).start()

    # 2. Start the Bot
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    logger.info("Starting bot polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
