"""
LLM News Tracker — Channel Relation Analyzer
Analyzes relationships between channels:
- Topic overlap (Jaccard similarity)
- Content focus per channel (via Gemini)
- Complementary/contrasting relationships
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import GEMINI_MODEL

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
VIDEOS_FILE = os.path.join(DATA_DIR, "videos.json")
CHANNELS_FILE = os.path.join(DATA_DIR, "channels.json")
RELATIONS_FILE = os.path.join(DATA_DIR, "channel_relations.json")


def load_json(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return []


def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def jaccard_similarity(set_a: set, set_b: set) -> float:
    """Calculate Jaccard similarity between two sets."""
    if not set_a or not set_b:
        return 0.0
    intersection = len(set_a & set_b)
    union = len(set_a | set_b)
    return intersection / union if union > 0 else 0.0


def get_channel_topic_distribution(videos: list, channel_id: str) -> Counter:
    """Get topic distribution for a channel based on analyzed videos."""
    topics = Counter()
    for v in videos:
        if v.get("channel_id") == channel_id and v.get("analysis"):
            for topic in v["analysis"].get("topics", []):
                if topic != "Other":
                    topics[topic] += 1
    return topics


def get_channel_sample_summaries(videos: list, channel_id: str,
                                 count: int = 5) -> list:
    """Get representative video summaries for a channel."""
    channel_videos = [
        v for v in videos
        if v.get("channel_id") == channel_id and v.get("analysis")
    ]
    channel_videos.sort(key=lambda v: v.get("view_count", 0), reverse=True)
    return [
        {
            "title": v["title"],
            "summary": v["analysis"].get("summary", ""),
            "view_count": v.get("view_count", 0),
        }
        for v in channel_videos[:count]
    ]


def analyze_channel_focus(api_key: str, channel_name: str,
                          topic_dist: Counter,
                          sample_summaries: list) -> str:
    """Use Gemini to generate a content focus description for a channel."""
    from google import genai

    client = genai.Client(api_key=api_key)

    topics_str = ", ".join(
        f"{topic}({count})" for topic, count in topic_dist.most_common(5)
    )
    summaries_str = "\n".join(
        f"- {s['title']}: {s['summary'][:100]}"
        for s in sample_summaries[:3]
    )

    prompt = f"""Analyze this YouTube channel's content focus on LLM topics.

Channel: {channel_name}
Topic distribution (topic: video count): {topics_str}
Sample video summaries:
{summaries_str}

Write a concise description (2-3 sentences, in Chinese) summarizing:
1. What LLM topics this channel primarily covers
2. The channel's unique angle or approach
3. Who would benefit most from watching this channel

Return ONLY the description text, no JSON, no markdown."""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        return response.text.strip()[:300]
    except Exception as e:
        print(f"    [WARN] Focus analysis failed: {e}")
        top_topic = topic_dist.most_common(1)
        if top_topic:
            return f"主要关注{top_topic[0][0]}相关内容"
        return "LLM 综合频道"


def analyze_channel_relation(api_key: str, ch_a: dict, ch_b: dict,
                             samples_a: list, samples_b: list,
                             similarity: float) -> dict:
    """Use Gemini to analyze the relationship between two channels."""
    from google import genai

    client = genai.Client(api_key=api_key)

    summaries_a = "\n".join(
        f"- {s['title']}: {s['summary'][:100]}"
        for s in samples_a[:2]
    )
    summaries_b = "\n".join(
        f"- {s['title']}: {s['summary'][:100]}"
        for s in samples_b[:2]
    )

    prompt = f"""Analyze the relationship between two YouTube channels covering LLM/AI topics.

Channel A: {ch_a['name']}
Content focus: {ch_a.get('content_focus', 'N/A')}
Sample content:
{summaries_a}

Channel B: {ch_b['name']}
Content focus: {ch_b.get('content_focus', 'N/A')}
Sample content:
{summaries_b}

Topic overlap (Jaccard): {similarity:.2f}

Return ONLY a JSON object (no markdown, no code fences):
{{
  "relation_type": "complementary/contrasting/referencing",
  "description": "One sentence in Chinese describing how these channels relate. E.g., 'A侧重工程实现，B提供理论对比，两者互补'"
}}

- "complementary": they cover different aspects of the same topic
- "contrasting": they have opposing views or different approaches
- "referencing": one channel frequently cites or discusses the other's work
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
        return json.loads(text)
    except Exception as e:
        print(f"    [WARN] Relation analysis failed: {e}")
        if similarity > 0.3:
            return {
                "relation_type": "complementary",
                "description": f"两者在{similarity:.0%}的LLM主题上有重叠"
            }
        return {
            "relation_type": "complementary",
            "description": "两个频道都在LLM领域，但侧重不同"
        }


def main():
    print("=" * 60)
    print("LLM News Tracker — Channel Relation Analyzer")
    print("=" * 60)

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        sys.exit(1)

    channels = load_json(CHANNELS_FILE)
    videos = load_json(VIDEOS_FILE)

    if not channels:
        print("No channels found. Run fetch_channels.py first.")
        return

    # Step 1: Calculate topic distributions
    print("\n[1/3] Calculating topic distributions...")
    channel_topics = {}
    for ch in channels:
        dist = get_channel_topic_distribution(videos, ch["channel_id"])
        channel_topics[ch["channel_id"]] = dist
        top = dist.most_common(3)
        top_str = ", ".join(f"{t}({c})" for t, c in top) if top else "No data"
        print(f"  {ch['name']}: {top_str}")

    # Step 2: Generate content focus for each channel
    print("\n[2/3] Generating channel content focus...")
    for ch in channels:
        ch_id = ch["channel_id"]
        dist = channel_topics.get(ch_id, Counter())
        samples = get_channel_sample_summaries(videos, ch_id)
        if not dist and not samples:
            ch["content_focus"] = "新频道，暂无足够数据"
            continue

        print(f"  Analyzing: {ch['name']}...")
        focus = analyze_channel_focus(api_key, ch["name"], dist, samples)
        ch["content_focus"] = focus
        print(f"    → {focus[:100]}...")
        time.sleep(2)  # Rate limit

    save_json(CHANNELS_FILE, channels)

    # Step 3: Analyze pairwise channel relations
    print("\n[3/3] Analyzing channel relationships...")
    relations = []
    for i, ch_a in enumerate(channels):
        for ch_b in channels[i + 1:]:
            a_topics = set(channel_topics.get(ch_a["channel_id"], Counter()).keys())
            b_topics = set(channel_topics.get(ch_b["channel_id"], Counter()).keys())
            similarity = jaccard_similarity(a_topics, b_topics)

            if similarity == 0 and not a_topics and not b_topics:
                continue  # Skip if no data for either channel

            samples_a = get_channel_sample_summaries(videos, ch_a["channel_id"])
            samples_b = get_channel_sample_summaries(videos, ch_b["channel_id"])

            print(f"  {ch_a['name']} ↔ {ch_b['name']} (overlap: {similarity:.0%})")

            relation = analyze_channel_relation(
                api_key, ch_a, ch_b, samples_a, samples_b, similarity
            )
            relations.append({
                "channel_a_id": ch_a["channel_id"],
                "channel_a_name": ch_a["name"],
                "channel_b_id": ch_b["channel_id"],
                "channel_b_name": ch_b["name"],
                "topic_overlap": round(similarity, 3),
                "relation_type": relation.get("relation_type", "complementary"),
                "description": relation.get("description", ""),
                "generated_at": datetime.now(timezone.utc).isoformat(),
            })
            print(f"    → {relation.get('description', '')[:80]}...")
            time.sleep(2)  # Rate limit

    save_json(RELATIONS_FILE, relations)

    print(f"\n{'=' * 60}")
    print(f"DONE: {len(channels)} channels analyzed, "
          f"{len(relations)} relationships mapped")
    print(f"Data saved to: {CHANNELS_FILE}, {RELATIONS_FILE}")


if __name__ == "__main__":
    main()
