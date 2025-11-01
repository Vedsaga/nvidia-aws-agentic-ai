# Configuration Guide for Karaka Knowledge Graph System

## Overview
All configurable values have been extracted from `google_colab_cells.py` into `config.yaml` for easier management and adjustment.

## Configuration Files

### config.yaml
Main configuration file for all system parameters.

### prompts.yaml
All system prompts used throughout the application.

## Configuration File: config.yaml

### Model Configuration
- **llm.model_id**: HuggingFace model ID for the main LLM
- **llm.dtype_primary/dtype_fallback**: Data types for model loading (bfloat16/float16)
- **embedding.model_id**: HuggingFace model ID for embeddings
- **embedding.dimension**: Embedding vector dimension (2048)

### Entity Resolution
- **similarity_threshold**: Threshold for entity matching (0.85 = 85% similarity)

### File Paths
- **db_file**: Output file for graph database
- **graph_viz_file**: Output file for graph visualization
- **prompts_file**: JSON file containing main prompts (kriya extraction, query decomposition)
- **prompts_yaml_file**: YAML file containing additional prompts (metaphor resolution, entity classification)
- **docs_folder**: Input folder for documents to process

### Graph Schema
- **node_types**: Valid node types (Kriya, Entity, Document)
- **edge_relations**: Valid edge relation types
- **karaka_relation_mapping**: Maps Karaka roles to graph relations

### GSV-Retry Engine
- **max_retries**: Maximum retry attempts for extraction (2)
- **scoring_ensemble_size**: Number of scoring calls per candidate (3 for accuracy, 1 for speed)
- **num_candidates**: Number of candidates to generate (3)
- **generation_temperature**: Temperature for candidate generation (0.5)
- **scoring_temperature**: Temperature for scoring (0.0 = deterministic)
- **verification_temperature**: Temperature for verification (0.0 = deterministic)

### LLM Call Configuration
- **max_tokens**: Maximum tokens for LLM output (2048)
- **temperature**: Default temperature for LLM calls (0.0)

### Sentence Splitting
- **max_paragraph_tokens**: Maximum tokens per paragraph (3500)
- **chunk_size_tokens**: Chunk size for long paragraphs (3000)
- **overlap_tokens**: Overlap between chunks (200)
- **max_retries**: Maximum retries for sentence splitting (2)
- **fidelity_threshold**: Similarity threshold for fidelity check (0.99)
- **abbreviations**: List of common abbreviations for sentence boundary detection

### FAISS Vector Store
- **dimension**: Vector dimension (2048)
- **nearby_k**: Number of nearby documents to retrieve (5)

### Graph Traversal
- **max_hops**: Maximum traversal depth (3)
- **default_direction**: Default traversal direction (out/in/both)

### Query Pipeline
- **citation_limit**: Maximum citations to display (5)

### Display Settings
- **max_text_preview_length**: Maximum text preview length (100)
- **max_citation_text_length**: Maximum citation text length (80)
- **show_debug_output**: Show debug output (false)
- **show_verifier_input**: Show verifier input (false)

### Test Queries
- List of default test queries to run

## How to Adjust Configuration

1. **Edit config.yaml** - Modify any value in the YAML file
2. **No code changes needed** - The system automatically loads from config.yaml
3. **Restart execution** - Re-run the cells to apply new configuration

## Common Adjustments

### Speed vs Accuracy Trade-off
```yaml
gsv_retry:
  scoring_ensemble_size: 1  # Fast (1 call) vs Accurate (3 calls)
  max_retries: 1            # Fast (1 retry) vs Robust (2 retries)
```

### Entity Resolution Sensitivity
```yaml
entity_resolution:
  similarity_threshold: 0.90  # Stricter (fewer matches)
  similarity_threshold: 0.80  # Looser (more matches)
```

### Model Selection
```yaml
models:
  llm:
    model_id: "your-preferred-model-id"
  embedding:
    model_id: "your-preferred-embedding-model"
```

### Debug Mode
```yaml
display:
  show_debug_output: true      # Show detailed debug info
  show_verifier_input: true    # Show verifier input details
```

## Prompt Management

### prompts.yaml Structure
The prompts.yaml file contains:
- **System prompts**: Instructions for the LLM on how to perform tasks
- **User prompt templates**: Templates for formatting user inputs with context

### Customizing Prompts
1. Edit prompts.yaml to modify any prompt
2. Use `{variable}` syntax for template variables
3. No code changes needed - prompts are loaded at runtime

### Available Prompts
- **metaphor_resolution_prompt**: Resolves metaphorical references to actual entities
- **entity_type_classifier_prompt**: Classifies entities into types (Person, Deity, Location, etc.)
- **causal_relationship_detector_prompt**: Detects causal relationships between actions
- **answer_generator_prompt**: Generates natural language answers from context
- **sentence_split_simple_prompt**: Simple sentence splitting
- **sentence_split_retry_prompt**: Retry prompt for sentence splitting with feedback

### Prompt Templates
User prompt templates format context and variables:
- **metaphor_resolution_user_template**: `{metaphor}`, `{context}`
- **entity_type_classifier_user_template**: `{entity_name}`, `{context}`
- **causal_relationship_user_template**: `{verb1}`, `{text1}`, `{verb2}`, `{text2}`
- **answer_generator_user_template**: `{question}`, `{context}`
- **coreference_resolution_user_template**: `{hint}`, `{context}`

## Dependencies
The system now requires PyYAML:
```python
!pip install pyyaml
```

This is automatically handled in the first cell of google_colab_cells.py.
