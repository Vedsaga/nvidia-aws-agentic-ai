# Requirements Document

## Introduction

This document outlines the requirements for enhancing the existing KārakaKG frontend application. The application currently supports document upload and basic status monitoring. We need to extend it with a complete chat interface, knowledge graph reference panel, and improved processing visualization to match the specification provided. The application interacts with a serverless backend that processes documents through a multi-stage GSSR (Generate, Score, Select, Refine) pipeline for knowledge graph extraction.

## Requirements

### Requirement 1

**User Story:** As a user, I want to upload .txt documents to the KārakaKG service with immediate feedback and status tracking, so that I can process them into a knowledge graph for later querying.

#### Acceptance Criteria

1. WHEN the user clicks the "+ New Upload" button THEN the system SHALL display a file picker that accepts only .txt files and allows single file selection
2. WHEN a file is selected THEN the system SHALL immediately add it to the document list with "Uploading..." status and set it as the active document
3. WHEN the upload is initiated THEN the system SHALL call POST /upload with {"filename": "filename.txt"} to get job_id and pre_signed_url
4. WHEN the pre_signed_url is received THEN the system SHALL upload the file content via PUT request to the S3 pre_signed_url
5. WHEN the S3 upload succeeds THEN the system SHALL call POST /trigger/{job_id} to start backend processing
6. WHEN processing starts THEN the system SHALL update status to "Processing" and switch to ProcessingView automatically
7. IF POST /upload fails THEN the system SHALL show error toast with API error message
8. IF S3 PUT fails THEN the system SHALL show "File upload failed. Please try again." toast
9. IF POST /trigger fails THEN the system SHALL show error but allow manual retry

### Requirement 2

**User Story:** As a user, I want to see detailed real-time processing status with GSSR pipeline visibility, so that I understand the knowledge graph extraction progress and know when documents are ready for querying.

#### Acceptance Criteria

1. WHEN a document has status "processing_kg" or similar THEN the system SHALL display ProcessingView with status, progress percentage, sentences processed (completed_sentences/total_sentences), and llm_calls_made
2. WHEN ProcessingView is active THEN the system SHALL poll GET /status/{job_id} every 5 seconds to update progress metrics
3. WHEN ProcessingView is active THEN the system SHALL poll GET /processing-chain/{job_id} every 5 seconds to update live processing chain with timestamped entries
4. WHEN processing chain data is received THEN the system SHALL display entries showing pipeline stages (D1_Entities, D2a_Kriya, D2b_Events, etc.) with timestamps
5. WHEN the status becomes "completed" THEN the system SHALL stop polling and automatically switch to ChatView
6. WHEN the status becomes "failed" THEN the system SHALL stop polling and show error state with failure details
7. IF GET /status fails 3+ consecutive times THEN the system SHALL show non-blocking "Connection issue: Retrying status..." banner
8. IF GET /processing-chain returns 502 THEN the system SHALL show "Could not load processing log" in chain area while maintaining other ProcessingView functionality
9. WHEN processing is active THEN the system SHALL disable chat input with message "Chat will be enabled once processing is complete"

### Requirement 3

**User Story:** As a user, I want to view and select from all my uploaded documents with clear status indicators, so that I can interact with different processed documents and understand their current state.

#### Acceptance Criteria

1. WHEN the application loads THEN the system SHALL call GET /docs to fetch all existing documents and normalize DynamoDB-style responses
2. WHEN documents are fetched THEN the system SHALL display them in DocumentList with filename and status indicators (spinner for processing, green check for completed, error icon for failed)
3. WHEN a user clicks on a completed document THEN the system SHALL set it as active_job_id and display ChatView with enabled input
4. WHEN a user clicks on a processing document THEN the system SHALL set it as active_job_id and display ProcessingView with polling enabled
5. WHEN a user clicks on a failed document THEN the system SHALL set it as active_job_id and display error state with failure details
6. WHEN no documents exist THEN the system SHALL show EmptyStateView with illustration and "Upload your first document to begin" message
7. WHEN documents list is refreshed THEN the system SHALL maintain the currently selected document if it still exists
8. WHEN a new document is uploaded THEN the system SHALL add it to the top of the list and automatically select it

### Requirement 4

**User Story:** As a user, I want to ask questions about completed documents through a chat interface with reference support, so that I can extract information from the processed knowledge graph and see supporting evidence.

#### Acceptance Criteria

1. WHEN a completed document is selected THEN the system SHALL display ChatView with enabled chat input and any existing chat history
2. WHEN a user types a question and presses Send THEN the system SHALL disable input, show "thinking..." indicator, and call POST /query with {"query": "question text"}
3. WHEN the query response is received THEN the system SHALL display the answer text in chat history and re-enable input
4. WHEN the response contains non-empty references array THEN the system SHALL render clickable "Reference [1]", "Reference [2]" links after the answer
5. WHEN a reference link is clicked THEN the system SHALL slide in KnowledgeReferencePanel from the right and store the reference data
6. IF POST /query fails THEN the system SHALL display error message in chat styled as error: "Sorry, an error occurred: [API Error Message]"
7. IF POST /query returns internal server error THEN the system SHALL show appropriate error message in chat
8. WHEN a processing or failed document is selected THEN the system SHALL disable chat input with appropriate status message
9. WHEN chat is active THEN the system SHALL maintain conversation history for the session

### Requirement 5

**User Story:** As a user, I want to view detailed knowledge graph data and sentence-level processing information for specific references, so that I can understand the source evidence and how it was extracted.

#### Acceptance Criteria

1. WHEN a user clicks a reference link THEN the system SHALL slide in KnowledgeReferencePanel from the right, expanding to 3-panel layout
2. WHEN the reference panel opens THEN the system SHALL display the sentence_text from the reference at the top with source document context
3. WHEN the reference panel opens THEN the system SHALL display the kg_snippet JSON (nodes and edges) in a formatted code block with syntax highlighting
4. WHEN the reference panel opens THEN the system SHALL extract sentence_hash from reference and call GET /sentence-chain/{sentence_hash}
5. WHEN sentence chain data is received THEN the system SHALL populate "Sentence Processing Chain" with timestamped entries showing D1_Entities, D2a_Kriya, D2b_Events stages with execution times
6. WHEN the user clicks close button or outside panel THEN the system SHALL slide panel out and return to 2-panel layout
7. WHEN sentence chain call fails THEN the system SHALL show "Could not load sentence processing details" in the chain section
8. WHEN kg_snippet contains nodes and edges THEN the system SHALL display them in readable format showing entity relationships

### Requirement 6

**User Story:** As a user, I want the application to handle errors gracefully with clear feedback and recovery options, so that I understand what went wrong and can take appropriate action.

#### Acceptance Criteria

1. WHEN file upload validation fails (non-.txt file or multiple files) THEN the system SHALL prevent API calls and show validation error toast
2. WHEN POST /upload fails THEN the system SHALL show toast: "Error: Could not initiate upload. [API Error Message]"
3. WHEN S3 PUT to pre_signed_url fails THEN the system SHALL show toast: "Error: File upload failed. Please try again."
4. WHEN POST /trigger fails THEN the system SHALL show error but allow manual retry via trigger button
5. WHEN GET /status polling fails 3+ consecutive times THEN the system SHALL show non-blocking banner: "Connection issue: Retrying status..." and continue retrying
6. WHEN GET /processing-chain returns 502 THEN the system SHALL show "Could not load processing log" in chain area while maintaining other functionality
7. WHEN POST /query fails THEN the system SHALL display error in chat: "Sorry, an error occurred: [API Error Message]"
8. WHEN GET /sentence-chain fails THEN the system SHALL show "Could not load sentence processing details" in reference panel
9. WHEN network errors occur THEN the system SHALL log errors to console and maintain application stability without crashes

### Requirement 7

**User Story:** As a user, I want a responsive and intuitive multi-panel interface layout that adapts to my workflow, so that I can efficiently navigate between documents and interact with knowledge graph data.

#### Acceptance Criteria

1. WHEN the application loads THEN the system SHALL display a 2-panel layout with DocumentList (25% width) and MainPanel (75% width)
2. WHEN a reference is clicked THEN the system SHALL expand to 3-panel layout with KnowledgeReferencePanel sliding in from right
3. WHEN no document is selected THEN the system SHALL show EmptyStateView in MainPanel with illustration and "Upload your first document to begin" text
4. WHEN active_job_id changes THEN the system SHALL update MainPanel to show appropriate view (EmptyState, ProcessingView, ChatView, or ErrorView)
5. WHEN KnowledgeReferencePanel is open THEN the system SHALL adjust MainPanel width to accommodate 3-panel layout
6. WHEN panels transition THEN the system SHALL use smooth animations for sliding and resizing
7. WHEN on smaller screens THEN the system SHALL maintain usability with responsive breakpoints
8. WHEN user interactions occur THEN the system SHALL provide immediate visual feedback (loading states, hover effects, active states)
### Require
ment 8

**User Story:** As a user, I want support for both synchronous and asynchronous query processing, so that I can get quick answers for simple questions and handle complex queries that require longer processing time.

#### Acceptance Criteria

1. WHEN a user submits a query THEN the system SHALL use POST /query (synchronous) as the primary method for immediate responses
2. IF POST /query takes too long or fails THEN the system SHALL fallback to async flow using POST /query/submit with {"question": "question text"}
3. WHEN using async flow THEN the system SHALL receive query_id from POST /query/submit and poll GET /query/status/{query_id} every 2 seconds
4. WHEN async query status becomes "completed" THEN the system SHALL display the answer and references in chat and stop polling
5. WHEN async query status becomes "failed" THEN the system SHALL display error message in chat and stop polling
6. WHEN using POST /query/submit THEN the system SHALL send {"question": "text"} not {"query": "text"} to avoid 400 "question is required" error
7. WHEN async polling is active THEN the system SHALL show appropriate loading indicator in chat
8. WHEN either sync or async query succeeds THEN the system SHALL handle references identically for consistency