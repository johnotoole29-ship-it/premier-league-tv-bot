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
# Edit this list to match the channels your app provides.
# Keep everything lowercase. Partial names (like "sky sports") 
# will automatically match "Sky Sports Main Event", etc.
MY_CHANNELS = [
    "sky sports",
    "tnt sports",
    "amazon prime",
    "usa network",
    "peacock",
    "optus sport",
    "fubo",
    "nbc",
    "supermport",
    "bein sports",
    "astro supersport"
    "Sanata Events"
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
        # STRICT FILTER: 4328 is the ONLY ID for the English Premier League.
        if str(e.get("idLeague")) == "4328":
            pl_events.append(e)
            
    # Hard limit to 15 matches to guarantee it never breaches Telegram's character limit
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
        country = (b.get("strCountry") or b.get("strLocation") or "Intl").strip()
        
        if event_id and channel:
            channel_lower = channel.lower()
            
            # --- CUSTOM CHANNEL FILTER ---
            # Only keep the channel if a match is found in your MY_CHANNELS list
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
    # Safe fallback date in the future to avoid sorting crash
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
# UI FORMATTING
# ============================================================
def build_pl_page(date_value):
    events = get_premier_league_events(date_value)
    tv_data = get_tv_channels(date_value)
    
    # Sort safely by UK time
    events.sort(key=parse_uk_time)
    
    text = f"🏆 <b>Premier League Fixtures</b>\n📅 <b>{pretty_date(date_value)}</b>\n\n"
    
    if not events:
        text += "❌ <i>No Premier League matches on this date.</i>"
    else:
        for idx, event in enumerate(events, 1):
            home = html.escape(event.get("strHomeTeam") or "Home")
            away = html.escape(event.get("strAwayTeam") or "Away")
            
            # Extract formatted time
            dt = parse_uk_time(event)
            time_str = dt.strftime("%H:%M") if dt.year != 2099 else "TBC"
            
            # Build TV text (capping at 6 channels to save space)
            event_id = str(event.get("idEvent", ""))
            channels = tv_data.get(event_id, [])
            
            if not channels:
                tv_text = "📺 <b>TV:</b> No supported channels"
            else:
                tv_text = "📺 <b>TV:</b>\n" + "\n".join(f"• {html.escape(c)}" for c in channels[:6])
                if len(channels) > 6:
                    tv_text += f"\n• <i>+{len(channels)-6} more</i>"
            
            text += f"{idx}. 🕒 <b>{time_str} UK</b>\n⚽ <b>{home} vs {away}</b>\n{tv_text}\n\n"
            
    # Simple, direct navigation
    today_str = date_string(datetime.now(UK_TIMEZONE).date())
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ Prev Day", callback_data=f"date:{date_string(date_value - timedelta(days=1))}"),
            InlineKeyboardButton("Today", callback_data=f"date:{today_str}"),
            InlineKeyboardButton("Next Day ➡️", callback_data=f"date:{date_string(date_value + timedelta(days=1))}")
        ]
    ])
    
    return text, kb

# ============================================================
# HANDLERS
# ============================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    today = datetime.now(UK_TIMEZONE).date()
    text, kb = build_pl_page(today)
    await update.message.reply_text(text, reply_markup=kb, parse_mode="HTML")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith("date:"):
        date_str = query.data.split(":")[1]
        try:
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            text, kb = build_pl_page(target_date)
            await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.error(f"UI Error: {e}")
            await query.edit_message_text("❌ <b>Error loading date.</b>", parse_mode="HTML")

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
    
    logger.info("Bot starting...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
