# Async Microservice Architecture

## Overview

This directory contains the complete design documentation for our async microservice architecture. Each user flow is documented in its own file for better organization and maintainability.

## Core Principles

1. **One-Way API Execution** - Each API call either succeeds or fails, no retries
2. **Status-Driven Flow** - Every operation updates job status in SQLite
3. **Client-Controlled Execution** - Client triggers each step independently
4. **Failure Transparency** - All failure reasons captured and exposed
5. **Per-User Scaling** - SQLite enables user-specific databases

## Architecture Files

### Foundation

- [`error-handling.md`](./error-handling.md) - Application-wide error tracking and tracing system
- [`global-status-enum.md`](./global-status-enum.md) - Centralized status definitions

### User Flows

- [`upload-flow.md`](./upload-flow.md) - Document upload with deduplication
- [`validation-flow.md`](./validation-flow.md) - Document validation (TODO)
- [`sentence-split-flow.md`](./sentence-split-flow.md) - Sentence splitting (TODO)
- [`kg-processing-flow.md`](./kg-processing-flow.md) - Knowledge graph processing (TODO)
- [`query-flow.md`](./query-flow.md) - Query processing and RAG (TODO)

## Implementation Status

| Flow | Status | File |
| ------ | -------- | ------ |
| Error Handling | ✅ Complete | `error-handling.md` |
| Upload Flow | ✅ Complete | `upload-flow.md` |
| Validation Flow | 🔄 TODO | `validation-flow.md` |
| Sentence Split | 🔄 TODO | `sentence-split-flow.md` |
| KG Processing | 🔄 TODO | `kg-processing-flow.md` |
| Query Flow | 🔄 TODO | `query-flow.md` |

## Database Design

Each user has their own SQLite database containing:

- **documents** - Upload and document metadata
- **sentences** - Sentence-level processing status
- **request_traces** - End-to-end request tracking
- **error_logs** - Detailed error information

## Key Benefits

- **Granular Control** - Client controls execution pace and retry logic
- **Failure Transparency** - Every failure reason captured and exposed
- **Horizontal Scaling** - Each API endpoint scales independently
- **User Isolation** - SQLite per user prevents cross-contamination
- **Debugging** - Complete audit trail via trace_id
- **Flexibility** - Different retry strategies per operation
- **Testability** - Each microservice tested in isolation

## Getting Started

1. Read [`error-handling.md`](./error-handling.md) for the foundation
2. Review [`upload-flow.md`](./upload-flow.md) as an example implementation
3. Follow the same pattern for implementing additional flows
