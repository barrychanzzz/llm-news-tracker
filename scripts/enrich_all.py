#!/usr/bin/env python3
"""
数据补齐脚本（并发版）— 在本地环境运行（CI 环境被 YouTube 封锁）
为所有视频补齐：字幕、播放量、分析
"""
import json
import os
import sys
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from analysis_utils import rule_based_analysis

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEOS_FILE = os.path.join(BASE, "data", "videos.json")


def fetch_subs(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        t = api.fetch(video_id)
        text = " ".join(s.text for s in t).strip()
        return text if len(text) > 50 else ""
    except Exception:
        return ""


def fetch_meta(url):
    try:
        r = subprocess.run(
            ["yt-dlp", "--dump-json", "--no-playlist", "--no-check-certificate",
             "--extractor-args", "youtube:player_client=web", url],
            capture_output=True, text=True, timeout=20,
        )
        if r.returncode == 0 and r.stdout.strip():
            d = json.loads(r.stdout.strip())
            return d.get("view_count", 0) or 0, d.get("duration", 0) or 0, d.get("duration_string", "")
    except Exception:
        pass
    return 0, 0, ""


def enrich_one(v):
    """补齐单个视频，返回是否有更新"""
    changed = False
    # 1. 字幕
    if not v.get("raw_transcript") or len(v.get("raw_transcript", "")) < 50:
        text = fetch_subs(v["video_id"])
        if text:
            v["raw_transcript"] = text
            v["has_captions"] = True
            v["analyzed"] = False
            changed = True
    # 2. 播放量
    if not v.get("view_count", 0):
        vc, dur, ds = fetch_meta(v["url"])
        if vc:
            v["view_count"] = vc
            v["duration"] = dur
            v["duration_string"] = ds
            changed = True
    # 3. 分析兜底
    a = v.get("analysis") or {}
    summary = a.get("summary", "")
    if (not summary) or summary.startswith("No transcript") or a.get("_fallback") or (not v.get("analyzed") and not v.get("raw_transcript")):
        v["analysis"] = rule_based_analysis(v.get("title", ""), v.get("channel_name", ""), v.get("description", ""))
        v["analyzed"] = True
        changed = True
    return changed


def main():
    with open(VIDEOS_FILE) as f:
        videos = json.load(f)

    total = len(videos)
    print(f"处理 {total} 个视频（并发 12 线程）...", flush=True)

    # 分批并发处理，每批保存
    batch_size = 40
    for start in range(0, total, batch_size):
        batch = videos[start:start + batch_size]
        with ThreadPoolExecutor(max_workers=12) as ex:
            futures = {ex.submit(enrich_one, v): v for v in batch}
            for fut in as_completed(futures):
                try:
                    fut.result()
                except Exception as e:
                    print(f"  [WARN] {e}", flush=True)
        # 每批保存一次
        with open(VIDEOS_FILE, "w") as f:
            json.dump(videos, f, indent=2, ensure_ascii=False)
        print(f"  进度 {min(start + batch_size, total)}/{total}", flush=True)

    print("\n完成!", flush=True)
    print(f"字幕覆盖: {sum(1 for v in videos if v.get('raw_transcript') and len(v['raw_transcript'])>50)}/{total}", flush=True)
    print(f"播放量覆盖: {sum(1 for v in videos if v.get('view_count',0)>0)}/{total}", flush=True)
    print(f"有摘要: {sum(1 for v in videos if v.get('analysis',{}).get('summary'))}/{total}", flush=True)
    print(f"有主题标签: {sum(1 for v in videos if v.get('analysis',{}).get('topics') and v['analysis']['topics']!=['Other'])}/{total}", flush=True)


if __name__ == "__main__":
    main()
