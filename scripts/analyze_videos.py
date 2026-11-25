"""
LLM News Tracker — AI Content Analyzer
Uses Google Gemini API to analyze video transcripts:
- Topic classification
- Content summary (Chinese, 150 chars)
- Speaker identification
- Technical depth assessment
"""
import json
import os
import sys
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import (
    TOPIC_TAXONOMY, TECHNICAL_LEVELS, MAX_TRANSCRIPT_CHARS, GEMINI_MODEL,
)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
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


def build_analysis_prompt(transcript: str, title: str, channel_name: str) -> str:
    """Build the prompt for Gemini analysis."""
    topics_str = ", ".join(TOPIC_TAXONOMY)
    levels_str = ", ".join(TECHNICAL_LEVELS)

    prompt = f"""You are an AI content analyst specializing in LLM (Large Language Model) topics.

Analyze the following YouTube video transcript and provide a structured analysis.

Video Title: {title}
Channel: {channel_name}

Transcript (excerpt):
---
{transcript}
---

Please analyze this content and return ONLY a valid JSON object (no markdown, no code fences) with these fields:

{{
  "summary": "A concise Chinese summary of what this video actually discusses (max 150 Chinese characters). Base this on the transcript content, not just the title.",
  "topics": ["Topic1", "Topic2"],
  "speaker": "The name of the main speaker/presenter (or 'Unknown' if not identifiable)",
  "technical_level": "Beginner/Intermediate/Advanced"
}}

Rules:
- "topics" must be chosen from: {topics_str}. Select 1-3 most relevant topics.
- "technical_level" must be one of: {levels_str}.
- If the transcript is unrelated to LLMs, set topics to ["Other"] and summary to "Non-LLM content".
- Return ONLY the JSON object, no explanation."""
    return prompt


def analyze_with_gemini(api_key: str, transcript: str,
                        title: str, channel_name: str) -> dict:
    """Send transcript to Gemini API and get structured analysis."""
    from google import genai

    client = genai.Client(api_key=api_key)
    prompt = build_analysis_prompt(transcript, title, channel_name)

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
        )

        text = response.text.strip()

        # Remove markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])

        result = json.loads(text)

        # Validate required fields
        return {
            "summary": str(result.get("summary", ""))[:150],
            "topics": result.get("topics", ["Other"]),
            "speaker": str(result.get("speaker", "Unknown")),
            "technical_level": str(result.get("technical_level", "Intermediate")),
        }
    except json.JSONDecodeError as e:
        print(f"    [WARN] JSON parse failed: {e}")
        print(f"    Raw response: {text[:200]}...")
        return None
    except Exception as e:
        print(f"    [ERROR] Gemini API call failed: {e}")
        return None


def main():
    print("=" * 60)
    print("LLM News Tracker — AI Content Analyzer (Gemini)")
    print("=" * 60)

    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        print("ERROR: GEMINI_API_KEY environment variable not set.")
        print("  Run: export GEMINI_API_KEY=your_key_here")
        sys.exit(1)

    videos = load_json(VIDEOS_FILE)
    if not videos:
        print("No videos found. Run fetch_videos.py first.")
        return

    # Find videos that need analysis (including fallback rule-based ones)
    to_analyze = [
        v for v in videos
        if v.get("raw_transcript") and (
            not v.get("analyzed", False) or
            v.get("analysis", {}).get("_fallback", False)
        )
    ]
    # Also include videos without transcripts (mark as no-analysis)
    no_transcript = [
        v for v in videos
        if not v.get("raw_transcript") and not v.get("analyzed", False)
    ]

    print(f"Videos to analyze: {len(to_analyze)} (with transcripts)")
    print(f"Videos without transcripts: {len(no_transcript)}")
    print()

    # 无字幕视频：立即用规则兜底，绝不产生 "No transcript available" 空壳
    from analysis_utils import rule_based_analysis
    for v in no_transcript:
        if not v.get("no_subtitle_count"):
            v["no_subtitle_count"] = 0
        v["no_subtitle_count"] += 1
        v["has_captions"] = False
        a = v.get("analysis") or {}
        # 总是用元数据兜底，保证有标签/摘要/主讲人/深度
        v["analysis"] = rule_based_analysis(
            v.get("title", ""), v.get("channel_name", ""), v.get("description", "")
        )
        v["analyzed"] = True

    # Analyze videos with transcripts
    success = 0
    failed = 0
    # Gemini free tier: 5 RPM, 20 RPD. Sleep 15s for safety.
    for i, video in enumerate(to_analyze):
        title = video.get("title", "Unknown")[:80]
        channel = video.get("channel_name", "Unknown")
        transcript = video.get("raw_transcript", "")

        print(f"[{i + 1}/{len(to_analyze)}] {title}...")
        print(f"  Channel: {channel}")
        print(f"  Transcript: {len(transcript)} chars")

        # Truncate transcript for API
        truncated = transcript[:MAX_TRANSCRIPT_CHARS]
        print(f"  Sending {len(truncated)} chars to Gemini...")

        # Retry up to 3 times with backoff
        result = None
        for retry in range(3):
            result = analyze_with_gemini(api_key, truncated, title, channel)
            if result:
                break
            if retry < 2:
                wait = (retry + 1) * 15
                print(f"    [RETRY] Waiting {wait}s...")
                time.sleep(wait)

        if result:
            video["analyzed"] = True
            video["analysis"] = {
                **result,
                "analyzed_at": datetime.now(timezone.utc).isoformat(),
            }
            print(f"  [OK] Topics: {result['topics']}, "
                  f"Speaker: {result['speaker']}, "
                  f"Level: {result['technical_level']}")
            success += 1
        else:
            # Gemini 全部失败 → 规则兜底，保证不留空壳
            from analysis_utils import rule_based_analysis
            video["analyzed"] = True
            video["analysis"] = rule_based_analysis(
                video.get("title", ""), channel, video.get("description", "")
            )
            failed += 1
            print(f"  [FALLBACK] Gemini failed, used rule-based analysis")

        # Rate limit: Gemini free tier allows 5 RPM
        if i < len(to_analyze) - 1:
            time.sleep(15)  # ~4 requests per minute (safe margin)

    # Save updated videos
    save_json(VIDEOS_FILE, videos)

    print(f"\n{'=' * 60}")
    print(f"DONE: {success} analyzed, {failed} failed, "
          f"{len(no_transcript)} skipped (no transcript)")
    print(f"Data saved to: {VIDEOS_FILE}")


if __name__ == "__main__":
    main()
