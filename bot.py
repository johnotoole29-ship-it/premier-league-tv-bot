import threading
import html

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

import bot_core

bot_core.ALLOWED_LOCATIONS = [
    {"chat_id": "3988874271", "topic_id": "10394"},
    {"chat_id": "2523097986", "topic_id": "12121"},
]


def build_compact_group_card(bot_username):
    text = (
        "🏟️ <b>SPORTS BOT</b>\n"
        "<b>FIXTURES • TV • LIVE SPORT</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "⚽ Premier League • Championship\n"
        "🌍 La Liga • Serie A • Bundesliga • Ligue 1\n"
        "🏉 Rugby • 🥊 Combat • ⛳ Golf • 🎯 Darts\n"
        "📺 TV listings • 🕒 UK times\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "🔒 <b>PRIVATE MATCH CENTRE</b>\n"
        "📩 Tap below for fixtures, TV & live scores."
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("⚡ OPEN MATCH CENTRE", url=f"https://t.me/{bot_username}?start=open")
    ]])
    return text, keyboard


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    if not chat or not message:
        return
    if chat.type in ["group", "supergroup"]:
        chat_id = str(chat.id)
        thread_id = str(message.message_thread_id) if message.message_thread_id else None
        allowed = any(chat_id.endswith(loc["chat_id"]) and thread_id == loc["topic_id"] for loc in bot_core.ALLOWED_LOCATIONS)
        if not allowed:
            return
        bot_info = await context.bot.get_me()
        text, keyboard = build_compact_group_card(bot_info.username)
        await message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")
        return
    await bot_core.start(update, context)


_original_build_home_page = bot_core.build_home_page


def build_home_page_with_live():
    text, keyboard = _original_build_home_page()
    home_rows = [row for row in keyboard.inline_keyboard if not any(button.callback_data == "menu:channels" for button in row)]
    rows = [
        [InlineKeyboardButton("🔴 LIVE NOW", callback_data="live:menu")],
        [InlineKeyboardButton("📊 LEAGUE TABLES", callback_data="table:menu")],
        *home_rows,
    ]
    return text, InlineKeyboardMarkup(rows)


bot_core.build_home_page = build_home_page_with_live

LIVE_LEAGUES = {"4328": "Premier League", "4329": "Championship", "4335": "La Liga", "4332": "Serie A", "4331": "Bundesliga", "4334": "Ligue 1"}
LEAGUE_ICONS = {"4328": "🏴", "4329": "🏴", "4335": "🇪🇸", "4332": "🇮🇹", "4331": "🇩🇪", "4334": "🇫🇷"}


def _extract_live_events(data):
    if isinstance(data, list): events = data
    elif isinstance(data, dict): events = data.get("events") or data.get("livescore") or data.get("livescores") or data.get("event") or []
    else: events = []
    return events if isinstance(events, list) else []


def fetch_live_sport(api_sport):
    url = f"https://www.thesportsdb.com/api/v2/json/livescore/{api_sport}"
    try:
        response = requests.get(url, headers={"X-API-KEY": bot_core.SPORTSDB_API_KEY}, timeout=20)
        response.raise_for_status()
        return _extract_live_events(response.json())
    except Exception as error:
        bot_core.logger.error("Live score request failed for %s: %s", api_sport, error)
        return None


def fetch_live_football_league(league_id):
    events = fetch_live_sport("soccer")
    if events is None: return None
    return [event for event in events if str(event.get("idLeague") or "") == str(league_id)]


def event_progress(event):
    status = str(event.get("strStatus") or "").strip().upper()
    progress = str(event.get("strProgress") or "").strip()
    if status == "HT": return "HALF-TIME"
    if status in ("FT", "AET", "AOT"): return "FULL-TIME" if status == "FT" else "AFTER EXTRA TIME"
    if status in ("PEN", "PENS"): return "PENALTIES"
    if status in ("PST", "POST"): return "POSTPONED"
    if status in ("CANC", "CAN"): return "CANCELLED"
    return progress or status or "LIVE"


def event_score_line(event):
    home, away = str(event.get("strHomeTeam") or "Home").strip(), str(event.get("strAwayTeam") or "Away").strip()
    hs, as_ = event.get("intHomeScore"), event.get("intAwayScore")
    progress = event_progress(event)
    if hs in (None, "") or as_ in (None, ""): return f"🔴 {html.escape(home)} vs {html.escape(away)} · {html.escape(progress)}"
    return f"🔴 <b>{html.escape(home)} {html.escape(str(hs))}–{html.escape(str(as_))} {html.escape(away)}</b> · {html.escape(progress)}"


def build_live_overview():
    events = fetch_live_sport("soccer")
    lines = ["🔴 <b>LIVE NOW</b>", "━━━━━━━━━━━━━━━━━━━━", "Live scores across all supported football leagues."]
    if events is None: lines.extend(["", "⚠️ Live scores are temporarily unavailable."])
    else:
        supported = [e for e in events if str(e.get("idLeague") or "") in LIVE_LEAGUES]
        if not supported: lines.extend(["", "No supported league matches are live right now."])
        else:
            for league_id, league_name in LIVE_LEAGUES.items():
                league_events = [e for e in supported if str(e.get("idLeague") or "") == league_id]
                if league_events:
                    lines.extend(["", f"{LEAGUE_ICONS.get(league_id, '⚽')} <b>{html.escape(league_name)}</b>"])
                    lines.extend(event_score_line(e) for e in league_events)
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏴 Premier League", callback_data="live:league:4328"), InlineKeyboardButton("🏴 Championship", callback_data="live:league:4329")],
        [InlineKeyboardButton("🇪🇸 La Liga", callback_data="live:league:4335"), InlineKeyboardButton("🇮🇹 Serie A", callback_data="live:league:4332")],
        [InlineKeyboardButton("🇩🇪 Bundesliga", callback_data="live:league:4331"), InlineKeyboardButton("🇫🇷 Ligue 1", callback_data="live:league:4334")],
        [InlineKeyboardButton("🔄 REFRESH ALL SCORES", callback_data="live:menu")], [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")],
    ])
    return "\n".join(lines), keyboard


def build_live_menu(): return build_live_overview()
def build_live_football_menu(): return build_live_overview()


def fetch_league_table(league_id):
    data = bot_core.sportsdb_get("lookuptable.php", {"l": str(league_id)})
    if data is None: return None
    if not isinstance(data, dict): return []
    table = data.get("table") or data.get("standings") or []
    return table if isinstance(table, list) else []


def _table_value(row, *keys, default="0"):
    for key in keys:
        if row.get(key) not in (None, ""): return str(row[key])
    return default


def build_tables_menu():
    text = "📊 <b>LEAGUE TABLES</b>\n━━━━━━━━━━━━━━━━━━━━\nChoose a competition to view the latest standings."
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏴 Premier League", callback_data="table:league:4328"), InlineKeyboardButton("🏴 Championship", callback_data="table:league:4329")],
        [InlineKeyboardButton("🇪🇸 La Liga", callback_data="table:league:4335"), InlineKeyboardButton("🇮🇹 Serie A", callback_data="table:league:4332")],
        [InlineKeyboardButton("🇩🇪 Bundesliga", callback_data="table:league:4331"), InlineKeyboardButton("🇫🇷 Ligue 1", callback_data="table:league:4334")],
        [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")],
    ])
    return text, keyboard


def build_league_table_page(league_id):
    league_id = str(league_id); league_name = LIVE_LEAGUES.get(league_id, "League"); icon = LEAGUE_ICONS.get(league_id, "⚽"); table = fetch_league_table(league_id)
    if table is None: text = f"{icon} <b>{html.escape(league_name.upper())} TABLE</b>\n━━━━━━━━━━━━━━━━━━━━\n⚠️ League table data is temporarily unavailable."
    elif not table: text = f"{icon} <b>{html.escape(league_name.upper())} TABLE</b>\n━━━━━━━━━━━━━━━━━━━━\nNo standings are currently available from the data provider."
    else:
        rows = []
        for index, row in enumerate(table, start=1):
            if isinstance(row, dict):
                pos = _table_value(row, "intRank", "intPosition", "rank", default=str(index)); team = _table_value(row, "strTeam", "name", "strName", default="Team"); played = _table_value(row, "intPlayed", "intGamesPlayed", "played"); gd = _table_value(row, "intGoalDifference", "intGoalDiff", "goalDifference"); pts = _table_value(row, "intPoints", "points")
                rows.append(f"{pos:>2} {team[:15]:<15} {played:>2} {gd:>4} {pts:>3}")
        table_text = "\n".join([" # Team             P   GD Pts", *rows])
        text = f"{icon} <b>{html.escape(league_name.upper())} TABLE</b>\n━━━━━━━━━━━━━━━━━━━━\n<pre>{html.escape(table_text)}</pre><i>P = Played • GD = Goal Difference • Pts = Points</i>"
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 REFRESH TABLE", callback_data=f"table:league:{league_id}")], [InlineKeyboardButton("⬅️ LEAGUE TABLES", callback_data="table:menu")], [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")]])
    return text, keyboard


def _v1_lookup(endpoint, event_id):
    try:
        data = bot_core.sportsdb_get(endpoint, {"id": str(event_id)})
        return data if isinstance(data, dict) else {}
    except Exception as error:
        bot_core.logger.warning("%s failed for event %s: %s", endpoint, event_id, error); return {}


def fetch_event_details(event_id):
    events = _v1_lookup("lookupevent.php", event_id).get("events") or []
    return events[0] if isinstance(events, list) and events and isinstance(events[0], dict) else {}


def fetch_event_timeline(event_id):
    timeline = _v1_lookup("lookuptimeline.php", event_id).get("timeline") or []
    return timeline if isinstance(timeline, list) else []


def fetch_event_tv(event_id):
    data = _v1_lookup("lookuptv.php", event_id); broadcasts = data.get("tvevents") or data.get("tv") or data.get("events") or []
    if not isinstance(broadcasts, list): return []
    output = []
    for item in broadcasts:
        if isinstance(item, dict):
            channel = str(item.get("strChannel") or item.get("strName") or "").strip(); country = str(item.get("strCountry") or item.get("strLocation") or "").strip()
            if channel:
                value = f"{country}: {channel}" if country else channel
                if value not in output: output.append(value)
    return output[:8]


def _timeline_minute(item): return str(item.get("intTime") or item.get("strTime") or item.get("intMinute") or item.get("strMinute") or item.get("time") or "").strip().replace("'", "")
def _timeline_player(item): return str(item.get("strPlayer") or item.get("strPlayerName") or item.get("strName") or item.get("player") or "").strip()
def _timeline_team(item): return str(item.get("strTeam") or item.get("strTeamName") or item.get("team") or "").strip()


def _timeline_type(item):
    # Use only dedicated event-type fields. Never classify from arbitrary values/player text.
    return str(item.get("strTimeline") or item.get("strType") or item.get("type") or item.get("strEventType") or "").strip().lower()


def _timeline_detail(item):
    return str(item.get("strTimelineDetail") or item.get("strDetail") or item.get("detail") or "").strip().lower()


def _is_goal(item):
    event_type = _timeline_type(item); detail = _timeline_detail(item)
    rejected = ("disallow", "cancel", "overturn", "ruled out", "offside", "no goal")
    if any(term in event_type or term in detail for term in rejected): return False
    return event_type in ("goal", "goals") or event_type.startswith("goal ") or detail in ("goal", "penalty goal", "own goal")


def _card_kind(item):
    event_type = _timeline_type(item); detail = _timeline_detail(item)
    value = f"{event_type} {detail}"
    if "red card" in value or event_type in ("red", "redcard"): return "🟥"
    if "yellow card" in value or event_type in ("yellow", "yellowcard"): return "🟨"
    return None


def _is_substitution(item):
    event_type = _timeline_type(item); detail = _timeline_detail(item)
    return event_type in ("substitution", "substitute", "sub") or event_type.startswith("substitution") or detail.startswith("substitution")


def fetch_confirmed_goals(event_id, max_goals=None):
    goals = []; seen = set()
    for item in fetch_event_timeline(event_id):
        if not isinstance(item, dict) or not _is_goal(item): continue
        player = _timeline_player(item) or "Unknown scorer"; minute = _timeline_minute(item); team = _timeline_team(item); key = (player.lower(), minute.lower(), team.lower())
        if key not in seen:
            seen.add(key); goals.append({"player": player, "minute": minute, "team": team})
    # Do not truncate timeline events by score; classification is authoritative.
    return goals


def fetch_cards_and_subs(event_id):
    cards = []; substitutions = []; seen_cards = set(); seen_subs = set()
    for item in fetch_event_timeline(event_id):
        if not isinstance(item, dict): continue
        minute = _timeline_minute(item); player = _timeline_player(item) or "Player"; team = _timeline_team(item)
        icon = _card_kind(item)
        if icon:
            key = (icon, player.lower(), minute.lower(), team.lower())
            if key not in seen_cards: seen_cards.add(key); cards.append({"icon": icon, "player": player, "minute": minute, "team": team})
        if _is_substitution(item):
            player_on = str(item.get("strPlayer2") or item.get("strPlayerIn") or item.get("strSubstitute") or item.get("player2") or "").strip(); player_off = str(item.get("strPlayer") or item.get("strPlayerOut") or item.get("player") or "").strip(); detail = str(item.get("strTimelineDetail") or item.get("strDetail") or "").strip()
            label = f"{player_off} → {player_on}" if player_on and player_off and player_on.lower() != player_off.lower() else (detail or player_off or player_on or "Substitution")
            key = (label.lower(), minute.lower(), team.lower())
            if key not in seen_subs: seen_subs.add(key); substitutions.append({"label": label, "minute": minute, "team": team})
    return cards[:12], substitutions[:12]


def event_button_text(event):
    home = str(event.get("strHomeTeam") or "Home"); away = str(event.get("strAwayTeam") or "Away"); hs, as_ = event.get("intHomeScore"), event.get("intAwayScore"); progress = event_progress(event)
    return (f"🔴 {home} vs {away} · {progress}" if hs in (None, "") or as_ in (None, "") else f"🔴 {home} {hs}-{as_} {away} · {progress}")[:60]


def build_live_league_page(league_id):
    league_name = LIVE_LEAGUES.get(str(league_id), "Football"); events = fetch_live_football_league(league_id); buttons = []
    if events is None: text = f"🔴 <b>{html.escape(league_name.upper())} LIVE</b>\n━━━━━━━━━━━━━━━━━━━━\nLive scores are temporarily unavailable."
    elif not events: text = f"🔴 <b>{html.escape(league_name.upper())} LIVE</b>\n━━━━━━━━━━━━━━━━━━━━\nNo matches are live in this league right now."
    else:
        text = f"🔴 <b>{html.escape(league_name.upper())} LIVE</b>\n━━━━━━━━━━━━━━━━━━━━\nTap a match to open its Match Centre."
        for event in events:
            event_id = str(event.get("idEvent") or "")
            if event_id: buttons.append([InlineKeyboardButton(event_button_text(event), callback_data=f"matchcentre:{event_id}:{league_id}")])
    buttons.extend([[InlineKeyboardButton("🔄 REFRESH", callback_data=f"live:league:{league_id}")], [InlineKeyboardButton("⬅️ ALL LIVE SCORES", callback_data="live:menu")], [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")]])
    return text, InlineKeyboardMarkup(buttons)


def find_live_event(event_id):
    events = fetch_live_sport("soccer")
    if not events: return None
    return next((event for event in events if str(event.get("idEvent") or "") == str(event_id)), None)


def _same_team(event_team, team_name):
    a, b = str(event_team or "").strip().lower(), str(team_name or "").strip().lower()
    return bool(a and b and (a == b or a in b or b in a))


def _goal_line(goal):
    player = html.escape(goal.get("player") or "Unknown scorer"); minute = html.escape(goal.get("minute") or "")
    return f"⚽ {minute}' {player}" if minute else f"⚽ {player}"


def _incident_line(item, label_key="player"):
    minute = html.escape(str(item.get("minute") or ""))
    if label_key == "label":
        label = html.escape(str(item.get("label") or "Substitution")); return f"🔄 {minute}' {label}" if minute else f"🔄 {label}"
    icon = item.get("icon") or "🟨"; player = html.escape(str(item.get("player") or "Player")); return f"{icon} {minute}' {player}" if minute else f"{icon} {player}"


def _finished(event):
    status = str(event.get("strStatus") or "").strip().upper()
    progress = event_progress(event).upper()
    return status in ("FT", "AET", "AOT", "PEN", "PENS") or progress in ("FULL-TIME", "AFTER EXTRA TIME")


def build_match_centre(event_id, league_id):
    live_event = find_live_event(event_id); details = fetch_event_details(event_id); event = live_event or details; league_name = LIVE_LEAGUES.get(str(league_id), str(details.get("strLeague") or "Football"))
    if not event: text = "🏟️ <b>MATCH CENTRE</b>\n━━━━━━━━━━━━━━━━━━━━\nThis match is no longer available."
    else:
        home_raw = str(event.get("strHomeTeam") or details.get("strHomeTeam") or "Home").strip(); away_raw = str(event.get("strAwayTeam") or details.get("strAwayTeam") or "Away").strip(); home = html.escape(home_raw); away = html.escape(away_raw)
        hs = event.get("intHomeScore") if event.get("intHomeScore") not in (None, "") else details.get("intHomeScore"); as_ = event.get("intAwayScore") if event.get("intAwayScore") not in (None, "") else details.get("intAwayScore")
        progress = html.escape(event_progress(event)); venue = str(details.get("strVenue") or event.get("strVenue") or "").strip()
        goals = fetch_confirmed_goals(event_id); cards, substitutions = fetch_cards_and_subs(event_id); tv_channels = fetch_event_tv(event_id)
        home_goals = [g for g in goals if _same_team(g.get("team"), home_raw)]; away_goals = [g for g in goals if _same_team(g.get("team"), away_raw)]; unassigned_goals = [g for g in goals if g not in home_goals and g not in away_goals]
        home_cards = [c for c in cards if _same_team(c.get("team"), home_raw)]; away_cards = [c for c in cards if _same_team(c.get("team"), away_raw)]; other_cards = [c for c in cards if c not in home_cards and c not in away_cards]
        home_subs = [s for s in substitutions if _same_team(s.get("team"), home_raw)]; away_subs = [s for s in substitutions if _same_team(s.get("team"), away_raw)]; other_subs = [s for s in substitutions if s not in home_subs and s not in away_subs]
        home_score = "–" if hs in (None, "") else html.escape(str(hs)); away_score = "–" if as_ in (None, "") else html.escape(str(as_))
        lines = ["🏟️ <b>MATCH CENTRE</b>", "━━━━━━━━━━━━━━━━━━━━", f"🏆 {html.escape(league_name)}", f"⏱ <b>{progress}</b>"]
        if venue: lines.append(f"📍 {html.escape(venue)}")
        lines.extend(["", f"🏠 <b>{home}</b>   <b>{home_score}</b>"])
        if home_goals: lines.extend(_goal_line(g) for g in home_goals)
        elif hs not in (None, "", 0, "0"): lines.append("⚽ Scorer details pending")
        lines.extend(_incident_line(c) for c in home_cards); lines.extend(_incident_line(s, "label") for s in home_subs)
        lines.extend(["", f"✈️ <b>{away}</b>   <b>{away_score}</b>"])
        if away_goals: lines.extend(_goal_line(g) for g in away_goals)
        elif as_ not in (None, "", 0, "0"): lines.append("⚽ Scorer details pending")
        lines.extend(_incident_line(c) for c in away_cards); lines.extend(_incident_line(s, "label") for s in away_subs)
        if unassigned_goals or other_cards or other_subs:
            lines.extend(["", "📋 <b>OTHER MATCH EVENTS</b>"]); lines.extend(_goal_line(g) for g in unassigned_goals); lines.extend(_incident_line(c) for c in other_cards); lines.extend(_incident_line(s, "label") for s in other_subs)
        lines.extend(["", "━━━━━━━━━━━━━━━━━━━━"])
        if tv_channels:
            lines.append("📺 <b>WHERE TO WATCH</b>"); lines.extend(f"• {html.escape(ch)}" for ch in tv_channels[:6])
        else: lines.append("📺 Broadcast information not currently listed.")
        lines.extend(["", "⚫ <b>FULL-TIME</b>" if _finished(event) else "🔴 <b>LIVE MATCH</b>"])
        text = "\n".join(lines)
        if len(text) > 3900: text = text[:3850] + "\n…more match events may be available."
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔄 REFRESH MATCH", callback_data=f"matchcentre:{event_id}:{league_id}")], [InlineKeyboardButton("⬅️ LIVE MATCHES", callback_data=f"live:league:{league_id}")], [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")]])
    return text, keyboard


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query: return
    data = query.data or ""
    if data.startswith("live:") or data.startswith("matchcentre:") or data.startswith("table:"):
        await query.answer()
        if data == "live:menu": text, keyboard = build_live_menu()
        elif data == "live:football": text, keyboard = build_live_football_menu()
        elif data.startswith("live:league:"): text, keyboard = build_live_league_page(data.split(":", 2)[2])
        elif data == "table:menu": text, keyboard = build_tables_menu()
        elif data.startswith("table:league:"): text, keyboard = build_league_table_page(data.split(":", 2)[2])
        elif data.startswith("matchcentre:"):
            _, event_id, league_id = data.split(":", 2); text, keyboard = build_match_centre(event_id, league_id)
        else: text, keyboard = build_live_menu()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML"); return
    await bot_core.button_handler(update, context)


async def preview_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat; message = update.effective_message
    if not chat or not message or chat.type != "private": return
    bot_info = await context.bot.get_me(); text, keyboard = build_compact_group_card(bot_info.username); await message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


def main():
    bot_core.logger.info("Starting Sports Bot..."); threading.Thread(target=bot_core.start_health_server, daemon=True).start(); application = Application.builder().token(bot_core.TELEGRAM_TOKEN).build(); application.add_handler(CommandHandler("start", start_handler)); application.add_handler(CommandHandler("previewgroup", preview_group)); application.add_handler(CallbackQueryHandler(callback_router)); application.add_error_handler(bot_core.error_handler); bot_core.logger.info("Sports Bot is online."); application.run_polling(drop_pending_updates=True)


if __name__ == "__main__": main()
