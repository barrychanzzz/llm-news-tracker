"""
兜底分析工具 — 当 Gemini API 不可用时的稳健降级方案
基于视频标题/描述生成合理的主题标签、摘要、主讲人、技术深度
确保任何视频入库时都不会是"空壳"

v2 (2026-11-25): 扩充关键词覆盖行业观点/访谈类内容，补全主讲人映射
"""
import re
from datetime import datetime, timezone

TOPIC_KEYWORDS = {
    "RAG": ["rag", "retrieval", "retrieve", "vector", "embedding", "knowledge base", "memory"],
    "Agent": ["agent", "autonomous", "agentic", "harness", "workflow", "coding agent", "claude code", "verifier"],
    "Prompt Engineering": ["prompt", "prompting", "instruction", "chain-of-thought", "eli5", "explain like"],
    "Fine-tuning": ["fine-tun", "finetun", "lora", "qlora", "train your model", "training", "adapter", "distill"],
    "Model Architecture": ["transformer", "architecture", "mamba", "ssm", "mixture of experts", "looped", "attention", "weight space", "weights"],
    "Multimodal": ["multimodal", "vision", "image", "audio", "video", "speech", "voice", "squirrel", "wet"],
    "Inference Optimization": ["inference", "quantization", "pruning", "distillation", "latency", "efficiency", "efficient", "efficiency monster"],
    "Evaluation & Benchmark": ["benchmark", "eval", "score", "comparison", "vs ", "versus", "solved", "test", "wrong", "doesn't know", "simulated"],
    "Open Source": ["open source", "open-source", "opensource", "mit license", "apache", "open model"],
    "Safety & Alignment": ["safety", "alignment", "jailbreak", "guardrail", "ethical", "worried", "risk", "bans cruelty", "political hit", "ban rsi"],
    "Tool Use": ["tool", "function call", "api", "plugin", "codex", "cursor", "mcp", "cli", "adapters"],
    "Reasoning": ["reasoning", "chain of thought", "logical", "planning", "thinking", "understanding", "cosplay", "knows", "language"],
    "Industry & Society": [
        "anthropic", "ipo", "altman", "amodei", "jensen", "gpt 6", "astra", "claude", "gemini",
        "economics", "post-labor", "labor", "loneliness", "life", "society", "-democrats", "election",
        "hit job", "gate", "is gone", "thoughts", "bigger story", "what is", "everything", "enough",
    ],
    "Research & Cognition": [
        "tomasello", "joscha", "bach", "froese", "karl", "michael", "jeremy howard", "akshay kapoor",
        "cognition", "consciousness", "language", "human", "humans", "cooperative", "lying", "dream",
        "minecraft", "traffic light", "stake", "taxi drivers", "what a", "nothing", "real",
    ],
}

SPEAKER_MAP = {
    "Prompt Engineering": "Unknown",
    "AI Explained": "Unknown",
    "Yannic Kilcher": "Yannic Kilcher",
    "Andrej Karpathy": "Andrej Karpathy",
    "Sam Witteveen": "Sam Witteveen",
    "David Shapiro": "David Shapiro",
    "Machine Learning Street Talk": "Various Guests",
    "Two Minute Papers": "Dr. Károly Zsolnai-Fehér",
    "AI Jason": "AI Jason",
    # 访谈嘉宾：从标题括号中提取
    "Michael Tomasello": "Michael Tomasello",
    "Joscha Bach": "Joscha Bach",
    "Tom Froese": "Tom Froese",
    "Jeremy Howard": "Jeremy Howard",
}

# 标题中出现的嘉宾名 → 覆盖频道默认主讲人
GUEST_PATTERNS = [
    (r"\(Michael Tomasello\)", "Michael Tomasello"),
    (r"\(Joscha Bach\)", "Joscha Bach"),
    (r"\(Tom Froese\)", "Tom Froese"),
    (r"\(Jeremy Howard\)", "Jeremy Howard"),
    (r"\(Kevin Buzzard\)", "Kevin Buzzard"),
    (r"\(Paul Lessard\)", "Paul Lessard"),
    (r"\(Edward H\)", "Edward H"),
]

ADVANCED_CHANNELS = ["Yannic Kilcher", "Machine Learning Street Talk", "Andrej Karpathy"]


def extract_speaker(title, channel):
    """优先从标题括号提取嘉宾名，否则用频道映射"""
    for pattern, name in GUEST_PATTERNS:
        if re.search(pattern, title or "", re.IGNORECASE):
            return name
    return SPEAKER_MAP.get(channel, "Unknown")


def rule_based_analysis(title, channel, description=""):
    """基于元数据生成分析结果。返回 dict，保证字段完整。"""
    title_l = (title or "").lower()
    desc = description or ""
    desc_l = desc.lower()

    topics = []
    for topic, keywords in TOPIC_KEYWORDS.items():
        if any(kw in title_l or kw in desc_l for kw in keywords):
            topics.append(topic)
    if not topics:
        topics = ["Research & Cognition" if "(" in (title or "") else "Industry & Society"]

    if channel in ADVANCED_CHANNELS:
        level = "Advanced"
    elif "Two Minute" in (channel or ""):
        level = "Beginner"
    else:
        level = "Intermediate"

    desc_first = re.sub(r"\s+", " ", desc).strip()
    desc_first = re.sub(r"https?://\S+", "", desc_first).strip()
    # 清理常见噪声
    for noise in ["Subscribe", "LINKS", "Join my", "Get the", "Check out"]:
        if noise.lower() in desc_first.lower():
            desc_first = desc_first[:desc_first.lower().find(noise.lower())].strip()
    if len(desc_first) > 20:
        summary = desc_first[:160]
    else:
        speaker = extract_speaker(title, channel)
        context = f"与 {speaker} 的对话" if speaker not in ("Unknown", "Various Guests") and speaker != channel else ""
        summary = f"{channel} 发布{context}，聚焦 {', '.join(topics[:2])}：{(title or '')[:70]}"
    summary = f"【自动摘要】{summary}"

    return {
        "summary": summary,
        "topics": topics[:4],
        "speaker": extract_speaker(title, channel),
        "technical_level": level,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "_fallback": True,
    }
