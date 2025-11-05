# Design Document

## Overview

This design document outlines the architecture for enhancing the existing KārakaKG frontend application. The application is built with Next.js 16, React 19, TypeScript, and Tailwind CSS, using React Query for state management and API calls. The enhancement focuses on implementing a complete chat interface, knowledge graph reference panel, and improved processing visualization while maintaining the existing upload and status monitoring functionality.

The application follows a component-based architecture with clear separation of concerns between UI components, API layer, and state management. The design emphasizes real-time updates, error handling, and responsive user experience.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Application                      │
├─────────────────┬─────────────────┬─────────────────────────┤
│   DocumentList  │    MainPanel    │ KnowledgeReferencePanel │
│     (25%)       │     (75%)       │      (on-demand)        │
├─────────────────┼─────────────────┼─────────────────────────┤
│ - Document Items│ - EmptyStateView│ - Sentence Text         │
│ - Upload Button │ - ProcessingView│ - KG Snippet JSON       │
│ - Status Icons  │ - ChatView      │ - Processing Chain      │
│                 │ - ErrorView     │                         │
└─────────────────┴─────────────────┴─────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Layer (lib/api.ts)                   │
├─────────────────────────────────────────────────────────────┤
│ - HTTP Client (Axios)                                       │
│ - DynamoDB Response Normalization                           │
│ - Error Handling & Retry Logic                              │
│ - TypeScript Interfaces                                     │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              Serverless Backend (AWS)                       │
├─────────────────────────────────────────────────────────────┤
│ - Document Upload & Processing                               │
│ - GSSR Knowledge Graph Pipeline                             │
│ - Query Processing (Sync & Async)                          │
│ - Sentence-level Processing Chain                           │
└─────────────────────────────────────────────────────────────┘
```

### State Management Architecture

The application uses a combination of React Query for server state and React Context/useState for UI state:

```
┌─────────────────────────────────────────────────────────────┐
│                    Global State                              │
├─────────────────────────────────────────────────────────────┤
│ React Query Cache:                                          │
│ - documents: Document[]                                     │
│ - status/{jobId}: StatusData                               │
│ - processingChain/{jobId}: ProcessingChainData             │
│ - sentenceChain/{sentenceHash}: SentenceChainData          │
│                                                             │
│ Local UI State:                                             │
│ - activeJobId: string | null                               │
│ - activeReference: Reference | null                        │
│ - chatHistory: ChatMessage[]                               │
│ - panelLayout: '2-panel' | '3-panel'                       │
└─────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### Core Components

#### 1. App Layout (app/page.tsx)
- **Purpose**: Root component managing global layout and state
- **State**: activeJobId, activeReference, panelLayout
- **Responsibilities**: 
  - Coordinate between DocumentList and MainPanel
  - Manage panel layout transitions
  - Handle global error boundaries

#### 2. DocumentList Component
- **Purpose**: Display and manage document selection
- **API Integration**: GET /docs (on mount and refresh)
- **State**: documents[], loading, error
- **Key Features**:
  - Document status indicators (spinner, check, error icons)
  - Upload button integration
  - Auto-refresh on upload completion
  - Click handling for document selection

#### 3. MainPanel Component
- **Purpose**: Container for dynamic content based on selected document
- **Conditional Rendering**:
  - EmptyStateView: No document selected
  - ProcessingView: Document status is processing
  - ChatView: Document status is completed
  - ErrorView: Document status is failed
- **Props**: activeJobId, onReferenceClick

#### 4. ProcessingView Component
- **Purpose**: Real-time processing status and GSSR pipeline visualization
- **API Integration**: 
  - GET /status/{jobId} (polling every 5s)
  - GET /processing-chain/{jobId} (polling every 5s)
- **Key Features**:
  - Progress bar with percentage
  - Sentences processed counter (completed/total)
  - LLM calls counter
  - Live processing chain with timestamps
  - Pipeline stage indicators (D1_Entities, D2a_Kriya, D2b_Events, etc.)
  - Auto-transition to ChatView on completion

#### 5. ChatView Component
- **Purpose**: Interactive chat interface for querying completed documents
- **API Integration**: 
  - POST /query (primary, synchronous)
  - POST /query/submit + GET /query/status/{queryId} (fallback, asynchronous)
- **State**: chatHistory[], currentQuery, isLoading
- **Key Features**:
  - Message history display
  - Input with send button
  - Reference link rendering
  - Error message display
  - Loading states ("thinking..." indicator)

#### 6. KnowledgeReferencePanel Component
- **Purpose**: Display detailed knowledge graph data for selected references
- **API Integration**: GET /sentence-chain/{sentenceHash}
- **Key Features**:
  - Slide-in animation from right
  - Sentence text display
  - Formatted KG snippet JSON with syntax highlighting
  - Sentence processing chain with timestamps
  - Close button and outside-click handling

#### 7. UploadButton Component (Enhanced)
- **Purpose**: Handle file upload workflow with improved feedback
- **API Integration**: 
  - POST /upload
  - PUT to pre_signed_url
  - POST /trigger/{jobId}
- **Enhanced Features**:
  - File type validation (.txt only)
  - Progress indicators for each step
  - Error handling with specific messages
  - Auto-selection of uploaded document

### Data Models and Interfaces

```typescript
interface Document {
  job_id: string;
  filename: string;
  status: 'PENDING_UPLOAD' | 'processing_kg' | 'completed' | 'failed';
  created_at?: string;
}

interface StatusData {
  job_id: string;
  filename: string;
  status: string;
  total_sentences: number;
  completed_sentences: number;
  llm_calls_made: number;
  progress_percentage: number;
  created_at: string;
}

interface ProcessingChainEntry {
  stage: string;
  timestamp: string;
  sentence_number?: number;
  duration_ms?: number;
  status: 'running' | 'completed' | 'failed';
}

interface ChatMessage {
  id: string;
  type: 'user' | 'assistant' | 'error';
  content: string;
  references?: Reference[];
  timestamp: Date;
}

interface Reference {
  sentence_text: string;
  sentence_hash: string;
  kg_snippet: {
    nodes: Array<{id: string; label: string; node_type: string}>;
    edges: Array<{source: string; target: string; label: string}>;
  };
}

interface QueryResponse {
  answer: string;
  references: Reference[];
}

interface SentenceChainData {
  sentence_hash: string;
  processing_stages: Array<{
    stage: string;
    timestamp: string;
    duration_ms: number;
    status: string;
  }>;
}
```

## Error Handling

### Error Handling Strategy

The application implements a multi-layered error handling approach:

1. **API Layer**: Centralized error handling in api.ts with specific error types
2. **Component Layer**: Local error states and user-friendly messages
3. **Global Layer**: Error boundaries for unexpected errors

### Error Types and Handling

```typescript
enum ErrorType {
  NETWORK_ERROR = 'NETWORK_ERROR',
  VALIDATION_ERROR = 'VALIDATION_ERROR',
  API_ERROR = 'API_ERROR',
  UPLOAD_ERROR = 'UPLOAD_ERROR',
  PROCESSING_ERROR = 'PROCESSING_ERROR'
}

interface AppError {
  type: ErrorType;
  message: string;
  details?: any;
  retryable: boolean;
}
```

### Specific Error Scenarios

1. **Upload Errors**:
   - File validation: Show toast with validation message
   - POST /upload failure: "Error: Could not initiate upload. [API Error]"
   - S3 PUT failure: "Error: File upload failed. Please try again."
   - POST /trigger failure: Show error with manual retry option

2. **Polling Errors**:
   - GET /status failures: Retry up to 3 times, then show connection banner
   - GET /processing-chain 502: Show "Could not load processing log" in chain area
   - Network timeouts: Continue retrying with exponential backoff

3. **Query Errors**:
   - POST /query failure: Display error in chat as error message
   - POST /query/submit 400: Ensure correct field name ("question" not "query")
   - Async query timeout: Show timeout message with retry option

4. **Reference Panel Errors**:
   - GET /sentence-chain failure: "Could not load sentence processing details"
   - Invalid reference data: Graceful degradation with available data



### Performance Considerations

1. **Polling Optimization**:
   - Intelligent polling intervals based on status
   - Automatic polling stop on completion/failure
   - Debounced API calls to prevent excessive requests

2. **Memory Management**:
   - Chat history limits to prevent memory leaks
   - Proper cleanup of polling intervals
   - React Query cache management

3. **Bundle Optimization**:
   - Code splitting for large components
   - Lazy loading of reference panel
   - Optimized re-renders with React.memo

4. **API Optimization**:
   - Request deduplication with React Query
   - Proper error retry strategies
   - Caching of static data (document list)

## Implementation Notes

### Technology Stack Integration

- **Next.js 16**: App router for routing and SSR capabilities
- **React 19**: Latest React features including concurrent rendering
- **TypeScript**: Full type safety across components and API layer
- **Tailwind CSS**: Utility-first styling with custom design system
- **React Query**: Server state management with caching and synchronization
- **Axios**: HTTP client with interceptors for error handling
- **Lucide React**: Icon library for consistent iconography

### Development Workflow

1. **Component Development**: Start with TypeScript interfaces and props
2. **API Integration**: Implement API calls with proper error handling
3. **State Management**: Add React Query hooks for server state
4. **UI Implementation**: Build responsive UI with Tailwind CSS
5. **Testing**: Add tests for critical paths and error scenarios
6. **Performance**: Optimize rendering and API calls

### Deployment Considerations

- **Environment Variables**: API URL configuration for different environments
- **Build Optimization**: Static generation where possible
- **Error Monitoring**: Integration with error tracking services
- **Performance Monitoring**: Real user monitoring for API response times