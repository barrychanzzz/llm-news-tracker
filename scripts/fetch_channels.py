"""
LLM News Tracker — Channel Manager
Discovers, verifies, and maintains the list of monitored YouTube channels.
Uses yt-dlp for channel metadata and related channel discovery.
"""
import json
import subprocess
import sys
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

# Add parent to path for config import
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import SEED_CHANNELS, MIN_ACTIVE_SCORE, MIN_AVG_VIEWS

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")
VIDEOS_FILE = os.path.join(DATA_DIR, "videos.json")


def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_channel_id(url: str) -> Optional[str]:
    """Extract channel ID from a YouTube channel URL using yt-dlp."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--print", "channel_id", "--playlist-end", "1", url],
            capture_output=True, text=True, timeout=30,
        )
        channel_id = result.stdout.strip()
        if channel_id and not result.returncode:
            return channel_id
    except Exception as e:
        print(f"  [WARN] Failed to get channel ID for {url}: {e}")
    return None


def get_channel_metadata(channel_url: str) -> dict:
    """Get channel name, subscriber count, etc. using yt-dlp."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--playlist-end", "1", channel_url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            return {
                "name": data.get("channel", data.get("uploader", "")),
                "channel_id": data.get("channel_id", ""),
                "subscriber_count": data.get("channel_follower_count", 0),
            }
    except Exception as e:
        print(f"  [WARN] Failed to get metadata for {channel_url}: {e}")
    return {}


def get_recent_videos_rss(channel_id: str, days: int = 7) -> list:
    """Get recent videos via YouTube RSS feed."""
    import feedparser
    import requests
    rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    try:
        resp = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"},
                            timeout=30)
        feed = feedparser.parse(resp.text)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        recent = []
        for entry in feed.entries:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if published >= cutoff:
                recent.append(entry)
        return recent
    except Exception as e:
        print(f"  [WARN] RSS fetch failed for {channel_id}: {e}")
        return []


def get_related_channels(channel_url: str) -> list:
    """Attempt to get related/featured channels from a channel page."""
    related = []
    # Try the /channels tab
    try:
        result = subprocess.run(
            ["yt-dlp", "--flat-playlist", "--dump-json",
             f"{channel_url}/channels"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    related.append({
                        "channel_id": data.get("channel_id", ""),
                        "name": data.get("channel", data.get("title", "")),
                        "url": data.get("channel_url", data.get("url", "")),
                    })
                except json.JSONDecodeError:
                    pass
    except Exception as e:
        print(f"  [WARN] Related channels fetch failed: {e}")
    return related


def evaluate_channel(channel_id: str, channel_name: str, url: str) -> dict:
    """Evaluate a channel's activity and popularity."""
    recent = get_recent_videos_rss(channel_id, days=7)

    if not recent:
        return {"active_score": 0, "avg_views": 0, "should_add": False}

    # Count recent videos
    active_score = len(recent)

    # Estimate average views from video metadata in RSS
    # RSS doesn't include views directly; use yt-dlp for the first few
    total_views = 0
    view_count = 0
    for entry in recent[:5]:
        try:
            vid_url = entry.get("link", "")
            if vid_url:
                r = subprocess.run(
                    ["yt-dlp", "--print", "view_count", vid_url],
                    capture_output=True, text=True, timeout=15,
                )
                v = r.stdout.strip()
                if v and v.isdigit():
                    total_views += int(v)
                    view_count += 1
        except Exception:
            pass

    avg_views = total_views / view_count if view_count > 0 else 0

    return {
        "active_score": active_score,
        "avg_views": round(avg_views),
        "should_add": (active_score >= MIN_ACTIVE_SCORE
                       and avg_views >= MIN_AVG_VIEWS),
    }


def build_channel_entry(channel_id: str, name: str, url: str,
                        is_seed: bool = False) -> dict:
    """Build a standardized channel entry."""
    return {
        "channel_id": channel_id,
        "name": name,
        "url": url,
        "rss_url": f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
        "content_focus": "",
        "is_seed": is_seed,
        "active_score": 0,
        "added_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    print("=" * 60)
    print("LLM News Tracker — Channel Discovery")
    print("=" * 60)

    existing = load_json(CHANNELS_FILE)
    existing_ids = {ch["channel_id"] for ch in existing}

    channels = list(existing)  # Start with existing channels

    # Process seed channels
    print("\n[1/3] Processing seed channels...")
    for seed in SEED_CHANNELS:
        print(f"  Checking: {seed['name']} ({seed['handle']})")
        channel_id = get_channel_id(seed["url"])
        if not channel_id:
            print(f"  [SKIP] Could not resolve channel ID")
            continue

        if channel_id in existing_ids:
            print(f"  [OK] Already tracked")
            continue

        entry = build_channel_entry(
            channel_id, seed["name"], seed["url"], is_seed=True
        )
        channels.append(entry)
        existing_ids.add(channel_id)
        print(f"  [ADD] {seed['name']} (ID: {channel_id})")

    # Update activity scores for all channels
    print("\n[2/3] Updating channel activity scores...")
    for ch in channels:
        print(f"  Evaluating: {ch['name']}")
        recent = get_recent_videos_rss(ch["channel_id"], days=7)
        ch["active_score"] = len(recent)
        ch["updated_at"] = datetime.now(timezone.utc).isoformat()
        print(f"    Active score: {ch['active_score']} (videos in last 7 days)")

    # Discover related channels from seed channels
    print("\n[3/3] Discovering related channels...")
    seed_channels_in_list = [ch for ch in channels if ch.get("is_seed")]
    discovered = 0
    for seed_ch in seed_channels_in_list:
        print(f"  Checking related from: {seed_ch['name']}")
        related = get_related_channels(seed_ch["url"])
        if not related:
            print(f"    No related channels found")
            continue

        for rel in related[:5]:  # Limit to top 5 per seed
            rel_id = rel.get("channel_id", "")
            if not rel_id or rel_id in existing_ids:
                continue
            # Quick evaluation
            name = rel.get("name", "Unknown")
            url = rel.get("url", f"https://www.youtube.com/channel/{rel_id}")
            evaluation = evaluate_channel(rel_id, name, url)
            if evaluation["should_add"]:
                entry = build_channel_entry(rel_id, name, url)
                entry["active_score"] = evaluation["active_score"]
                channels.append(entry)
                existing_ids.add(rel_id)
                discovered += 1
                print(f"    [ADD] {name} (score: {evaluation['active_score']}, "
                      f"avg views: {evaluation['avg_views']})")

    # Save
    save_json(CHANNELS_FILE, channels)
    print(f"\n{'=' * 60}")
    print(f"DONE: {len(channels)} channels tracked "
          f"({len([c for c in channels if c.get('is_seed')])} seed, "
          f"{discovered} new discovered)")
    print(f"Data saved to: {CHANNELS_FILE}")


if __name__ == "__main__":
    main()
