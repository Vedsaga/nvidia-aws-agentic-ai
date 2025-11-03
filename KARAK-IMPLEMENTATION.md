# 6 Karaka Implementation

## Changes Made

### 1. New Karaka Prompt
**File**: `prompts/karak_prompt.txt`

Extracts 6 core Karaka roles:
1. **Agent (Kartā)**: Who does the action
2. **Object (Karma)**: What receives the action  
3. **Instrument (Karaṇa)**: Tool/means used
4. **Recipient (Sampradāna)**: Beneficiary/destination
5. **Source (Apādāna)**: Origin/separation point
6. **Location (Adhikaraṇa)**: Where/when action occurs

### 2. Updated Lambda: l11_build_events
**File**: `src/lambda_src/kg_agents/l11_build_events/lambda_function.py`

- Calls LLM with karak_prompt.txt
- Passes sentence, entities, and verb
- Extracts Karaka relationships
- Stores in events.json with structure:
```json
{
  "sentence": "...",
  "entities": [...],
  "verb": "...",
  "karakas": [
    {"role": "Agent", "entity": "..."},
    {"role": "Object", "entity": "..."}
  ]
}
```

### 3. Updated Lambda: l16_graph_edge_ops
**File**: `src/lambda_src/graph_ops/l16_graph_edge_ops/lambda_function.py`

- Reads Karaka relationships from events.json
- Creates primary edge: Agent -> Object (with verb)
- Creates secondary edges for other Karakas (Instrument, Recipient, Source, Location)
- Each edge stores:
  - `edge_type`: 'karaka'
  - `relation`: verb
  - `karaka_role`: specific role (Agent->Object, Instrument, etc.)

## Example

**Input**: "Rama gives book to Sita in library."

**Extracted**:
- Entities: ["Rama", "book", "Sita", "library"]
- Verb: "give"
- Karakas:
  - Agent: Rama
  - Object: book
  - Recipient: Sita
  - Location: library

**Graph**:
- Rama -> book [relation=give, karaka_role=Agent->Object]
- Rama -> Sita [relation=give, karaka_role=Recipient]
- Rama -> library [relation=give, karaka_role=Location]

## Testing

Run: `python3 test-karak-local.py`

Shows expected prompt and output format.

## Deployment

Deploy with: `./deploy-model.sh`

Note: AWS permissions currently blocked in lab environment.
