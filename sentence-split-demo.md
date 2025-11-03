# Sentence Splitting Output Demo

## Input Document
**File:** `trigger-test.txt`
```
Rama eats mango. Sita sings beautifully.
```

## Sentence Splitting Process

### Step 1: L3 SanitizeDoc Lambda
The L3 lambda reads the document and splits it using either:
1. **LLM-based splitting** (primary method)
2. **Regex fallback** (if LLM fails)

### Step 2: Output Format
The sentences are saved to S3 as `sentences.json`:

```json
[
  {
    "text": "Rama eats mango. ",
    "hash": "a1b2c3d4e5f6...",
    "job_id": "d110a076-d160-464a-854b-8a7a4435e78d"
  },
  {
    "text": "Sita sings beautifully. ",
    "hash": "f6e5d4c3b2a1...",
    "job_id": "d110a076-d160-464a-854b-8a7a4435e78d"
  }
]
```

**Location:** `s3://verified-documents-{account}-{region}/{job_id}/sentences.json`

### Step 3: Sentence Details

| # | Sentence Text | Hash (first 16 chars) | Processing |
|---|--------------|----------------------|------------|
| 1 | "Rama eats mango. " | a1b2c3d4e5f6... | ✅ Sent to Step Functions |
| 2 | "Sita sings beautifully. " | f6e5d4c3b2a1... | ✅ Sent to Step Functions |

## Key Features

### 1. Hash Generation
Each sentence gets a SHA-256 hash for:
- Deduplication across documents
- Tracking processing status
- Referencing in knowledge graph

### 2. Whitespace Preservation
- Sentences end with punctuation + space
- Preserves original formatting
- Enables perfect reconstruction

### 3. Fidelity Validation
The system validates that:
```
joined_sentences == original_document
```

If validation fails, it falls back to regex splitting.

## Verification Commands

### Check Job Status
```bash
curl "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/status/d110a076-d160-464a-854b-8a7a4435e78d"
```

**Expected Output:**
```json
{
  "job_id": "d110a076-d160-464a-854b-8a7a4435e78d",
  "filename": "trigger-test.txt",
  "status": "processing_kg",
  "total_sentences": 2,
  "completed_sentences": 0,
  "llm_calls_made": 0
}
```

### Download Sentences (requires AWS credentials)
```bash
aws s3 cp s3://verified-documents-151534200269-us-east-1/d110a076-d160-464a-854b-8a7a4435e78d/sentences.json -
```

## Processing Flow

```
Input Document (trigger-test.txt)
    ↓
L2 ValidateDoc (S3 trigger)
    ↓
L3 SanitizeDoc
    ↓
Split into sentences
    ↓
Generate hashes
    ↓
Save to verified bucket
    ↓
Update DynamoDB (total_sentences: 2)
    ↓
Start Step Functions
    ↓
Process each sentence through KG pipeline
```

## Example: Longer Document

**Input:**
```
The Mahabharata is an ancient Indian epic. It tells the story of the Kurukshetra War. The war was fought between the Pandavas and Kauravas. Krishna served as Arjuna's charioteer.
```

**Output:** 4 sentences
```json
[
  {"text": "The Mahabharata is an ancient Indian epic. ", "hash": "..."},
  {"text": "It tells the story of the Kurukshetra War. ", "hash": "..."},
  {"text": "The war was fought between the Pandavas and Kauravas. ", "hash": "..."},
  {"text": "Krishna served as Arjuna's charioteer. ", "hash": "..."}
]
```

Each sentence then goes through:
1. Entity extraction (L9)
2. Kriya extraction (L10)
3. Event building (L11)
4. Event auditing (L12)
5. Relation extraction (L13)
6. Attribute extraction (L14)
7. Graph node operations (L15)
8. Graph edge operations (L16)
9. Embedding generation (L8)
