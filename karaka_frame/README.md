# Kāraka Frame Graph POC - Local Implementation

This folder contains the complete POC implementation for the Kāraka Frame Graph system.

## Quick Start

```bash
# 1. Install dependencies
pip install openai python-dotenv spacy fastapi uvicorn websockets

# 2. Download spaCy model
python -m spacy download en_core_web_sm

# 3. Set your API key
echo "LLM_API_KEY=your-key-here" > .env
echo "LLM_BASE_URL=https://openrouter.ai/api/v1" >> .env

# 4. Run the server
uvicorn server:app --reload --port 8000

# 5. Open browser
open http://localhost:8000
```

## Architecture

```
Text Input
    ↓
┌──────────────────────────────────────────┐
│  Sentence Splitter (sentence_splitter.py) │
└──────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────┐
│  Eventive Filter (eventive_filter.py)    │
│  "Is this an action or a state?"         │
└──────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────┐
│  Frame Extractor (frame_extractor.py)    │
│  "Kriyā + Kāraka roles"                  │
└──────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────┐
│  Frame Store (frame_store.py)            │
│  "In-memory JSON storage"                │
└──────────────────────────────────────────┘
    ↓
┌──────────────────────────────────────────┐
│  QA Engine (qa_engine.py)                │
│  "Question → Frame → Answer"             │
└──────────────────────────────────────────┘
```

## Files

| File | Purpose |
|------|---------|
| `llm_client.py` | Async LLM client (OpenRouter/OpenAI) |
| `sentence_splitter.py` | Cascading splitter (Regex → Spacy → LLM) |
| `eventive_filter.py` | Filters out stative sentences |
| `frame_extractor.py` | Extracts Kriyā + Kāraka roles |
| `frame_store.py` | In-memory frame storage |
| `qa_engine.py` | Question answering engine |
| `server.py` | FastAPI WebSocket server |
| `static/index.html` | Demo UI |

## API

### WebSocket: `/ws`

**Messages from Client:**
```json
{"type": "process_text", "text": "Ram ate the mango in the kitchen."}
{"type": "ask_question", "question": "Who ate the mango?"}
{"type": "get_frames"}
```

**Messages from Server:**
```json
{"type": "status", "message": "Processing..."}
{"type": "frame", "data": {...}}
{"type": "answer", "text": "...", "sources": [...]}
```
