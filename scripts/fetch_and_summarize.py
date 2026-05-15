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


def fetch_channel_messages_24h(channel: str) -> tuple[list[str], list[datetime], list[int | None], int | None]:
    """
    Scrape messages from the last 24 hours of a public Telegram channel.
    Returns (texts, timestamps, post_ids, max_message_id).
    """
    base_url = f"https://t.me/s/{channel}"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    seen: set[str] = set()
    all_texts: list[str] = []
    all_times: list[datetime] = []
    all_ids: list[int | None] = []
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
            current_mid: int | None = None
            data_post = msg.get("data-post", "")
            if "/" in data_post:
                try:
                    mid = int(data_post.split("/")[-1])
                    current_mid = mid
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
                all_ids.append(current_mid)

        if not any_within_24h and page_num > 0:
            break
        if oldest_id_on_page is None or oldest_id_on_page == before_id:
            break

        before_id = oldest_id_on_page
        time.sleep(0.9)

    return all_texts, all_times, all_ids, max_id


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


def fetch_kpszsu_all_texts(channel: str = "kpszsu") -> list[str]:
    """Fetch all text from kpszsu without is_relevant() filter (daily summaries are short/numeric)."""
    base_url = f"https://t.me/s/{channel}"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=30)
    all_texts: list[str] = []
    before_id: int | None = None

    for page_num in range(5):
        url = base_url if before_id is None else f"{base_url}?before={before_id}"
        try:
            resp = requests.get(url, headers=HEADERS, timeout=18)
            resp.raise_for_status()
        except Exception as e:
            print(f"  [warn] kpszsu raw page {page_num}: {e}", file=sys.stderr)
            break

        soup = BeautifulSoup(resp.text, "html.parser")
        msg_els = soup.select(".tgme_widget_message")
        if not msg_els:
            break

        oldest_id: int | None = None
        any_within_window = False

        for msg in msg_els:
            data_post = msg.get("data-post", "")
            if "/" in data_post:
                try:
                    mid = int(data_post.split("/")[-1])
                    if oldest_id is None or mid < oldest_id:
                        oldest_id = mid
                except ValueError:
                    pass
            time_el = msg.select_one("time[datetime]")
            if time_el:
                try:
                    dt_str = time_el["datetime"].replace("Z", "+00:00")
                    msg_time = datetime.fromisoformat(dt_str)
                    if msg_time < cutoff:
                        continue
                    any_within_window = True
                except Exception:
                    pass
            elif page_num > 0:
                continue
            txt_el = msg.select_one(".tgme_widget_message_text")
            if txt_el:
                txt = txt_el.get_text(separator=" ", strip=True)
                if len(txt) > 5:
                    all_texts.append(txt)

        if not any_within_window and page_num > 0:
            break
        if oldest_id is None or oldest_id == before_id:
            break
        before_id = oldest_id
        time.sleep(0.9)

    print(f"  [kpszsu raw] {len(all_texts)} texts", file=sys.stderr)
    return all_texts


def parse_missile_count(texts: list[str]) -> int:
    """Extract missile count from kpszsu posts (dedicated function)."""
    for text in texts:
        m = re.search(r'(\d+)\s+MISSILES?\s+AND', text, re.IGNORECASE)
        if m:
            return int(m.group(1))
        m = re.search(r'AND\s+(\d+)\s+MISSILES?', text, re.IGNORECASE)
        if m:
            return int(m.group(1))
        m_total = re.search(r'(\d{2,4})\s+засо?б\w*\s+повітряного\s+нападу', text, re.IGNORECASE)
        if m_total:
            m_dr = re.search(r'(\d+)\s+(?:ворожих?\s+)?(?:[Бб][Пп][Лл][Аа]|дрон\w*)', text)
            return int(m_total.group(1)) - (int(m_dr.group(1)) if m_dr else 0)
        hits = re.findall(r'(\d+)\s+(?:крилатих?|балістичних?)\s*ракет\w*', text, re.IGNORECASE)
        if hits:
            return sum(int(x) for x in hits)
        if re.search(r'(?:ЗБИТО|ПЕРЕХОПЛЕНО|знищено|SHOT)', text, re.IGNORECASE):
            m = re.search(r'(\d{1,3})\s+(?:missile|ракет|rocket)', text, re.IGNORECASE)
            if m:
                return int(m.group(1))
    return 0


def parse_drone_count(texts: list[str]) -> int:
    """Extract drone/UAV count from kpszsu posts (dedicated function)."""
    for text in texts:
        m = re.search(r'(\d+)\s+(?:ENEMY\s+)?UAV', text, re.IGNORECASE)
        if m:
            return int(m.group(1))
        m = re.search(r'(\d+)\s+(?:ворожих?\s+)?(?:[Бб][Пп][Лл][Аа]|дрон\w*)', text)
        if m:
            return int(m.group(1))
        if re.search(r'(?:ЗБИТО|ПЕРЕХОПЛЕНО|знищено|SHOT)', text, re.IGNORECASE):
            m = re.search(r'(\d{2,4})\s+(?:UAV|БПЛА|БпЛА|дрон)', text, re.IGNORECASE)
            if m:
                return int(m.group(1))
    return 0


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

    section_instructions = []
    for key in section_keys:
        if key == "executive_summary":
            section_instructions.append(
                f'- {key}: 3-sentence executive brief. Start with the single most operationally significant development.'
            )
        elif key == "key_developments":
            section_instructions.append(
                f'- {key}: list of exactly 7 concise, actionable intelligence headlines ordered by operational significance. '
                f'Each must end with (Source: @channel/postID) or (Source: @channel) — only the specific channel that provided that information.'
            )
        elif key in ("threat_assessment", "regional_response", "intelligence_notes"):
            section_instructions.append(
                f'- {key}: string (2–4 sentences of analytical prose)'
            )
        else:
            section_instructions.append(
                f'- {key}: object with "points" list (3–6 concise bullet points, each under 60 words)'
            )

    prompt = f"""You are an intelligence analyst producing structured conflict briefings.
Analyse the following messages from {conflict_name} channels and extract structured intelligence.

Messages are prefixed [channel/postID] or [channel]. When citing sources, use format (Source: @channel/postID) if a post ID is present, or (Source: @channel) otherwise.
Only cite the specific channel(s) that actually provided each piece of information.

Return ONLY valid JSON with this exact structure:
{{
  "summary": "3-sentence executive summary",
  "key_points": ["7 short bullet points for ticker"],
  "sentiment": "one of: escalating|volatile|active|tense|stable|calm",
  "intensity": <1-10>,
  "sections": {{
    {chr(10).join(section_instructions)}
  }}
}}

For key_developments, each item in the list should be a complete sentence ending with its source citation.

Messages (newest first, may include Hebrew/Arabic/Ukrainian/Russian):
{combined[:14000]}

Return only the JSON object, no other text."""

    last_exc: Exception | None = None
    for model in MODELS:
        try:
            raw = call_openrouter(prompt, model)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            result = json.loads(raw)
            print(f"  [ok] model={model}", file=sys.stderr)
            return result
        except Exception as e:
            last_exc = e
            print(f"  [warn] model={model} failed: {e}", file=sys.stderr)
            time.sleep(2)
    print(f"  [error] all models failed: {last_exc}", file=sys.stderr)
    return {"summary": "Summary unavailable.", "key_points": [], "sentiment": "unknown", "intensity": 5, "sections": {}}


def build_messages_by_channel(channels: list[str], counts: dict[str, int]) -> dict[str, int]:
    return {f"@{ch}": counts.get(ch, 0) for ch in channels if counts.get(ch, 0) > 0}


def run() -> None:
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)

    for key, conf in CONFLICTS.items():
        print(f"\n=== {conf['title']} ===", file=sys.stderr)

        per_channel_messages: dict[str, list[str]] = {}
        per_channel_timestamps: dict[str, list[datetime]] = {}
        per_channel_message_ids: dict[str, list[int | None]] = {}
        per_channel_counts: dict[str, int] = {}
        recent_post_urls: dict[str, str] = {}

        for ch in conf["channels"]:
            print(f"  Fetching {ch}...", file=sys.stderr)
            msgs, times, ids, max_id = fetch_channel_messages_24h(ch)
            per_channel_messages[ch] = msgs
            per_channel_timestamps[ch] = times
            per_channel_message_ids[ch] = ids
            per_channel_counts[ch] = len(msgs)
            if max_id:
                recent_post_urls[ch] = f"https://t.me/{ch}/{max_id}"
            print(f"    -> {len(msgs)} messages", file=sys.stderr)

        # Ukraine gets higher per-channel limit for better AI coverage
        per_ch_limit = 25 if key == "ukraine" else 15
        tagged: list[str] = []
        for ch in conf["channels"]:
            msgs = per_channel_messages.get(ch, [])[:per_ch_limit]
            ids = per_channel_message_ids.get(ch, [])[:per_ch_limit]
            for msg, mid in zip(msgs, ids):
                prefix = f"{ch}/{mid}" if mid else ch
                tagged.append(f"[{prefix}] {msg}")
        random.shuffle(tagged)
        all_messages = tagged

        total_count = sum(per_channel_counts.values())
        print(f"  Total messages collected: {total_count} ({len(all_messages)} sent to AI)", file=sys.stderr)
        print(f"  Generating AI summary...", file=sys.stderr)

        ai_result = generate_summary(conf["title"], conf["section_keys"], all_messages)
        ai_result.pop("red_alerts", None)

        msgs_by_channel = build_messages_by_channel(conf["channels"], per_channel_counts)

        all_timestamps = [ts for ch in conf["channels"] for ts in per_channel_timestamps.get(ch, [])]
        if any(ts is not None for ts in all_timestamps):
            activity_timeline = bucket_into_24h_slots(all_timestamps)
        else:
            activity_timeline = build_activity_timeline_synthetic(total_count)

        alert_ch = conf.get("alert_channel", "")

        if key == "middle_east":
            alert_texts = per_channel_messages.get(alert_ch, [])
            alert_times = per_channel_timestamps.get(alert_ch, [])
            real_pairs = [
                (t, ts) for t, ts in zip(alert_texts, alert_times) if is_real_alert(t)
            ]
            red_alerts_raw = len(real_pairs)
            real_alert_timestamps = [ts for _, ts in real_pairs if ts is not None]
            alert_timeline = bucket_into_24h_slots(real_alert_timestamps) if real_alert_timestamps else [0] * 24

        else:  # ukraine
            # Fetch kpszsu without is_relevant() filter so short/numeric daily summaries are parsed
            kpszsu_raw = fetch_kpszsu_all_texts("kpszsu")
            missiles = parse_missile_count(kpszsu_raw)
            drones = parse_drone_count(kpszsu_raw)
            red_alerts_raw = missiles + drones
            print(f"  [kpszsu] missiles={missiles} drones={drones} total={red_alerts_raw}", file=sys.stderr)
            update_ukraine_history(output_dir, {"total": red_alerts_raw, "missiles": missiles, "drones": drones, "ts": None})
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
        if key == "ukraine":
            output["missiles"] = missiles
            output["drones"] = drones

        path = output_dir / f"{key}.json"
        path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
        print(f"  Saved -> {path}", flush=True)

    print("\nDone.", flush=True)


if __name__ == "__main__":
    run()
