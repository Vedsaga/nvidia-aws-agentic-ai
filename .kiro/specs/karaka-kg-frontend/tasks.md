# Implementation Plan

- [ ] 1. Enhance API layer and data models
  - Update lib/api.ts with missing endpoints and proper TypeScript interfaces
  - Add error handling utilities and response normalization
  - Implement query retry logic and timeout handling
  - _Requirements: 6.1, 6.2, 6.9, 8.6_

- [ ] 2. Create core UI components and layout system
- [ ] 2.1 Implement EmptyStateView component
  - Create component with illustration and "Upload your first document to begin" message
  - Add proper styling with Tailwind CSS
  - _Requirements: 3.6, 7.3_

- [ ] 2.2 Create ErrorView component for failed documents
  - Display error state with failure details
  - Add retry options where applicable
  - _Requirements: 3.5, 6.7_

- [ ] 2.3 Enhance MainPanel component with conditional rendering
  - Implement view switching based on document status
  - Add smooth transitions between views
  - _Requirements: 7.4, 7.6_

- [ ] 3. Implement ProcessingView with real-time monitoring
- [ ] 3.1 Create ProcessingView component structure
  - Build layout matching the specification with status, progress, sentences, and LLM calls
  - Add progress bar and counters display
  - _Requirements: 2.1, 2.9_

- [ ] 3.2 Implement processing chain visualization
  - Create live processing chain list with timestamped entries
  - Display pipeline stages (D1_Entities, D2a_Kriya, D2b_Events) with status indicators
  - Handle 502 errors gracefully with fallback message
  - _Requirements: 2.3, 2.4, 2.8_

- [ ] 3.3 Add polling logic for status and processing chain
  - Implement 5-second polling for GET /status and GET /processing-chain
  - Add connection error handling with retry logic and banner display
  - Auto-stop polling on completion/failure and transition to appropriate view
  - _Requirements: 2.2, 2.5, 2.6, 2.7_

- [ ] 4. Build ChatView with query interface
- [ ] 4.1 Create ChatView component structure
  - Build chat interface with message history and input area
  - Implement message display with user/assistant/error styling
  - Add "thinking..." loading indicator
  - _Requirements: 4.1, 4.2, 4.9_

- [ ] 4.2 Implement synchronous query functionality
  - Add POST /query integration with proper error handling
  - Display answers in chat history with reference links
  - Handle API errors with user-friendly messages in chat
  - _Requirements: 4.2, 4.3, 4.6, 4.7_

- [ ] 4.3 Add reference link rendering and interaction
  - Create clickable "Reference [1]", "Reference [2]" links after answers
  - Implement reference click handling to trigger KnowledgeReferencePanel
  - Store reference data for panel display
  - _Requirements: 4.4, 4.5_

- [ ] 4.4 Implement asynchronous query fallback
  - Add POST /query/submit with correct "question" field
  - Implement polling for GET /query/status with 2-second intervals
  - Handle async query completion and error states
  - _Requirements: 8.2, 8.3, 8.4, 8.5, 8.6, 8.7_

- [ ] 5. Create KnowledgeReferencePanel for detailed reference data
- [ ] 5.1 Build KnowledgeReferencePanel component structure
  - Create sliding panel layout with close functionality
  - Implement 3-panel layout expansion and smooth animations
  - Add outside-click and close button handling
  - _Requirements: 5.1, 5.6, 7.2, 7.5_

- [ ] 5.2 Display reference content and knowledge graph data
  - Show sentence text at top with source context
  - Format and display kg_snippet JSON with syntax highlighting
  - Handle nodes and edges display in readable format
  - _Requirements: 5.2, 5.3, 5.8_

- [ ] 5.3 Implement sentence processing chain display
  - Extract sentence_hash and call GET /sentence-chain
  - Display processing chain with timestamped D1/D2a/D2b stages
  - Handle API failures with appropriate error messages
  - _Requirements: 5.4, 5.5, 5.7_

- [ ] 6. Enhance DocumentList with improved status indicators
- [ ] 6.1 Add visual status indicators
  - Implement spinner icons for processing documents
  - Add green check icons for completed documents
  - Add error icons for failed documents
  - _Requirements: 3.2, 3.8_

- [ ] 6.2 Improve document selection and state management
  - Maintain selected document across refreshes
  - Auto-select newly uploaded documents
  - Add proper click handling for different document states
  - _Requirements: 3.3, 3.4, 3.5, 3.7, 3.8_

- [ ] 7. Enhance UploadButton with better feedback and error handling
- [ ] 7.1 Add comprehensive file validation
  - Enforce .txt file type restriction
  - Prevent multiple file selection
  - Show validation error toasts for invalid files
  - _Requirements: 1.1, 6.1_

- [ ] 7.2 Implement detailed upload progress tracking
  - Show "Uploading..." status during S3 upload
  - Update to "Processing" status after trigger
  - Add specific error messages for each failure point
  - Auto-select uploaded document and switch to ProcessingView
  - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

- [ ] 8. Implement global state management and layout coordination
- [ ] 8.1 Create global state context for activeJobId and activeReference
  - Implement React context for shared state management
  - Add state persistence and synchronization between components
  - Handle state updates for document selection and reference clicks
  - _Requirements: 7.1, 7.4_

- [ ] 8.2 Add panel layout management
  - Implement 2-panel to 3-panel layout transitions
  - Add responsive behavior for different screen sizes
  - Ensure smooth animations and proper width adjustments
  - _Requirements: 7.2, 7.5, 7.6, 7.7_

- [ ] 9. Add comprehensive error handling and user feedback
- [ ] 9.1 Implement toast notification system
  - Create toast component for upload errors and success messages
  - Add error toasts for API failures with specific messages
  - Implement non-blocking connection error banners
  - _Requirements: 6.2, 6.3, 6.5_

- [ ] 9.2 Add error boundaries and recovery mechanisms
  - Implement React error boundaries for unexpected errors
  - Add retry mechanisms for failed operations
  - Ensure application stability during network issues
  - _Requirements: 6.9, 2.7_

- [ ] 10. Final integration and polish
- [ ] 10.1 Integrate all components into main application
  - Wire up all components with proper props and state management
  - Ensure proper data flow between DocumentList, MainPanel, and KnowledgeReferencePanel
  - Test complete user workflows from upload to query to reference viewing
  - _Requirements: All requirements integration_

- [ ] 10.2 Add responsive design and accessibility improvements
  - Ensure proper responsive behavior across screen sizes
  - Add keyboard navigation support
  - Implement proper ARIA labels and accessibility features
  - _Requirements: 7.7, 7.8_