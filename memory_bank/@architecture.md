# LLM News Tracker — Architecture

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions (每12h)                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Channels │→│  Videos  │→│ Analyze  │→│ Generate │   │
│  │  Fetch   │  │  Fetch   │  │ (Gemini) │  │  Site    │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│       │              │              │              │         │
│       ▼              ▼              ▼              ▼         │
│  channels.json  videos.json   videos.json    docs/index.html│
│                                                             │
│                          ┌──────────┐                       │
│                          │ Relations│                       │
│                          │ Analyze  │                       │
│                          └──────────┘                       │
│                               │                             │
│                               ▼                             │
│                      channel_relations.json                 │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Pages (docs/)                      │
│  ┌──────────────────────────────────────────────────────┐   │
│  │ index.html (含内嵌 data JSON)                          │   │
│  │  ├── style.css (暗色/亮色主题, 响应式)                │   │
│  │  └── app.js (表格渲染, 搜索, 筛选, 频道关联)         │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Data Flow

```
YouTube RSS Feed ──→ feedparser ──→ videos.json (metadata)
                                         │
YouTube yt-dlp ────→ auto subs (VTT) ────┤
                                         ▼
                                  videos.json (with transcripts)
                                         │
Gemini 2.5 Flash API ────────────────────┤
                                         ▼
                                  videos.json (with analysis)
                                         │
                                  ┌──────┴──────┐
                                  ▼              ▼
                           generate_site.py  analyze_relations.py
                                  │              │
                                  ▼              ▼
                           docs/index.html  channel_relations.json
                                  │
                                  ▼
                           GitHub Pages 部署
```

## Key Design Decisions

### 1. 零 API Key 视频抓取
- YouTube RSS Feed (公开, 无需 Key) 用于获取视频列表
- yt-dlp `--write-auto-subs` 获取自动生成字幕 (无需 Key)
- 仅 Gemini API 需要一个免费 Key

### 2. docs/ 而非 site/
- GitHub Pages 分支部署只支持 `/` 或 `/docs`
- 选择 `/docs` 保持源码和部署文件分离

### 3. 数据内嵌而非 API
- 所有 JSON 数据直接内嵌在 `index.html` 的 `<script>` 标签中
- 零服务器成本, 无 API 调用, 页面加载即展示

### 4. requests + feedparser 组合
- macOS Python 3.13 SSL 证书问题导致 feedparser 内置 HTTP 客户端失败
- 改用 `requests` 库获取 RSS 内容, 再传给 feedparser 解析

### 5. google-genai SDK (非 google-generativeai)
- 旧 SDK (google-generativeai) 已停止维护
- 新 SDK (google-genai) 使用 `gemini-2.5-flash` 模型

## File Responsibilities

| 文件 | 职责 |
|------|------|
| `scripts/config.py` | 种子频道定义, 主题分类体系, 配置常量 |
| `scripts/fetch_channels.py` | 频道发现, 验证, 活跃度评分 |
| `scripts/fetch_videos.py` | RSS 视频抓取, yt-dlp 字幕下载, VTT 解析 |
| `scripts/analyze_videos.py` | Gemini AI 内容分析, 主题分类, 摘要生成 |
| `scripts/analyze_relations.py` | 频道间 Jaccard 相似度计算, Gemini 关联分析 |
| `scripts/generate_site.py` | JSON 数据注入 HTML, 生成静态页面 |
| `docs/index.html` | HTML 模板 + 内嵌数据 |
| `docs/app.js` | 表格渲染, 搜索/筛选, 频道关联展示 |
| `docs/style.css` | 响应式样式, 暗色/亮色主题 |
