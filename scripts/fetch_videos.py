"""
LLM News Tracker — Video Fetcher
Fetches new videos from monitored channels via RSS,
downloads auto-generated subtitles via yt-dlp.
"""
import json
import subprocess
import sys
import os
import tempfile
from datetime import datetime, timedelta, timezone
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import RETENTION_DAYS

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


def fetch_rss_videos(rss_url: str, days: int = 30) -> list:
    """Fetch recent videos from a YouTube RSS feed."""
    import feedparser
    import requests
    try:
        resp = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"},
                            timeout=30)
        feed = feedparser.parse(resp.text)
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        videos = []
        for entry in feed.entries:
            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if published < cutoff:
                continue

            video_id = entry.get("yt_videoid", "")
            if not video_id and "link" in entry:
                # Extract video ID from URL
                link = entry["link"]
                if "v=" in link:
                    video_id = link.split("v=")[-1].split("&")[0]

            videos.append({
                "video_id": video_id,
                "title": entry.get("title", ""),
                "url": entry.get("link", ""),
                "published_at": published.isoformat(),
                "description": entry.get("summary", "")[:500],
            })
        return videos
    except Exception as e:
        print(f"  [WARN] RSS fetch failed: {e}")
        return []


def get_video_metadata(video_url: str) -> dict:
    """Get view count, duration, and other metadata via yt-dlp."""
    try:
        result = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-playlist", video_url],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            data = json.loads(result.stdout.strip())
            return {
                "view_count": data.get("view_count", 0) or 0,
                "duration": data.get("duration", 0) or 0,
                "duration_string": data.get("duration_string", ""),
            }
    except Exception as e:
        print(f"    [WARN] Metadata fetch failed: {e}")
    return {"view_count": 0, "duration": 0, "duration_string": ""}


def download_subtitles(video_url: str) -> tuple:
    """Download auto-generated English subtitles using yt-dlp.
    Returns (transcript_text, has_captions).
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            result = subprocess.run(
                [
                    "yt-dlp",
                    "--write-auto-subs",
                    "--sub-lang", "en",
                    "--skip-download",
                    "--convert-subs", "vtt",
                    "--output", f"{tmpdir}/%(id)s",
                    "--no-warnings",
                    video_url,
                ],
                capture_output=True, text=True, timeout=60,
            )

            # Look for VTT subtitle file
            for fname in os.listdir(tmpdir):
                if fname.endswith(".en.vtt"):
                    filepath = os.path.join(tmpdir, fname)
                    text = parse_vtt(filepath)
                    if text.strip():
                        return text.strip(), True
        except subprocess.TimeoutExpired:
            print(f"    [WARN] Subtitle download timed out")
        except Exception as e:
            print(f"    [WARN] Subtitle download failed: {e}")

    return "", False


def parse_vtt(filepath: str) -> str:
    """Parse VTT subtitle file and extract plain text."""
    lines = []
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()

        # Remove VTT header
        if content.startswith("WEBVTT"):
            content = content.split("\n", 1)[-1] if "\n" in content else ""

        for line in content.split("\n"):
            line = line.strip()
            # Skip cue timing lines, numbers, and empty lines
            if not line:
                continue
            if "-->" in line:
                continue
            if line.isdigit():
                continue
            if line.startswith("Kind:") or line.startswith("Language:"):
                continue
            # Remove VTT tags like <c> <00:00:01.234>
            import re
            line = re.sub(r'<[^>]+>', '', line)
            line = line.strip()
            if line:
                lines.append(line)

        # Deduplicate consecutive identical lines
        deduped = []
        for line in lines:
            if not deduped or line != deduped[-1]:
                deduped.append(line)

        return " ".join(deduped)
    except Exception as e:
        print(f"    [WARN] VTT parsing failed: {e}")
        return ""


def clean_old_videos(videos: list):
    """Remove videos older than retention period."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    return [
        v for v in videos
        if datetime.fromisoformat(v["published_at"]) >= cutoff
    ]


def main():
    print("=" * 60)
    print("LLM News Tracker — Video Fetcher")
    print("=" * 60)

    channels = load_json(CHANNELS_FILE)
    if not channels:
        print("ERROR: No channels found. Run fetch_channels.py first.")
        sys.exit(1)

    existing_videos = load_json(VIDEOS_FILE)
    existing_ids = {v["video_id"] for v in existing_videos}

    total_new = 0
    total_subtitles = 0

    for ch in channels:
        ch_name = ch["name"]
        ch_id = ch["channel_id"]
        rss_url = ch.get("rss_url", "")
        if not rss_url:
            continue

        print(f"\n[{ch_name}]")
        print(f"  Fetching RSS: {rss_url}")

        rss_videos = fetch_rss_videos(rss_url)
        print(f"  Found {len(rss_videos)} videos in last 30 days")

        for vid in rss_videos:
            vid_id = vid["video_id"]
            if vid_id in existing_ids:
                continue

            print(f"  [NEW] {vid['title'][:70]}...")

            # Get metadata
            meta = get_video_metadata(vid["url"])

            # Download subtitles
            print(f"    Downloading subtitles...")
            transcript, has_captions = download_subtitles(vid["url"])

            entry = {
                "video_id": vid_id,
                "channel_id": ch_id,
                "channel_name": ch_name,
                "title": vid["title"],
                "url": vid["url"],
                "published_at": vid["published_at"],
                "view_count": meta["view_count"],
                "duration": meta["duration"],
                "duration_string": meta.get("duration_string", ""),
                "description": vid.get("description", ""),
                "has_captions": has_captions,
                "raw_transcript": transcript,
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "analyzed": False,
            }
            existing_videos.append(entry)
            existing_ids.add(vid_id)
            total_new += 1
            if has_captions:
                total_subtitles += 1

            print(f"    Views: {meta['view_count']:,}, "
                  f"Captions: {'Yes' if has_captions else 'No'}, "
                  f"Transcript: {len(transcript)} chars")

    # Clean old videos
    existing_videos = clean_old_videos(existing_videos)

    # Sort by publish date (newest first)
    existing_videos.sort(key=lambda v: v["published_at"], reverse=True)

    save_json(VIDEOS_FILE, existing_videos)
    print(f"\n{'=' * 60}")
    print(f"DONE: {total_new} new videos ({total_subtitles} with subtitles)")
    print(f"Total videos in DB: {len(existing_videos)}")
    print(f"Data saved to: {VIDEOS_FILE}")


if __name__ == "__main__":
    main()
