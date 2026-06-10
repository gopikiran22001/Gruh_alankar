"""
Gruha Alankara — Application Constants
Central registry of agent names, collection names, model identifiers, and status codes.
"""

from __future__ import annotations


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Agent Identifiers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class AgentName:
    """Canonical agent names used throughout the system."""

    SUPERVISOR = "supervisor_agent"
    BUDDY = "buddy_agent"
    VISION = "vision_agent"
    DESIGN = "design_agent"
    FURNITURE = "furniture_agent"
    WEB = "web_agent"
    BUDGET = "budget_agent"
    BOOKING = "booking_agent"
    MEMORY = "memory_agent"
    VOICE = "voice_agent"
    CRITIC = "critic_agent"
    IMAGE_GEN = "image_generation_agent"

    ALL = [
        SUPERVISOR, BUDDY, VISION, DESIGN, FURNITURE,
        WEB, BUDGET, BOOKING, MEMORY, VOICE, CRITIC, IMAGE_GEN,
    ]

    # Agents the Supervisor can dispatch (excludes Supervisor itself)
    DISPATCHABLE = [
        BUDDY, VISION, DESIGN, FURNITURE,
        WEB, BUDGET, BOOKING, MEMORY, VOICE, CRITIC, IMAGE_GEN,
    ]


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MongoDB Collections
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MongoCollection:
    """MongoDB collection names."""

    USERS = "users"
    PROJECTS = "projects"
    DESIGNS = "designs"
    FURNITURE = "furniture"
    BOOKINGS = "bookings"
    CHAT_HISTORY = "chat_history"
    AGENT_LOGS = "agent_logs"
    VOICE_LOGS = "voice_logs"
    TREND_DATA = "trend_data"
    SCRAPED_PRODUCTS = "scraped_products"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ChromaDB Collections
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class VectorCollection:
    """ChromaDB vector collection names."""

    USER_MEMORY = "user_memory"
    CONVERSATION_MEMORY = "conversation_memory"
    DESIGN_MEMORY = "design_memory"
    STYLE_MEMORY = "style_memory"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Task / Workflow Status
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class TaskStatus:
    """Status values for agent tasks and workflow steps."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    CANCELLED = "cancelled"
    WAITING_HUMAN = "waiting_human_input"


class BookingStatus:
    """Status values for bookings."""

    DRAFT = "draft"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Model Identifiers
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ModelProvider:
    """Supported model providers."""

    GROQ = "groq"
    HUGGINGFACE = "huggingface"

    ALL = [GROQ, HUGGINGFACE]


class ModelID:
    """Model identifiers for LLM/Vision/Voice."""

    # DeepSeek (Supervisor + Critic — DO NOT CHANGE)
    DEEPSEEK_R1 = "deepseek-reasoner"

    # Qwen (legacy / HuggingFace provider)
    QWEN_72B = "qwen2.5-72b-instruct"
    QWEN_VL = "qwen2.5-vl-72b-instruct"
    QWEN_7B = "Qwen/Qwen2.5-7B-Instruct"

    # Groq-hosted models
    GROQ_LLAMA_70B = "llama-3.3-70b-versatile"
    GROQ_QWEN3_32B = "qwen/qwen3-32b"

    # Embeddings
    BGE_M3 = "BAAI/bge-m3"

    # Vision
    FLORENCE2 = "florence-2-large"
    YOLOV11 = "yolov11"
    SAM2 = "sam2"

    # Voice
    WHISPER_LARGE = "large-v3"
    XTTS_V2 = "tts_models/multilingual/multi-dataset/xtts_v2"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Memory Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class MemoryType:
    """Types of memories stored in the vector DB."""

    PREFERENCE = "preference"
    CONVERSATION = "conversation"
    DESIGN_HISTORY = "design_history"
    STYLE_PREFERENCE = "style_preference"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Intent Types
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class IntentType:
    """User intent categories recognized by the Supervisor."""

    ROOM_ANALYSIS = "room_analysis"
    DESIGN_REQUEST = "design_request"
    FURNITURE_SEARCH = "furniture_search"
    BUDGET_PLANNING = "budget_planning"
    BOOKING = "booking"
    GENERAL_CHAT = "general_chat"
    VOICE_INPUT = "voice_input"
    WEB_SEARCH = "web_search"
    PROJECT_MANAGEMENT = "project_management"
    STYLE_CONSULTATION = "style_consultation"
    MULTI_INTENT = "multi_intent"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Web Scraping Sources
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class ScrapingSource:
    """Supported e-commerce sources for web scraping."""

    PEPPERFRY = "pepperfry"
    URBAN_LADDER = "urban_ladder"
    IKEA = "ikea"
    AMAZON = "amazon"

    ALL = [PEPPERFRY, URBAN_LADDER, IKEA, AMAZON]

    BASE_URLS = {
        PEPPERFRY: "https://www.pepperfry.com",
        URBAN_LADDER: "https://www.urbanladder.com",
        IKEA: "https://www.ikea.com/in/en",
        AMAZON: "https://www.amazon.in",
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# API Response Codes
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class APIStatus:
    """Standard API response status strings."""

    SUCCESS = "success"
    ERROR = "error"
    PROCESSING = "processing"
    UNAUTHORIZED = "unauthorized"
    NOT_FOUND = "not_found"
    VALIDATION_ERROR = "validation_error"
    RATE_LIMITED = "rate_limited"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Retry Defaults
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAX_AGENT_RETRIES = 1
MAX_LLM_RETRIES = 3
LLM_TIMEOUT_SECONDS = 120
SUPERVISOR_MAX_PLANNING_ITERATIONS = 2

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Cache TTLs (seconds)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CACHE_TTL_SHORT = 300        # 5 minutes
CACHE_TTL_MEDIUM = 3600      # 1 hour
CACHE_TTL_LONG = 86400       # 24 hours
CACHE_TTL_SESSION = 1800     # 30 minutes
