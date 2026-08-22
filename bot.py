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
# MY APP CHANNELS & SPORT CATEGORIES
# ============================================================
MY_CHANNELS = [
    "sky sports",       # UK
    "tnt sports",       # UK
    "amazon prime",     # UK
    "stan sport",       # Australia
    "fubo",             # Canada
    "espn",             # Caribbean/USA
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

CATEGORIES = {
    "football": {"icon": "⚽", "title": "Premier League", "sport": "Soccer"},
    "nrl": {"icon": "🦘", "title": "NRL", "sport": "Rugby"},
    "superleague": {"icon": "🇬🇧", "title": "Super League", "sport": "Rugby"},
    "union": {"icon": "🏉", "title": "Rugby Union", "sport": "Rugby"},
    "ufc": {"icon": "🥋", "title": "UFC", "sport": "Fighting"},
    "boxing": {"icon": "🥊", "title": "Boxing", "sport": "Fighting"},
    "wwe": {"icon": "🤼", "title": "WWE", "sport": "Fighting"},
}

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

def fetch_events(date_value, category):
    meta = CATEGORIES.get(category)
    data = sportsdb_get("eventsday.php", {"d": date_string(date_value), "s": meta["sport"]})
    
    if not data or not isinstance(data.get("events"), list):
        return []
        
    filtered = []
    for e in data["events"]:
        lid = str(e.get("idLeague", ""))
        lname = str(e.get("strLeague") or "").lower()
        
        if category == "football":
            if lid == "4328": # Strict Premier League filter
                filtered.append(e)
                
        elif category == "nrl":
            if lid == "4416" or "nrl" in lname or "national rugby league" in lname:
                filtered.append(e)
                
        elif category == "superleague":
            if lid == "4415" or "super league" in lname:
                filtered.append(e)
                
        elif category == "union":
            # Exclude NRL and Super League IDs to ensure it is purely Union or international Rugby
            if lid not in ["4415", "4416"] and "nrl" not in lname and "super league" not in lname:
                filtered.append(e)
                
        elif category == "ufc":
            if lid == "4443" or "ufc" in lname:
                filtered.append(e)
                
        elif category == "boxing":
            if lid == "4445" or "boxing" in lname:
                filtered.append(e)
                
        elif category == "wwe":
            if lid == "4444" or "wwe" in lname:
                filtered.append(e)
                
    return filtered[:15]

def get_tv_channels(date_value, sport):
    data = sportsdb_get("eventstv.php", {"d": date_string(date_value), "s": sport})
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
    
    text = (
        "🔥 <b>SPORT PULSE ALERTS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Welcome to your centralized sports hub.\n\n"
        f"🕒 <b>Current UK Time:</b> {now_uk.strftime('%H:%M - %A %d %b')}\n\n"
        "Select a sport below to view fixtures and broadcast channels."
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚽ Premier League", callback_data=f"date:{today_str}:football")
        ],
        [
            InlineKeyboardButton("🏉 Rugby", callback_data="menu:rugby"),
            InlineKeyboardButton("🥊 Combat Sports", callback_data="menu:combat")
        ],
        [
            InlineKeyboardButton("📺 Supported App Channels", callback_data="menu:channels")
        ]
    ])
    
    return text, kb

def build_rugby_menu():
    today_str = date_string(datetime.now(UK_TIMEZONE).date())
    text = (
        "🏉 <b>RUGBY FIXTURES</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Select a league or code below to view matches:"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🦘 NRL", callback_data=f"date:{today_str}:nrl"),
            InlineKeyboardButton("🇬🇧 Super League", callback_data=f"date:{today_str}:superleague")
        ],
        [
            InlineKeyboardButton("🏉 Rugby Union", callback_data=f"date:{today_str}:union")
        ],
        [
            InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu:home")
        ]
    ])
    
    return text, kb

def build_combat_menu():
    today_str = date_string(datetime.now(UK_TIMEZONE).date())
    text = (
        "🥊 <b>COMBAT SPORTS</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Select an organization below to view events:"
    )
    
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🥋 UFC", callback_data=f"date:{today_str}:ufc"),
            InlineKeyboardButton("🥊 Boxing", callback_data=f"date:{today_str}:boxing")
        ],
        [
            InlineKeyboardButton("🤼 WWE", callback_data=f"date:{today_str}:wwe")
        ],
        [
            InlineKeyboardButton("⬅️ Back to Main Menu", callback_data="menu:home")
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

def build_fixtures_page(date_value, category):
    meta = CATEGORIES.get(category)
    if not meta:
        return "❌ <b>Error:</b> Unknown category.", InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="menu:home")]])
        
    events = fetch_events(date_value, category)
    tv_data = get_tv_channels(date_value, meta["sport"])
    
    events.sort(key=parse_uk_time)
    
    text = (
        f"{meta['icon']} <b>{meta['title'].upper()} FIXTURES</b>\n"
        f"📅 <b>{pretty_date(date_value)}</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
    )
    
    if not events:
        text += f"❌ <i>No {meta['title']} events scheduled for this date.</i>\n\n"
    else:
        for idx, event in enumerate(events, 1):
            home = html.escape(str(event.get("strHomeTeam") or ""))
            away = html.escape(str(event.get("strAwayTeam") or ""))
            
            # Combat sports fallback to event name
            if not home or not away or home == "None" or away == "None":
                match_title = html.escape(str(event.get("strEvent") or "TBA Match"))
            else:
                match_title = f"{home} vs {away}"
                
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
                f"<b>{idx}. {match_title}</b>\n"
                f"⏰ <b>Kick-off:</b> {time_str} UK\n"
                f"{tv_text}\n\n"
            )
            
    today_str = date_string(datetime.now(UK_TIMEZONE).date())
    prev_day_str = date_string(date_value - timedelta(days=1))
    next_day_str = date_string(date_value + timedelta(days=1))
    
    back_target = "menu:home"
    if category in ["nrl", "superleague", "union"]:
        back_target = "menu:rugby"
    elif category in ["ufc", "boxing", "wwe"]:
        back_target = "menu:combat"
        
    kb = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ Prev Day", callback_data=f"date:{prev_day_str}:{category}"),
            InlineKeyboardButton("📅 Today", callback_data=f"date:{today_str}:{category}"),
            InlineKeyboardButton("Next Day ➡️", callback_data=f"date:{next_day_str}:{category}")
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"date:{date_string(date_value)}:{category}"),
            InlineKeyboardButton("⬅️ Back", callback_data=back_target)
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
            
        if data == "menu:rugby":
            text, kb = build_rugby_menu()
            await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
            return
            
        if data == "menu:combat":
            text, kb = build_combat_menu()
            await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
            return

        if data == "view_channels" or data == "menu:channels":
            text, kb = build_channels_page()
            await query.edit_message_text(text, reply_markup=kb, parse_mode="HTML")
            return

        if data.startswith("date:"):
            parts = data.split(":")
            date_str = parts[1]
            category = parts[2]
            
            target_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            text, kb = build_fixtures_page(target_date, category)
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
    
    logger.info("Bot starting with expanded subfolders...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
    
