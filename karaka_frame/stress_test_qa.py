"""
Stress Test Suite for Kāraka QA Engine
Evaluates the schema-aware Q&A capabilities using a complex causal dataset.
"""

import asyncio
import json
import time
from pathlib import Path
from frame_store import FrameStore
from frame_extractor import Frame
from qa_engine import ask

# 1. Load the Stress Test Frames (Virtual "Golden" Database)
def load_frames():
    path = Path("stress_test_frames.json")
    with open(path, "r") as f:
        data = json.load(f)
    
    frames = []
    for item in data:
        frames.append(Frame(**item))
    return frames

# 2. Define the Test Questions
TEST_CASES = [
    {
        "type": "Simple Fact (Kartā)",
        "question": "Who discovered the novel protein marker?",
        "expected_fact": "Professor Sharma"
    },
    {
        "type": "Passive Voice (Karma)",
        "question": "What was analyzed by Dr. Williams?",
        "expected_fact": "the protein"
    },
    {
        "type": "Causal Reasoning (Direct)",
        "question": "What led to the collaboration between IIT Delhi and Stanford?",
        "expected_fact": "The discovery of the novel protein marker"
    },
    {
        "type": "Complex Causal (Multi-hop)",
        "question": "Did the NIH funding help reduce tumor size?",
        "expected_fact": "Yes (Funding -> enabled trials -> drug used in trials -> reduced tumors)"
    },
    {
        "type": "Instrument (Karaṇa)",
        "question": "How did Dr. Williams analyze the protein?",
        "expected_fact": "using CRISPR technology"
    },
    {
        "type": "Temporal Logic",
        "question": "What happened in December 2023?",
        "expected_fact": "FDA approved the drug"
    },
    {
        "type": "Reasoning (Outcome)",
        "question": "What was the outcome of the clinical trials by 2023?",
        "expected_fact": "reduced tumor size by 60%"
    },
    {
        "type": "Attribution (Hetu)",
        "question": "To what did Professor Sharma attribute the success?",
        "expected_fact": "the collaborative approach"
    }
]

async def run_stress_test():
    print("🚀 Starting Kāraka Q&A Stress Test...")
    
    # Setup Store
    frames = load_frames()
    store = FrameStore()
    store.add_frames(frames)
    print(f"📂 Loaded {len(frames)} frames with complex causal chains.\n")
    
    results = []
    
    # Run Tests
    for i, test in enumerate(TEST_CASES):
        print(f"Test {i+1}: {test['type']}")
        print(f"❓ Q: {test['question']}")
        
        start_time = time.time()
        try:
            response = await ask(test['question'], store)
            duration = time.time() - start_time
            
            result = {
                "id": i+1,
                "type": test["type"],
                "question": test["question"],
                "answer": response["answer"],
                "reasoning": response.get("reasoning", "N/A"),
                "interrogative": response.get("interrogative_type", "N/A"),
                "karaka": response.get("mapped_karaka", "N/A"),
                "duration": f"{duration:.2f}s",
                "status": "Success"
            }
            print(f"✅ A: {response['answer']}")
            print(f"   (mapped to {response.get('mapped_karaka', 'unknown')})\n")
            
        except Exception as e:
            print(f"❌ Failed: {e}\n")
            result = {
                "id": i+1,
                "type": test["type"],
                "question": test["question"],
                "error": str(e),
                "status": "Failed"
            }
        
        results.append(result)
        # Small pause to avoid aggressive rate limiting if using generic API
        await asyncio.sleep(1)

    # Generate Report
    generate_report(results)

def generate_report(results):
    report = "# 🧪 Kāraka Q&A Stress Test Report\n\n"
    report += f"**Date:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
    report += f"**Total Tests:** {len(results)}\n\n"
    
    report += "| ID | Type | Question | Answer | Mapped Role | Reasoning |\n"
    report += "|---|---|---|---|---|---|\n"
    
    for r in results:
        # Escape pipes for markdown table
        ans = r.get('answer', 'ERROR').replace('|', r'\|').replace('\n', ' ')
        reason = r.get('reasoning', '').replace('|', r'\|').replace('\n', ' ')
        
        report += f"| {r['id']} | {r['type']} | {r['question']} | {ans} | {r.get('karaka', '-')} | {reason} |\n"
    
    with open("QA_STRESS_TEST_REPORT.md", "w") as f:
        f.write(report)
    
    print("📄 Report saved to QA_STRESS_TEST_REPORT.md")

if __name__ == "__main__":
    asyncio.run(run_stress_test())
