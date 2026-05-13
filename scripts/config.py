"""
LLM News Tracker — Configuration
Seed channels and topic taxonomy for AI content analysis.
"""

# Seed YouTube channels (manually curated LLM-focused channels)
# Format: { "name": str, "url": str, "handle": str }
SEED_CHANNELS = [
    {
        "name": "Andrej Karpathy",
        "url": "https://www.youtube.com/@AndrejKarpathy",
        "handle": "@AndrejKarpathy",
    },
    {
        "name": "AI Explained",
        "url": "https://www.youtube.com/@aiexplained-official",
        "handle": "@aiexplained-official",
    },
    {
        "name": "Yannic Kilcher",
        "url": "https://www.youtube.com/@YannicKilcher",
        "handle": "@YannicKilcher",
    },
    {
        "name": "Sam Witteveen",
        "url": "https://www.youtube.com/@samwitteveen",
        "handle": "@samwitteveen",
    },
    {
        "name": "Matt Wolfe",
        "url": "https://www.youtube.com/@mattwolfe",
        "handle": "@mattwolfe",
    },
    {
        "name": "AI Jason",
        "url": "https://www.youtube.com/@AIJasonZ",
        "handle": "@AIJasonZ",
    },
    {
        "name": "Two Minute Papers",
        "url": "https://www.youtube.com/@TwoMinutePapers",
        "handle": "@TwoMinutePapers",
    },
    {
        "name": "Prompt Engineering",
        "url": "https://www.youtube.com/@engineerprompt",
        "handle": "@engineerprompt",
    },
    {
        "name": "Machine Learning Street Talk",
        "url": "https://www.youtube.com/@MachineLearningStreetTalk",
        "handle": "@MachineLearningStreetTalk",
    },
    {
        "name": "David Shapiro",
        "url": "https://www.youtube.com/@DaveShap",
        "handle": "@DaveShap",
    },
]

# Predefined topic taxonomy for video classification
TOPIC_TAXONOMY = [
    "Fine-tuning",
    "RAG",
    "Agent",
    "Prompt Engineering",
    "Model Architecture",
    "Training & Pre-training",
    "Inference Optimization",
    "Multimodal",
    "Evaluation & Benchmark",
    "Industry Application",
    "Open Source",
    "Safety & Alignment",
    "Tool Use",
    "Reasoning",
]

# Technical depth levels
TECHNICAL_LEVELS = ["Beginner", "Intermediate", "Advanced"]

# Data retention: keep videos from the last N days
RETENTION_DAYS = 90

# Max transcript characters sent to Gemini (safety margin under context window)
MAX_TRANSCRIPT_CHARS = 30000

# Gemini model to use
GEMINI_MODEL = "gemini-2.5-flash"

# Channel discovery: minimum active score to add a new channel
MIN_ACTIVE_SCORE = 3  # channels with >= 3 videos in last 7 days

# Minimum average views for auto-discovered channels
MIN_AVG_VIEWS = 5000
