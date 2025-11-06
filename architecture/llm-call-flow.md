# LLM Call Flow

## Overview

Centralized async LLM processing system with queue-based task management and single-worker execution to prevent LLM overload.

## Architecture Principles

### 1. **Queue-Based Processing**
- All LLM requests go through centralized queue
- Single worker processes tasks sequentially
- Prevents LLM rate limiting and overload

### 2. **Async Request/Response**
- Immediate request acceptance with pending status
- Client polling for completion status
- Decoupled from business logic flows

### 3. **Worker Management**
- Single worker processes queue continuously
- Idle mode when no tasks pending
- Auto-trigger on new task arrival

## Database Schema

```sql
-- LLM request queue and responses
CREATE TABLE llm_requests (
    request_id TEXT PRIMARY KEY,
    
    -- Request details (pre-processed, ready to send)
    system_prompt TEXT,                -- Complete system prompt (ready to send)
    user_prompt TEXT NOT NULL,         -- Complete user prompt (ready to send)
    operation TEXT NOT NULL,           -- sentence_split, extract_entities, etc. (for logging)
    
    -- LLM parameters
    temperature REAL DEFAULT 0.6,
    max_tokens INTEGER DEFAULT 4000,
    reasoning_enabled BOOLEAN DEFAULT FALSE,    -- Was reasoning mode enabled for this request?
    json_mode_enabled BOOLEAN DEFAULT FALSE,
    
    -- LLM endpoint configuration
    llm_provider TEXT NOT NULL,        -- openai, anthropic, nvidia, etc.
    llm_model TEXT NOT NULL,           -- gpt-4, claude-3, llama-70b, etc.
    llm_endpoint_url TEXT,             -- Actual endpoint URL used
    
    -- Context and tracing
    context_data TEXT,                 -- JSON blob with operation context
    parent_trace_id TEXT,              -- Links to calling operation
    
    -- Status and timing
    status TEXT NOT NULL,              -- pending, processing, completed, failed
    priority INTEGER DEFAULT 5,       -- 1=highest, 10=lowest
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    
    -- Worker assignment
    assigned_worker_id TEXT,           -- Which worker is processing this
    
    -- Token tracking (provider-specific)
    prompt_tokens INTEGER,             -- Input tokens (if supported by provider)
    completion_tokens INTEGER,         -- Output tokens (if supported by provider)  
    total_tokens INTEGER,              -- Total tokens (if supported by provider)
    
    -- Response data
    response_data TEXT,                -- Raw LLM response
    parsed_response TEXT,              -- Processed/validated response
    error_message TEXT,
    failure_reason TEXT,
    
    -- Timestamps
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    started_at INTEGER,
    completed_at INTEGER,
    
    -- Performance metrics
    processing_duration_ms INTEGER,
    llm_call_duration_ms INTEGER,
    
    FOREIGN KEY (parent_trace_id) REFERENCES request_traces(trace_id)
);

-- Worker status tracking (supports multiple workers)
CREATE TABLE llm_worker_status (
    worker_id TEXT PRIMARY KEY,       -- worker_1, worker_2, etc.
    worker_type TEXT NOT NULL,        -- lambda, ecs, local
    status TEXT NOT NULL,             -- idle, processing, error, offline
    current_request_id TEXT,
    
    -- Worker capabilities
    supported_providers TEXT,         -- JSON array: ["openai", "anthropic"]
    max_concurrent_requests INTEGER DEFAULT 1,
    current_load INTEGER DEFAULT 0,
    
    -- Health tracking
    last_heartbeat INTEGER DEFAULT (strftime('%s', 'now')),
    processed_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    avg_processing_time_ms INTEGER DEFAULT 0,
    
    -- Worker metadata
    deployment_info TEXT,             -- JSON blob with deployment details
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (current_request_id) REFERENCES llm_requests(request_id)
);

-- LLM provider configurations
CREATE TABLE llm_providers (
    provider_id TEXT PRIMARY KEY,     -- openai, anthropic, nvidia, etc.
    provider_name TEXT NOT NULL,
    base_url TEXT NOT NULL,
    api_key_env_var TEXT,             -- Environment variable name for API key
    
    -- Rate limiting (for monitoring, not enforcement)
    requests_per_minute INTEGER DEFAULT 60,
    tokens_per_minute INTEGER DEFAULT 100000,
    

    
    -- Provider capabilities
    supports_temperature BOOLEAN DEFAULT TRUE,
    supports_max_tokens BOOLEAN DEFAULT TRUE,
    supports_streaming BOOLEAN DEFAULT FALSE,
    supports_reasoning BOOLEAN DEFAULT FALSE,    -- Does provider support reasoning mode?
    supports_system_prompts BOOLEAN DEFAULT TRUE,
    supports_json_mode BOOLEAN DEFAULT FALSE,
    supports_function_calling BOOLEAN DEFAULT FALSE,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    health_check_url TEXT,
    last_health_check INTEGER,
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
);

-- Model configurations per provider
CREATE TABLE llm_models (
    model_id TEXT PRIMARY KEY,        -- gpt-4, claude-3-sonnet, llama-70b
    provider_id TEXT NOT NULL,
    model_name TEXT NOT NULL,
    
    -- Model limits (IMPORTANT: Check before calling)
    max_context_tokens INTEGER DEFAULT 4000,    -- Total context window
    max_output_tokens INTEGER DEFAULT 4000,     -- Max tokens in response
    max_input_tokens INTEGER DEFAULT 3000,      -- Max input tokens (context - output)
    

    
    -- Model capabilities
    supports_json_mode BOOLEAN DEFAULT FALSE,
    supports_function_calling BOOLEAN DEFAULT FALSE,
    supports_reasoning BOOLEAN DEFAULT FALSE,    -- Model-specific reasoning override
    default_reasoning_mode TEXT DEFAULT 'auto',  -- 'on', 'off', 'auto'
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (provider_id) REFERENCES llm_providers(provider_id)
);
```

## Implementation

### LLM Request Submission

```python
def submit_llm_request(system_prompt, user_prompt, operation, 
                      llm_provider, llm_model, context=None,
                      parent_trace_id=None, temperature=0.6, priority=5,
                      reasoning_enabled=False, json_mode=False):
    """
    Submit pre-processed request to LLM queue.
    
    This function is PURE - no business logic, no prompt processing, no model selection.
    All prompts are pre-built and ready to send.
    """
    trace_id = start_trace("llm_request_submit", parent_trace_id=parent_trace_id)
    request_id = generate_uuid()
    
    try:
        # Get provider endpoint URL
        provider_info = db.query("SELECT base_url FROM llm_providers WHERE provider_id=?", llm_provider)
        endpoint_url = provider_info[0].base_url if provider_info else None
        
        # Check model limits before submitting
        model_info = db.query("SELECT max_input_tokens, max_output_tokens FROM llm_models WHERE model_id=?", llm_model)
        if model_info:
            estimated_input_tokens = estimate_token_count(system_prompt or "") + estimate_token_count(user_prompt)
            if estimated_input_tokens > model_info[0].max_input_tokens:
                log_error_with_trace(trace_id, "TOKEN_LIMIT_EXCEEDED", 
                                   f"Input tokens ({estimated_input_tokens}) exceed model limit ({model_info[0].max_input_tokens})", 
                                   "llm_request_submit")
                complete_trace(trace_id, "FAILED", {"error": "Token limit exceeded"})
                return None
        
        db.insert("llm_requests", {
            "request_id": request_id,
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "operation": operation,
            "temperature": temperature,
            "reasoning_enabled": reasoning_enabled,
            "json_mode_enabled": json_mode,
            "llm_provider": llm_provider,
            "llm_model": llm_model,
            "llm_endpoint_url": endpoint_url,
            "context_data": json.dumps(context) if context else None,
            "parent_trace_id": parent_trace_id,
            "status": "pending",
            "priority": priority
        })
        
        # Trigger available worker
        trigger_available_worker(llm_provider)
        
        complete_trace(trace_id, "SUCCESS", {"request_id": request_id})
        return request_id
        
    except Exception as e:
        log_error_with_trace(trace_id, "SYSTEM_ERROR", str(e), "llm_request_submit")
        complete_trace(trace_id, "FAILED", {"error": str(e)})
        return None

def determine_reasoning_config(requested_mode, provider_supports, model_supports, model_default):
    """Determine final reasoning configuration based on capabilities and request"""
    
    # Check if reasoning is supported
    reasoning_supported = provider_supports and model_supports
    
    if requested_mode == 'on':
        if reasoning_supported:
            return True, 'on'
        else:
            print(f"Warning: Reasoning requested but not supported by provider/model")
            return False, 'off'
    
    elif requested_mode == 'off':
        return False, 'off'
    
    else:  # requested_mode == 'auto'
        if reasoning_supported:
            # Use model's default preference
            if model_default == 'on':
                return True, 'on'
            else:
                return False, 'off'
        else:
            return False, 'off'

def select_llm_provider_and_model(operation, preferred_provider=None, preferred_model=None,
                                  requires_reasoning=False, requires_json_mode=False):
    """Select best available LLM provider and model for operation with capability filtering"""
    
    # Build capability filters
    capability_filters = []
    if requires_reasoning:
        capability_filters.append("supports_reasoning = TRUE")
    if requires_json_mode:
        capability_filters.append("supports_json_mode = TRUE")
    
    capability_clause = " AND " + " AND ".join(capability_filters) if capability_filters else ""
    
    # Get active providers with required capabilities
    providers = db.query(f"""
        SELECT * FROM llm_providers 
        WHERE is_active = TRUE {capability_clause}
        ORDER BY requests_per_minute DESC
    """)
    
    if preferred_provider:
        providers = [p for p in providers if p.provider_id == preferred_provider]
    
    if not providers:
        missing_caps = []
        if requires_reasoning:
            missing_caps.append("reasoning")
        if requires_json_mode:
            missing_caps.append("json_mode")
        raise Exception(f"No active providers support required capabilities: {missing_caps}")
    
    # Select provider (could add load balancing logic here)
    selected_provider = providers[0]
    
    # Get available models for provider with required capabilities
    models = db.query(f"""
        SELECT * FROM llm_models 
        WHERE provider_id = ? AND is_active = TRUE {capability_clause}
        ORDER BY max_context_tokens DESC
    """, selected_provider.provider_id)
    
    if preferred_model:
        models = [m for m in models if m.model_id == preferred_model]
    
    if not models:
        raise Exception(f"No active models for provider {selected_provider.provider_id} with required capabilities")
    
    selected_model = models[0]
    
    return selected_provider, selected_model

def get_llm_request_status(request_id):
    """Get current status of LLM request"""
    return db.query("SELECT * FROM llm_requests WHERE request_id=?", request_id)

def trigger_available_worker(required_provider=None):
    """Find and trigger available worker that supports the required provider"""
    
    # Find available workers
    available_workers = db.query("""
        SELECT * FROM llm_worker_status 
        WHERE status IN ('idle', 'processing') 
        AND current_load < max_concurrent_requests
        ORDER BY current_load ASC, last_heartbeat DESC
    """)
    
    # Filter by provider support if specified
    if required_provider:
        compatible_workers = []
        for worker in available_workers:
            supported_providers = json.loads(worker.supported_providers or '[]')
            if required_provider in supported_providers:
                compatible_workers.append(worker)
        available_workers = compatible_workers
    
    if not available_workers:
        # No available workers - could trigger auto-scaling here
        print(f"No available workers for provider {required_provider}")
        return False
    
    # Select best worker (lowest load)
    selected_worker = available_workers[0]
    
    # Trigger worker based on type
    if selected_worker.worker_type == "lambda":
        trigger_lambda_worker(selected_worker.worker_id)
    elif selected_worker.worker_type == "ecs":
        trigger_ecs_worker(selected_worker.worker_id)
    else:
        # Local or other worker types
        trigger_generic_worker(selected_worker.worker_id)
    
    return True
```

### LLM Worker Implementation

```python
def llm_worker_main():
    """Main worker loop - processes LLM queue continuously"""
    worker_id = "main_worker"
    
    try:
        # Update worker status
        update_worker_status(worker_id, "processing")
        
        while True:
            # Get next pending request (priority order)
            next_request = db.query("""
                SELECT * FROM llm_requests 
                WHERE status='pending' 
                ORDER BY priority ASC, created_at ASC 
                LIMIT 1
            """)
            
            if not next_request:
                # No more tasks - go idle
                update_worker_status(worker_id, "idle")
                break
            
            # Process the request
            process_llm_request(next_request[0], worker_id)
            
            # Update heartbeat
            update_worker_heartbeat(worker_id)
    
    except Exception as e:
        # Worker error - log and set error status
        log_worker_error(worker_id, str(e))
        update_worker_status(worker_id, "error", error_message=str(e))

def process_llm_request(request, worker_id):
    """Process single LLM request with error tracking"""
    request_id = request.request_id
    start_time = int(time.time())
    trace_id = start_trace("llm_request_process", parent_trace_id=request.parent_trace_id)
    
    try:
        # Update request status
        db.update("llm_requests", {
            "status": "processing",
            "started_at": start_time,
            "assigned_worker_id": worker_id
        }, {"request_id": request_id})
        
        # Update worker current task
        db.update("llm_worker_status", {
            "current_request_id": request_id
        }, {"worker_id": worker_id})
        
        # Get provider and model info
        provider = get_provider_config(request.llm_provider)
        model = get_model_config(request.llm_model)
        
        # Call LLM with provider-specific implementation
        llm_start = int(time.time())
        llm_response = call_llm_api(
            provider=provider,
            model=model,
            system_prompt=request.system_prompt,
            user_prompt=request.user_prompt,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            reasoning_enabled=request.reasoning_enabled,
            json_mode=request.json_mode_enabled
        )
        llm_duration = (int(time.time()) - llm_start) * 1000
        
        # Extract token usage from response (provider-specific)
        token_usage = extract_token_usage(llm_response, request.llm_provider)
        
        # Process and validate response
        parsed_response = process_llm_response(llm_response, request.operation)
        
        # Save successful response
        end_time = int(time.time())
        db.update("llm_requests", {
            "status": "completed",
            "response_data": json.dumps(llm_response),
            "parsed_response": json.dumps(parsed_response) if parsed_response else None,
            "prompt_tokens": token_usage.get("prompt_tokens"),
            "completion_tokens": token_usage.get("completion_tokens"),
            "total_tokens": token_usage.get("total_tokens"),
            "completed_at": end_time,
            "processing_duration_ms": (end_time - start_time) * 1000,
            "llm_call_duration_ms": llm_duration
        }, {"request_id": request_id})
        
        # Update worker stats
        db.execute("""
            UPDATE llm_worker_status 
            SET processed_count = processed_count + 1,
                current_request_id = NULL,
                current_load = current_load - 1
            WHERE worker_id = ?
        """, worker_id)
        
        complete_trace(trace_id, "SUCCESS", {
            "request_id": request_id,
            "tokens_used": token_usage.get("total_tokens", 0),
            "duration_ms": llm_duration
        })
        
    except Exception as e:
        # Handle request failure with error tracking
        log_error_with_trace(trace_id, "LLM_PROCESSING_ERROR", str(e), "llm_request_process")
        handle_llm_request_failure(request, str(e), worker_id, trace_id)
        complete_trace(trace_id, "FAILED", {"error": str(e)})

def handle_llm_request_failure(request, error_message, worker_id, trace_id):
    """Handle failed LLM request with retry logic and error tracking"""
    request_id = request.request_id
    retry_count = request.retry_count + 1
    
    # Determine error code based on error message
    error_code = classify_llm_error(error_message)
    
    if retry_count <= request.max_retries:
        # Retry - reset to pending
        db.update("llm_requests", {
            "status": "pending",
            "retry_count": retry_count,
            "error_message": error_message,
            "priority": max(1, request.priority - 1)  # Higher priority for retries
        }, {"request_id": request_id})
        
        log_error_with_trace(trace_id, error_code, f"LLM request failed, retry {retry_count}/{request.max_retries}: {error_message}", "llm_request_retry")
    else:
        # Max retries reached - mark as failed
        db.update("llm_requests", {
            "status": "failed",
            "retry_count": retry_count,
            "error_message": error_message,
            "failure_reason": "MAX_RETRIES_EXCEEDED",
            "completed_at": int(time.time())
        }, {"request_id": request_id})
        
        log_error_with_trace(trace_id, "MAX_RETRIES_EXCEEDED", f"LLM request failed after {request.max_retries} retries: {error_message}", "llm_request_failed")
    
    # Update worker stats
    db.execute("""
        UPDATE llm_worker_status 
        SET error_count = error_count + 1,
            current_request_id = NULL,
            current_load = current_load - 1
        WHERE worker_id = ?
    """, worker_id)

def classify_llm_error(error_message):
    """Classify error message into structured error codes"""
    error_lower = error_message.lower()
    
    if "timeout" in error_lower:
        return "LLM_TIMEOUT"
    elif "rate limit" in error_lower or "429" in error_lower:
        return "LLM_RATE_LIMIT"
    elif "token" in error_lower and "limit" in error_lower:
        return "LLM_TOKEN_LIMIT"
    elif "authentication" in error_lower or "401" in error_lower:
        return "LLM_AUTH_ERROR"
    elif "connection" in error_lower or "network" in error_lower:
        return "LLM_CONNECTION_ERROR"
    elif "json" in error_lower or "parse" in error_lower:
        return "LLM_RESPONSE_PARSE_ERROR"
    else:
        return "LLM_UNKNOWN_ERROR"

def load_prompt_template(template_name, inputs):
    """Load and populate prompt template"""
    # Load template from file or database
    template_content = read_prompt_template_file(template_name)
    
    # Replace placeholders with inputs
    for key, value in inputs.items():
        template_content = template_content.replace(f"{{{key}}}", str(value))
    
    return template_content

def process_llm_response(llm_response, operation):
    """Process and validate LLM response based on operation type"""
    try:
        if operation == "sentence_split":
            return parse_sentence_split_response(llm_response)
        elif operation == "extract_entities":
            return parse_entities_response(llm_response)
        elif operation == "extract_kriya":
            return parse_kriya_response(llm_response)
        # Add more operation types as needed
        
    except Exception as e:
        # Parsing failed - will trigger retry
        raise ValueError(f"Response parsing failed: {str(e)}")
```

### Integration with Other Flows

```python
# Example: Sentence Split Flow Integration
def check_chunk_llm_status(chunk_id):
    """Check if chunk's LLM request is complete"""
    chunk = db.query("SELECT * FROM document_chunks WHERE chunk_id=?", chunk_id)
    
    if chunk.llm_request_id:
        llm_request = get_llm_request_status(chunk.llm_request_id)
        
        if llm_request.status == "completed":
            # Process the response
            sentences = json.loads(llm_request.parsed_response)
            save_chunk_sentences(chunk_id, sentences)
            
            # Update chunk status
            db.update("document_chunks", {
                "status": "splitting_complete"
            }, {"chunk_id": chunk_id})
            
        elif llm_request.status == "failed":
            # Handle failure
            db.update("document_chunks", {
                "status": "splitting_failed",
                "failure_reason": llm_request.failure_reason
            }, {"chunk_id": chunk_id})
```

## Key Features

### 1. **Queue Management**
- Priority-based processing
- Automatic retry with backoff
- Worker status monitoring

### 2. **Performance Tracking**
- Processing duration metrics
- LLM call timing
- Success/failure rates

### 3. **Error Handling**
- Structured error messages
- Retry logic with max attempts
- Worker error recovery

### 4. **Scalability**
- Single worker prevents overload
- Queue can handle high volume
- Easy to add worker monitoring

## API Design

```python
# Internal APIs (used by other flows)
submit_llm_request(prompt_template, inputs, operation, ...)  # Submit to queue
get_llm_request_status(request_id)                          # Check status

# Admin/Monitoring APIs
GET /llm/queue/status        # Queue statistics
GET /llm/worker/status       # Worker health
POST /llm/worker/restart     # Restart worker
```

## Worker Deployment Options

### 1. **Lambda-based Worker**
- Triggered by CloudWatch Events
- Auto-scaling based on queue depth
- Cost-effective for variable load

### 2. **ECS/Container Worker**
- Long-running worker process
- Better for consistent load
- Easier debugging and monitoring

### 3. **Hybrid Approach**
- Primary worker in ECS
- Lambda backup for overflow
- Best of both worlds

## Benefits

- **Rate Limit Protection** - Single worker prevents LLM overload
- **Reliability** - Retry logic and error handling
- **Observability** - Complete request tracking
- **Scalability** - Queue handles volume spikes
- **Decoupling** - Business logic independent of LLM timing##
 Multi-Worker Support

### Worker Registration

```python
def register_worker(worker_id, worker_type, supported_providers, deployment_info=None):
    """Register a new worker in the system"""
    
    db.insert("llm_worker_status", {
        "worker_id": worker_id,
        "worker_type": worker_type,  # lambda, ecs, local
        "status": "idle",
        "supported_providers": json.dumps(supported_providers),
        "max_concurrent_requests": get_worker_concurrency_limit(worker_type),
        "deployment_info": json.dumps(deployment_info) if deployment_info else None
    })

# Example registrations:
register_worker("lambda_worker_1", "lambda", ["openai", "anthropic"])
register_worker("ecs_worker_1", "ecs", ["nvidia", "openai"], {"container_id": "abc123"})
register_worker("local_worker_1", "local", ["openai"])
```

### Load Balancing

```python
def assign_request_to_worker(request_id):
    """Assign pending request to best available worker"""
    
    request = get_llm_request(request_id)
    required_provider = request.llm_provider
    
    # Find workers that support this provider
    compatible_workers = db.query("""
        SELECT * FROM llm_worker_status 
        WHERE status IN ('idle', 'processing')
        AND current_load < max_concurrent_requests
        AND json_extract(supported_providers, '$') LIKE ?
        ORDER BY current_load ASC, avg_processing_time_ms ASC
    """, f'%{required_provider}%')
    
    if not compatible_workers:
        return None  # No available workers
    
    # Select best worker (lowest load + fastest average time)
    selected_worker = compatible_workers[0]
    
    # Assign request to worker
    db.update("llm_requests", {
        "assigned_worker_id": selected_worker.worker_id
    }, {"request_id": request_id})
    
    # Update worker load
    db.execute("""
        UPDATE llm_worker_status 
        SET current_load = current_load + 1,
            current_request_id = ?
        WHERE worker_id = ?
    """, request_id, selected_worker.worker_id)
    
    return selected_worker.worker_id
```

## Token Tracking & Cost Estimation

### Provider-Specific Token Extraction

```python
def extract_token_usage(llm_response, provider):
    """Extract token usage from provider-specific response format"""
    
    if provider == "openai":
        usage = llm_response.get("usage", {})
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    
    elif provider == "anthropic":
        usage = llm_response.get("usage", {})
        return {
            "prompt_tokens": usage.get("input_tokens", 0),
            "completion_tokens": usage.get("output_tokens", 0),
            "total_tokens": usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
        }
    
    elif provider == "nvidia":
        usage = llm_response.get("usage", {})
        return {
            "prompt_tokens": usage.get("prompt_tokens", 0),
            "completion_tokens": usage.get("completion_tokens", 0),
            "total_tokens": usage.get("total_tokens", 0)
        }
    
    else:
        # Fallback - estimate tokens if not provided
        prompt_text = llm_response.get("prompt", "")
        completion_text = llm_response.get("completion", "")
        
        return {
            "prompt_tokens": estimate_token_count(prompt_text),
            "completion_tokens": estimate_token_count(completion_text),
            "total_tokens": estimate_token_count(prompt_text + completion_text)
        }

def estimate_token_count(text):
    """Rough token estimation (4 chars ≈ 1 token for English)"""
    return max(1, len(text) // 4)


```

## Provider Management

### Provider Configuration Examples

```python
# Initialize common providers
def setup_default_providers():
    """Setup default LLM providers and models"""
    
    # OpenAI
    db.insert("llm_providers", {
        "provider_id": "openai",
        "provider_name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "api_key_env_var": "OPENAI_API_KEY",
        "requests_per_minute": 500,
        "tokens_per_minute": 150000,
        "input_token_price": 0.03,   # $0.03 per 1K tokens
        "output_token_price": 0.06   # $0.06 per 1K tokens
    })
    
    db.insert("llm_models", {
        "model_id": "gpt-4",
        "provider_id": "openai", 
        "model_name": "gpt-4",
        "max_context_tokens": 8192,
        "max_output_tokens": 4096,
        "supports_json_mode": True
    })
    
    # Anthropic
    db.insert("llm_providers", {
        "provider_id": "anthropic",
        "provider_name": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "api_key_env_var": "ANTHROPIC_API_KEY",
        "requests_per_minute": 100,
        "tokens_per_minute": 100000,
        "input_token_price": 0.015,
        "output_token_price": 0.075
    })
    
    db.insert("llm_models", {
        "model_id": "claude-3-sonnet",
        "provider_id": "anthropic",
        "model_name": "claude-3-sonnet-20240229", 
        "max_context_tokens": 200000,
        "max_output_tokens": 4096
    })
    
    # NVIDIA
    db.insert("llm_providers", {
        "provider_id": "nvidia",
        "provider_name": "NVIDIA NIM",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env_var": "NVIDIA_API_KEY",
        "requests_per_minute": 200,
        "tokens_per_minute": 50000,
        "input_token_price": 0.0,    # Often free for research
        "output_token_price": 0.0
    })
    
    db.insert("llm_models", {
        "model_id": "llama-70b",
        "provider_id": "nvidia",
        "model_name": "meta/llama3-70b-instruct",
        "max_context_tokens": 8192,
        "max_output_tokens": 4096
    })
```

## Enhanced Monitoring



## Missing Features Now Added

### ✅ **Multi-Worker Support**
- Worker registration system
- Load balancing across workers
- Worker-specific capabilities

### ✅ **LLM Provider Tracking** 
- Provider and model configuration tables
- Request tracking by provider/model
- Provider-specific rate limiting

### ✅ **Token Tracking**
- Provider-specific token extraction
- Cost estimation per request
- Token usage analytics

### ✅ **Production Features**
- Health checking for providers
- Worker performance monitoring
- Cost tracking and reporting
- Auto-scaling trigger points#
# Reasoning Mode Implementation

### Provider-Specific Reasoning Support

```python
def call_llm_api(provider, model, prompt, system_prompt=None, temperature=0.6, 
                max_tokens=4000, reasoning_enabled=False, reasoning_mode='auto',
                json_mode=False, top_p=1.0):
    """Call LLM API with provider-specific reasoning implementation"""
    
    if provider["provider_id"] == "openai":
        return call_openai_api(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_enabled=reasoning_enabled,
            json_mode=json_mode,
            top_p=top_p
        )
    
    elif provider["provider_id"] == "anthropic":
        return call_anthropic_api(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_enabled=reasoning_enabled
        )
    
    elif provider["provider_id"] == "nvidia":
        return call_nvidia_api(
            model=model,
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            reasoning_enabled=reasoning_enabled,
            reasoning_mode=reasoning_mode
        )
    
    else:
        raise Exception(f"Unsupported provider: {provider['provider_id']}")

def call_openai_api(model, system_prompt=None, user_prompt=None, temperature=0.6, 
                   max_tokens=4000, reasoning_enabled=False, json_mode=False):
    """OpenAI API call with reasoning support"""
    
    messages = []
    
    if system_prompt:
        # Add reasoning directive to system prompt if enabled
        if reasoning_enabled:
            system_prompt = f"Think step by step and show your reasoning.\n\n{system_prompt}"
        messages.append({"role": "system", "content": system_prompt})
    
    messages.append({"role": "user", "content": user_prompt})
    
    # OpenAI API call
    payload = {
        "model": model["model_name"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    
    if json_mode and model.get("supports_json_mode"):
        payload["response_format"] = {"type": "json_object"}
    
    # Make API call (implementation depends on HTTP client)
    response = openai_client.chat.completions.create(**payload)
    
    return {
        "choices": [{"message": {"content": response.choices[0].message.content}}],
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
    }

def call_nvidia_api(model, system_prompt=None, user_prompt=None, temperature=0.6,
                   max_tokens=4000, reasoning_enabled=False):
    """NVIDIA NIM API call with reasoning support"""
    
    # NVIDIA's reasoning implementation (based on your google-colab-cell.py)
    if reasoning_enabled:
        reasoning_directive = "detailed thinking on"
        if system_prompt:
            system_prompt = f"{reasoning_directive}\n\n{system_prompt}"
        else:
            system_prompt = reasoning_directive
    
    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": user_prompt})
    
    # NVIDIA API call
    payload = {
        "model": model["model_name"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "top_p": 0.95 if reasoning_enabled else 1.0  # Use 0.95 for reasoning mode
    }
    
    response = nvidia_client.chat.completions.create(**payload)
    
    return {
        "choices": [{"message": {"content": response.choices[0].message.content}}],
        "usage": {
            "prompt_tokens": response.usage.prompt_tokens if hasattr(response.usage, 'prompt_tokens') else 0,
            "completion_tokens": response.usage.completion_tokens if hasattr(response.usage, 'completion_tokens') else 0,
            "total_tokens": response.usage.total_tokens if hasattr(response.usage, 'total_tokens') else 0
        }
    }
```

### Enhanced Provider Setup with Reasoning

```python
def setup_providers_with_reasoning():
    """Setup providers with reasoning capabilities"""
    
    # OpenAI
    db.insert("llm_providers", {
        "provider_id": "openai",
        "provider_name": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "api_key_env_var": "OPENAI_API_KEY",
        "supports_reasoning": True,
        "supports_system_prompts": True,
        "supports_json_mode": True,
        "requests_per_minute": 500,
        "tokens_per_minute": 150000
    })
    
    db.insert("llm_models", {
        "model_id": "gpt-4",
        "provider_id": "openai",
        "model_name": "gpt-4",
        "max_context_tokens": 8192,
        "max_output_tokens": 4096,
        "max_input_tokens": 4096,
        "supports_reasoning": True,
        "supports_json_mode": True
    })
    
    # NVIDIA
    db.insert("llm_providers", {
        "provider_id": "nvidia",
        "provider_name": "NVIDIA NIM",
        "base_url": "https://integrate.api.nvidia.com/v1",
        "api_key_env_var": "NVIDIA_API_KEY",
        "supports_reasoning": True,
        "supports_system_prompts": True,
        "requests_per_minute": 200,
        "tokens_per_minute": 50000
    })
    
    db.insert("llm_models", {
        "model_id": "llama-70b",
        "provider_id": "nvidia",
        "model_name": "meta/llama3-70b-instruct",
        "max_context_tokens": 8192,
        "max_output_tokens": 4096,
        "max_input_tokens": 4096,
        "supports_reasoning": True,
        "default_reasoning_mode": "on"
    })
```

### Reasoning Analytics

```sql
-- Reasoning usage by operation
SELECT 
    operation,
    reasoning_enabled,
    COUNT(*) as requests,
    AVG(processing_duration_ms) as avg_processing_time,
    AVG(total_tokens) as avg_tokens,
    AVG(estimated_cost_usd) as avg_cost
FROM llm_requests 
WHERE status = 'completed'
GROUP BY operation, reasoning_enabled
ORDER BY operation, reasoning_enabled;

-- Reasoning effectiveness (success rate)
SELECT 
    llm_provider,
    reasoning_enabled,
    COUNT(*) as total_requests,
    SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as successful_requests,
    ROUND(100.0 * SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 2) as success_rate
FROM llm_requests 
GROUP BY llm_provider, reasoning_enabled;

-- Token usage impact of reasoning
SELECT 
    llm_provider,
    reasoning_enabled,
    AVG(total_tokens) as avg_tokens,
    AVG(processing_duration_ms) as avg_processing_time
FROM llm_requests 
WHERE status = 'completed'
GROUP BY llm_provider, reasoning_enabled;
```

## Additional Missing Features Added

### ✅ **Request Parameter Tracking**
- `system_prompt` - Track system prompts used
- `json_mode_enabled` - JSON response format requests
- `top_p`, `frequency_penalty`, `presence_penalty` - Advanced sampling parameters

### ✅ **Provider Capability Matrix**
- `supports_system_prompts` - System prompt support
- `supports_json_mode` - Structured JSON responses
- `supports_function_calling` - Function/tool calling

### ✅ **Model-Level Configuration**
- `default_reasoning_mode` - Per-model reasoning preferences
- Model-specific capability overrides

### ✅ **Smart Provider Selection**
- Capability-based filtering (requires reasoning, JSON mode, etc.)
- Automatic fallback when capabilities not supported
- Warning when requested features unavailable

This comprehensive tracking enables:
- **Performance analysis** of reasoning vs non-reasoning requests
- **Token usage optimization** by understanding reasoning impact
- **Quality metrics** by operation and reasoning mode
- **Provider comparison** for reasoning effectiveness
- **Error pattern analysis** for improving reliability##
 Prompt Management System (Separate from LLM Call Flow)

### Prompt Storage & Versioning

```sql
-- Prompt templates with versioning
CREATE TABLE prompt_templates (
    template_id TEXT PRIMARY KEY,      -- sentence_split_v1, extract_entities_v2
    template_name TEXT NOT NULL,       -- sentence_split, extract_entities
    version INTEGER NOT NULL,          -- 1, 2, 3, etc.
    
    -- Prompt content
    system_prompt TEXT,                -- System prompt template
    user_prompt_template TEXT NOT NULL, -- User prompt with placeholders
    
    -- Metadata
    operation TEXT NOT NULL,           -- sentence_split, extract_entities
    description TEXT,
    created_by TEXT,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    is_default BOOLEAN DEFAULT FALSE,  -- Default version for this template_name
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    UNIQUE(template_name, version)
);

-- Prompt usage tracking
CREATE TABLE prompt_usage (
    usage_id TEXT PRIMARY KEY,
    template_id TEXT NOT NULL,
    llm_request_id TEXT NOT NULL,
    
    -- Rendered prompts (after variable substitution)
    final_system_prompt TEXT,
    final_user_prompt TEXT,
    
    -- Variables used
    template_variables TEXT,           -- JSON blob with substituted variables
    
    created_at INTEGER DEFAULT (strftime('%s', 'now')),
    
    FOREIGN KEY (template_id) REFERENCES prompt_templates(template_id),
    FOREIGN KEY (llm_request_id) REFERENCES llm_requests(request_id)
);
```

### Prompt Processing Layer (Before LLM Call)

```python
class PromptProcessor:
    """Handles prompt loading, versioning, and variable substitution"""
    
    def build_prompts(self, template_name, variables, version=None):
        """
        Build system and user prompts from template.
        This runs BEFORE submitting to LLM queue.
        """
        # Get template (default version if not specified)
        if version:
            template = self.get_template_by_version(template_name, version)
        else:
            template = self.get_default_template(template_name)
        
        if not template:
            raise Exception(f"Template not found: {template_name} v{version}")
        
        # Substitute variables in templates
        system_prompt = self.substitute_variables(template.system_prompt, variables) if template.system_prompt else None
        user_prompt = self.substitute_variables(template.user_prompt_template, variables)
        
        return {
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
            "template_id": template.template_id
        }
    
    def get_default_template(self, template_name):
        """Get default version of template"""
        return db.query("""
            SELECT * FROM prompt_templates 
            WHERE template_name = ? AND is_default = TRUE AND is_active = TRUE
        """, template_name)
    
    def get_template_by_version(self, template_name, version):
        """Get specific version of template"""
        return db.query("""
            SELECT * FROM prompt_templates 
            WHERE template_name = ? AND version = ? AND is_active = TRUE
        """, template_name, version)
    
    def substitute_variables(self, template, variables):
        """Replace {VARIABLE_NAME} with actual values"""
        if not template:
            return None
        
        result = template
        for key, value in variables.items():
            placeholder = f"{{{key}}}"
            result = result.replace(placeholder, str(value))
        
        return result

# Usage in sentence split flow:
def process_chunk_with_llm(chunk_id, chunk_text):
    """Example of how to use prompt processor before LLM call"""
    
    # 1. Build prompts using prompt processor
    prompt_processor = PromptProcessor()
    prompts = prompt_processor.build_prompts(
        template_name="sentence_split",
        variables={"CHUNK_TEXT": chunk_text}
    )
    
    # 2. Submit to LLM queue (pure call)
    llm_request_id = submit_llm_request(
        system_prompt=prompts["system_prompt"],
        user_prompt=prompts["user_prompt"],
        operation="sentence_split",
        llm_provider="nvidia",  # Pre-selected by business logic
        llm_model="llama-70b",  # Pre-selected by business logic
        reasoning_enabled=True  # Pre-decided by business logic
    )
    
    # 3. Track prompt usage
    db.insert("prompt_usage", {
        "usage_id": generate_uuid(),
        "template_id": prompts["template_id"],
        "llm_request_id": llm_request_id,
        "final_system_prompt": prompts["system_prompt"],
        "final_user_prompt": prompts["user_prompt"],
        "template_variables": json.dumps({"CHUNK_TEXT": chunk_text})
    })
    
    return llm_request_id
```

### Sample Prompt Templates

```python
def setup_prompt_templates():
    """Setup initial prompt templates"""
    
    # Sentence splitting prompt v1
    db.insert("prompt_templates", {
        "template_id": "sentence_split_v1",
        "template_name": "sentence_split",
        "version": 1,
        "system_prompt": "You are an expert at splitting text into grammatically correct sentences. Return only a JSON array of sentences.",
        "user_prompt_template": "Split the following text into sentences:\n\n{CHUNK_TEXT}",
        "operation": "sentence_split",
        "description": "Basic sentence splitting",
        "is_active": True,
        "is_default": True
    })
    
    # Entity extraction prompt v1
    db.insert("prompt_templates", {
        "template_id": "extract_entities_v1", 
        "template_name": "extract_entities",
        "version": 1,
        "system_prompt": "Extract entities from the given sentence. Return JSON format with entity types and names.",
        "user_prompt_template": "Extract entities from: {SENTENCE_TEXT}",
        "operation": "extract_entities",
        "description": "Basic entity extraction",
        "is_active": True,
        "is_default": True
    })
    
    # Sentence splitting prompt v2 (improved)
    db.insert("prompt_templates", {
        "template_id": "sentence_split_v2",
        "template_name": "sentence_split", 
        "version": 2,
        "system_prompt": "You are an expert at splitting text into grammatically correct sentences. Preserve all original text. Return only a JSON array of sentences with no additional formatting.",
        "user_prompt_template": "Split this text into sentences, preserving all original content:\n\n{CHUNK_TEXT}\n\nReturn format: [\"sentence1\", \"sentence2\", ...]",
        "operation": "sentence_split",
        "description": "Improved sentence splitting with better instructions",
        "is_active": True,
        "is_default": False  # Not default yet, still testing
    })
```

## Simplified LLM Call Flow

### Core Principle: Pure Execution Only

The LLM call flow now only does:
1. **Receive pre-built prompts** (no template processing)
2. **Call LLM API** (provider-specific implementation)
3. **Save response** (raw + parsed)
4. **Track tokens** (input/output only)

### What's Removed:
- ❌ Prompt template loading
- ❌ Variable substitution  
- ❌ Model selection logic
- ❌ Capability checking
- ❌ Cost calculation
- ❌ Complex parameter validation

### What's Added:
- ✅ Prompt versioning system
- ✅ Prompt usage tracking
- ✅ Clean separation of concerns

### Integration Example:

```python
# Business layer (sentence-split-flow)
def handle_chunk_processing(chunk_id):
    # 1. Business logic decides everything
    chunk = get_chunk(chunk_id)
    provider = "nvidia"  # Business decision
    model = "llama-70b"  # Business decision
    use_reasoning = True  # Business decision
    
    # 2. Build prompts
    prompts = PromptProcessor().build_prompts(
        template_name="sentence_split",
        variables={"CHUNK_TEXT": chunk.text}
    )
    
    # 3. Pure LLM call
    request_id = submit_llm_request(
        system_prompt=prompts["system_prompt"],
        user_prompt=prompts["user_prompt"], 
        operation="sentence_split",
        llm_provider=provider,
        llm_model=model,
        reasoning_enabled=use_reasoning
    )
    
    return request_id

# LLM layer (pure execution)
def submit_llm_request(system_prompt, user_prompt, operation, llm_provider, llm_model, **kwargs):
    # Just execute - no business logic
    # Save request, call API, save response
    pass
```

This creates **clean separation**:
- **Business layer**: Decides what to do, builds prompts
- **LLM layer**: Just executes the call
- **Prompt layer**: Manages templates and versions## Token Lim
it Validation

### Pre-Submission Checks

```python
def estimate_token_count(text):
    """Rough token estimation (4 chars ≈ 1 token for English)"""
    return max(1, len(text) // 4) if text else 0

def validate_token_limits(system_prompt, user_prompt, model_id, max_tokens):
    """Check if request will exceed model limits"""
    
    model = db.query("SELECT * FROM llm_models WHERE model_id=?", model_id)
    if not model:
        return False, "Model not found"
    
    model = model[0]
    
    # Estimate input tokens
    estimated_input = estimate_token_count(system_prompt or "") + estimate_token_count(user_prompt)
    
    # Check limits
    if estimated_input > model.max_input_tokens:
        return False, f"Input tokens ({estimated_input}) exceed model limit ({model.max_input_tokens})"
    
    if max_tokens > model.max_output_tokens:
        return False, f"Requested output tokens ({max_tokens}) exceed model limit ({model.max_output_tokens})"
    
    if estimated_input + max_tokens > model.max_context_tokens:
        return False, f"Total tokens ({estimated_input + max_tokens}) exceed context window ({model.max_context_tokens})"
    
    return True, None
```

## Error Integration

### LLM-Specific Error Codes

```python
# Added to global ErrorCodes class in error-handling.md
class ErrorCodes:
    # ... existing codes ...
    
    # LLM-specific errors
    LLM_TIMEOUT = "LLM_TIMEOUT"
    LLM_RATE_LIMIT = "LLM_RATE_LIMIT" 
    LLM_TOKEN_LIMIT = "LLM_TOKEN_LIMIT"
    LLM_AUTH_ERROR = "LLM_AUTH_ERROR"
    LLM_CONNECTION_ERROR = "LLM_CONNECTION_ERROR"
    LLM_RESPONSE_PARSE_ERROR = "LLM_RESPONSE_PARSE_ERROR"
    LLM_UNKNOWN_ERROR = "LLM_UNKNOWN_ERROR"
    TOKEN_LIMIT_EXCEEDED = "TOKEN_LIMIT_EXCEEDED"
    MAX_RETRIES_EXCEEDED = "MAX_RETRIES_EXCEEDED"
```

### Usage in Other Flows

```python
# Example: Sentence split flow integration
def process_chunk_with_llm(chunk_id, chunk_text):
    """How sentence-split-flow integrates with LLM call flow"""
    
    # 1. Business layer builds prompts (using prompt management system)
    prompt_processor = PromptProcessor()
    prompts = prompt_processor.build_prompts(
        template_name="sentence_split",
        variables={"CHUNK_TEXT": chunk_text},
        version=2  # Use specific version
    )
    
    # 2. Business layer selects provider/model (not LLM layer's job)
    provider = "nvidia"
    model = "llama-70b"
    use_reasoning = True
    
    # 3. Pure LLM call (no business logic in LLM layer)
    llm_request_id = submit_llm_request(
        system_prompt=prompts["system_prompt"],
        user_prompt=prompts["user_prompt"],
        operation="sentence_split",
        llm_provider=provider,
        llm_model=model,
        reasoning_enabled=use_reasoning,
        context={"chunk_id": chunk_id}
    )
    
    return llm_request_id
```

## Simplified LLM Call Flow Responsibilities

### ✅ What LLM Layer Does:
- Accept pre-built prompts
- Validate token limits against model
- Call LLM API
- Save raw response
- Parse response (basic JSON extraction)
- Track tokens (input/output)
- Handle retries
- Update worker status

### ❌ What LLM Layer Does NOT Do:
- Prompt template loading
- Variable substitution
- Model selection
- Cost calculation
- Business logic validation
- Complex capability checking

### 🔄 Clean Integration Pattern:
```
Business Flow → Prompt Processor → LLM Call Flow → LLM API
     ↑                                    ↓
     ←── Response Processing ←── Raw Response
```

The LLM call flow is now **pure execution** with proper **error tracking** and **token limit validation**!