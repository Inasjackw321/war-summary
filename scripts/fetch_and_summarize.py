#!/usr/bin/env python3
import os
import json
import time
import re
import sys
import random
import traceback
from datetime import datetime, timezone, timedelta
from pathlib import Path

import requests
from bs4 import BeautifulSoup

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

MODELS = [
    "openai/gpt-oss-120b:free",
    "openrouter/owl-alpha",
    "nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
]

CONFLICTS = {
    "middle_east": {
        "title": "Middle-East War",
        "alert_channel": "tzevaadom_en",
        "channels": [
            "N12chat", "manniefabian", "asafroz", "yediotnews25",
            "SharghDaily", "amitsegal", "presstv", "mamlekate",
            "kianmeli1", "Faytuks_Network", "rodast_omiddana",
            "naya_foriraq", "tzevaadom_en", "VahidOnline", "idf_telegram",
            "lelotsenzura", "rasedal3ado138e", "shin_persian",
            "almogboker78", "New_security8200", "inon_yttach",
            "redlinkleb", "pkpoi"
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
            "eRadarrua", "kpszsu", "mon1tor_ua",
            "UkraineNow", "DeepStateUA", "ukr_leaks_eng", "tass_agency"
        ],
        "section_keys": [
            "executive_summary", "ukraine", "russia", "eastern_front",
            "northern_front", "southern_front", "air_war",
            "key_developments", "threat_assessment", "regional_response", "intelligence_notes"
        ],
    },
}

MEDIA_CHANNELS = {"Faytuks_Network", "manniefabian", "idf_telegram", "kpszsu", "eRadarrua", "VahidOnline", "amitsegal"}

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


def _fetch_url(url: str, retries: int = 3) -> "requests.Response | None":
    """GET with exponential-backoff retries."""
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            resp.raise_for_status()
            return resp
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                print(f"  [warn] fetch failed ({url}): {e}", file=sys.stderr)
    return None


def cleanup_unreferenced_media(media_dir: Path, referenced_paths: set[str]) -> None:
    """Delete any image file in media_dir not in referenced_paths."""
    if not media_dir.exists():
        return
    for f in media_dir.iterdir():
        if f.name.startswith(".") or f.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
            continue
        rel = f"data/media/{f.name}"
        if rel not in referenced_paths:
            try:
                f.unlink()
                print(f"  [media] deleted unreferenced: {f.name}", file=sys.stderr)
            except Exception as e:
                print(f"  [media] delete failed {f.name}: {e}", file=sys.stderr)


_IMAGE_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}

def download_media(url: str, dest: Path) -> bool:
    try:
        resp = requests.get(url, headers={**HEADERS, "Referer": "https://t.me/"}, timeout=20, stream=True)
        resp.raise_for_status()
        ct = resp.headers.get("Content-Type", "").split(";")[0].strip().lower()
        if ct and ct not in _IMAGE_CONTENT_TYPES:
            print(f"  [media] skipped (not image, ct={ct}): {dest.name}", file=sys.stderr)
            return False
        with open(dest, "wb") as fh:
            for chunk in resp.iter_content(8192):
                if chunk:
                    fh.write(chunk)
        print(f"  [media] saved: {dest.name}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"  [media] failed {dest.name}: {e}", file=sys.stderr)
        return False


def _cdn_url(photo_wrap) -> str | None:
    style = photo_wrap.get("style", "") if photo_wrap else ""
    m = re.search(r"background-image:url\('([^']+)'\)", style)
    return m.group(1) if m else None


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


def fetch_channel_messages_24h(channel: str) -> tuple[list[str], list[datetime], list[int | None], int | None, list[dict]]:
    """
    Scrape messages from the last 24 hours of a public Telegram channel.
    Returns (texts, timestamps, post_ids, max_message_id, images).
    """
    base_url = f"https://t.me/s/{channel}"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    seen: set[str] = set()
    all_texts: list[str] = []
    all_times: list[datetime] = []
    all_ids: list[int | None] = []
    all_images: list[dict] = []
    before_id: int | None = None
    max_id: int | None = None

    for page_num in range(12):
        url = base_url if before_id is None else f"{base_url}?before={before_id}"
        resp = _fetch_url(url)
        if resp is None:
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
                photo_wrap = msg.select_one("a.tgme_widget_message_photo_wrap")
                if photo_wrap and current_mid and msg_time:
                    entry: dict = {"post_url": f"https://t.me/{channel}/{current_mid}", "post_id": current_mid, "channel": channel, "ts": msg_time.isoformat()}
                    if channel in MEDIA_CHANNELS:
                        cdn = _cdn_url(photo_wrap)
                        if cdn:
                            entry["cdn_url"] = cdn
                    all_images.append(entry)
                continue
            txt = txt_el.get_text(separator=" ", strip=True)

            photo_wrap = msg.select_one("a.tgme_widget_message_photo_wrap")
            if photo_wrap and current_mid and msg_time:
                entry = {"post_url": f"https://t.me/{channel}/{current_mid}", "post_id": current_mid, "channel": channel, "ts": msg_time.isoformat() if msg_time else None}
                if channel in MEDIA_CHANNELS:
                    cdn = _cdn_url(photo_wrap)
                    if cdn:
                        entry["cdn_url"] = cdn
                all_images.append(entry)

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

    # Tag photo posts that are directly adjacent (±1 ID) to a text post.
    # When the AI cites the text post ID, the alias in _build_post_images will
    # find the photo from the neighbouring message in the same story group.
    if channel in MEDIA_CHANNELS:
        text_id_set = {i for i in all_ids if i is not None}
        for img in all_images:
            pid = img.get("post_id")
            if pid is None:
                continue
            for adj in (pid - 1, pid + 1, pid - 2, pid + 2):
                if adj in text_id_set:
                    img["companion_text_id"] = adj
                    break

    return all_texts, all_times, all_ids, max_id, all_images


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


_ATTACK_SUMMARY_RE = re.compile(
    r'attacked\s+with|атакув\w+|Shahed|Кh-\d+|Kh-\d+|Х-\d+|attack\s+UAV|ударни\w+\s+БпЛА'
    r'|засобів\s+повітряного|MISSILE.{0,20}UAV|UAV.{0,20}MISSILE|air\s+attack\s+vehicles?',
    re.IGNORECASE,
)


def fetch_kpszsu_all_texts(channel: str = "kpszsu") -> list[str]:
    """Fetch kpszsu posts from last 72h, attack-summary texts sorted newest-first."""
    base_url = f"https://t.me/s/{channel}"
    cutoff = datetime.now(timezone.utc) - timedelta(hours=72)
    attack_entries: list[tuple[int, str]] = []   # (post_id, text) for attack summaries
    other_texts: list[str] = []
    before_id: int | None = None

    for page_num in range(8):
        url = base_url if before_id is None else f"{base_url}?before={before_id}"
        resp = _fetch_url(url)
        if resp is None:
            break
        soup = BeautifulSoup(resp.text, "html.parser")
        msg_els = soup.select(".tgme_widget_message")
        if not msg_els:
            break

        oldest_id: int | None = None
        any_within_window = False

        for msg in msg_els:
            mid: int | None = None
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
                if len(txt) > 10:
                    if _ATTACK_SUMMARY_RE.search(txt):
                        attack_entries.append((mid or 0, txt))
                    else:
                        other_texts.append(txt)

        if not any_within_window and page_num > 0:
            break
        if oldest_id is None or oldest_id == before_id:
            break
        before_id = oldest_id
        time.sleep(0.9)

    # Sort attack summaries newest-first by post ID so today's summary is parsed before older ones
    attack_entries.sort(key=lambda x: x[0], reverse=True)
    attack_texts = [text for _, text in attack_entries]

    # Attack-summary posts first so parse functions find them before non-attack posts
    all_texts = attack_texts + other_texts
    print(f"  [kpszsu raw] {len(all_texts)} texts ({len(attack_texts)} attack summaries)", file=sys.stderr)
    return all_texts


_WORD_NUMS = {
    # English
    'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
    'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
    'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14, 'fifteen': 15,
    # Ukrainian nominative/accusative/instrumental forms of 1–10
    'одна': 1, 'один': 1, 'одну': 1, 'одним': 1, 'одного': 1, 'однієї': 1, 'однією': 1,
    'два': 2, 'двох': 2, 'двома': 2,
    'три': 3, 'трьох': 3, 'трьома': 3,
    'чотири': 4, 'чотирьох': 4, 'чотирма': 4,
    "п'ять": 5, "п'ятьох": 5, "п'ятьма": 5, "п'яти": 5,
    'шість': 6, 'шістьох': 6, 'шістьма': 6, 'шести': 6,
    'сім': 7, 'семи': 7, 'сімома': 7,
    'вісім': 8, 'восьми': 8, 'вісьмома': 8,
    "дев'ять": 9, "дев'яти": 9, "дев'ятьма": 9,
    'десять': 10, 'десяти': 10, 'десятьма': 10,
}

def _to_int(s: str) -> int:
    return _WORD_NUMS.get(s.lower(), int(s) if s.isdigit() else 0)


_KH_WORD_PREFIX = (
    r'одн\w+|дво\w*|трьо\w+|чотир\w+|п\'ят\w+|шіст\w+|сімо\w+|вісь\w+|дев\'ят\w+|десят\w+'
    r'|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve'
    r'|\d+'
)
# Matches "five Kh-31P" or "п'ятьма ... Х-31П" (0-2 adjective words allowed between numeral and Х-)
_KH_RE = re.compile(
    rf'({_KH_WORD_PREFIX})\s+(?:\w+\s+){{0,2}}(?:Kh|Х)-\d+',
    re.IGNORECASE | re.UNICODE,
)


def _extract_drones_from_text(text: str) -> int:
    """Extract drone count from a single text. Returns 0 if not found."""
    m = re.search(r'(\d{2,4})\s+(?:attack|strike|combat)\s+UAVs?\b', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d{2,4})\s+Shahed', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    m = re.search(r'(\d+)\s+ударни\w+\s+(?:[Бб][Пп][Лл][Аа]|дрон\w*)', text)
    if m:
        return int(m.group(1))
    m = re.search(r'air\s+attack\s+vehicles?.{0,200}[-–,]\s*(\d{2,4})\s+UAVs?\b', text, re.IGNORECASE | re.DOTALL)
    if m:
        return int(m.group(1))
    return 0


def _extract_missiles_from_text(text: str) -> int:
    """Extract missile count from a single text via explicit patterns. Returns 0 if not found."""
    m = re.search(r'[-–]\s*(\d{1,3})\s+missiles?\b', text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    # Kh-type enumeration in launch portion (before any shoot-down text)
    launch_m = re.search(
        r'(?:атакув\w+|attacked\s+with\b|launched.{0,40}(?:missile|UAV|drone|strike|aerial)).+',
        text, re.IGNORECASE | re.DOTALL,
    )
    if launch_m:
        launch_text = launch_m.group(0)
        zbito = re.search(r'(?:збит|подавлен|shot\s*down|shotdown|suppressed|ЗБИТО)', launch_text, re.IGNORECASE)
        if zbito:
            launch_text = launch_text[:zbito.start()]
        kh_hits = _KH_RE.findall(launch_text)
        if kh_hits:
            total = sum(_to_int(h) for h in kh_hits)
            if total > 0:
                return total
    hits = re.findall(r'(\d+)\s+(?:крилатих?|балістичних?)\s*ракет\w*', text, re.IGNORECASE)
    if hits:
        return sum(int(x) for x in hits)
    return 0


def parse_attack_counts(texts: list[str]) -> tuple[int, int]:
    """Return (missiles, drones) from the most recent attack summary in texts.

    All numbers come from the SAME text to avoid mixing totals across different attacks.
    texts must be sorted newest-first (highest post_id first).
    """
    for text in texts:
        if not _ATTACK_SUMMARY_RE.search(text):
            continue

        # Total aerial means in this text
        m_total_uk = re.search(r'(\d{2,4})\s+засо?б\w*\s+повітряного\s+нападу', text, re.IGNORECASE)
        m_total_en = re.search(r'(\d{2,4})\s+air\s+attack\s+vehicles?\b', text, re.IGNORECASE)
        total_m = m_total_uk or m_total_en
        total = int(total_m.group(1)) if total_m else 0

        drones = _extract_drones_from_text(text)
        missiles = _extract_missiles_from_text(text)

        if total > 0:
            if drones > 0 and missiles == 0:
                missiles = max(0, total - drones)
            elif missiles > 0 and drones == 0:
                drones = max(0, total - missiles)
            elif drones == 0 and missiles == 0:
                # Can't split total without a breakdown — skip this text
                continue
            return missiles, drones

        if drones > 0 or missiles > 0:
            # No total available — trust the explicit counts found
            return missiles, drones

    return 0, 0


# Keep thin wrappers for any other call sites (not used by _process_conflict any more)
def parse_missile_count(texts: list[str], drones: int = 0) -> int:
    m, _ = parse_attack_counts(texts)
    return m


def parse_drone_count(texts: list[str], missiles: int = 0) -> int:
    _, d = parse_attack_counts(texts)
    return d


def update_conflict_history(output_dir: Path, conflict_key: str, data: dict) -> None:
    """Append today's data to a conflict's history file. Keeps last 90 days."""
    path = output_dir / f"{conflict_key}_history.json"
    try:
        hist = json.loads(path.read_text()) if path.exists() else {"entries": []}
    except Exception:
        hist = {"entries": []}
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    hist["entries"] = [e for e in hist["entries"] if e["date"] != today]
    hist["entries"].append({"date": today, **data})
    hist["entries"].sort(key=lambda e: e["date"])
    hist["entries"] = hist["entries"][-90:]
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
    resp = requests.post(url, json=body, headers=headers, timeout=180)
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
                f'- {key}: list of exactly 7 detailed, actionable intelligence items ordered by operational significance. '
                f'Each item must be 30-60 words, include specific locations, unit types, distances or quantities where known, '
                f'and end with (Source: @channel/postID) or (Source: @channel).'
            )
        elif key in ("threat_assessment", "regional_response", "intelligence_notes"):
            section_instructions.append(
                f'- {key}: string (3–5 sentences of analytical prose with specific details, named actors, and operational implications)'
            )
        else:
            section_instructions.append(
                f'- {key}: object with "points" list (4–7 detailed bullet points, each 40–90 words. '
                f'Include specific locations, distances, unit types, weapon systems, casualty figures, or quantities where known. '
                f'Do not pad with vague language — cite specific operational facts.)'
            )

    prompt = f"""You are an intelligence analyst producing structured conflict briefings.
Analyse the following messages from {conflict_name} channels and extract structured intelligence.

STRICT GROUNDING RULES — read carefully before writing anything:
1. Every claim, location, unit, number, or event you write MUST be directly stated in the source messages. Do not infer, extrapolate, or add context from your training data.
2. If a message is vague or lacks details, write vaguely. Never invent specifics (distances, casualty figures, unit names, weapon types) that are not explicitly stated in the messages.
3. If you cannot find 7 key_developments or all section points from the actual messages, write fewer — do not pad with plausible-sounding inventions.
4. STRICT RELEVANCE: Only include information about {conflict_name}. Discard messages about other conflicts, regions, or off-topic events.
5. Source citations: use the EXACT channel and post ID from the message prefix [channel/postID]. Never cite a post you did not use.

Messages are prefixed [channel/postID] or [channel]. Cite as (Source: @channel/postID) or (Source: @channel).

Return ONLY valid JSON with this exact structure:
{{
  "summary": "3-sentence executive summary using only facts from the messages",
  "key_points": [
    "Up to 8 most significant developments, each 15-25 words of facts FROM the messages, then (Source: @channel/postID). No invented details. Ordered by operational importance."
  ],
  "sentiment": "one of: escalating|volatile|active|tense|stable|calm",
  "intensity": <1-10>,
  "sections": {{
    {chr(10).join(section_instructions)}
  }}
}}

For key_developments, each item must be a complete sentence ending with its source citation, using only information explicitly present in the cited message.

Messages (newest first, may include Hebrew/Arabic/Ukrainian/Russian):
{combined[:14000]}

Return only the JSON object, no other text."""

    last_exc: Exception | None = None
    for i, model in enumerate(MODELS):
        try:
            raw = call_openrouter(prompt, model)
            raw = raw.strip()
            if raw.startswith("```"):
                raw = re.sub(r"^```[a-z]*\n?", "", raw)
                raw = re.sub(r"\n?```$", "", raw)
            result = json.loads(raw)
            if not result.get("sections"):
                raise ValueError("AI returned empty sections")
            print(f"  [ok] model={model}", file=sys.stderr)
            return result
        except Exception as e:
            last_exc = e
            wait = 20 * (i + 1)  # 20s, 40s, 60s between model attempts
            print(f"  [warn] model={model} failed: {e} — waiting {wait}s before next model", file=sys.stderr)
            time.sleep(wait)
    print(f"  [error] all models failed: {last_exc}", file=sys.stderr)
    return {"summary": "Summary unavailable.", "key_points": [], "sentiment": "unknown", "intensity": 5, "sections": {}}


def _extract_cited_posts(ai_result: dict, valid_channels: set[str]) -> dict[str, str]:
    """Return {channel: url} linking to the specific post ID the AI cited, falling back to channel root."""
    parts: list[str] = []
    parts.extend(ai_result.get("key_points", []))
    parts.append(ai_result.get("summary", ""))
    for v in ai_result.get("sections", {}).values():
        if isinstance(v, str):
            parts.append(v)
        elif isinstance(v, dict):
            parts.extend(v.get("points", []))
        elif isinstance(v, list):
            parts.extend(str(x) for x in v)
    combined = " ".join(parts)
    cited: dict[str, str] = {}
    for m in re.finditer(r'@(\w+)(?:/(\d+))?', combined):
        ch, post_id = m.group(1), m.group(2)
        if ch not in valid_channels or ch in cited:
            continue
        cited[ch] = f"https://t.me/{ch}/{post_id}" if post_id else f"https://t.me/{ch}"
    return cited


def build_messages_by_channel(channels: list[str], counts: dict[str, int]) -> dict[str, int]:
    return {f"@{ch}": counts.get(ch, 0) for ch in channels if counts.get(ch, 0) > 0}


def _build_post_images(all_media: list[dict], media_dir: Path) -> dict[str, str]:
    post_images: dict[str, str] = {}
    for img in all_media:
        cdn = img.get("cdn_url")
        if not cdn:
            continue
        ch, pid = img["channel"], img["post_id"]
        m = re.search(r'\.(\w{2,4})(?:\?|$)', cdn)
        ext = m.group(1).lower() if m else "jpg"
        local_name = f"{ch}_{pid}.{ext}"
        dest = media_dir / local_name
        key = f"{ch}/{pid}"
        path_str = f"data/media/{local_name}"
        if dest.exists() or download_media(cdn, dest):
            post_images[key] = path_str
        # Create alias for the adjacent text post so AI citations resolve to this photo
        if key in post_images:
            companion = img.get("companion_text_id")
            if companion:
                ckey = f"{ch}/{companion}"
                if ckey not in post_images:
                    post_images[ckey] = path_str
    return post_images


def run() -> None:
    output_dir = Path("data")
    output_dir.mkdir(exist_ok=True)
    media_dir = output_dir / "media"
    media_dir.mkdir(exist_ok=True)

    failed_conflicts = []
    conflict_keys = list(CONFLICTS.keys())
    for i, key in enumerate(conflict_keys):
        conf = CONFLICTS[key]
        print(f"\n=== {conf['title']} ===", file=sys.stderr)
        try:
            _process_conflict(key, conf, output_dir, media_dir)
        except Exception as exc:
            print(f"  ERROR processing {key}: {exc}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            failed_conflicts.append(key)
        if i < len(conflict_keys) - 1:
            print("  Pausing 90s before next conflict to avoid rate limits...", file=sys.stderr)
            time.sleep(90)

    # Delete media files no longer referenced by any conflict's current output
    referenced: set[str] = set()
    for key in conflict_keys:
        json_path = output_dir / f"{key}.json"
        try:
            d = json.loads(json_path.read_text())
            referenced.update(d.get("post_images", {}).values())
        except Exception:
            pass
    cleanup_unreferenced_media(media_dir, referenced)

    if failed_conflicts:
        print(f"\nFailed conflicts: {failed_conflicts}", file=sys.stderr)
        if len(failed_conflicts) == len(CONFLICTS):
            sys.exit(1)  # All failed — hard fail so workflow retries
        print("Partial success — committing available data.", file=sys.stderr)

    print("\nDone.", flush=True)


def _process_conflict(key: str, conf: dict, output_dir: Path, media_dir: Path) -> None:
    per_channel_messages: dict[str, list[str]] = {}
    per_channel_timestamps: dict[str, list[datetime]] = {}
    per_channel_message_ids: dict[str, list[int | None]] = {}
    per_channel_counts: dict[str, int] = {}
    recent_post_urls: dict[str, str] = {}
    all_media: list[dict] = []

    for ch in conf["channels"]:
        print(f"  Fetching {ch}...", file=sys.stderr)
        msgs, times, ids, max_id, images = fetch_channel_messages_24h(ch)
        per_channel_messages[ch] = msgs
        per_channel_timestamps[ch] = times
        per_channel_message_ids[ch] = ids
        per_channel_counts[ch] = len(msgs)
        if max_id:
            recent_post_urls[ch] = f"https://t.me/{ch}/{max_id}"
        for img in images[:15]:  # cap per channel
            all_media.append({**img, "channel": ch})
        print(f"    -> {len(msgs)} messages, {len(images)} images", file=sys.stderr)

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

    cited_post_urls = _extract_cited_posts(ai_result, set(conf["channels"]))

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
        update_conflict_history(output_dir, "middle_east", {"red_alerts": red_alerts_raw})
        real_alert_timestamps = [ts for _, ts in real_pairs if ts is not None]
        alert_timeline = bucket_into_24h_slots(real_alert_timestamps) if real_alert_timestamps else [0] * 24

    else:  # ukraine
        # Always use dedicated fetch so attack summaries are sorted newest-first (by post ID)
        # and is_relevant() filtering doesn't drop short numeric daily summaries.
        # parse_attack_counts extracts both numbers from the SAME text to avoid mixing
        # totals from different attacks (e.g. yesterday's 690 total - today's 262 drones).
        print("  [kpszsu] doing dedicated fetch for missile/drone counts", file=sys.stderr)
        kpszsu_raw = fetch_kpszsu_all_texts("kpszsu")
        missiles, drones = parse_attack_counts(kpszsu_raw)
        red_alerts_raw = missiles + drones
        print(f"  [kpszsu] missiles={missiles} drones={drones} total={red_alerts_raw}", file=sys.stderr)
        update_conflict_history(output_dir, "ukraine", {"total": red_alerts_raw, "missiles": missiles, "drones": drones})
        # Count UAV events per eRadarrua post (each city direction = 1 event for accuracy)
        ua_alert_events = []
        ua_texts = per_channel_messages.get(alert_ch, [])
        ua_times = per_channel_timestamps.get(alert_ch, [])
        for text, ts in zip(ua_texts, ua_times):
            if ts is None:
                continue
            directions = len(re.findall(
                r'(?:UAV|drone|БПЛА|БпЛА)\w*\s+(?:on|to|near|over|in|heading|from)',
                text, re.IGNORECASE
            ))
            count = directions if directions > 0 else (
                1 if re.search(r'\bUAV\b|\bdrone\b|\bBPLA\b|\bБПЛА\b', text, re.IGNORECASE) else 0
            )
            ua_alert_events.extend([ts] * count)
        raw_timeline = bucket_into_24h_slots(ua_alert_events) if ua_alert_events else [0] * 24
        # Scale timeline so it reflects actual drone count (distribution proxy)
        tl_sum = sum(raw_timeline) or 1
        if drones > 0:
            alert_timeline = [round(v * drones / tl_sum) for v in raw_timeline]
        else:
            alert_timeline = raw_timeline

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
        "cited_post_urls": cited_post_urls,
        "media": sorted(all_media, key=lambda x: x.get("ts") or "", reverse=True)[:20],
        "post_images": _build_post_images(all_media, media_dir),
        **ai_result,
    }
    if key == "ukraine":
        output["missiles"] = missiles
        output["drones"] = drones
        output["kpszsu_timeline"] = bucket_into_24h_slots(per_channel_timestamps.get("kpszsu", []))

    path = output_dir / f"{key}.json"
    path.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"  Saved -> {path}", flush=True)


if __name__ == "__main__":
    run()
