# LLM News Tracker — 实施计划

> 本文件是 AI 开发者的分步指令指南。
> **严格按顺序执行，每步完成后验证通过才可进行下一步。**

## 前置条件

- 开始前确保已阅读：
  - `memory_bank/@main_functions.md`（功能规格）
  - `memory_bank/@tech_stack.md`（技术栈方案）
- 确认开发环境已安装：
  - Python 3.11+（`python3 --version`）
  - Git（`git --version`）
  - pip（`pip3 --version`）
- 准备 Google Gemini API Key（从 https://aistudio.google.com/apikey 获取）

---

## Step 0: 项目初始化与目录结构

### 指令
在项目根目录创建完整目录结构（scripts/、data/、site/、.github/workflows/、memory_bank/），创建 requirements.txt 并安装 Python 依赖（feedparser、yt-dlp、google-generativeai），创建初始的空 JSON 数据文件。

### 验证方式
- 运行 `pip3 list | grep -E "feedparser|yt-dlp|google-generativeai"` 确认三个依赖全部安装
- 运行 `ls -la data/` 确认 channels.json、videos.json、channel_relations.json 三个空文件存在
- 运行 `ls -la site/` 确认 index.html、style.css、app.js 存在（初始可为空占位）

### 预期产出
- 完整的目录结构
- requirements.txt 含 3 个依赖
- data/ 下 3 个空 JSON 文件
- site/ 下 3 个占位文件
- .github/workflows/ 目录存在

---

## Step 1: 种子频道配置与发现（fetch_channels.py）

### 指令
创建种子频道配置文件（5-10 个精选 LLM 频道），编写 fetch_channels.py 脚本：读取种子频道列表 → 通过每个频道的 RSS Feed 验证其有效性 → 使用 yt-dlp 获取每个频道的「相关频道」推荐 → 评估这些推荐频道（检查最近 7 天是否有新视频、平均播放量）→ 将合格频道加入 data/channels.json。

种子频道建议清单（手动选 5-10 个活跃 LLM 频道，提供频道名和 channel_id）。

### 验证方式
- 手动运行 `python3 scripts/fetch_channels.py`，查看 data/channels.json 是否包含种子频道 + 自动发现的频道
- 检查 JSON 中每个频道是否具有完整字段：channel_id, name, rss_url, content_focus（初始可为空）, is_seed, active_score, added_at

### 预期产出
- scripts/config.py（种子频道定义 + 主题分类常量）
- scripts/fetch_channels.py
- data/channels.json（含初始频道列表）

---

## Step 2: 视频抓取与字幕下载（fetch_videos.py）

### 指令
编写 fetch_videos.py 脚本：读取 data/channels.json 中所有频道 → 对每个频道抓取其 YouTube RSS Feed → 解析出最近 30 天的视频（video_id、title、url、published_at）→ 与 data/videos.json 中已有记录去重 → 对新增视频，使用 yt-dlp 的 `--write-auto-subs --sub-lang en --skip-download` 参数仅下载字幕（不下载视频本身）→ 将字幕文本和元数据存入 data/videos.json。

关键约束：yt-dlp 的 `--write-auto-subs` 获取的是 YouTube 自动生成字幕（免费），`--sub-lang en` 限定英文以控制字幕大小。

### 验证方式
- 手动运行 `python3 scripts/fetch_videos.py`，检查 data/videos.json 中是否新增了视频条目
- 随机抽查一条视频记录，确认包含字段：video_id, channel_id, title, url, published_at, view_count, duration, has_captions, raw_transcript（字幕文本）, fetched_at
- 再次运行脚本，确认没有重复抓取已有的视频

### 预期产出
- scripts/fetch_videos.py
- data/videos.json 中有实际视频数据

---

## Step 3: AI 内容分析（analyze_videos.py）

### 指令
编写 analyze_videos.py 脚本：读取 data/videos.json 中所有 `raw_transcript` 非空且尚未分析的视频 → 对每条视频，将字幕文本截断至 30000 字符（Gemini 上下文窗口安全值）→ 构造 Prompt 调用 Gemini API，要求返回结构化 JSON：summary（150 字中文摘要）、topics（主题标签列表，从预定义主题集中选择）、speaker（主讲人）、technical_level（入门/中级/高级）→ 将分析结果写回 data/videos.json。

预定义主题集（在 config.py 中定义）：Fine-tuning、RAG、Agent、Prompt Engineering、Model Architecture、Training/Pre-training、Inference Optimization、Multimodal、Evaluation/Benchmark、Industry Application、Open Source、Safety/Alignment、Tool Use、Reasoning。

约束：Gemini API Key 从环境变量 `GEMINI_API_KEY` 读取，使用 `gemini-1.5-flash` 模型（免费额度充足且速度快）。

### 验证方式
- 设置环境变量 `export GEMINI_API_KEY=your_key` 后运行 `python3 scripts/analyze_videos.py`
- 检查 data/videos.json 中视频是否被补充了 analysis 字段（summary、topics、speaker、technical_level）
- 随机抽查 3 条分析结果，确认 summary 为中文、topics 标签在预定义列表中、speaker 非空

### 预期产出
- scripts/analyze_videos.py
- data/videos.json 中视频含有 AI 分析结果

---

## Step 4: 频道关联分析（analyze_relations.py）

### 指令
编写 analyze_relations.py 脚本：收集每个频道下所有视频的主题标签分布 → 对所有频道两两计算内容重叠度（Jaccard 相似度）→ 调用 Gemini API，输入两个频道的代表性视频摘要，判断它们的内容侧重、观点关系（互补/对立/引用）→ 生成频道关联描述 → 将结果存入 data/channel_relations.json。

同时也更新 data/channels.json 中每个频道的 content_focus 字段（AI 生成的频道内容侧重描述）。

### 验证方式
- 运行 `python3 scripts/analyze_relations.py`
- 检查 data/channel_relations.json 是否每条记录包含：channel_a_id, channel_b_id, relation_type, description
- 检查 data/channels.json 中每个频道 content_focus 字段是否已有内容

### 预期产出
- scripts/analyze_relations.py
- data/channel_relations.json
- data/channels.json 中 content_focus 已填充

---

## Step 5: 静态页面生成（generate_site.py + 前端文件）

### 指令
编写 generate_site.py 脚本：读取 data/videos.json、data/channels.json、data/channel_relations.json → 将 JSON 数据以内嵌 `<script>` 标签形式注入 site/index.html 模板 → 输出可直接部署的静态页面文件。

前端页面（site/index.html + site/style.css + site/app.js）需实现：
- 主表格：列 = 频道名称、视频标题（可点击跳转）、发布时间、播放量、主题标签（彩色标签）、AI 摘要、主讲人、技术深度
- 搜索框：输入关键词实时过滤（匹配标题、摘要、主讲人、标签）
- 主题筛选：多选标签过滤
- 频道筛选：下拉选择单个频道
- 频道关联区域：表格下方，展示各频道内容侧重 + 频道间关系
- 响应式布局：移动端表格可横向滚动，筛选器折叠为下拉
- 暗色/亮色主题：跟随系统主题

样式要求：专业简洁的企业级风格，不花哨，强调可读性和信息密度。

### 验证方式
- 运行 `python3 scripts/generate_site.py`
- 用浏览器打开 site/index.html，确认表格正常渲染、搜索/筛选功能可用
- 点击视频标题链接，确认能跳转到 YouTube
- 缩小浏览器窗口到 375px，确认移动端布局正常

### 预期产出
- scripts/generate_site.py
- site/index.html（含内嵌数据）
- site/style.css
- site/app.js

---

## Step 6: GitHub 仓库初始化与 Pages 配置

### 指令
在本地项目根目录初始化 Git 仓库 → 创建 .gitignore（排除 __pycache__/、.env、*.pyc、venv/）→ 在 GitHub 上创建公开仓库 → 推送代码 → 在仓库 Settings → Pages 中启用 GitHub Pages（Source: GitHub Actions）。

同时将 Gemini API Key 添加到仓库的 Settings → Secrets and variables → Actions → 添加 Secret：`GEMINI_API_KEY`。

### 验证方式
- `git remote -v` 确认指向正确的 GitHub 仓库
- GitHub 仓库页面确认代码已推送
- Settings → Pages 确认 Build and deployment Source 为 "GitHub Actions"

### 预期产出
- GitHub 公开仓库
- .gitignore 文件
- Git 远程仓库已配置

---

## Step 7: CI/CD 流水线（GitHub Actions）

### 指令
创建 .github/workflows/update.yml：定义每 12 小时触发的工作流（cron: `0 */12 * * *`），包含以下 job：
1. Checkout 代码
2. 设置 Python 3.11
3. 安装依赖（pip install -r requirements.txt）
4. 安装 ffmpeg（yt-dlp 字幕处理需要）
5. 按顺序执行：fetch_channels.py → fetch_videos.py → analyze_videos.py → analyze_relations.py → generate_site.py
6. 使用 peaceiris/actions-gh-pages@v4 将 site/ 部署到 GitHub Pages

约束：
- GEMINI_API_KEY 从 GitHub Secrets 读取
- 如果某个脚本失败，后续脚本不应执行（`&&` 串联）
- 部署步骤只在前面所有步骤成功时执行
- 工作流也可手动触发（workflow_dispatch）

### 验证方式
- 在 GitHub Actions 页面手动触发 workflow（Run workflow）
- 等待 workflow 完成，检查所有步骤是否绿勾
- 访问 `https://<username>.github.io/<repo-name>/` 确认页面可访问且内容正确

### 预期产出
- .github/workflows/update.yml
- 成功部署的 GitHub Pages 页面

---

## Step 8: 端到端验证与文档

### 指令
完整测试一遍流程：手动触发 GitHub Actions → 等待完成 → 验证页面所有功能 → 在 README.md 中写简明使用说明（包含：项目介绍、页面地址、如何添加新频道、如何本地运行）。

同时做边界情况测试：
- 当一个频道没有新视频时，不影响其他频道
- 当一个视频没有字幕时，标记 has_captions: false，跳过分析
- Gemini API 调用失败时，记录错误但不中断整体流程

### 验证方式
- 页面 URL 可在无痕浏览器窗口中正常打开
- 表格数据与 data/videos.json 一致
- 搜索 "RAG" 能正确筛出含 RAG 标签的视频
- 频道筛选下拉列出所有频道
- 查看 README.md，确认包含使用说明

### 预期产出
- README.md
- 完整可用的公开页面

---

## 执行顺序依赖

```
Step 0 → Step 1 → Step 2 → Step 3 → Step 4 → Step 5 → Step 6 → Step 7 → Step 8
  │        │        │        │        │        │        │        │        │
  └─ 基础 ─┘        │        │        │        │        │        │        │
            └─ 数据源 ─┘        │        │        │        │        │        │
                       └─ 原始数据 ─┘        │        │        │        │        │
                                  └─ AI 分析 ─┘        │        │        │        │
                                             └─ 关联 ──┘        │        │        │
                                                       └─ 页面 ─┘        │        │
                                                              └─ 仓库 ──┘        │
                                                                       └─ 部署 ─┘
                                                                              └─ 验证
```

> ⚠️ Step 1-5 必须先本地调通，Step 6-7 再做 GitHub 集成。
