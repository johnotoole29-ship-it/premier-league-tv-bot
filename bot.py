import os
import logging
import threading
import html
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from http.server import BaseHTTPRequestHandler, HTTPServer

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# ============================================================
# CONFIG
# ============================================================
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
SPORTSDB_API_KEY = os.getenv("SPORTSDB_API_KEY")
SPORTSDB_BASE = "https://www.thesportsdb.com/api/v1/json"
UK_TIMEZONE = ZoneInfo("Europe/London")

# ============================================================
# MY APP CHANNELS (LOWERCASE)
# ============================================================
MY_CHANNELS = [
    "sky sports",       # UK
    "tnt sports",       # UK
    "amazon prime",     # UK
    "stan sport",       # Australia
    "fubo",             # Canada
    "espn",             # Caribbean
    "now prem",         # Hong Kong
    "now 4k",           # Hong Kong
    "star sports",      # India
    "vidio",            # Indonesia
    "coupang play",     # Korea
    "astro",            # Malaysia
    "bein sports",      # MENA
    "sky sport",        # New Zealand
    "hub premier",      # Singapore
    "supersport",       # South Africa
    "monomax",          # Thailand
    "usa network",      # USA
    "peacock",          # USA
    "nbc"               # USA
]

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger("SportPulse")

if not TELEGRAM_TOKEN or not SPORTSDB_API_KEY:
    raise RuntimeError("Missing TELEGRAM_TOKEN or SPORTSDB_API_KEY. Check your Bunny.net environment variables.")

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
# API & DATA
# ============================================================
def sportsdb_get(endpoint, params=None):
    url = f"{SPORTSDB_BASE}/{SPORTSDB_API_KEY}/{endpoint}"
    try:
        response = requests.get(url, params=params or {}, timeout=15)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"SportsDB Error: {e}")
        return None

def date_string(d): 
    return d.strftime("%Y-%m-%d")

def pretty_date(d): 
    return d.strftime("%A %d %B %Y")

def get_premier_league_events(date_value):
    data = sportsdb_get("eventsday.php", {"d": date_string(date_value), "s": "Soccer"})
    
    if not data or not isinstance(data.get("events"), list):
        return []
    
    pl_events = []
    for e in data["events"]:
        if str(e.get("idLeague")) == "4328":
            pl_events.append(e)
            
    return pl_events[:15]

def get_tv_channels(date_value):
    data = sportsdb_get("eventstv.php", {"d": date_string(date_value), "s": "Soccer"})
    tv_dict = {}
    
    if not data:
        return tv_dict
        
    broadcasts = data.get("tvevents") or data.get("events") or []
    if not isinstance(broadcasts, list):
        return tv_dict
        
    for b in broadcasts:
        event_id = str(b.get("idEvent") or b.get("id") or "")
        channel = (b.get("strChannel") or b.get("strName") or "").strip()
        country = (b.get("strCountry") or b.get("strLocation") or "UK").strip()
        
        if event_id and channel:
            channel_lower = channel.lower()
            is_available = any(my_chan in channel_lower for my_chan in MY_CHANNELS)
            
            if is_available:
                tv_dict.setdefault(event_id, [])
                entry = f"{country}: {channel}"
                if entry not in tv_dict[event_id]:
                    tv_dict[event_id].append(entry)
                
    return tv_dict

# ============================================================
# TIME PARSING
# ============================================================
def parse_uk_time(event):
    fallback = datetime(2099, 12, 31, tzinfo=UK_TIMEZONE)
    date_val = event.get("dateEvent")
    time_val = event.get("strTime")
    
    if not date_val:
        return fallback
        
    try:
        time_str = str(time_val)[:8] if time_val else "00:00:00"
        if len(time_str) == 5:
            time_str += ":00"
            
        utc_dt = datetime.strptime(f"{date_val} {time_str}", "%Y-%m-%d %H:%M:%S")
        utc_dt = utc_dt.replace(tzinfo=timezone.utc)
        return utc_dt.astimezone(UK_TIMEZONE)
    except Exception:
        return fallback

# ============================================================
# UI VIEWS
# ============================================================

def build_home_page():
    now_uk = datetime.now(UK_TIMEZONE)
    today_str = date_string(now_uk.date())
    tomorrow_str = date_string((now_uk + timedelta(days=1)).date())
    
    text = (
        "⚽ <b>SPORT PULSE ALERTS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Welcome to your Premier League Fixtures & TV Guide.\n\n"
        f"🕒 <b>Current UK Time:</b> {now_uk.strftime('%H:%M - %A %d %b')}\n\n"
        "Select an option below to view kick-off times and broadcast channels."
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚽ Today's Matches", callback_data=f"date:{today_str}"),
            InlineKeyboardButton("📅 Tomorrow", callback_data=f"date:{tomorrow_str}")
        ],
        [
            InlineKeyboardButton("📺 Supported App Channels", callback_data="view_channels")
        ]
    ])
    
    return text, kb


def build_channels_page():
    channel_list = "\n".join(f"• {c.title()}" for c in MY_CHANNELS)
    text = (
        "📺 <b>SUPPORTED APP CHANNELS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "The bot automatically matches and displays feeds from the following broadcasters:\n\n"
        f"{channel_list}\n\n"
        "<i>Feeds outside this list are filtered out to keep listings clean.</i>"
    )
    
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu:home")]
    ])
    
    return text, kb


def build_pl_page(date_value):
    events = get_premier_league_events(date_value)
    tv_data = get_tv_channels(date_value)
    
    events.sort(key=parse_uk_time)
    
    text = (
        f"🏆 <b>PREMIER LEAGUE FIXTURES</b>\n"
        f"📅 <b>{pretty_date(date_value)}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    if not events:
        text += "❌ <i>No Premier League matches scheduled for this date.</i>\n\n"
    else:
        for idx, event in enumerate(events, 1):
            home = html.escape(event.get("strHomeTeam") or "Home")
            away = html.escape(event.get("strAwayTeam") or "Away")
            
            dt = parse_uk_time(event)
            time_str = dt.strftime("%H:%M") if dt.year != 2099 else "TBC"
            
            event_id = str(event.get("idEvent", ""))
            channels = tv_data.get(event_id, [])
            
            if not channels:
                tv_text = "📺 <i>No app channels listed yet</i>"
            else:
                tv_text = "📺 <b>Broadcasts:</b>\n" + "\n".join(f"   └ {html.escape(c)}" for c in channels[:6])
                if len(channels) > 6:
                    tv_text += f"\n   └ <i>+{len(channels)-6} more feeds</i>"
            
            text += (
                f"<b>{idx}. {home} vs {away}</b>\n"
                f"⏰ <b>Kick-off:</b> {time_str} UK\n"
                f"{tv_text}\n\n"
            )
            
    today_str = date_string(datetime.now(UK_TIMEZONE).date())
    prev_day_str = date_string(date_value - timedelta(days=1))
    next_day_str = date_string(date_value + timedelta(days=1))
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ Prev Day", callback_data=f"date:{prev_day_str}"),
            InlineKeyboardButton("📅 Today", callback_data=f"date:{today_str}"),
            InlineKeyboardButton("Next Day ➡️", callback_data=f"date:{next_day_str}")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"date:{date_string(date_value)}"),
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu:home")
        ]
    ])
    
    return text, kb

# ============================================================
# HANDLERS
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text, kb = build_home_page()
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    try:
        if data == "menu:home":
            text, kb = build_home_page()
            await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
            return

        if data == "view_channels":
            text, kb = build_channels_page()
            await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
            return

        if data.startswith("date:"):
            date_str = data.split(":")[1]
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            text, kb = build_pl_page(target_date)
            await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
            return

    except Exception as e:
        logger.error(f"UI Error: {e}")
        await query.edit_message_text(
            "❌ <b>Something went wrong.</b>",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu:home")]]),
            parse_mode="HTML"
        )

async def error_handler(update, context):
    logger.error("Telegram error:", exc_info=context.error)

# ============================================================
# MAIN
# ============================================================
def main():
    threading.Thread(target=start_health_server, daemon=True).start()
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_error_handler(error_handler)
    
    logger.info("Bot starting with updated navigation menus...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
    
