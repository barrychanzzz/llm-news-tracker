# LLM News Tracker — 技术栈方案

## 选型依据

基于 `main_functions.md` 分析：
- **部署目标**：GitHub Pages（纯静态）
- **数据流**：定时抓取 → AI 分析 → 生成静态页面 → 自动部署
- **外部依赖**：仅 Gemini API（免费额度）
- **无数据库需求**：数据量小（<1000 条视频记录），JSON 文件足矣

## 前端

| 层面 | 方案 | 理由 |
|-----|------|------|
| 框架 | **无框架**，纯 HTML + Vanilla JS | GitHub Pages 静态部署，无构建步骤，极致简单 |
| 样式 | **纯 CSS**（CSS Variables + Grid + Flexbox） | 零依赖，响应式无障碍 |
| 表格渲染 | 原生 `<table>` + JS 动态填充 | JSON 数据直接渲染，无需虚拟 DOM |
| 搜索筛选 | 原生 JS `filter()` + `includes()` | 数据量小（<500 行），无需 Fuse.js 等库 |

> 选择「零框架」方案的理由：数据量小（<500 条视频）、交互简单（表格+搜索+筛选），引入 React/Vue 反而增加构建复杂度和页面体积。原生方案可让页面总大小控制在 50KB 以内，加载速度极快。

## 后端（数据管道）

| 层面 | 方案 | 理由 |
|-----|------|------|
| 运行时 | **Python 3.11+** | yt-dlp 仅支持 Python；Gemini SDK 对 Python 支持最好 |
| RSS 解析 | **feedparser** | Python 最成熟的 RSS 库，支持 YouTube RSS Feed |
| 字幕下载 | **yt-dlp** | 无需 API Key，自动下载 YouTube 字幕（含自动生成字幕） |
| AI 分析 | **google-generativeai**（Gemini SDK） | 官方 SDK，免费额度充足（每分钟 15 次请求） |
| 频道发现 | 调用 YouTube unofficial API 端点 + yt-dlp 的 related 功能 | 无需 Key，通过频道 ID 获取推荐频道 |

## 基础设施

| 层面 | 方案 | 理由 |
|-----|------|------|
| 数据存储 | **JSON 文件**（Git 仓库内） | <1MB 数据量，无需数据库 |
| 定时调度 | **GitHub Actions**（cron: `0 */12 * * *`） | 免费，与 GitHub Pages 原生集成 |
| 部署 | **GitHub Pages** | 免费，`peaceiris/actions-gh-pages` Action 自动部署 |
| 密钥管理 | **GitHub Secrets** | Gemini API Key 安全存储，不暴露在代码中 |

## 第三方服务

| 用途 | 服务 | 备选 |
|-----|------|------|
| AI 内容分析 | Google Gemini API（gemini-1.5-flash） | Groq Cloud（免费 Llama 3） |
| 视频元数据 | YouTube RSS Feed（公开，无需 Key） | — |
| 字幕获取 | yt-dlp（开源工具） | YouTube Transcript API |

## 项目结构建议

```
llm-news-tracker/
├── .github/
│   └── workflows/
│       └── update.yml            # GitHub Actions 定时任务
├── scripts/
│   ├── fetch_channels.py         # 频道发现与管理
│   ├── fetch_videos.py           # RSS + yt-dlp 抓取视频
│   ├── analyze_videos.py         # Gemini API 内容分析
│   ├── analyze_relations.py      # 频道间关联分析
│   ├── generate_site.py          # 生成静态 HTML 页面
│   └── config.py                 # 种子频道配置 + 主题分类定义
├── data/
│   ├── channels.json             # 频道列表
│   ├── videos.json               # 视频数据（含分析结果）
│   └── channel_relations.json    # 频道关联分析
├── site/
│   ├── index.html                # 主页面模板
│   ├── style.css                 # 样式
│   └── app.js                    # 表格渲染 + 搜索筛选逻辑
├── requirements.txt              # Python 依赖
├── memory_bank/                  # 项目文档
│   ├── @init.md
│   ├── @main_functions.md
│   ├── @tech_stack.md
│   ├── @implementation_plan.md
│   ├── @architecture.md
│   └── @progress.md
└── README.md
```

### 数据流

```
GitHub Actions (每12h)
  │
  ├─ fetch_channels.py  → data/channels.json (种子频道 + 自动发现)
  ├─ fetch_videos.py    → data/videos.json (新视频元数据 + 字幕)
  ├─ analyze_videos.py  → data/videos.json (补充 AI 分析结果)
  ├─ analyze_relations.py → data/channel_relations.json
  ├─ generate_site.py   → site/ (内嵌 data JSON 的纯静态页面)
  │
  └─ deploy → GitHub Pages
```
