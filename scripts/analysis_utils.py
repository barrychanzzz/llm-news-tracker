"""
兜底分析工具 — 当 Gemini API 不可用时的稳健降级方案
基于视频标题/描述生成合理的主题标签、摘要、主讲人、技术深度
确保任何视频入库时都不会是"空壳"
"""
import re
from datetime import datetime, timezone

TOPIC_KEYWORDS = {
    "RAG": ["rag", "retrieval", "retrieve", "vector", "embedding", "knowledge", "memory"],
    "Agent": ["agent", "autonomous", "agentic", "harness", "workflow", "coding agent", "claude code"],
    "Prompt Engineering": ["prompt", "prompting", "instruction", "chain-of-thought"],
    "Fine-tuning": ["fine-tun", "finetun", "lora", "qlora", "train your model", "training", "adapter"],
    "Model Architecture": ["transformer", "architecture", "mamba", "ssm", "mixture of experts", "looped", "attention"],
    "Multimodal": ["multimodal", "vision", "image", "audio", "video", "speech", "voice"],
    "Inference Optimization": ["inference", "quantization", "pruning", "distillation", "latency", "efficiency", "efficient"],
    "Evaluation & Benchmark": ["benchmark", "eval", "score", "comparison", "vs ", "versus", "solved", "test"],
    "Open Source": ["open source", "open-source", "opensource", "free", "mit license", "apache"],
    "Safety & Alignment": ["safety", "alignment", "jailbreak", "guardrail", "ethical", "worried", "risk"],
    "Tool Use": ["tool", "function call", "api", "plugin", "codex", "cursor", "mcp", "cli"],
    "Reasoning": ["reasoning", "chain of thought", "logical", "planning", "thinking"],
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
}

ADVANCED_CHANNELS = ["Yannic Kilcher", "Machine Learning Street Talk", "Andrej Karpathy"]


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
        topics = ["Agent" if "ai" in title_l else "Other"]

    if channel in ADVANCED_CHANNELS:
        level = "Advanced"
    elif "Two Minute" in (channel or ""):
        level = "Beginner"
    else:
        level = "Intermediate"

    desc_first = re.sub(r"\s+", " ", desc).strip()
    desc_first = re.sub(r"https?://\S+", "", desc_first).strip()
    if len(desc_first) > 20:
        summary = desc_first[:140]
    else:
        summary = f"{channel} 发布的关于 {', '.join(topics[:2])} 的视频：{(title or '')[:60]}"
    summary = f"【自动摘要】{summary}"

    return {
        "summary": summary,
        "topics": topics[:4],
        "speaker": SPEAKER_MAP.get(channel, "Unknown"),
        "technical_level": level,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),
        "_fallback": True,
    }
