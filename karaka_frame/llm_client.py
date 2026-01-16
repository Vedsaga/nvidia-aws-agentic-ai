"""
Async LLM Client for Kāraka Frame Graph POC.
Supports OpenRouter, OpenAI, and other compatible APIs.
"""

import os
import json
from dotenv import load_dotenv
from openai import AsyncOpenAI

load_dotenv()

# Async Client for non-blocking operations
client = AsyncOpenAI(
    base_url=os.getenv("LLM_BASE_URL", "https://openrouter.ai/api/v1"),
    api_key=os.getenv("LLM_API_KEY")
)

DEFAULT_MODEL = os.getenv("LLM_MODEL", "meta-llama/llama-3.1-70b-instruct")


import re

def extract_json_from_text(text: str) -> str:
    """Extract JSON object or array from text that may contain other content."""
    # Try to find JSON object
    obj_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', text, re.DOTALL)
    if obj_match:
        return obj_match.group()
    
    # Try to find JSON array
    arr_match = re.search(r'\[[^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*\]', text, re.DOTALL)
    if arr_match:
        return arr_match.group()
    
    return text


async def call_llm(
    system_prompt: str,
    user_text: str,
    model: str = None,
    json_mode: bool = False,
    temperature: float = 0.1
) -> str:
    """
    Generic ASYNC wrapper for LLM calls.
    
    Args:
        system_prompt: Instructions for the LLM
        user_text: User input to process
        model: LLM model to use (defaults to env var)
        json_mode: If True, request JSON output (note: some models don't support this)
        temperature: Sampling temperature (lower = more deterministic)
    
    Returns:
        LLM response as string
    """
    used_model = model or DEFAULT_MODEL
    print(f"  🤖 LLM call to: {used_model[:40]}...")
    
    # Add JSON instruction to prompt if json_mode requested
    if json_mode:
        system_prompt = system_prompt + "\n\nIMPORTANT: Respond with ONLY valid JSON, no other text."
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_text}
    ]
    
    kwargs = {
        "model": used_model,
        "messages": messages,
        "temperature": temperature,
        "timeout": 30.0,
    }
    
    # Don't use response_format as many free models don't support it
    # Instead we'll extract JSON from the response
    
    try:
        response = await client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        print(f"  📨 Raw response (first 200 chars): {content[:200] if content else 'EMPTY'}...")
    except Exception as e:
        print(f"  ❌ LLM API error: {type(e).__name__}: {e}")
        raise
    
    # If json_mode was requested, try to extract JSON from response
    if json_mode and content:
        extracted = extract_json_from_text(content)
        if extracted != content:
            print(f"  🔧 Extracted JSON: {extracted[:150]}...")
        content = extracted
    
    return content


async def call_llm_with_retry(
    system_prompt: str,
    user_text: str,
    max_retries: int = 2,
    **kwargs
) -> str:
    """
    LLM call with automatic retry on failure.
    """
    last_error = None
    
    for attempt in range(max_retries + 1):
        try:
            return await call_llm(system_prompt, user_text, **kwargs)
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                print(f"⚠️ LLM call failed (attempt {attempt + 1}), retrying...")
    
    raise last_error
