# Local Kāraka NexusGraph Implementation Plan

This plan details how to build the core "Intelligence Engine" of the Kāraka system on your local machine, utilizing a lightweight Python server communicating with a web frontend.

## 📂 1. Directory Structure
We will create a specific folder `local_karaka/` to house this independent engine.

```text
local_karaka/
├── .env                  # API Keys (OpenRouter/OpenAI)
├── server.py             # FastAPI/Websocket Server (The Brain)
├── llm_client.py         # Async Generic LLM Handler
├── sentence_splitter.py  # The Cascading Splitter (Regex -> Spacy -> LLM)
└── static/               # Frontend (HTML/JS)
    └── index.html
```

---

## 🏗️ 2. Architectural Overview
*   **Local Server (Python/FastAPI):** Acts as the central processing unit.
    *   Runs **Regex** and **Spacy** locally (CPU-bound, fast).
    *   Orchestrates **Async** calls to the generic LLM provider (I/O-bound).
    *   Maintains the active Knowledge Graph state.
*   **Frontend (Browser):** A "dumb" display layer.
    *   Connects to Server via **WebSockets**.
    *   Sends raw text/files.
    *   Receives real-time graph updates (nodes/edges) to visualize.
*   **Data Flow:**
    `User Input` -> `WebSocket` -> `Server (Splitting)` -> `LLM (Extraction)` -> `Graph Update` -> `WebSocket` -> `UI Update`

---

## 🛠️ 3. Component 1: Async LLM Client (`llm_client.py`)
**Goal:** A centralized, **asynchronous** handler for all LLM calls.

```python
import os
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI # Note: Async Client

load_dotenv()

# Async Client for non-blocking operations
client = AsyncOpenAI(
    base_url=os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("LLM_API_KEY")
)

async def call_llm(system_prompt, user_text, model="meta-llama/llama-3.1-70b-instruct", json_mode=False):
    """
    Generic ASYNC wrapper for LLM calls. 
    Allows the server to handle multiple sentences in parallel.
    """
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]
    
    response = await client.chat.completions.create(
        model=model,
        messages=messages,
        response_format={"type": "json_object"} if json_mode else None
    )
    
    return response.choices[0].message.content
```

---

## ✂️ 4. Component 2: Cascading Sentence Splitter (`sentence_splitter.py`)
**Goal:** A layered filter pipeline ensuring 100% fidelity. `Regex` -> `Spacy` -> `LLM`.

```python
import re
import spacy
import json
from llm_client import call_llm

# Load Spacy (Server-side)
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading Spacy model...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def verify_fidelity(original, segments):
    """The Iron Law: Input MUST equal Output exactly."""
    return "".join(segments) == original

def split_text_regex(text):
    """Layer 1: Fast Regex Split"""
    pattern = r'([.?!]\s+)' 
    parts = re.split(pattern, text)
    sentences = []
    current_sent = ""
    for part in parts:
        if re.match(pattern, part):
             current_sent += part
             sentences.append(current_sent)
             current_sent = ""
        else:
             current_sent += part
    if current_sent: sentences.append(current_sent)
    return sentences

def split_text_spacy(text):
    """Layer 2: Spacy Dependency Parse"""
    doc = nlp(text)
    return [sent.text_with_ws for sent in doc.sents]

async def split_text_llm(text):
    """Layer 3: Async LLM Fallback"""
    prompt = """
    Split this text into sentences. 
    CRITICAL: Keep original punctuation and trailing spaces.
    Return JSON: ["Sentence 1. ", "Sentence 2."]
    """
    response = await call_llm(prompt, text, json_mode=True)
    try:
        data = json.loads(response)
        if isinstance(data, list): return data
        if isinstance(data, dict): return list(data.values())[0]
    except:
        return [text]

async def smart_split(text):
    # 1. Try Regex (Instance, Free)
    candidates = split_text_regex(text)
    if verify_fidelity(text, candidates):
        return candidates

    # 2. Try Spacy (Fast, Free)
    candidates = split_text_spacy(text)
    if verify_fidelity(text, candidates):
        print(f"✅ Spacy Split Succeeded")
        return candidates
        
    # 3. Fallback to LLM (Slow, Costly)
    print("⚠️ Local methods failed. Escalating to LLM...")
    candidates = await split_text_llm(text)
    
    # 4. Final Safety Net
    if verify_fidelity(text, candidates):
        return candidates
    else:
        print("❌ Critical Failure: Returning original text un-split.")
        return [text]
```

---

## 🌐 5. Component 3: The Server (`server.py`)
**Goal:** Orchestrate the flow using WebSockets.

```python
from fastapi import FastAPI, WebSocket
from sentence_splitter import smart_split
from llm_client import call_llm

app = FastAPI()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # 1. Receive Text
    text = await websocket.receive_text()
    await websocket.send_text(f"Status: Received {len(text)} chars. Splitting...")
    
    # 2. Split (Cascading)
    sentences = await smart_split(text)
    await websocket.send_text(f"Status: Split into {len(sentences)} sentences.")
    
    # 3. Process Each Sentence (Pipeline)
    for i, sentence in enumerate(sentences):
        await websocket.send_text(f"Processing: {i+1}/{len(sentences)}")
        
        # Call LLM for Extraction (Async)
        # Note: In production, we'd use asyncio.gather to do this in parallel
        # extraction = await extract_entities(sentence) 
        
        # Update Graph logic here...
        
        # Send update to UI
        await websocket.send_json({"type": "node_update", "data": "..."})
        
    await websocket.send_text("Status: Complete.")
```

## 📝 6. Next Steps
1.  **Install Requirements:**
    ```bash
    pip install openai python-dotenv spacy fastapi uvicorn websockets
    python -m spacy download en_core_web_sm
    ```
2.  **Run Server:** `uvicorn server:app --reload`
3.  **Build UI:** A simple HTML file connecting to `ws://localhost:8000/ws`.
