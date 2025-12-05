"""
Configuration for the LLM Council.

Defines default models, chairman selection, and council parameters
for trading decision deliberation.
"""

from typing import List, Optional
from dataclasses import dataclass


@dataclass
class CouncilConfig:
    """Configuration for LLM Council deliberation."""
    
    # Council member models
    council_models: List[str]
    
    # Chairman model (synthesizes final decision)
    chairman_model: str
    
    # OpenRouter API configuration
    api_key: str
    
    # Timeout settings (in seconds)
    model_timeout: float = 30.0
    total_timeout: float = 60.0
    
    @classmethod
    def create_default(cls, api_key: str, num_models: int = 2) -> "CouncilConfig":
        """
        Create a default council configuration using free tier models.
        
        NOTE: Free tier models have strict rate limits (~20 requests/min).
        Using 2 models by default to avoid rate limiting issues.
        For more models, consider using paid tier models.
        
        Args:
            api_key: OpenRouter API key
            num_models: Number of council models (default 2 to avoid rate limits)
            
        Returns:
            CouncilConfig with default free models
        """
        # Default model pool (FREE tier models - best performing ones)
        # Based on AVAILABLE_MODELS from backend/api/models.py
        # NOTE: Using fewer models due to free tier rate limits
        default_models = [
            "meta-llama/llama-3.3-70b-instruct:free",  # Large, high quality
            "google/gemma-3-27b-it:free",  # Google's 27B model
            "nousresearch/hermes-3-llama-3.1-405b:free",  # Very large, excellent reasoning
            "mistralai/mistral-small-3.1-24b-instruct:free",  # Mistral 24B
            "google/gemma-3-12b-it:free",  # Smaller but fast
        ]
        
        # Select requested number of models (capped at 3 for free tier to avoid rate limits)
        max_free_models = min(num_models, 3)
        if num_models > 3:
            import logging
            logging.getLogger(__name__).warning(
                f"Requested {num_models} free tier models, capping at 3 to avoid rate limits. "
                "Use paid tier models for larger councils."
            )
        selected_models = default_models[:max_free_models]
        
        # Default chairman (Large, good at synthesis - Hermes 405B)
        chairman = "nousresearch/hermes-3-llama-3.1-405b:free"
        
        return cls(
            council_models=selected_models,
            chairman_model=chairman,
            api_key=api_key
        )


# OpenRouter API endpoint
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

