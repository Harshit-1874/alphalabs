"""
OpenRouter API client for making parallel LLM requests with rate limit handling.

Handles communication with OpenRouter API for querying multiple models
simultaneously with exponential backoff for rate limits.

Key rate limit handling strategies:
1. Staggered parallel requests to avoid burst rate limits
2. Extended retry logic for free tier models
3. Global rate limiting between requests
"""

import httpx
import asyncio
import logging
import random
import time
from typing import List, Dict, Any, Optional

from .config import OPENROUTER_API_URL

logger = logging.getLogger(__name__)

# Global rate limiter state
_last_request_time: float = 0.0
_rate_limit_lock = asyncio.Lock()

# Rate limit settings for free tier models
FREE_TIER_MIN_DELAY = 0.5  # Minimum delay between requests (seconds)
FREE_TIER_STAGGER_DELAY = 0.3  # Delay between parallel requests (seconds)
FREE_TIER_MAX_RETRIES = 5  # More retries for free tier
FREE_TIER_BASE_DELAY = 2.0  # Longer base delay for backoff


def is_free_tier_model(model: str) -> bool:
    """Check if a model is a free tier model."""
    return model.endswith(":free")


async def _apply_rate_limit() -> None:
    """Apply global rate limiting to avoid overwhelming the API."""
    global _last_request_time
    
    async with _rate_limit_lock:
        current_time = time.time()
        time_since_last = current_time - _last_request_time
        
        if time_since_last < FREE_TIER_MIN_DELAY:
            delay = FREE_TIER_MIN_DELAY - time_since_last
            await asyncio.sleep(delay)
        
        _last_request_time = time.time()


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = 30.0,
    http_referer: str = "http://localhost:3000",
    x_title: str = "AlphaLabs",
    max_retries: int = 3,
    base_delay: float = 1.0
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API with exponential backoff for rate limits.
    
    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        api_key: OpenRouter API key
        timeout: Request timeout in seconds
        http_referer: HTTP Referer header
        x_title: X-Title header
        max_retries: Maximum number of retry attempts for rate limits
        base_delay: Base delay in seconds for exponential backoff
        
    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    # Use extended retry settings for free tier models
    is_free = is_free_tier_model(model)
    actual_max_retries = FREE_TIER_MAX_RETRIES if is_free else max_retries
    actual_base_delay = FREE_TIER_BASE_DELAY if is_free else base_delay
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": http_referer,
        "X-Title": x_title,
    }
    
    payload = {
        "model": model,
        "messages": messages,
    }
    
    for attempt in range(actual_max_retries):
        try:
            # Apply global rate limiting before each request
            await _apply_rate_limit()
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    OPENROUTER_API_URL,
                    headers=headers,
                    json=payload
                )
                
                # Handle rate limiting with exponential backoff
                if response.status_code == 429:
                    if attempt < actual_max_retries - 1:
                        # Add jitter to prevent thundering herd
                        jitter = random.uniform(0.5, 1.5)
                        delay = actual_base_delay * (2 ** attempt) * jitter
                        
                        # Check for Retry-After header
                        retry_after = response.headers.get('Retry-After')
                        if retry_after:
                            try:
                                delay = max(delay, float(retry_after))
                            except ValueError:
                                pass
                        
                        logger.warning(
                            f"Rate limit hit for model {model}, "
                            f"retrying in {delay:.1f}s (attempt {attempt + 1}/{actual_max_retries})"
                        )
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"Rate limit exceeded for model {model} after {actual_max_retries} attempts")
                        return None
                
                response.raise_for_status()
                data = response.json()
                
                message = data['choices'][0]['message']
                return {
                    'content': message.get('content'),
                    'reasoning_details': message.get('reasoning_details')
                }
                
        except httpx.TimeoutException:
            logger.warning(f"Timeout querying model {model} (attempt {attempt + 1}/{actual_max_retries})")
            if attempt == actual_max_retries - 1:
                return None
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                # This is already handled above
                continue
            logger.error(f"HTTP error querying model {model}: {e.response.status_code}")
            return None
        except Exception as e:
            logger.error(f"Error querying model {model}: {e}")
            return None
    
    return None


async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float = 30.0
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models with staggered parallel requests.
    
    For free tier models, requests are staggered to avoid burst rate limits.
    This provides a balance between speed and rate limit compliance.
    
    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model
        api_key: OpenRouter API key
        timeout: Request timeout per model
        
    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    # Check if any models are free tier
    has_free_models = any(is_free_tier_model(m) for m in models)
    
    if has_free_models:
        # Staggered execution for free tier models to avoid rate limits
        logger.info(f"Using staggered requests for {len(models)} free tier models")
        return await _query_models_staggered(models, messages, api_key, timeout)
    else:
        # Full parallel execution for paid models
        return await _query_models_full_parallel(models, messages, api_key, timeout)


async def _query_models_full_parallel(
    models: List[str],
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float
) -> Dict[str, Optional[Dict[str, Any]]]:
    """Execute all model queries in full parallel (for paid tier)."""
    tasks = [
        query_model(model, messages, api_key, timeout)
        for model in models
    ]
    
    responses = await asyncio.gather(*tasks, return_exceptions=True)
    
    result = {}
    for model, response in zip(models, responses):
        if isinstance(response, Exception):
            logger.error(f"Exception querying model {model}: {response}")
            result[model] = None
        else:
            result[model] = response
    
    return result


async def _query_models_staggered(
    models: List[str],
    messages: List[Dict[str, str]],
    api_key: str,
    timeout: float
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Execute model queries with staggered starts to avoid rate limits.
    
    Models are started with delays between them but still run concurrently.
    This provides a balance between parallel execution and rate limit compliance.
    """
    async def query_with_delay(model: str, delay: float) -> tuple:
        """Query a model after a specified delay."""
        if delay > 0:
            await asyncio.sleep(delay)
        response = await query_model(model, messages, api_key, timeout)
        return model, response
    
    # Create tasks with staggered delays
    tasks = []
    for i, model in enumerate(models):
        delay = i * FREE_TIER_STAGGER_DELAY
        tasks.append(query_with_delay(model, delay))
    
    # Wait for all to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # Map models to their responses
    result = {}
    for item in results:
        if isinstance(item, Exception):
            logger.error(f"Exception in staggered query: {item}")
        else:
            model, response = item
            result[model] = response
    
    return result

