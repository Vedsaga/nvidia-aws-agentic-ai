"""
Stress Test Suite for Kāraka Extraction
Verifies if the extraction pipeline correctly identifies frames and causal links.
"""

import asyncio
import json
import time
from frame_extractor import extract_frame

TEST_SENTENCES = [
    {
        "id": "T1",
        "text": "This discovery led to a collaboration between IIT Delhi and Stanford University.",
        "expected_kriya": "lead",
        "expected_karta": "This discovery",
        "expected_karma": "a collaboration",
        "desc": "Causal Agent (Event as Agent)"
    },
    {
        "id": "T2",
        "text": "The funding enabled them to conduct clinical trials in three countries.",
        "expected_kriya": "enable",
        "expected_karta": "The funding",
        "expected_sampradana": "them",
        "desc": "Enabling Action (Instrumental)"
    },
    {
        "id": "T3",
        "text": "The study was conducted in Copenhagen using advanced imaging tools by the team.",
        "expected_kriya": "conduct",
        "expected_karta": "the team",
        "expected_karma": "The study",
        "expected_locus_space": "Copenhagen",
        "desc": "Passive Voice with explicit Agent"
    },
    {
        "id": "T4",
        "text": "Dr. Rao presented the findings at the global conference in Geneva on Tuesday.",
        "expected_kriya": "present",
        "expected_karta": "Dr. Rao",
        "expected_karma": "the findings",
        "expected_locus_space": "the global conference in Geneva", 
        "expected_locus_time": "Tuesday",
        "desc": "Complex Locus (Space + Time)"
    }
]

async def run_extraction_test():
    print(f"🚀 Starting Extraction Stress Test ({len(TEST_SENTENCES)} complex cases)...\n")
    
    results = []
    
    for test in TEST_SENTENCES:
        print(f"🔹 CASE {test['id']}: {test['desc']}")
        print(f"   Input: \"{test['text']}\"")
        
        start_time = time.time()
        try:
            # 1. Extract
            frame = await extract_frame(0, test['text'])
            duration = time.time() - start_time
            
            if not frame:
                print("   ❌ Failed: No frame returned")
                continue
                
            print(f"   ⏱️  Extracted in {duration:.2f}s")
            
            # 2. Verify
            errors = []
            
            # Check Kriyā (fuzzy match for root)
            if test['expected_kriya'].lower() not in frame.kriya.lower():
                errors.append(f"Kriyā mismatch: expected '{test['expected_kriya']}', got '{frame.kriya}'")
            
            # Check Kartā
            if 'expected_karta' in test:
                got_karta = frame.karta or ""
                if test['expected_karta'].lower() not in got_karta.lower():
                    errors.append(f"Kartā mismatch: expected '{test['expected_karta']}', got '{got_karta}'")
            
            # Check Karma
            if 'expected_karma' in test:
                got_karma = frame.karma or ""
                if test['expected_karma'].lower() not in got_karma.lower():
                    errors.append(f"Karma mismatch: expected '{test['expected_karma']}', got '{got_karma}'")

            # Check Locus Space
            if 'expected_locus_space' in test:
                got_space = frame.locus_space or ""
                if test['expected_locus_space'].lower() not in got_space.lower() and got_space.lower() not in test['expected_locus_space'].lower():
                    errors.append(f"Locus Space mismatch: expected '{test['expected_locus_space']}', got '{got_space}'")
            
            # Result
            if not errors:
                print("   ✅ PASS: Frame structure matches expectations.")
                print(f"      Frame: {json.dumps(frame.to_display(), indent=2)}")
                results.append({"id": test['id'], "status": "PASS", "frame": frame})
            else:
                print("   ⚠️ PARTIAL MATCH / CHECK REQUIRED:")
                for e in errors:
                    print(f"      - {e}")
                print(f"      Frame: {json.dumps(frame.to_display(), indent=2)}")
                results.append({"id": test['id'], "status": "WARN", "frame": frame})
                
        except Exception as e:
            print(f"   ❌ ERROR: {e}")
            results.append({"id": test['id'], "status": "ERROR", "error": str(e)})
        
        print("-" * 60)
        # Sleep to avoid rate limits
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(run_extraction_test())
