#!/usr/bin/env python3
import os
import json
import time
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# Tried in order until one succeeds
MODELS = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "openai/gpt-oss-120b:free",
]

CONFLICTS = {
    "middle_east": {
        "title": "Middle East Conflict",
        "channels": [
            "N12chat", "manniefabian", "asafroz", "yediotnews25",
            "SharghDaily", "amitsegal", "presstv", "mamlekate",
            "kianmeli1", "Faytuks_Network", "rodast_omiddana",
            "naya_foriraq", "tzevaadom_en", "VahidOnline", "idf_telegram"
        ],
    },
    "ukraine": {
        "title": "Ukraine-Russia War",
        "channels": [
            "eRadarrua", "kpszsu", "mon1tor_ua", "Faytuks_Network"
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
        "temperature": 0.4,
        "max_tokens": 2048,
    }
    resp = requests.post(url, json=body, headers=headers, timeout=60)
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def generate_summary(conflict_name: str, raw_messages: list[str]) -> dict:
    if not raw_messages:
        return {
            "summary": "No recent updates available.",
            "key_points": [],
            "sentiment": "neutral",
            "intensity": 3,
        }

    combined = "\n\n---\n\n".join(raw_messages[:40])
    prompt = f"""You are a conflict analyst. Analyze these recent Telegram messages about the {conflict_name} and produce a structured intelligence brief.

Messages:
{combined}

Respond with ONLY valid JSON (no markdown, no code fences) in this exact format:
{{
  "summary": "3-4 sentence executive summary of current situation",
  "key_points": [
    "Key development 1",
    "Key development 2",
    "Key development 3",
    "Key development 4",
    "Key development 5"
  ],
  "casualties_mentioned": "Brief note on any casualties/losses mentioned, or 'Not specified'",
  "territorial": "Any territorial changes or front-line movements mentioned, or 'No significant changes reported'",
  "sentiment": "escalating|de-escalating|stable|volatile",
  "intensity": 7
}}

The intensity field is 1-10 (1=minimal, 10=extreme conflict).
Keep all text factual, concise, and neutral. No speculation."""

    if not OPENROUTER_API_KEY:
        print("  [error] OPENROUTER_API_KEY not set", file=sys.stderr)
        return {"summary": "API key not configured.", "key_points": [], "sentiment": "unknown", "intensity": 5}

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
        return {"summary": "Summary generation temporarily unavailable.", "key_points": [], "sentiment": "unknown", "intensity": 5}

    # Strip accidental markdown fences
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
        return {"summary": raw_json[:500], "key_points": [], "sentiment": "unknown", "intensity": 5}


def run():
    output_dir = Path(__file__).parent.parent / "data"
    output_dir.mkdir(exist_ok=True)

    for key, conf in CONFLICTS.items():
        print(f"\n=== {conf['title']} ===")
        all_messages = []
        for ch in conf["channels"]:
            print(f"  Fetching t.me/{ch} ...")
            msgs = fetch_channel_messages(ch, limit=8)
            print(f"    -> {len(msgs)} messages")
            all_messages.extend(msgs)
            time.sleep(1.2)

        print(f"  Generating AI summary ({len(all_messages)} messages)...")
        ai_result = generate_summary(conf["title"], all_messages)

        output = {
            "conflict": conf["title"],
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "message_count": len(all_messages),
            "channels": conf["channels"],
            **ai_result,
        }

        path = output_dir / f"{key}.json"
        path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
        print(f"  Saved -> {path}")

    print("\nDone.")


if __name__ == "__main__":
    run()
