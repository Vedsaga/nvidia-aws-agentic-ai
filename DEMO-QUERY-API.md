# Query API - READY FOR DEMO

## Endpoints

**POST** `/query/submit`
```bash
curl -X POST "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/query/submit" \
  -H "Content-Type: application/json" \
  -d '{"question": "Who eats mango?"}'
```

Response:
```json
{"query_id": "xxx", "question": "Who eats mango?", "status": "processing"}
```

**GET** `/query/status/{query_id}`
```bash
curl "https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod/query/status/{query_id}"
```

Response:
```json
{
  "query_id": "xxx",
  "question": "Who eats mango?",
  "status": "completed",
  "answer": "Rama eats mango.",
  "references": [{
    "sentence_text": "Rama eats mango.",
    "sentence_hash": "xxx",
    "doc_id": "xxx",
    "kg_snippet": {
      "nodes": [{"id": "Rama", "type": "PERSON"}, {"id": "mango", "type": "OBJECT"}],
      "edges": [{"source": "Rama", "target": "mango", "label": "Agent (Kartā)"}]
    }
  }]
}
```

## Features
✅ Async query processing
✅ Embedding-based retrieval
✅ NetworkX graph with Karaka relations
✅ Poll-based status checking
