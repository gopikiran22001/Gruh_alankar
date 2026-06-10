# Gruha Alankara — AI-Powered Interior Design Platform

## 🏠 Overview

Gruha Alankara is a fully autonomous agentic AI platform for interior design. A reasoning-based **Supervisor Agent** (DeepSeek-R1) dynamically plans, selects, invokes, validates, retries, and coordinates 11 specialized agents to handle interior design tasks end-to-end.

**No hardcoded chains. No predefined workflows. All orchestration is reasoning-driven.**

## 🏗️ Architecture

```
User → Buddy Agent → Supervisor Agent (DeepSeek-R1) → Dynamic Task Graph
                                    ↓
         ┌──────────┬──────────┬──────────┬──────────┐
         ↓          ↓          ↓          ↓          ↓
     Vision    Design    Web Agent  Furniture   Budget
     Agent     Agent                 Agent      Agent
         └──────────┴──────────┴──────────┴──────────┘
                                    ↓
                            Critic Agent (QA)
                                    ↓
                            Buddy Agent (Response)
                                    ↓
                                  User
```

## 🤖 Agents

| Agent | Model | Role |
|-------|-------|------|
| Supervisor | DeepSeek-R1 | Planning, reasoning, orchestration |
| Buddy | Qwen2.5-72B | User interaction, response generation |
| Vision | Florence-2 + YOLOv11 + SAM2 | Room analysis, object detection |
| Design | Qwen2.5-72B | Design proposals, layouts, palettes |
| Furniture | Qwen2.5-72B | Product recommendations, ranking |
| Web | Playwright + BS4 | Product scraping, price comparison |
| Budget | Qwen2.5-72B | Cost estimation, optimization |
| Booking | — | Order management, tracking |
| Memory | ChromaDB + BGE-M3 | Long-term user memory |
| Voice | Whisper + XTTS-v2 | Speech-to-text, text-to-speech |
| Critic | DeepSeek-R1 | Output validation, retry decisions |

## ⚡ Quick Start

### 1. Environment Setup

```bash
cd Backend
cp .env.example .env
# Edit .env with your API keys
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Services (Docker)

```bash
docker-compose up -d redis chromadb
```

### 4. Run Development Server

```bash
python run.py
```

### 5. Run with Docker Compose (Full Stack)

```bash
docker-compose up --build
```

## 📡 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login and get JWT |
| POST | `/api/chat` | **Main chat endpoint** (autonomous) |
| POST | `/api/vision/analyze` | Analyze room image |
| POST | `/api/design/generate` | Generate design proposal |
| POST | `/api/furniture/search` | Search/recommend furniture |
| POST | `/api/budget/calculate` | Calculate budget |
| POST | `/api/booking/create` | Create booking |
| POST | `/api/web/search` | Search products online |
| POST | `/api/voice/transcribe` | Speech to text |
| POST | `/api/voice/speak` | Text to speech |
| GET | `/api/projects` | List projects |
| POST | `/api/projects` | Create project |
| GET | `/api/health` | Health check |

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=app --cov-report=html
```

## 📁 Project Structure

```
Backend/
├── app/
│   ├── __init__.py          # Flask app factory
│   ├── extensions.py        # JWT, MongoDB, Redis singletons
│   ├── agents/              # All 11 agents
│   ├── api/                 # REST API endpoints
│   ├── auth/                # Authentication
│   ├── database/            # MongoDB, ChromaDB, Redis
│   ├── llm/                 # LLM API clients
│   ├── orchestration/       # LangGraph workflow engine
│   ├── observability/       # Logging, metrics
│   └── tasks/               # Celery background jobs
├── config/                  # Settings, constants, logging
├── tests/                   # Unit & integration tests
├── docker-compose.yml       # Docker orchestration
├── Dockerfile               # Multi-stage production build
└── requirements.txt         # Python dependencies
```

## 🔧 Tech Stack

- **Backend**: Flask, Flask-JWT-Extended, Flask-CORS
- **Database**: MongoDB Atlas, ChromaDB, Redis
- **Agent Framework**: LangGraph
- **LLMs**: DeepSeek-R1, Qwen2.5-72B, Qwen2.5-VL
- **Vision**: Florence-2, YOLOv11, SAM2
- **Voice**: Faster Whisper, XTTS-v2
- **Embeddings**: BAAI/bge-m3
- **Task Queue**: Celery + Redis
- **Scraping**: httpx, BeautifulSoup, lxml

## 📜 License

Proprietary — Gruha Alankara © 2025
