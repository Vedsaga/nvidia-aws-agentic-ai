"""
FastAPI Server for Kāraka Frame Graph POC.
WebSocket-based real-time processing and Q&A.
"""

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from sentence_splitter import smart_split
from eventive_filter import filter_eventive
from frame_extractor import extract_frames
from frame_store import get_store
from frame_extractor import Frame
from qa_engine import ask


def load_demo_frames():
    """Load pre-extracted demo frames if available."""
    demo_path = Path(__file__).parent / "demo_frames.json"
    if demo_path.exists():
        try:
            with open(demo_path, "r") as f:
                data = json.load(f)
            frames = []
            for item in data:
                frame = Frame(
                    frame_id=item["frame_id"],
                    sentence_id=item["sentence_id"],
                    sentence_text=item["sentence_text"],
                    kriya=item["kriya"],
                    kriya_surface=item["kriya_surface"],
                    karta=item.get("karta"),
                    karma=item.get("karma"),
                    karana=item.get("karana"),
                    sampradana=item.get("sampradana"),
                    apadana=item.get("apadana"),
                    locus_time=item.get("locus_time"),
                    locus_space=item.get("locus_space"),
                    locus_topic=item.get("locus_topic"),
                    causal_links=item.get("causal_links"),
                )
                frames.append(frame)
            return frames
        except Exception as e:
            print(f"⚠️ Could not load demo frames: {e}")
            return []
    return []


def load_stress_test_frames():
    """Load complex stress test frames with causal chains."""
    stress_path = Path(__file__).parent / "stress_test_frames.json"
    if stress_path.exists():
        try:
            with open(stress_path, "r") as f:
                data = json.load(f)
            frames = []
            for item in data:
                frame = Frame(
                    frame_id=item["frame_id"],
                    sentence_id=item["sentence_id"],
                    sentence_text=item["sentence_text"],
                    kriya=item["kriya"],
                    kriya_surface=item["kriya_surface"],
                    karta=item.get("karta"),
                    karma=item.get("karma"),
                    karana=item.get("karana"),
                    sampradana=item.get("sampradana"),
                    apadana=item.get("apadana"),
                    locus_time=item.get("locus_time"),
                    locus_space=item.get("locus_space"),
                    locus_topic=item.get("locus_topic"),
                    causal_links=item.get("causal_links"),
                )
                frames.append(frame)
            print(f"✨ Loaded {len(frames)} stress test frames with causal chains")
            return frames
        except Exception as e:
            print(f"⚠️ Could not load stress test frames: {e}")
            return []
    return []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Setup and teardown."""
    print("🚀 Kāraka Frame Graph POC Server starting...")
    print("📂 Frame store initialized")
    
    # Load demo frames if available
    demo_frames = load_demo_frames()
    if demo_frames:
        store = get_store()
        store.add_frames(demo_frames)
        print(f"✨ Loaded {len(demo_frames)} demo frames (demo mode ready)")
    
    yield
    print("👋 Server shutting down")


app = FastAPI(
    title="Kāraka Frame Graph POC",
    description="Event-centric semantic extraction and QA",
    version="0.1.0",
    lifespan=lifespan
)

# Serve static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")


@app.get("/")
async def root():
    """Serve the demo UI."""
    index_path = static_path / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path))
    return {"message": "Kāraka Frame Graph POC", "status": "running"}


@app.get("/api/stats")
async def get_stats():
    """Get frame store statistics."""
    store = get_store()
    return store.get_stats()


@app.get("/api/frames")
async def get_frames():
    """Get all frames."""
    store = get_store()
    return [f.to_display() for f in store.get_all_frames()]


@app.get("/api/graph")
async def get_graph():
    """Get graph visualization data."""
    store = get_store()
    return store.to_graph_data()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time processing.
    
    Message types:
    - process_text: Process a text document
    - ask_question: Ask a question about the frames
    - get_frames: Get all current frames
    - clear: Clear all frames
    """
    await websocket.accept()
    store = get_store()
    
    async def send_status(message: str, progress: float = None):
        """Send a status update to the client."""
        data = {"type": "status", "message": message}
        if progress is not None:
            data["progress"] = progress
        await websocket.send_json(data)
    
    async def send_error(message: str):
        """Send an error to the client."""
        await websocket.send_json({"type": "error", "message": message})
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await send_error("Invalid JSON")
                continue
            
            msg_type = message.get("type")
            
            # ─────────────────────────────────────────────
            # PROCESS TEXT
            # ─────────────────────────────────────────────
            if msg_type == "process_text":
                text = message.get("text", "")
                if not text.strip():
                    await send_error("Empty text")
                    continue
                
                await send_status(f"Received {len(text)} characters", 0.1)
                
                # Step 1: Split sentences
                await send_status("Splitting sentences...", 0.2)
                sentences = await smart_split(text)
                await send_status(f"Split into {len(sentences)} sentences", 0.3)
                
                # Step 2: Filter eventive
                await send_status("Filtering eventive sentences...", 0.4)
                filtered = await filter_eventive(sentences)
                eventive_count = sum(1 for f in filtered if f["is_eventive"])
                await send_status(f"Found {eventive_count} eventive sentences", 0.5)
                
                # Send sentence analysis
                await websocket.send_json({
                    "type": "sentences",
                    "data": filtered
                })
                
                # Step 3: Extract frames
                await send_status("Extracting frames...", 0.6)
                frames = await extract_frames(filtered)
                
                # Add to store
                store.add_frames(frames)
                
                # Send frames
                for i, frame in enumerate(frames):
                    await websocket.send_json({
                        "type": "frame",
                        "data": frame.to_display()
                    })
                    progress = 0.6 + (0.3 * (i + 1) / len(frames)) if frames else 0.9
                    await send_status(f"Extracted frame {i + 1}/{len(frames)}", progress)
                
                # Send graph data
                await websocket.send_json({
                    "type": "graph",
                    "data": store.to_graph_data()
                })
                
                await send_status(f"Complete! Extracted {len(frames)} frames", 1.0)
                await websocket.send_json({"type": "complete", "frame_count": len(frames)})
            
            # ─────────────────────────────────────────────
            # ASK QUESTION
            # ─────────────────────────────────────────────
            elif msg_type == "ask_question":
                question = message.get("question", "")
                if not question.strip():
                    await send_error("Empty question")
                    continue
                
                await send_status("Processing question...")
                
                result = await ask(question, store)
                
                await websocket.send_json({
                    "type": "answer",
                    "question": result["question"],
                    "answer": result["answer"],
                    "sources": result["sources"],
                    "frame_count": result["frame_count"]
                })
            
            # ─────────────────────────────────────────────
            # GET FRAMES
            # ─────────────────────────────────────────────
            elif msg_type == "get_frames":
                frames = store.get_all_frames()
                await websocket.send_json({
                    "type": "frames",
                    "data": [f.to_display() for f in frames],
                    "stats": store.get_stats()
                })
            
            # ─────────────────────────────────────────────
            # GET GRAPH
            # ─────────────────────────────────────────────
            elif msg_type == "get_graph":
                await websocket.send_json({
                    "type": "graph",
                    "data": store.to_graph_data()
                })
            
            # ─────────────────────────────────────────────
            # CLEAR
            # ─────────────────────────────────────────────
            elif msg_type == "clear":
                store.clear()
                await send_status("Frames cleared")
                await websocket.send_json({"type": "cleared"})
            
            # ─────────────────────────────────────────────
            # LOAD DEMO (bypass extraction, use pre-loaded frames)
            # ─────────────────────────────────────────────
            elif msg_type == "load_demo":
                demo_frames = load_demo_frames()
                if demo_frames:
                    store.clear()
                    store.add_frames(demo_frames)
                    
                    # Send frames to UI
                    for frame in demo_frames:
                        await websocket.send_json({
                            "type": "frame",
                            "data": frame.to_display()
                        })
                    
                    # Send graph data
                    await websocket.send_json({
                        "type": "graph",
                        "data": store.to_graph_data()
                    })
                    
                    await send_status(f"Demo mode: Loaded {len(demo_frames)} pre-extracted frames", 1.0)
                    await websocket.send_json({"type": "complete", "frame_count": len(demo_frames), "demo_mode": True})
                else:
                    await send_error("No demo frames available")
            
            # ─────────────────────────────────────────────
            # LOAD STRESS TEST (complex causal reasoning)
            # ─────────────────────────────────────────────
            elif msg_type == "load_stress_test":
                stress_frames = load_stress_test_frames()
                if stress_frames:
                    store.clear()
                    store.add_frames(stress_frames)
                    
                    # Send frames to UI
                    for frame in stress_frames:
                        await websocket.send_json({
                            "type": "frame",
                            "data": frame.to_display()
                        })
                    
                    # Send graph data
                    await websocket.send_json({
                        "type": "graph",
                        "data": store.to_graph_data()
                    })
                    
                    await send_status(f"Stress Test: Loaded {len(stress_frames)} frames with causal chains", 1.0)
                    await websocket.send_json({"type": "complete", "frame_count": len(stress_frames), "stress_test": True})
                else:
                    await send_error("No stress test frames available")
            
            else:
                await send_error(f"Unknown message type: {msg_type}")
    
    except WebSocketDisconnect:
        print("📤 Client disconnected")
    except Exception as e:
        print(f"❌ WebSocket error: {e}")
        try:
            await send_error(str(e))
        except:
            pass


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
