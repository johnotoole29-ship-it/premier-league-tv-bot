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
        except Exception:
            pass

    date_value = event.get("dateEvent") or event.get("dateEventLocal")
    time_value = event.get("strTime") or event.get("strEventTime") or "00:00:00"
    if not date_value:
        return None
    try:
        clean_time = str(time_value)[:8]
        if len(clean_time) == 5:
            clean_time += ":00"
        utc_datetime = datetime.strptime(
            f"{date_value} {clean_time}", "%Y-%m-%d %H:%M:%S"
        ).replace(tzinfo=timezone.utc)
        return utc_datetime.astimezone(UK_TIMEZONE)
    except Exception:
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
    return [e for e in events if "premier league" in (e.get("strLeague") or "").lower()]

def get_global_tv(date_value):
    # Removed the 'a' parameter so it pulls channels worldwide
    data = sportsdb_get("eventstv.php", {"d": date_string(date_value), "s": "Soccer"})
    if not data:
        return {}

    broadcasts = data.get("tvevents") or data.get("events") or []
    tv_by_event = {}

    for broadcast in broadcasts:
        event_id = str(broadcast.get("idEvent") or broadcast.get("id") or "")
        if not event_id:
            continue

        channel = (broadcast.get("strChannel") or broadcast.get("strName") or "").strip()
        country = (broadcast.get("strCountry") or broadcast.get("strLocation") or "Intl").strip()
        
        if not channel:
            continue

        tv_by_event.setdefault(event_id, [])
        entry = f"{country}: {channel}"
        
        if entry not in tv_by_event[event_id]:
            tv_by_event[event_id].append(entry)

    return tv_by_event


# ============================================================
# UI FORMATTING
# ============================================================

def tv_text_global(event, tv_by_event):
    event_id = str(event.get("idEvent") or "")
    channels = tv_by_event.get(event_id, [])

    if not channels:
        return "📺 <b>TV:</b> TBC"

    lines = ["📺 <b>TV:</b>"]
    # Limit to 10 channels so the message doesn't get ridiculously long
    for entry in channels[:10]:
        safe_entry = html.escape(entry)
        lines.append(f"• {safe_entry}")
        
    if len(channels) > 10:
        lines.append(f"• <i>...and {len(channels) - 10} more</i>")

    return "\n".join(lines)


def match_text(event, tv_by_event, number=None):
    home = html.escape(event.get("strHomeTeam") or "Home")
    away = html.escape(event.get("strAwayTeam") or "Away")
    
    event_time = event_datetime_uk(event)
    time_text = event_time.strftime("%H:%M") if event_time else "TBC"
    prefix = f"{number}. " if number is not None else ""

    return (
        f"{prefix}🕒 <b>{time_text} UK</b>\n"
        f"⚽ <b>{home} vs {away}</b>\n"
        f"{tv_text_global(event, tv_by_event)}"
    )


# ============================================================
# FOLDER PAGES (LEAGUES)
# ============================================================

def leagues_menu_page(date_value):
    events = get_football_events(date_value)
    
    if not events:
        text = f"📅 <b>{pretty_date(date_value)}</b>\n\n❌ <b>No fixtures found.</b>"
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("⬅️ Prev Day", callback_data=f"lday:{date_string(date_value - timedelta(days=1))}"),
                InlineKeyboardButton("Next Day ➡️", callback_data=f"lday:{date_string(date_value + timedelta(days=1))}"),
            ],
            [InlineKeyboardButton("⬅️ Home", callback_data="home")]
        ])
        return text, keyboard

    # Extract unique leagues
    leagues = {}
    for e in events:
        lid = str(e.get("idLeague") or "")
        lname = e.get("strLeague") or "Unknown League"
        if lid:
            leagues[lid] = lname

    # Sort alphabetically
    sorted_leagues = sorted(leagues.items(), key=lambda x: x[1])
    
    text = f"📅 <b>{pretty_date(date_value)}</b>\n📁 <b>Select a League:</b>\n<i>({len(events)} matches across {len(leagues)} leagues)</i>"
    
    # Build keyboard (2 leagues per row)
    keyboard = []
    row = []
    for lid, lname in sorted_leagues:
        safe_name = lname if len(lname) < 30 else lname[:27] + "..."
        row.append(InlineKeyboardButton(safe_name, callback_data=f"lg:{date_string(date_value)}:{lid}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Add navigation to the bottom
    keyboard.append([
        InlineKeyboardButton("⬅️ Prev Day", callback_data=f"lday:{date_string(date_value - timedelta(days=1))}"),
        InlineKeyboardButton("Next Day ➡️", callback_data=f"lday:{date_string(date_value + timedelta(days=1))}"),
    ])
    keyboard.append([InlineKeyboardButton("⬅️ Back to Home", callback_data="home")])

    return text, InlineKeyboardMarkup(keyboard)


def specific_league_fixtures_page(date_value, league_id):
    events = get_football_events(date_value)
    
    # Filter for the selected league
    league_events = [e for e in events if str(e.get("idLeague")) == str(league_id)]
    
    if not league_events:
        return "❌ <b>Matches no longer found.</b>", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data=f"lday:{date_string(date_value)}")]])

    league_name = html.escape(league_events[0].get("strLeague") or "League")
    
    fallback_date = datetime(2099, 12, 31, tzinfo=UK_TIMEZONE)
    league_events.sort(key=lambda e: event_datetime_uk(e) or fallback_date)
    
    tv_by_event = get_global_tv(date_value)
    
    text = f"📅 <b>{pretty_date(date_value)}</b>\n🏆 <b>{league_name}</b>\n\n"
    
    for index, event in enumerate(league_events, start=1):
        text += match_text(event, tv_by_event, index) + "\n\n"
        
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Leagues", callback_data=f"lday:{date_string(date_value)}")],
        [InlineKeyboardButton("🏠 Home", callback_data="home")]
    ])
    
    return text, keyboard


# ============================================================
# BOT COMMANDS & HANDLERS
# ============================================================

def home_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🏆 Premier League Today", callback_data="premier_today")],
        [InlineKeyboardButton("📁 All Football (By League)", callback_data=f"lday:{date_string(uk_date())}")],
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

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data

    # HOME
    if data == "home":
        await query.answer()
        await query.edit_message_text(home_text(), reply_markup=home_keyboard(), parse_mode="HTML")
        return

    # PREMIER LEAGUE (Fast-track)
    if data == "premier_today":
        await query.answer()
        await query.edit_message_text("⏳ <b>Loading Premier League...</b>", parse_mode="HTML")
        try:
            date_value = uk_date()
            events = get_premier_league_events(date_value)
            tv_by_event = get_global_tv(date_value)
            
            fallback_date = datetime(2099, 12, 31, tzinfo=UK_TIMEZONE)
            events.sort(key=lambda e: event_datetime_uk(e) or fallback_date)
            
            text = f"📅 <b>{pretty_date(date_value)}</b>\n🏆 <b>Premier League</b>\n\n"
            if not events:
                text += "❌ <b>No Premier League fixtures today.</b>"
            else:
                for index, event in enumerate(events, start=1):
                    text += match_text(event, tv_by_event, index) + "\n\n"
                    
            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="home")]])
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as error:
            logger.exception("Error: %s", error)
            await query.edit_message_text("❌ <b>Error loading fixtures.</b>", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="home")]]), parse_mode="HTML")
        return

    # LEAGUE MENU (Folders)
    if data.startswith("lday:"):
        await query.answer()
        date_str = data.split(":")[1]
        try:
            date_value = datetime.strptime(date_str, "%Y-%m-%d").date()
            await query.edit_message_text("⏳ <b>Loading Leagues...</b>", parse_mode="HTML")
            text, keyboard = leagues_menu_page(date_value)
            await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        except Exception as error:
            logger.exception("Error loading leagues: %s", error)
        return

    # SPECIFIC LEAGUE VIEW
    if data.startswith("lg:"):
        await query.answer()
        parts = data.split(":")
        if len(parts) == 3:
            date_str, league_id = parts[1], parts[2]
            try:
                date_value = datetime.strptime(date_str, "%Y-%m-%d").date()
                await query.edit_message_text("⏳ <b>Fetching Matches & TV...</b>", parse_mode="HTML")
                text, keyboard = specific_league_fixtures_page(date_value, league_id)
                await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception as error:
                logger.exception("Error loading league fixtures: %s", error)
        return

    await query.answer("This button is no longer available.")

async def error_handler(update, context):
    logger.exception("Telegram error:", exc_info=context.error)


# ============================================================
# MAIN ENTRY POINT
# ============================================================

def main():
    threading.Thread(target=start_health_server, daemon=True).start()
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)

    logger.info("Starting bot polling...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
    
