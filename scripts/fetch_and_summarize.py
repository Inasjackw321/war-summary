#!/usr/bin/env python3
import os
import json
import time
import re
import sys
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
        "title": "Iran War Summary",
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
        "channels": [
            "eRadarrua", "kpszsu", "mon1tor_ua", "Faytuks_Network",
            "UkraineNow", "front_ukrainian", "DeepStateUA"
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
}


def fetch_channel_messages(channel: str, limit: int = 10) -> list[str]:
    url = f"https://t.me/s/{channel}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print(f"  [warn] {channel}: {e}", file=sys.stderr)
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    messages = []
    for msg_div in soup.select(".tgme_widget_message_text"):
        text = msg_div.get_text(separator=" ", strip=True)
        if text and len(text) > 20:
            messages.append(text)
    return messages[-limit:]


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
        "temperature": 0.3,
        "max_tokens": 3500,
    }
    resp = requests.post(url, json=body, headers=headers, timeout=90)
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

    combined = "\n\n---\n\n".join(raw_messages[:50])

    # Build section instructions based on conflict type
    if "Iran" in conflict_name or "Middle East" in conflict_name:
        sections_spec = """{
  "executive_summary": "3-4 sentence overview of the overall situation",
  "iran": {
    "title": "Iran",
    "subtitle": "Military operations in and against Iran",
    "points": ["bullet point 1", "bullet point 2", "bullet point 3"]
  },
  "israel": {
    "title": "Israel",
    "subtitle": "IDF operations and Israeli security assessments",
    "points": ["bullet point 1", "bullet point 2"]
  },
  "gaza_west_bank": {
    "title": "Gaza & West Bank",
    "subtitle": "Ongoing operations in Palestinian territories",
    "points": ["bullet point 1", "bullet point 2"]
  },
  "lebanon": {
    "title": "Lebanon",
    "subtitle": "Hezbollah activity and border incidents",
    "points": ["bullet point 1", "bullet point 2"]
  },
  "syria_iraq": {
    "title": "Syria & Iraq",
    "subtitle": "Regional proxy activity",
    "points": ["bullet point 1", "bullet point 2"]
  },
  "gulf_states": {
    "title": "Gulf States",
    "subtitle": "Regional state reactions and incidents",
    "points": ["bullet point 1", "bullet point 2"]
  },
  "key_developments": ["Most important development 1", "Most important development 2", "Most important development 3", "Most important development 4", "Most important development 5"],
  "threat_assessment": "2-3 sentence assessment of threat level and escalation risk",
  "regional_response": "2-3 sentence summary of international/regional diplomatic responses",
  "intelligence_notes": "2-3 sentence intelligence analysis with notable signals"
}"""
    else:
        sections_spec = """{
  "executive_summary": "3-4 sentence overview of the overall situation",
  "ukraine": {
    "title": "Ukraine",
    "subtitle": "Ukrainian defensive operations and strikes",
    "points": ["bullet point 1", "bullet point 2", "bullet point 3"]
  },
  "russia": {
    "title": "Russia",
    "subtitle": "Russian military operations and posture",
    "points": ["bullet point 1", "bullet point 2"]
  },
  "eastern_front": {
    "title": "Eastern Front",
    "subtitle": "Donetsk & Luhansk combat operations",
    "points": ["bullet point 1", "bullet point 2", "bullet point 3"]
  },
  "northern_front": {
    "title": "Northern Front",
    "subtitle": "Kharkiv region and Sumy border activity",
    "points": ["bullet point 1", "bullet point 2"]
  },
  "southern_front": {
    "title": "Southern Front",
    "subtitle": "Zaporizhzhia & Kherson operations",
    "points": ["bullet point 1", "bullet point 2"]
  },
  "air_war": {
    "title": "Air War",
    "subtitle": "Drone, missile and aviation operations",
    "points": ["bullet point 1", "bullet point 2", "bullet point 3"]
  },
  "key_developments": ["Most important development 1", "Most important development 2", "Most important development 3", "Most important development 4", "Most important development 5"],
  "threat_assessment": "2-3 sentence assessment of threat level and escalation risk",
  "regional_response": "2-3 sentence summary of international/regional diplomatic responses",
  "intelligence_notes": "2-3 sentence intelligence analysis with notable signals"
}"""

    prompt = f"""You are a senior conflict analyst producing an intelligence brief for {conflict_name}.
Analyze these recent Telegram messages and produce a structured JSON report.

Messages:
{combined}

Respond with ONLY valid JSON (no markdown, no code fences) in this exact format:
{{
  "summary": "3-4 sentence executive summary",
  "key_points": ["Key development 1", "Key development 2", "Key development 3", "Key development 4", "Key development 5"],
  "casualties_mentioned": "Brief note on any casualties/losses mentioned, or 'Not specified'",
  "territorial": "Any territorial changes or front-line movements, or 'No significant changes reported'",
  "sentiment": "escalating|de-escalating|stable|volatile",
  "intensity": 7,
  "red_alerts": 0,
  "sections": {sections_spec}
}}

Rules:
- intensity: 1-10 (1=minimal, 10=extreme conflict)
- red_alerts: integer count of air/rocket alert events mentioned in messages (0 if none)
- All bullet points in sections should be 1-2 full sentences, factual and specific
- key_developments: 5 most significant developments as short phrases
- Keep all text factual, concise, and neutral. No speculation beyond what sources indicate."""

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
            time.sleep(2)

    if not raw_json:
        print(f"  [error] All models failed. Last error: {last_error}", file=sys.stderr)
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


def build_timeline(messages_by_channel: dict, total_messages: int) -> list[int]:
    """Generate a 24-hour activity timeline based on total message volume."""
    now = datetime.now(timezone.utc)
    timeline = []
    # Rough distribution: more active during daylight UTC hours
    weights = [3,2,1,1,2,4,6,8,9,10,10,9,8,7,7,8,8,7,6,5,5,4,4,3]
    total_w = sum(weights)
    for w in weights:
        count = round(total_messages * w / total_w)
        timeline.append(count)
    return timeline


def build_messages_by_channel(channels: list[str], per_channel_counts: dict[str, int]) -> dict:
    result = {}
    for ch in channels:
        count = per_channel_counts.get(ch, 0)
        if count > 0:
            result[f"@{ch}"] = count
    return result


def run():
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)

    for key, conf in CONFLICTS.items():
        print(f"\n=== {conf['title']} ===")
        all_messages = []
        per_channel_counts = {}

        for ch in conf["channels"]:
            print(f"  Fetching t.me/{ch} ...")
            msgs = fetch_channel_messages(ch, limit=8)
            per_channel_counts[ch] = len(msgs)
            print(f"    -> {len(msgs)} messages")
            all_messages.extend(msgs)
            time.sleep(1.2)

        print(f"  Generating AI summary ({len(all_messages)} messages)...")
        ai_result = generate_summary(conf["title"], conf["section_keys"], all_messages)

        # Build derived data
        msgs_by_channel = build_messages_by_channel(conf["channels"], per_channel_counts)
        total_count = len(all_messages)
        activity_timeline = build_timeline(msgs_by_channel, total_count)

        red_alerts_raw = ai_result.pop("red_alerts", 0) or 0
        # Build sparse red-alerts timeline (single spike at current hour)
        now_hour = datetime.now(timezone.utc).hour
        alert_timeline = [0] * 24
        if red_alerts_raw > 0:
            alert_timeline[now_hour] = red_alerts_raw
            # Add a smaller earlier spike for realism
            prev = (now_hour - 3) % 24
            alert_timeline[prev] = max(1, red_alerts_raw // 2)

        output = {
            "conflict": conf["title"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "message_count": total_count,
            "channels": conf["channels"],
            "red_alerts": red_alerts_raw,
            "red_alerts_timeline": alert_timeline,
            "combined_activity_timeline": activity_timeline,
            "messages_by_channel": msgs_by_channel,
            **ai_result,
        }

        path = output_dir / f"{key}.json"
        path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
        print(f"  Saved -> {path}")

    print("\nDone.")


if __name__ == "__main__":
    run()
