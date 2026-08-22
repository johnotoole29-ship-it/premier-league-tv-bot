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
    home_rows = [
        row for row in keyboard.inline_keyboard
        if not any(button.callback_data == "menu:channels" for button in row)
    ]
    rows = [
        [InlineKeyboardButton("🔴 LIVE NOW", callback_data="live:menu")],
        [InlineKeyboardButton("📊 LEAGUE TABLES", callback_data="table:menu")],
        *home_rows,
    ]
    return text, InlineKeyboardMarkup(rows)


bot_core.build_home_page = build_home_page_with_live

LIVE_LEAGUES = {
    "4328": "Premier League",
    "4329": "Championship",
    "4335": "La Liga",
    "4332": "Serie A",
    "4331": "Bundesliga",
    "4334": "Ligue 1",
}

LEAGUE_ICONS = {
    "4328": "🏴",
    "4329": "🏴",
    "4335": "🇪🇸",
    "4332": "🇮🇹",
    "4331": "🇩🇪",
    "4334": "🇫🇷",
}


def _extract_live_events(data):
    if isinstance(data, list):
        events = data
    elif isinstance(data, dict):
        events = data.get("events") or data.get("livescore") or data.get("livescores") or data.get("event") or []
    else:
        events = []
    return events if isinstance(events, list) else []


def fetch_live_sport(api_sport):
    url = f"https://www.thesportsdb.com/api/v2/json/livescore/{api_sport}"
    try:
        response = requests.get(url, headers={"X-API-KEY": bot_core.SPORTSDB_API_KEY}, timeout=20)
        response.raise_for_status()
        events = _extract_live_events(response.json())
    except Exception as error:
        bot_core.logger.error("Live score request failed for %s: %s", api_sport, error)
        return None
    return events


def fetch_live_football_league(league_id):
    events = fetch_live_sport("soccer")
    if events is None:
        return None
    return [event for event in events if str(event.get("idLeague") or "") == str(league_id)]


def event_title(event):
    home = str(event.get("strHomeTeam") or "").strip()
    away = str(event.get("strAwayTeam") or "").strip()
    return f"{home} vs {away}" if home and away else str(event.get("strEvent") or "Live Event").strip()


def event_progress(event):
    status = str(event.get("strStatus") or "").strip().upper()
    progress = str(event.get("strProgress") or "").strip()
    if status == "HT":
        return "HALF-TIME"
    if status in ("FT", "AET", "AOT"):
        return "FULL-TIME" if status == "FT" else "AFTER EXTRA TIME"
    if status in ("PEN", "PENS"):
        return "PENALTIES"
    if status in ("PST", "POST"):
        return "POSTPONED"
    if status in ("CANC", "CAN"):
        return "CANCELLED"
    return progress or status or "LIVE"


def event_score_line(event):
    home = str(event.get("strHomeTeam") or "Home").strip()
    away = str(event.get("strAwayTeam") or "Away").strip()
    hs = event.get("intHomeScore")
    as_ = event.get("intAwayScore")
    progress = event_progress(event)
    if hs in (None, "") or as_ in (None, ""):
        return f"🔴 {html.escape(home)} vs {html.escape(away)} · {html.escape(progress)}"
    return f"🔴 <b>{html.escape(home)} {html.escape(str(hs))}–{html.escape(str(as_))} {html.escape(away)}</b> · {html.escape(progress)}"


def build_live_overview():
    events = fetch_live_sport("soccer")
    lines = [
        "🔴 <b>LIVE NOW</b>",
        "━━━━━━━━━━━━━━━━━━━━",
        "Live scores across all supported football leagues.",
    ]
    if events is None:
        lines.extend(["", "⚠️ Live scores are temporarily unavailable."])
    else:
        supported = [event for event in events if str(event.get("idLeague") or "") in LIVE_LEAGUES]
        if not supported:
            lines.extend(["", "No supported league matches are live right now."])
        else:
            for league_id, league_name in LIVE_LEAGUES.items():
                league_events = [event for event in supported if str(event.get("idLeague") or "") == league_id]
                if not league_events:
                    continue
                icon = LEAGUE_ICONS.get(league_id, "⚽")
                lines.extend(["", f"{icon} <b>{html.escape(league_name)}</b>"])
                for event in league_events:
                    lines.append(event_score_line(event))
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏴 Premier League", callback_data="live:league:4328"), InlineKeyboardButton("🏴 Championship", callback_data="live:league:4329")],
        [InlineKeyboardButton("🇪🇸 La Liga", callback_data="live:league:4335"), InlineKeyboardButton("🇮🇹 Serie A", callback_data="live:league:4332")],
        [InlineKeyboardButton("🇩🇪 Bundesliga", callback_data="live:league:4331"), InlineKeyboardButton("🇫🇷 Ligue 1", callback_data="live:league:4334")],
        [InlineKeyboardButton("🔄 REFRESH ALL SCORES", callback_data="live:menu")],
        [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")],
    ])
    return "\n".join(lines), keyboard


def build_live_menu():
    return build_live_overview()


def build_live_football_menu():
    return build_live_overview()


def fetch_league_table(league_id):
    data = bot_core.sportsdb_get("lookuptable.php", {"l": str(league_id)})
    if data is None:
        return None
    if not isinstance(data, dict):
        return []
    table = data.get("table") or data.get("standings") or []
    return table if isinstance(table, list) else []


def _table_value(row, *keys, default="0"):
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return str(value)
    return default


def build_tables_menu():
    text = (
        "📊 <b>LEAGUE TABLES</b>\n"
        "━━━━━━━━━━━━━━━━━━━━\n"
        "Choose a competition to view the latest standings."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🏴 Premier League", callback_data="table:league:4328"), InlineKeyboardButton("🏴 Championship", callback_data="table:league:4329")],
        [InlineKeyboardButton("🇪🇸 La Liga", callback_data="table:league:4335"), InlineKeyboardButton("🇮🇹 Serie A", callback_data="table:league:4332")],
        [InlineKeyboardButton("🇩🇪 Bundesliga", callback_data="table:league:4331"), InlineKeyboardButton("🇫🇷 Ligue 1", callback_data="table:league:4334")],
        [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")],
    ])
    return text, keyboard


def build_league_table_page(league_id):
    league_id = str(league_id)
    league_name = LIVE_LEAGUES.get(league_id, "League")
    icon = LEAGUE_ICONS.get(league_id, "⚽")
    table = fetch_league_table(league_id)

    if table is None:
        text = f"{icon} <b>{html.escape(league_name.upper())} TABLE</b>\n━━━━━━━━━━━━━━━━━━━━\n⚠️ League table data is temporarily unavailable."
    elif not table:
        text = f"{icon} <b>{html.escape(league_name.upper())} TABLE</b>\n━━━━━━━━━━━━━━━━━━━━\nNo standings are currently available from the data provider."
    else:
        rows = []
        for index, row in enumerate(table, start=1):
            if not isinstance(row, dict):
                continue
            pos = _table_value(row, "intRank", "intPosition", "rank", default=str(index))
            team = _table_value(row, "strTeam", "name", "strName", default="Team")
            played = _table_value(row, "intPlayed", "intGamesPlayed", "played")
            gd = _table_value(row, "intGoalDifference", "intGoalDiff", "goalDifference", default="0")
            pts = _table_value(row, "intPoints", "points", default="0")
            rows.append(f"{pos:>2} {team[:15]:<15} {played:>2} {gd:>4} {pts:>3}")
        header = " # Team             P   GD Pts"
        table_text = "\n".join([header, *rows])
        text = (
            f"{icon} <b>{html.escape(league_name.upper())} TABLE</b>\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            f"<pre>{html.escape(table_text)}</pre>"
            "<i>P = Played • GD = Goal Difference • Pts = Points</i>"
        )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 REFRESH TABLE", callback_data=f"table:league:{league_id}")],
        [InlineKeyboardButton("⬅️ LEAGUE TABLES", callback_data="table:menu")],
        [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")],
    ])
    return text, keyboard


def _v1_lookup(endpoint, event_id):
    try:
        data = bot_core.sportsdb_get(endpoint, {"id": str(event_id)})
        return data if isinstance(data, dict) else {}
    except Exception as error:
        bot_core.logger.warning("%s failed for event %s: %s", endpoint, event_id, error)
        return {}


def fetch_event_details(event_id):
    data = _v1_lookup("lookupevent.php", event_id)
    events = data.get("events") or []
    return events[0] if isinstance(events, list) and events and isinstance(events[0], dict) else {}


def fetch_event_timeline(event_id):
    data = _v1_lookup("lookuptimeline.php", event_id)
    timeline = data.get("timeline") or []
    return timeline if isinstance(timeline, list) else []


def fetch_event_tv(event_id):
    data = _v1_lookup("lookuptv.php", event_id)
    broadcasts = data.get("tvevents") or data.get("tv") or data.get("events") or []
    if not isinstance(broadcasts, list):
        return []
    output = []
    for item in broadcasts:
        if not isinstance(item, dict):
            continue
        channel = str(item.get("strChannel") or item.get("strName") or "").strip()
        country = str(item.get("strCountry") or item.get("strLocation") or "").strip()
        if not channel:
            continue
        value = f"{country}: {channel}" if country else channel
        if value not in output:
            output.append(value)
    return output[:8]


def _timeline_text(item):
    return " ".join(str(value).lower() for value in item.values() if value is not None)


def _timeline_minute(item):
    return str(item.get("intTime") or item.get("strTime") or item.get("intMinute") or item.get("strMinute") or item.get("time") or "").strip().replace("'", "")


def _timeline_player(item):
    return str(item.get("strPlayer") or item.get("strPlayerName") or item.get("strName") or item.get("player") or "").strip()


def _timeline_team(item):
    return str(item.get("strTeam") or item.get("strTeamName") or item.get("team") or "").strip()


def fetch_confirmed_goals(event_id, max_goals=None):
    timeline = fetch_event_timeline(event_id)
    rejected_terms = (
        "disallowed", "disallow", "no goal", "not a goal", "goal cancelled",
        "goal canceled", "cancelled goal", "canceled goal", "overturned",
        "ruled out", "offside goal", "goal ruled out", "var disallowed",
    )
    goals = []
    seen = set()
    for item in timeline:
        if not isinstance(item, dict):
            continue
        event_type = str(item.get("strTimeline") or item.get("strType") or item.get("type") or item.get("strEvent") or "").lower()
        detail = str(item.get("strTimelineDetail") or item.get("strDetail") or item.get("detail") or "").lower()
        all_text = _timeline_text(item)
        if any(term in all_text for term in rejected_terms):
            continue
        if "goal" not in event_type and "goal" not in detail:
            continue
        if ("var" in event_type or "offside" in event_type) and "goal" not in detail:
            continue
        player = _timeline_player(item) or "Unknown scorer"
        minute = _timeline_minute(item)
        team = _timeline_team(item)
        key = (player.lower(), minute.lower(), team.lower())
        if key in seen:
            continue
        seen.add(key)
        goals.append({"player": player, "minute": minute, "team": team})
    if isinstance(max_goals, int) and max_goals >= 0:
        goals = goals[:max_goals]
    return goals


def fetch_cards_and_subs(event_id):
    cards = []
    substitutions = []
    seen_cards = set()
    seen_subs = set()

    for item in fetch_event_timeline(event_id):
        if not isinstance(item, dict):
            continue
        all_text = _timeline_text(item)
        minute = _timeline_minute(item)
        player = _timeline_player(item) or "Player"
        team = _timeline_team(item)

        if "yellow" in all_text or "red card" in all_text or "redcard" in all_text:
            icon = "🟥" if "red" in all_text and "yellow" not in all_text else "🟨"
            key = (icon, player.lower(), minute.lower(), team.lower())
            if key not in seen_cards:
                seen_cards.add(key)
                cards.append({"icon": icon, "player": player, "minute": minute, "team": team})

        if "substitution" in all_text or "substitute" in all_text or "subbed" in all_text:
            player_on = str(item.get("strPlayer2") or item.get("strPlayerIn") or item.get("strSubstitute") or item.get("player2") or "").strip()
            player_off = str(item.get("strPlayer") or item.get("strPlayerOut") or item.get("player") or "").strip()
            detail = str(item.get("strTimelineDetail") or item.get("strDetail") or "").strip()
            label = ""
            if player_on and player_off and player_on.lower() != player_off.lower():
                label = f"{player_off} → {player_on}"
            elif detail:
                label = detail
            else:
                label = player_off or player_on or "Substitution"
            key = (label.lower(), minute.lower(), team.lower())
            if key not in seen_subs:
                seen_subs.add(key)
                substitutions.append({"label": label, "minute": minute, "team": team})

    return cards[:12], substitutions[:12]


def event_button_text(event):
    home = str(event.get("strHomeTeam") or "Home")
    away = str(event.get("strAwayTeam") or "Away")
    hs, as_ = event.get("intHomeScore"), event.get("intAwayScore")
    progress = event_progress(event)
    text = f"🔴 {home} vs {away} · {progress}" if hs in (None, "") or as_ in (None, "") else f"🔴 {home} {hs}-{as_} {away} · {progress}"
    return text[:60]


def build_live_league_page(league_id):
    league_name = LIVE_LEAGUES.get(str(league_id), "Football")
    events = fetch_live_football_league(league_id)
    buttons = []
    if events is None:
        text = f"🔴 <b>{html.escape(league_name.upper())} LIVE</b>\n━━━━━━━━━━━━━━━━━━━━\nLive scores are temporarily unavailable."
    elif not events:
        text = f"🔴 <b>{html.escape(league_name.upper())} LIVE</b>\n━━━━━━━━━━━━━━━━━━━━\nNo matches are live in this league right now."
    else:
        text = f"🔴 <b>{html.escape(league_name.upper())} LIVE</b>\n━━━━━━━━━━━━━━━━━━━━\nTap a match to open its Match Centre."
        for event in events:
            event_id = str(event.get("idEvent") or "")
            if event_id:
                buttons.append([InlineKeyboardButton(event_button_text(event), callback_data=f"matchcentre:{event_id}:{league_id}")])
    buttons.extend([
        [InlineKeyboardButton("🔄 REFRESH", callback_data=f"live:league:{league_id}")],
        [InlineKeyboardButton("⬅️ ALL LIVE SCORES", callback_data="live:menu")],
        [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")],
    ])
    return text, InlineKeyboardMarkup(buttons)


def find_live_event(event_id):
    events = fetch_live_sport("soccer")
    if not events:
        return None
    return next((event for event in events if str(event.get("idEvent") or "") == str(event_id)), None)


def _same_team(goal_team, team_name):
    a = str(goal_team or "").strip().lower()
    b = str(team_name or "").strip().lower()
    if not a or not b:
        return False
    return a == b or a in b or b in a


def _goal_line(goal):
    player = html.escape(goal.get("player") or "Unknown scorer")
    minute = html.escape(goal.get("minute") or "")
    return f"⚽ {minute}' {player}" if minute else f"⚽ {player}"


def _incident_line(item, label_key="player"):
    minute = html.escape(str(item.get("minute") or ""))
    if label_key == "label":
        label = html.escape(str(item.get("label") or "Substitution"))
        return f"🔄 {minute}' {label}" if minute else f"🔄 {label}"
    icon = item.get("icon") or "🟨"
    player = html.escape(str(item.get("player") or "Player"))
    return f"{icon} {minute}' {player}" if minute else f"{icon} {player}"


def build_match_centre(event_id, league_id):
    live_event = find_live_event(event_id)
    details = fetch_event_details(event_id)
    event = live_event or details
    league_name = LIVE_LEAGUES.get(str(league_id), str(details.get("strLeague") or "Football"))

    if not event:
        text = "🏟️ <b>MATCH CENTRE</b>\n━━━━━━━━━━━━━━━━━━━━\nThis match is no longer available."
    else:
        home_raw = str(event.get("strHomeTeam") or details.get("strHomeTeam") or "Home").strip()
        away_raw = str(event.get("strAwayTeam") or details.get("strAwayTeam") or "Away").strip()
        home = html.escape(home_raw)
        away = html.escape(away_raw)

        hs = event.get("intHomeScore")
        as_ = event.get("intAwayScore")
        if hs in (None, ""):
            hs = details.get("intHomeScore")
        if as_ in (None, ""):
            as_ = details.get("intAwayScore")

        progress = html.escape(event_progress(event))
        venue = str(details.get("strVenue") or event.get("strVenue") or "").strip()

        max_goals = None
        try:
            if hs not in (None, "") and as_ not in (None, ""):
                max_goals = max(0, int(hs) + int(as_))
        except (TypeError, ValueError):
            max_goals = None

        goals = fetch_confirmed_goals(event_id, max_goals=max_goals)
        cards, substitutions = fetch_cards_and_subs(event_id)
        tv_channels = fetch_event_tv(event_id)

        home_goals = [g for g in goals if _same_team(g.get("team"), home_raw)]
        away_goals = [g for g in goals if _same_team(g.get("team"), away_raw)]
        unassigned_goals = [g for g in goals if g not in home_goals and g not in away_goals]

        home_cards = [c for c in cards if _same_team(c.get("team"), home_raw)]
        away_cards = [c for c in cards if _same_team(c.get("team"), away_raw)]
        other_cards = [c for c in cards if c not in home_cards and c not in away_cards]

        home_subs = [s for s in substitutions if _same_team(s.get("team"), home_raw)]
        away_subs = [s for s in substitutions if _same_team(s.get("team"), away_raw)]
        other_subs = [s for s in substitutions if s not in home_subs and s not in away_subs]

        home_score = "–" if hs in (None, "") else html.escape(str(hs))
        away_score = "–" if as_ in (None, "") else html.escape(str(as_))

        lines = [
            "🏟️ <b>MATCH CENTRE</b>",
            "━━━━━━━━━━━━━━━━━━━━",
            f"🏆 {html.escape(league_name)}",
            f"⏱ <b>{progress}</b>",
        ]
        if venue:
            lines.append(f"📍 {html.escape(venue)}")

        lines.extend(["", f"🏠 <b>{home}</b>   <b>{home_score}</b>"])
        if home_goals:
            lines.extend(_goal_line(goal) for goal in home_goals)
        elif hs not in (None, "", 0, "0"):
            lines.append("⚽ Scorer details pending")
        for card in home_cards:
            lines.append(_incident_line(card))
        for sub in home_subs:
            lines.append(_incident_line(sub, "label"))

        lines.extend(["", f"✈️ <b>{away}</b>   <b>{away_score}</b>"])
        if away_goals:
            lines.extend(_goal_line(goal) for goal in away_goals)
        elif as_ not in (None, "", 0, "0"):
            lines.append("⚽ Scorer details pending")
        for card in away_cards:
            lines.append(_incident_line(card))
        for sub in away_subs:
            lines.append(_incident_line(sub, "label"))

        if unassigned_goals or other_cards or other_subs:
            lines.extend(["", "📋 <b>OTHER MATCH EVENTS</b>"])
            lines.extend(_goal_line(goal) for goal in unassigned_goals)
            lines.extend(_incident_line(card) for card in other_cards)
            lines.extend(_incident_line(sub, "label") for sub in other_subs)

        lines.extend(["", "━━━━━━━━━━━━━━━━━━━━"])
        if tv_channels:
            lines.append("📺 <b>WHERE TO WATCH</b>")
            for channel in tv_channels[:6]:
                lines.append(f"• {html.escape(channel)}")
        else:
            lines.append("📺 Broadcast information not currently listed.")

        lines.extend(["", "🔴 <b>LIVE MATCH</b>"])
        text = "\n".join(lines)

        if len(text) > 3900:
            text = text[:3850] + "\n…more match events may be available."

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 REFRESH MATCH", callback_data=f"matchcentre:{event_id}:{league_id}")],
        [InlineKeyboardButton("⬅️ LIVE MATCHES", callback_data=f"live:league:{league_id}")],
        [InlineKeyboardButton("🏠 MAIN MENU", callback_data="menu:home")],
    ])
    return text, keyboard


async def callback_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    data = query.data or ""
    if data.startswith("live:") or data.startswith("matchcentre:") or data.startswith("table:"):
        await query.answer()
        if data == "live:menu":
            text, keyboard = build_live_menu()
        elif data == "live:football":
            text, keyboard = build_live_football_menu()
        elif data.startswith("live:league:"):
            league_id = data.split(":", 2)[2]
            text, keyboard = build_live_league_page(league_id)
        elif data == "table:menu":
            text, keyboard = build_tables_menu()
        elif data.startswith("table:league:"):
            league_id = data.split(":", 2)[2]
            text, keyboard = build_league_table_page(league_id)
        elif data.startswith("matchcentre:"):
            _, event_id, league_id = data.split(":", 2)
            text, keyboard = build_match_centre(event_id, league_id)
        else:
            text, keyboard = build_live_menu()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="HTML")
        return
    await bot_core.button_handler(update, context)


async def preview_group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.effective_message
    if not chat or not message or chat.type != "private":
        return
    bot_info = await context.bot.get_me()
    text, keyboard = build_compact_group_card(bot_info.username)
    await message.reply_text(text, reply_markup=keyboard, parse_mode="HTML")


def main():
    bot_core.logger.info("Starting Sports Bot...")
    health_thread = threading.Thread(target=bot_core.start_health_server, daemon=True)
    health_thread.start()
    application = Application.builder().token(bot_core.TELEGRAM_TOKEN).build()
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("previewgroup", preview_group))
    application.add_handler(CallbackQueryHandler(callback_router))
    application.add_error_handler(bot_core.error_handler)
    bot_core.logger.info("Sports Bot is online.")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
