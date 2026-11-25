#!/usr/bin/env python3
"""
纯分析重跑 — 只重算 analysis 字段，不下载字幕、不改播放量、不调 API
用于关键词表升级后立即刷新全库分析结果
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "scripts"))
from analysis_utils import rule_based_analysis

VIDEOS_FILE = os.path.join(BASE, "data", "videos.json")


def main():
    with open(VIDEOS_FILE) as f:
        videos = json.load(f)

    before_other = sum(1 for v in videos if v.get("analysis", {}).get("topics") == ["Other"])
    before_unknown = sum(1 for v in videos if v.get("analysis", {}).get("speaker") == "Unknown")

    # 对所有 fallback 分析（或空分析）重新生成
    updated = 0
    for v in videos:
        a = v.get("analysis") or {}
        # 保留真实的 Gemini 分析结果（非 fallback 且有摘要）
        if a and not a.get("_fallback") and a.get("summary") and not a["summary"].startswith("No transcript"):
            continue
        v["analysis"] = rule_based_analysis(
            v.get("title", ""), v.get("channel_name", ""), v.get("description", "")
        )
        v["analyzed"] = True
        updated += 1

    with open(VIDEOS_FILE, "w") as f:
        json.dump(videos, f, indent=2, ensure_ascii=False)

    after_other = sum(1 for v in videos if v.get("analysis", {}).get("topics") == ["Other"])
    after_unknown = sum(1 for v in videos if v.get("analysis", {}).get("speaker") == "Unknown")

    print(f"重新分析: {updated}/{len(videos)} 个视频")
    print(f"Other 标签: {before_other} → {after_other}")
    print(f"Unknown 主讲: {before_unknown} → {after_unknown}")


if __name__ == "__main__":
    main()
