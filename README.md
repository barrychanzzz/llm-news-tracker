# 🧠 LLM News Tracker

自动监控 YouTube LLM 频道的智能聚合器。AI 驱动字幕分析，真实内容摘要，公开在线表格。

**🔗 在线页面**: [https://barrychanzzz.github.io/llm-news-tracker/](https://barrychanzzz.github.io/llm-news-tracker/)

## 监控频道

| 频道 | 侧重 |
|------|------|
| Andrej Karpathy | 从零实现、LLM 原理深度解析 |
| AI Explained | AI 新闻、基准评测、行业动态 |
| Yannic Kilcher | ML 论文解读、技术深度分析 |
| Sam Witteveen | LLM 实践教程、工具使用 |
| Two Minute Papers | AI 研究速览、最新突破 |
| AI Jason | AI 编码、Agent 开发 |
| Prompt Engineering | Prompt 技巧、RAG、Agent |
| Machine Learning Street Talk | 学术讨论、深度访谈 |
| David Shapiro | AGI、对齐、后劳动经济学 |

## 功能特性

- 📡 **自动抓取** — YouTube RSS 监控，每 12 小时检查新视频
- 🎙️ **字幕下载** — yt-dlp 自动下载英文自动生成字幕
- 🤖 **AI 分析** — Gemini 2.5 Flash 对字幕做主题分类、内容摘要（中文）、主讲人识别
- 📊 **多维表格** — 频道、标题、发布时间、播放量、主题标签、AI 摘要、主讲人、技术深度
- 🔍 **搜索筛选** — 关键词搜索 + 主题标签筛选 + 频道筛选
- 🔗 **频道关联** — 分析频道间的内容侧重和互补关系
- 🌙 **暗色模式** — 自动跟随系统主题

## 技术栈

- **数据管道**: Python 3.11 + yt-dlp + feedparser + requests
- **AI 分析**: Google Gemini 2.5 Flash (免费额度)
- **前端**: 纯 HTML/CSS/JS (零框架)
- **部署**: GitHub Pages + GitHub Actions
- **数据存储**: JSON 文件 (Git 仓库内)

## 本地运行

```bash
# 安装依赖
pip install -r requirements.txt

# 设置 API Key
export GEMINI_API_KEY=your_gemini_api_key

# 运行数据管道
python3 scripts/fetch_channels.py   # 频道发现
python3 scripts/fetch_videos.py     # 视频抓取
python3 scripts/analyze_videos.py   # AI 分析
python3 scripts/analyze_relations.py # 频道关联
python3 scripts/generate_site.py    # 生成页面

# 本地预览
python3 -m http.server 8000 -d docs/
# 打开 http://localhost:8000
```

## 添加新频道

编辑 `scripts/config.py`，在 `SEED_CHANNELS` 列表中添加：

```python
{
    "name": "频道名称",
    "url": "https://www.youtube.com/@频道handle",
    "handle": "@频道handle",
}
```

## 项目结构

```
llm-news-tracker/
├── .github/workflows/update.yml    # CI/CD 定时任务
├── scripts/
│   ├── config.py                   # 频道配置 & 主题定义
│   ├── fetch_channels.py           # 频道发现
│   ├── fetch_videos.py             # 视频抓取 & 字幕下载
│   ├── analyze_videos.py           # Gemini AI 内容分析
│   ├── analyze_relations.py        # 频道关联分析
│   └── generate_site.py            # 静态页面生成
├── data/
│   ├── channels.json               # 频道列表
│   ├── videos.json                 # 视频数据 & 分析结果
│   └── channel_relations.json      # 频道关联
├── docs/                           # 静态页面 (GitHub Pages)
│   ├── index.html
│   ├── style.css
│   └── app.js
└── memory_bank/                    # 项目文档
```
