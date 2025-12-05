"""
Model Inspector Service for OpenRouter.

Purpose:
    Inspects and caches OpenRouter model metadata to:
    - Validate model IDs before use
    - Get appropriate max_tokens based on context length
    - Check model capabilities (structured outputs, etc.)
    - Provide better error messages

Usage:
    inspector = ModelInspector(api_key)
    model_info = await inspector.get_model_info("anthropic/claude-3.5-sonnet")
    max_tokens = await inspector.get_optimal_max_tokens("anthropic/claude-3.5-sonnet")
"""
import asyncio
import logging
from typing import Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import httpx

from config import settings

logger = logging.getLogger(__name__)


class ModelInfo:
    """Model metadata from OpenRouter"""
    def __init__(self, data: Dict[str, Any]):
        self.id = data.get("id", "")
        self.name = data.get("name", "")
        self.context_length = data.get("context_length", 8192)
        self.pricing = data.get("pricing", {})
        self.capabilities = data.get("capabilities", {})
        self.architecture = data.get("architecture", {})
        
    @property
    def supports_structured_outputs(self) -> bool:
        """Check if model supports structured outputs (json_schema)"""
        # Most models with function calling support structured outputs
        return self.capabilities.get("function_calling", False) or \
               self.capabilities.get("structured_outputs", False)
    
    @property
    def supports_json_mode(self) -> bool:
        """Check if model supports json_object mode"""
        # Most modern models support this
        return True  # Most models support json_object mode


class ModelInspector:
    """
    Inspects OpenRouter models to get metadata and capabilities.
    
    Uses the single-model endpoints endpoint to fetch only the specific model
    needed, avoiding the expensive all-models fetch. Caches per-model for 1 hour.
    """
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        # Per-model cache with timestamps
        self._model_cache: Dict[str, Tuple[ModelInfo, datetime]] = {}
        self._cache_ttl = timedelta(hours=1)
        self._lock = asyncio.Lock()
    
    async def _fetch_models_list(self) -> Dict[str, Dict[str, Any]]:
        """
        Fetch all models from OpenRouter and return as a dict keyed by model ID.
        
        This is cached to avoid repeated fetches. The /models/{id}/endpoints
        endpoint doesn't work (returns 404), so we must use the /models list.
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://openrouter.ai/api/v1/models",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "HTTP-Referer": settings.OPENROUTER_HTTP_REFERER,
                        "X-Title": settings.OPENROUTER_X_TITLE
                    },
                    timeout=10.0
                )
                
                if response.status_code != 200:
                    logger.warning(
                        f"Failed to fetch models list from OpenRouter: {response.status_code}"
                    )
                    return {}
                
                data = response.json()
                models_data = data.get("data", [])
                
                # Convert to dict keyed by model ID for fast lookup
                models_dict = {model.get("id"): model for model in models_data if model.get("id")}
                
                logger.debug(f"Fetched {len(models_dict)} models from OpenRouter")
                return models_dict
                
        except Exception as e:
            logger.error(f"Error fetching models list from OpenRouter: {e}")
            return {}
    
    async def _fetch_single_model(self, model_id: str) -> Optional[ModelInfo]:
        """
        Fetch a single model's information by filtering the /models list.
        
        The /models/{id}/endpoints endpoint returns 404, so we fetch the
        full models list (cached) and filter for the specific model.
        """
        async with self._lock:
            now = datetime.now()
            
            # Check if we have a cached models list
            cache_key = "_models_list_cache"
            if hasattr(self, cache_key):
                cache_data, cache_time = getattr(self, cache_key)
                if (now - cache_time) < self._cache_ttl:
                    models_dict = cache_data
                else:
                    # Cache expired, fetch fresh
                    models_dict = await self._fetch_models_list()
                    setattr(self, cache_key, (models_dict, now))
            else:
                # No cache, fetch and store
                models_dict = await self._fetch_models_list()
                setattr(self, cache_key, (models_dict, now))
        
        # Try exact match first
        model_data = models_dict.get(model_id)
        
        # Try without suffix if model_id has one (e.g., "amazon/nova-2-lite-v1:free" -> "amazon/nova-2-lite-v1")
        if not model_data and ":" in model_id:
            base_id = model_id.split(":")[0]
            model_data = models_dict.get(base_id)
        
        if not model_data:
            logger.warning(f"Model {model_id} not found in OpenRouter models list")
            return None
        
        # Convert to ModelInfo format
        model_info_data = {
            "id": model_data.get("id", model_id),
            "name": model_data.get("name", model_id),
            "context_length": model_data.get("context_length", 8192),
            "pricing": model_data.get("pricing", {}),
            "capabilities": model_data.get("capabilities", {}),
            "architecture": model_data.get("architecture", {})
        }
        
        logger.debug(f"Found model info for {model_id} from OpenRouter models list")
        return ModelInfo(model_info_data)
    
    async def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        """
        Get model information by ID.
        
        Uses cached models list (fetched once per hour) and filters for the
        specific model needed. Much more efficient than fetching all models
        on every call.
        
        Args:
            model_id: Model identifier (e.g., "anthropic/claude-3.5-sonnet")
            
        Returns:
            ModelInfo if found, None otherwise
        """
        # Check per-model cache first (for faster repeated lookups)
        async with self._lock:
            now = datetime.now()
            
            if model_id in self._model_cache:
                cached_info, cache_time = self._model_cache[model_id]
                if (now - cache_time) < self._cache_ttl:
                    return cached_info
                del self._model_cache[model_id]
            
            # Try without suffix if model_id has one
            base_id = None
            if ":" in model_id:
                base_id = model_id.split(":")[0]
                if base_id in self._model_cache:
                    cached_info, cache_time = self._model_cache[base_id]
                    if (now - cache_time) < self._cache_ttl:
                        return cached_info
                    del self._model_cache[base_id]
        
        # Fetch from cached models list (models list itself is cached for 1 hour)
        model_info = await self._fetch_single_model(model_id)
        
        # If that failed and we have a base_id, try the base model
        if model_info is None and base_id:
            model_info = await self._fetch_single_model(base_id)
        
        # Cache the result for faster future lookups
        if model_info:
            async with self._lock:
                self._model_cache[model_id] = (model_info, datetime.now())
                if base_id:
                    self._model_cache[base_id] = (model_info, datetime.now())
            return model_info
        
        logger.warning(f"Model not found in OpenRouter: {model_id}")
        return None
    
    async def validate_model(self, model_id: str) -> bool:
        """
        Validate that a model exists and is available.
        
        Args:
            model_id: Model identifier
            
        Returns:
            True if model exists, False otherwise
        """
        model_info = await self.get_model_info(model_id)
        return model_info is not None
    
    async def get_optimal_max_tokens(
        self,
        model_id: str,
        default: int = 2048,
        min_tokens: int = 512,
        max_tokens: int = 8192
    ) -> int:
        """
        Get optimal max_tokens for a model based on its context length.
        
        Uses 10% of context length, but clamped between min and max.
        
        Args:
            model_id: Model identifier
            default: Default value if model not found
            min_tokens: Minimum allowed max_tokens
            max_tokens: Maximum allowed max_tokens
            
        Returns:
            Optimal max_tokens value
        """
        model_info = await self.get_model_info(model_id)
        
        if not model_info:
            logger.warning(
                f"Model {model_id} not found, using default max_tokens={default}"
            )
            return default
        
        # Use 10% of context length, but ensure reasonable bounds
        context_length = model_info.context_length
        optimal = int(context_length * 0.1)
        
        # Clamp to reasonable bounds
        optimal = max(min_tokens, min(optimal, max_tokens))
        
        logger.debug(
            f"Model {model_id}: context_length={context_length}, "
            f"optimal_max_tokens={optimal}"
        )
        
        return optimal
    
    async def supports_structured_outputs(self, model_id: str) -> bool:
        """
        Check if model supports structured outputs (json_schema).
        
        Args:
            model_id: Model identifier
            
        Returns:
            True if model supports structured outputs, False otherwise
        """
        model_info = await self.get_model_info(model_id)
        if not model_info:
            return False  # Default to False if model not found
        
        return model_info.supports_structured_outputs
    
    async def get_model_endpoints(self, model_id: str) -> Optional[Dict[str, Any]]:
        """
        Get model information including endpoints data.
        
        Note: The /models/{id}/endpoints endpoint returns 404, so we use
        the /models list and return the model data directly.
        
        Args:
            model_id: Model identifier (e.g., "openai/gpt-4o")
            
        Returns:
            Model data dict if found, None otherwise
        """
        model_info = await self.get_model_info(model_id)
        if not model_info:
            return None
        
        # Return model data in a format similar to what endpoints would return
        return {
            "id": model_info.id,
            "name": model_info.name,
            "architecture": model_info.architecture,
            "context_length": model_info.context_length,
            "pricing": model_info.pricing,
            "capabilities": model_info.capabilities
        }

