#!/bin/bash
# LLM News Tracker - 本地数据补充脚本
# 用于在 GitHub Actions 无法下载字幕时手动运行
# 使用方法: bash scripts/local_fix.sh

set -e

cd "$(dirname "$0")/.."

echo "=== LLM News Tracker - 本地数据修复 ==="

# 拉取最新数据
git pull

# 下载缺失字幕 + 更新播放量
python3 -c "
import json, time, subprocess
from youtube_transcript_api import YouTubeTranscriptApi

with open('data/videos.json') as f:
    videos = json.load(f)

api = YouTubeTranscriptApi()
sub_fixed = 0
view_fixed = 0

for v in videos:
    # 修复字幕
    if not v.get('raw_transcript') or len(v.get('raw_transcript', '')) < 50:
        try:
            transcript = api.fetch(v['video_id'])
            segments = list(transcript)
            text = ' '.join(s.text for s in segments)
            if text and len(text) > 50:
                v['raw_transcript'] = text
                v['has_captions'] = True
                v['analyzed'] = False
                v['subtitle_retries'] = 0
                sub_fixed += 1
                print(f'  ✅ 字幕: {v[\"title\"][:40]}...')
        except Exception as e:
            pass
        time.sleep(1)
    
    # 修复播放量
    if v.get('view_count', 0) == 0:
        try:
            result = subprocess.run(
                ['yt-dlp', '--dump-json', '--no-playlist', '--no-check-certificate',
                 '--extractor-args', 'youtube:player_client=web',
                 v['url']],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                data = json.loads(result.stdout.strip())
                vc = data.get('view_count', 0) or 0
                if vc > 0:
                    v['view_count'] = int(vc)
                    view_fixed += 1
        except:
            pass

with open('data/videos.json', 'w') as f:
    json.dump(videos, f, indent=2, ensure_ascii=False)

print(f'字幕修复: {sub_fixed}, 播放量修复: {view_fixed}')
"

# 重新生成页面
python3 scripts/generate_site.py

# 提交并推送
git add data/ docs/index.html
git diff --staged --quiet || git commit -m "Local data fix: subtitles + view counts"
git push

echo "=== 完成 ==="
