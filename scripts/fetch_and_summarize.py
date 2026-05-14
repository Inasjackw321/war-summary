#!/usr/bin/env python3
import os
import json
import time
import re
import sys
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

MODELS = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "openai/gpt-oss-120b:free",
]

CONFLICTS = {
    "middle_east": {
        "title": "Middle-East War",
        "alert_channel": "tzevaadom_en",
        "channels": [
            "N12chat", "manniefabian", "asafroz", "yediotnews25",
            "SharghDaily", "amitsegal", "presstv", "mamlekate",
            "kianmeli1", "Faytuks_Network", "rodast_omiddana",
            "naya_foriraq", "tzevaadom_en", "VahidOnline", "idf_telegram"
        ],
        "section_keys": [
            "executive_summary", "iran", "israel", "gaza_west_bank",
            "lebanon", "syria_iraq", "gulf_states",
            "key_developments", "threat_assessment", "regional_response", "intelligence_notes"
        ],
    },
    "ukraine": {
        "title": "Ukraine-Russia War",
        "alert_channel": "eRadarrua",
        "channels": [
            "eRadarrua", "kpszsu", "mon1tor_ua", "Faytuks_Network",
            "UkraineNow", "front_ukrainian", "DeepStateUA", "WarMonitor",
            "ukr_leaks_eng", "RationalistUA", "ukrainewar_report",
            "ukraine_news_24", "UAonlymilitary"
        ],
        "section_keys": [
            "executive_summary", "ukraine", "russia", "eastern_front",
            "northern_front", "southern_front", "air_war",
            "key_developments", "threat_assessment", "regional_response", "intelligence_notes"
        ],
    },
}

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

_PROMO_PATTERNS = re.compile(
    r"(subscribe\s+to\s+(our|this|the)\s+channel"
    r"|join\s+(our|the)\s+(channel|group|chat)"
    r"|follow\s+us\s+on"
    r"|send\s+to\s+friends"
    r"|share\s+this\s+channel"
    r"|advertisement"
    r"|sponsored\s+post"
    r"|^t\.me/"
    r"|\bbot\b.*\bcommand\b)",
    re.IGNORECASE,
)

# Patterns that indicate a genuine Red Alert activation (Middle East)
_REAL_ALERT_RE = re.compile(
    r"(hostile\s+aircraft|tzofar|red\s+alert|צבע\s*אדום|"
    r"confrontation\s+line|rocket\s+alert|missile\s+alert|\U0001f6a8|"
    r"air[\s-]raid\s+(?:warning|alert)|intrusion)",
    re.IGNORECASE,
)


def is_relevant(text: str) -> bool:
    cleaned = text.strip()
    if len(cleaned) < 45:
        return False
    alpha = sum(c.isalpha() for c in cleaned)
    if alpha / max(len(cleaned), 1) < 0.28:
        return False
    if _PROMO_PATTERNS.search(cleaned):
        return False
    if re.match(r"^https?://\S+$", cleaned) or re.match(r"^@\w+$", cleaned):
        return False
    return True


def is_real_alert(text: str) -> bool:
    """Return True only if the post is an actual Red Alert activation (not a map or analysis)."""
    return bool(_REAL_ALERT_RE.search(text))


def fetch_channel_messages_24h(channel: str) -> tuple[list[str], list[datetime], int | None]:
    """
    Scrape messages from the last 24 hours of a public Telegram channel.
    Returns (texts, timestamps, max_message_id) where max_message_id is the
    highest post ID seen (used to build a direct link to the most recent post).
    """
    base_url = f"https://t.me/s/{channel}"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    seen: set[str] = set()
    all_texts: list[str] = []
    all_times: list[datetime] = []
    before_id: int | None = None
    max_id: int | None = None

    for page_num in range(12):
        url = base_url if before_id is None else f"{base_url}?before={before_id}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=18)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [warn] {channel} page {page_num}: {e}", file=sys.stderr)
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        msg_els = soup.select(".tgme_widget_message")
        if not msg_els:
            break

        oldest_id_on_page: int | None = None
        any_within_24h = False

        for msg in msg_els:
            data_post = msg.get("data-post", "")
            if "/" in data_post:
                try:
                    mid = int(data_post.split("/")[-1])
                    if oldest_id_on_page is None or mid < oldest_id_on_page:
                        oldest_id_on_page = mid
                    if max_id is None or mid > max_id:
                        max_id = mid
                except ValueError:
                    pass

            msg_time: datetime | None = None
            time_el = msg.select_one("time[datetime]")
            if time_el:
                try:
                    dt_str = time_el["datetime"].replace("Z", "+00:00")
                    msg_time = datetime.fromisoformat(dt_str)
                    if msg_time < cutoff:
                        continue
                    any_within_24h = True
                except Exception:
                    pass
            else:
                if page_num > 0:
                    continue

            txt_el = msg.select_one(".tgme_widget_message_text")
            if not txt_el:
                continue
            txt = txt_el.get_text(separator=" ", strip=True)

            if txt and txt not in seen and is_relevant(txt):
                seen.add(txt)
                all_texts.append(txt)
                all_times.append(msg_time)

        if not any_within_24h and page_num > 0:
            break
        if oldest_id_on_page is None or oldest_id_on_page == before_id:
            break

        before_id = oldest_id_on_page
        time.sleep(0.9)

    return all_texts, all_times, max_id


def bucket_into_24h_slots(timestamps: list[datetime | None]) -> list[int]:
    """Convert real UTC timestamps into a 24-element hourly array. Index 0 = oldest, 23 = current."""
    now = datetime.now(timezone.utc)
    counts = [0] * 24
    for ts in timestamps:
        if ts is None:
            continue
        hours_ago = int((now - ts).total_seconds() // 3600)
        if 0 <= hours_ago < 24:
            counts[23 - hours_ago] += 1
    return counts


def build_activity_timeline_synthetic(total_messages: int) -> list[int]:
    weights = [3, 2, 1, 1, 1, 2, 4, 6, 8, 10, 10, 9, 9, 8, 8, 8, 7, 7, 6, 5, 5, 4, 4, 3]
    total_w = sum(weights)
    return [round(total_messages * w / total_w) for w in weights]


def parse_kpszsu_attack_summary(texts: list[str], timestamps: list[datetime | None]) -> dict:
    """
    Scan kpszsu messages for the daily attack summary infographic post.
    Parses the total missiles + drones launched (not just shot down).
    """
    for text, ts in zip(texts, timestamps):
        # Ukrainian: "731 засіб повітряного нападу"
        m = re.search(r'(\d{2,4})\s+засіб(?:ів)?\s+повітряного\s+нападу', text, re.IGNORECASE)
        if m:
            total = int(m.group(1))
            m_drones = re.search(r'(\d+)\s+(?:ворожих?\s+)?[Бб][Пп][Лл][Аа]', text)
            drones = int(m_drones.group(1)) if m_drones else 0
            return {"total": total, "missiles": total - drones, "drones": drones, "ts": ts}
        # English summary: "41 MISSILES AND 652 ENEMY UAVS SHOTDOWN/SUPPRESSED"
        m2 = re.search(r'(\d+)\s+MISSILES?\s+AND\s+(\d+)\s+(?:ENEMY\s+)?UAV', text, re.IGNORECASE)
        if m2:
            missiles, drones = int(m2.group(1)), int(m2.group(2))
            return {"total": missiles + drones, "missiles": missiles, "drones": drones, "ts": ts}
    return {"total": 0, "missiles": 0, "drones": 0, "ts": None}


def update_ukraine_history(output_dir: Path, attack_data: dict) -> None:
    """Append today's kpszsu attack summary to the running history file."""
    path = output_dir / "ukraine_history.json"
    try:
        hist = json.loads(path.read_text()) if path.exists() else {"entries": []}
    except Exception:
        hist = {"entries": []}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hist["entries"] = [e for e in hist["entries"] if e["date"] != today]
    if attack_data["total"] > 0:
        hist["entries"].append({
            "date": today,
            "total": attack_data["total"],
            "missiles": attack_data["missiles"],
            "drones": attack_data["drones"],
        })
    hist["entries"].sort(key=lambda e: e["date"])
    path.write_text(json.dumps(hist, indent=2, ensure_ascii=False))


def call_openrouter(prompt: str, model: str) -> str:
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "HTTP-Referer": "https://inasjackw321.github.io/war-summary",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 6000,
    }
    resp = requests.post(url, json=body, headers=headers, timeout=120)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def generate_summary(conflict_name: str, section_keys: list[str], raw_messages: list[str]) -> dict:
    if not raw_messages:
        return {
            "summary": "No recent updates available.",
            "key_points": [],
            "sentiment": "neutral",
            "intensity": 3,
            "sections": {},
        }

    combined = "\n\n---\n\n".join(raw_messages)
    is_ukraine = "Ukraine" in conflict_name or "Russia" in conflict_name

    if is_ukraine:
        sections_spec = """{
  "executive_summary": "4-5 sentence strategic overview covering the most significant developments of the past 24 hours, overall operational tempo, and front-line trajectory",
  "ukraine": {
    "title": "Ukraine",
    "subtitle": "Ukrainian defensive operations and strikes",
    "points": [
      "5-6 detailed bullets: each 2-3 sentences with specific unit names, locations, weapon systems, intercept/strike figures"
    ]
  },
  "russia": {
    "title": "Russia",
    "subtitle": "Russian military operations and strategic posture",
    "points": ["5-6 detailed bullets with specifics on weapons, tactics, claimed results, mobilization data"]
  },
  "eastern_front": {
    "title": "Eastern Front",
    "subtitle": "Donetsk & Luhansk combat operations",
    "points": ["5-6 detailed bullets with village names, assault wave counts, vehicle losses, ISW assessments where available"]
  },
  "northern_front": {
    "title": "Northern Front",
    "subtitle": "Kharkiv region and Sumy border activity",
    "points": ["4-5 detailed bullets"]
  },
  "southern_front": {
    "title": "Southern Front",
    "subtitle": "Zaporizhzhia & Kherson operations",
    "points": ["4-5 detailed bullets"]
  },
  "air_war": {
    "title": "Air War",
    "subtitle": "Drone, missile and aviation operations",
    "points": ["5-6 detailed bullets covering drone counts, intercept rates, SAM activations, aircraft claimed, EW incidents"]
  },
  "key_developments": ["7 concise one-line summaries of the most significant events, ordered by importance"],
  "threat_assessment": "5-6 sentence deep assessment: operational momentum, attrition balance, critical terrain, probability of major breakthrough (label LOW/MODERATE/HIGH/CRITICAL), and key indicators to watch",
  "regional_response": "4-5 sentences: specific aid packages approved, weapons delivered or announced, diplomatic positions, NATO/EU decisions, bilateral agreements",
  "intelligence_notes": "4-5 sentences: order-of-battle observations, logistics patterns, electronic warfare activity, satellite imagery findings, strategic reserve movements, deception indicators"
}"""
    else:
        sections_spec = """{
  "executive_summary": "4-5 sentence strategic overview covering the most significant developments of the past 24 hours, overall escalation trajectory, and key actors involved",
  "iran": {
    "title": "Iran",
    "subtitle": "Military operations in and against Iran",
    "points": [
      "First bullet: 2-3 sentences with specific details (unit names, locations, weapon types, casualty figures if known)",
      "Second bullet: same level of detail",
      "Third bullet: same",
      "Fourth bullet: same",
      "Fifth bullet: same — include at least 5 substantive points if the source material supports it"
    ]
  },
  "israel": {
    "title": "Israel",
    "subtitle": "IDF operations and Israeli security assessments",
    "points": ["5 detailed bullets as above"]
  },
  "gaza_west_bank": {
    "title": "Gaza & West Bank",
    "subtitle": "Ongoing operations in Palestinian territories",
    "points": ["5 detailed bullets"]
  },
  "lebanon": {
    "title": "Lebanon",
    "subtitle": "Hezbollah activity and northern border exchanges",
    "points": ["4-5 detailed bullets"]
  },
  "syria_iraq": {
    "title": "Syria & Iraq",
    "subtitle": "Regional proxy activity and cross-border operations",
    "points": ["4-5 detailed bullets"]
  },
  "gulf_states": {
    "title": "Gulf States",
    "subtitle": "Regional state reactions and security incidents",
    "points": ["4-5 detailed bullets"]
  },
  "key_developments": ["7 concise one-line summaries of the most significant events, ordered by importance"],
  "threat_assessment": "5-6 sentence deep assessment: current threat level, primary/secondary risks, operational indicators, probability of escalation (label it LOW/MODERATE/HIGH/CRITICAL), and key variables to watch",
  "regional_response": "4-5 sentences covering US, NATO, EU, Russia, China, and regional state positions; include specific policy decisions, diplomatic meetings, or military movements announced",
  "intelligence_notes": "4-5 sentences of analytical intelligence observations: SIGINT patterns, imagery analysis, logistics movements, capability assessments, deception indicators, or strategic intentions inferred from open-source signals"
}"""

    prompt = f"""You are a senior military intelligence analyst producing a classified-style open-source intelligence brief for {conflict_name}.

Analyze the following Telegram messages from conflict-monitoring channels (collected over the past 24 hours). Each message is prefixed with [channel_name] indicating its source.

SOURCE MESSAGES:
{combined}

INSTRUCTIONS:
- Write each bullet point as 2-3 full sentences. Lead with the most specific fact (unit, location, number, weapon system), then provide context and significance.
- Do NOT use vague language. Use exact place names, unit designations, weapon types, and figures wherever the sources support it.
- At the end of each bullet point, cite the source channel(s) that reported the information in the format: (Source: @channel_name) — e.g. (Source: @DeepStateUA) or (Source: @eRadarrua, @UkraineNow). Only cite channels that actually provided that specific information.
- Where multiple sources corroborate a fact, cite all of them. Where only one source reports something, note it is unconfirmed.
- key_developments should be 7 concise actionable headlines ordered by operational significance, each ending with (Source: @channel).
- threat_assessment, regional_response, and intelligence_notes should be analytical prose paragraphs (not bullet points), 4-6 sentences each.
- intensity: 1–10 (1 = minimal, 10 = all-out war with nuclear signaling)
- sentiment: one of escalating | de-escalating | stable | volatile

Respond with ONLY valid JSON (no markdown, no code fences) in this exact format:
{{
  "summary": "4-5 sentence executive overview",
  "key_points": ["Headline 1", "Headline 2", "Headline 3", "Headline 4", "Headline 5"],
  "casualties_mentioned": "Specific casualty figures mentioned across all messages, or 'Not specified'",
  "territorial": "Specific territorial changes or confirmed front-line movements, or 'No significant changes reported'",
  "sentiment": "escalating|de-escalating|stable|volatile",
  "intensity": 7,
  "sections": {sections_spec}
}}"""

    if not OPENROUTER_API_KEY:
        print("  [error] OPENROUTER_API_KEY not set", file=sys.stderr)
        return {"summary": "API key not configured.", "key_points": [], "sentiment": "unknown", "intensity": 5, "sections": {}}

    raw_json = ""
    last_error = None
    for model in MODELS:
        try:
            print(f"  Trying model: {model}", file=sys.stderr)
            raw_json = call_openrouter(prompt, model)
            break
        except Exception as e:
            print(f"  [warn] {model} failed: {e}", file=sys.stderr)
            last_error = e
            time.sleep(3)

    if not raw_json:
        print(f"  [error] All models failed. Last: {last_error}", file=sys.stderr)
        return {"summary": "Summary generation temporarily unavailable.", "key_points": [], "sentiment": "unknown", "intensity": 5, "sections": {}}

    raw_json = re.sub(r"^```[a-z]*\n?", "", raw_json.strip())
    raw_json = re.sub(r"\n?```$", "", raw_json.strip())

    try:
        return json.loads(raw_json)
    except json.JSONDecodeError:
        match = re.search(r"\{[\s\S]+\}", raw_json)
        if match:
            try:
                return json.loads(match.group())
            except Exception:
                pass
        return {"summary": raw_json[:500], "key_points": [], "sentiment": "unknown", "intensity": 5, "sections": {}}


def build_messages_by_channel(channels: list[str], counts: dict[str, int]) -> dict:
    return {f"@{ch}": cnt for ch in channels if (cnt := counts.get(ch, 0)) > 0}


def run():
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)

    for key, conf in CONFLICTS.items():
        print(f"\n=== {conf['title']} ===", flush=True)
        per_channel_messages: dict[str, list[str]] = {}
        per_channel_timestamps: dict[str, list[datetime]] = {}
        per_channel_counts: dict[str, int] = {}
        max_ids: dict[str, int] = {}

        for ch in conf["channels"]:
            print(f"  Fetching 24 h from t.me/{ch} ...", file=sys.stderr)
            msgs, times, max_id = fetch_channel_messages_24h(ch)
            per_channel_messages[ch] = msgs
            per_channel_timestamps[ch] = times
            per_channel_counts[ch] = len(msgs)
            if max_id is not None:
                max_ids[ch] = max_id
            print(f"    -> {len(msgs)} relevant messages in last 24 h", file=sys.stderr)
            time.sleep(1.5)

        # Most recent post URL per channel (for clickable source tags in frontend)
        recent_post_urls = {
            ch: f"https://t.me/{ch}/{max_ids[ch]}"
            for ch in conf["channels"] if ch in max_ids
        }

        # Build balanced, channel-tagged message list: up to 15 per channel, shuffled
        tagged: list[str] = []
        for ch in conf["channels"]:
            for msg in per_channel_messages.get(ch, [])[:15]:
                tagged.append(f"[{ch}] {msg}")
        random.shuffle(tagged)
        all_messages = tagged

        total_count = sum(per_channel_counts.values())
        print(f"  Total messages collected: {total_count} ({len(all_messages)} sent to AI)", file=sys.stderr)
        print(f"  Generating AI summary...", file=sys.stderr)

        ai_result = generate_summary(conf["title"], conf["section_keys"], all_messages)
        # red_alerts is computed from structured data below, not from AI estimation
        ai_result.pop("red_alerts", None)

        msgs_by_channel = build_messages_by_channel(conf["channels"], per_channel_counts)

        # Real activity timeline from all channel timestamps
        all_timestamps = [ts for ch in conf["channels"] for ts in per_channel_timestamps.get(ch, [])]
        if any(ts is not None for ts in all_timestamps):
            activity_timeline = bucket_into_24h_slots(all_timestamps)
        else:
            activity_timeline = build_activity_timeline_synthetic(total_count)

        alert_ch = conf.get("alert_channel", "")

        if key == "middle_east":
            # Filter tzevaadom_en posts to only genuine Red Alert activations
            alert_texts = per_channel_messages.get(alert_ch, [])
            alert_times = per_channel_timestamps.get(alert_ch, [])
            real_pairs = [
                (t, ts) for t, ts in zip(alert_texts, alert_times) if is_real_alert(t)
            ]
            red_alerts_raw = len(real_pairs)
            real_alert_timestamps = [ts for _, ts in real_pairs if ts is not None]
            alert_timeline = bucket_into_24h_slots(real_alert_timestamps) if real_alert_timestamps else [0] * 24

        else:  # ukraine
            # Parse kpszsu daily summary infographic for total missiles + drones launched
            kpszsu_msgs = per_channel_messages.get("kpszsu", [])
            kpszsu_times = per_channel_timestamps.get("kpszsu", [])
            attack_data = parse_kpszsu_attack_summary(kpszsu_msgs, kpszsu_times)
            red_alerts_raw = attack_data["total"]
            update_ukraine_history(output_dir, attack_data)
            # eRadarrua air raid siren timestamps as proxy for attack timing on the 24h chart
            ua_alert_timestamps = [ts for ts in per_channel_timestamps.get(alert_ch, []) if ts is not None]
            alert_timeline = bucket_into_24h_slots(ua_alert_timestamps) if ua_alert_timestamps else [0] * 24

        output = {
            "conflict": conf["title"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "message_count": total_count,
            "channels": conf["channels"],
            "red_alerts": red_alerts_raw,
            "red_alerts_timeline": alert_timeline,
            "combined_activity_timeline": activity_timeline,
            "messages_by_channel": msgs_by_channel,
            "recent_post_urls": recent_post_urls,
            **ai_result,
        }

        path = output_dir / f"{key}.json"
        path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
        print(f"  Saved -> {path}", flush=True)

    print("\nDone.", flush=True)


if __name__ == "__main__":
    run()
