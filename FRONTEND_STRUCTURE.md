# Frontend Structure

## Components Created

### 1. DocumentList (`frontend/src/components/document-list.tsx`)
- Left sidebar (25% width)
- Shows all uploaded documents
- Upload button with file picker
- Active document highlighting
- Loading states

### 2. DocumentStatus (`frontend/src/components/document-status.tsx`)
- Main panel for processing documents (75% width)
- Real-time status updates every 5s
- Shows:
  - Status, sentences processed, LLM calls
  - Progress bar
  - Live processing chain logs
- Disabled chat notice

### 3. ChatInterface (`frontend/src/components/chat-interface.tsx`)
- Split view: Chat (40%) + Knowledge Reference (35%)
- Chat panel:
  - Message history
  - Query input
  - Real-time answer polling (2s intervals)
- Reference panel:
  - Supporting evidence
  - Knowledge graph JSON
  - Processing chain details

## API Integration (`frontend/src/lib/api.ts`)

All endpoints from test-e2e-gssr.sh:

- `POST /upload` - Get pre-signed URL
- `GET /docs` - List all documents
- `GET /status/{job_id}` - Job status with progress
- `POST /query/submit` - Submit question
- `GET /query/status/{query_id}` - Get answer
- `GET /processing-chain/{job_id}` - Live logs

## Main Page (`frontend/src/app/page.tsx`)

Layout:
```
┌─────────────┬──────────────────────────────┐
│ DocumentList│  DocumentStatus (processing) │
│   (25%)     │  or ChatInterface (complete) │
│             │           (75%)              │
└─────────────┴──────────────────────────────┘
```

Polling:
- Job list: 5s intervals
- Job status: 5s intervals (when processing)
- Query status: 2s intervals (when waiting for answer)

## Environment

`.env.local`:
```
APP_API_GATEWAY_URL=https://7g3bdwsnsc.execute-api.us-east-1.amazonaws.com/prod
```

## Run

```bash
npm run dev --prefix frontend
```

Visit: http://localhost:3000
