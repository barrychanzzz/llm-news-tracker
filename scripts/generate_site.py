"""
LLM News Tracker — Static Site Generator
Generates the static HTML page for GitHub Pages deployment.
Injects JSON data into the HTML template.
"""
import json
import os
import sys
import shutil
from datetime import datetime, timezone

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
SITE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "docs")

VIDEOS_FILE = os.path.join(DATA_DIR, "videos.json")
CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")
RELATIONS_FILE = os.path.join(DATA_DIR, "channel_relations.json")


def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []


def main():
    print("=" * 60)
    print("LLM News Tracker — Site Generator")
    print("=" * 60)

    videos = load_json(VIDEOS_FILE)
    channels = load_json(CHANNELS_FILE)
    relations = load_json(RELATIONS_FILE)

    # Strip large fields not needed for display
    for v in videos:
        v.pop("raw_transcript", None)
        v.pop("description", None)

    # Prepare data payload
    data_payload = {
        "videos": videos,
        "channels": channels,
        "relations": relations,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_videos": len(videos),
        "total_channels": len(channels),
    }

    data_json = json.dumps(data_payload, ensure_ascii=False)

    # Read the HTML template
    html_path = os.path.join(SITE_DIR, "index.html")
    with open(html_path, "r") as f:
        html = f.read()

    # Inject data into the HTML
    # Replace the placeholder with actual data
    html = html.replace(
        'const DATA_PLACEHOLDER = null;',
        f'const APP_DATA = {data_json};'
    )

    # Write the final HTML (to site/index.html)
    with open(html_path, "w") as f:
        f.write(html)

    print(f"Injected {len(videos)} videos, {len(channels)} channels, "
          f"{len(relations)} relations")
    print(f"Generated: {html_path}")
    print("Ready for GitHub Pages deployment.")


if __name__ == "__main__":
    main()
