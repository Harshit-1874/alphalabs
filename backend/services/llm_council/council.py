"""
3-stage LLM Council orchestration for trading decisions.

Stage 1: Collect individual trading decisions from all council models
Stage 2: Each model ranks the anonymized decisions
Stage 3: Chairman synthesizes final trading decision

Includes rate limiting between stages to avoid API throttling.
"""

import re
import asyncio
import logging
import time
from typing import List, Dict, Any, Tuple, Optional
from collections import defaultdict

from .openrouter import query_models_parallel, query_model, is_free_tier_model
from .config import CouncilConfig

logger = logging.getLogger(__name__)

# Cooldown between stages for free tier models (seconds)
FREE_TIER_STAGE_COOLDOWN = 2.0

# Global cooldown between full council deliberations
_last_deliberation_time: float = 0.0
_deliberation_lock = asyncio.Lock()
DELIBERATION_COOLDOWN = 3.0  # Minimum seconds between deliberations


async def stage1_collect_responses(
    config: CouncilConfig,
    trading_prompt: str
) -> List[Dict[str, Any]]:
    """
    Stage 1: Collect individual trading decisions from all council models.
    
    Args:
        config: Council configuration
        trading_prompt: The trading analysis prompt
        
    Returns:
        List of dicts with 'model' and 'response' keys
    """
    messages = [{"role": "user", "content": trading_prompt}]
    
    # Query all models in parallel
    responses = await query_models_parallel(
        config.council_models,
        messages,
        config.api_key,
        config.model_timeout
    )
    
    # Format results (only include successful responses)
    stage1_results = []
    for model, response in responses.items():
        if response is not None:
            stage1_results.append({
                "model": model,
                "response": response.get('content', '')
            })
    
    logger.info(f"Stage 1: Collected {len(stage1_results)}/{len(config.council_models)} responses")
    return stage1_results


async def stage2_collect_rankings(
    config: CouncilConfig,
    trading_prompt: str,
    stage1_results: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized trading decisions.
    
    Args:
        config: Council configuration
        trading_prompt: The original trading prompt
        stage1_results: Results from Stage 1
        
    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    # Create anonymized labels for responses (Decision A, Decision B, etc.)
    labels = [chr(65 + i) for i in range(len(stage1_results))]  # A, B, C, ...
    
    # Create mapping from label to model name
    label_to_model = {
        f"Decision {label}": result['model']
        for label, result in zip(labels, stage1_results)
    }
    
    # Build the ranking prompt
    decisions_text = "\n\n".join([
        f"Decision {label}:\n{result['response']}"
        for label, result in zip(labels, stage1_results)
    ])
    
    ranking_prompt = f"""You are evaluating different trading decisions for the following scenario:

ORIGINAL TRADING SCENARIO:
{trading_prompt}

Here are the decisions from different AI models (anonymized):

{decisions_text}

Your task:
1. First, evaluate each decision individually. For each decision, analyze:
   - Risk assessment accuracy
   - Position sizing appropriateness
   - Stop-loss and take-profit levels
   - Reasoning quality
   - Alignment with market conditions

2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the decisions from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the decision label (e.g., "1. Decision A")
- Do not add any other text or explanations in the ranking section

Example of the correct format:

Decision A provides good risk management but the position size may be too aggressive...
Decision B has conservative stops but may miss the opportunity...
Decision C offers the most balanced approach considering the volatility...

FINAL RANKING:
1. Decision C
2. Decision A
3. Decision B

Now provide your evaluation and ranking:"""
    
    messages = [{"role": "user", "content": ranking_prompt}]
    
    # Get rankings from all council models in parallel
    responses = await query_models_parallel(
        config.council_models,
        messages,
        config.api_key,
        config.model_timeout
    )
    
    # Format results
    stage2_results = []
    for model, response in responses.items():
        if response is not None:
            full_text = response.get('content', '')
            parsed = parse_ranking_from_text(full_text)
            stage2_results.append({
                "model": model,
                "ranking": full_text,
                "parsed_ranking": parsed
            })
    
    logger.info(f"Stage 2: Collected {len(stage2_results)}/{len(config.council_models)} rankings")
    return stage2_results, label_to_model


async def stage3_synthesize_final(
    config: CouncilConfig,
    trading_prompt: str,
    stage1_results: List[Dict[str, Any]],
    stage2_results: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final trading decision.
    
    Args:
        config: Council configuration
        trading_prompt: The original trading prompt
        stage1_results: Individual model decisions from Stage 1
        stage2_results: Rankings from Stage 2
        
    Returns:
        Dict with 'model' and 'response' keys
    """
    # Build comprehensive context for chairman
    stage1_text = "\n\n".join([
        f"Model: {result['model']}\nDecision: {result['response']}"
        for result in stage1_results
    ])
    
    stage2_text = "\n\n".join([
        f"Model: {result['model']}\nRanking: {result['ranking']}"
        for result in stage2_results
    ])
    
    chairman_prompt = f"""You are the Chairman of an AI Trading Council. Multiple AI models have provided trading decisions for a scenario, and then ranked each other's decisions.

ORIGINAL TRADING SCENARIO:
{trading_prompt}

STAGE 1 - Individual Trading Decisions:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, optimal trading decision. Consider:
- The individual decisions and their risk/reward profiles
- The peer rankings and what they reveal about decision quality
- Any patterns of agreement or disagreement
- Market conditions and risk factors

CRITICAL: Your response MUST be in the EXACT SAME JSON FORMAT as the individual decisions above. Include:
- "action": one of ["long", "short", "close_long", "close_short", "hold"]
- "reasoning": your comprehensive analysis incorporating council wisdom
- "size_percentage": position size as decimal (0.0 to 1.0)
- "leverage": leverage multiplier (1 for no leverage)
- "stop_loss_price": stop loss price level (or null)
- "take_profit_price": take profit price level (or null)

Provide your final synthesized trading decision as a JSON object:"""
    
    messages = [{"role": "user", "content": chairman_prompt}]
    
    # Query the chairman model
    response = await query_model(
        config.chairman_model,
        messages,
        config.api_key,
        config.model_timeout
    )
    
    if response is None:
        # Fallback if chairman fails
        logger.error("Stage 3: Chairman model failed to respond")
        return {
            "model": config.chairman_model,
            "response": '{"action": "hold", "reasoning": "Council deliberation failed - chairman unable to synthesize decision", "size_percentage": 0.0, "leverage": 1, "stop_loss_price": null, "take_profit_price": null}'
        }
    
    logger.info(f"Stage 3: Chairman synthesized final decision")
    return {
        "model": config.chairman_model,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.
    
    Args:
        ranking_text: The full text response from the model
        
    Returns:
        List of decision labels in ranked order (e.g., ["Decision A", "Decision B"])
    """
    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            
            # Try to extract numbered list format (e.g., "1. Decision A")
            numbered_matches = re.findall(r'\d+\.\s*Decision [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Decision X" part
                return [re.search(r'Decision [A-Z]', m).group() for m in numbered_matches]
            
            # Fallback: Extract all "Decision X" patterns in order
            matches = re.findall(r'Decision [A-Z]', ranking_section)
            return matches
    
    # Fallback: try to find any "Decision X" patterns in order
    matches = re.findall(r'Decision [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Dict[str, Any]],
    label_to_model: Dict[str, str]
) -> List[Dict[str, Any]]:
    """
    Calculate aggregate rankings across all models using Borda count method.
    
    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names
        
    Returns:
        List of dicts with model name and average rank, sorted best to worst
    """
    # Track positions for each model
    model_positions = defaultdict(list)
    
    for ranking in stage2_results:
        parsed_ranking = ranking.get('parsed_ranking', [])
        
        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)
    
    # Calculate average position for each model
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append({
                "model": model,
                "average_rank": round(avg_rank, 2),
                "rankings_count": len(positions)
            })
    
    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x['average_rank'])
    
    return aggregate


async def _apply_deliberation_cooldown() -> None:
    """Apply cooldown between council deliberations."""
    global _last_deliberation_time
    
    async with _deliberation_lock:
        current_time = time.time()
        time_since_last = current_time - _last_deliberation_time
        
        if time_since_last < DELIBERATION_COOLDOWN:
            delay = DELIBERATION_COOLDOWN - time_since_last
            logger.info(f"Applying deliberation cooldown: {delay:.1f}s")
            await asyncio.sleep(delay)
        
        _last_deliberation_time = time.time()


async def run_trading_council(
    config: CouncilConfig,
    trading_prompt: str
) -> Tuple[str, Dict[str, Any]]:
    """
    Run the complete 3-stage council process for a trading decision.
    
    Includes rate limiting between stages for free tier models.
    
    Args:
        config: Council configuration
        trading_prompt: The trading analysis prompt with market data
        
    Returns:
        Tuple of (final_decision_text, deliberation_metadata)
        deliberation_metadata contains stage1, stage2, stage3 results and aggregate rankings
    """
    try:
        # Apply cooldown between deliberations
        await _apply_deliberation_cooldown()
        
        # Check if using free tier models
        has_free_models = any(is_free_tier_model(m) for m in config.council_models)
        stage_cooldown = FREE_TIER_STAGE_COOLDOWN if has_free_models else 0.5
        
        # Stage 1: Collect individual decisions
        logger.info("Council Stage 1: Collecting individual decisions...")
        stage1_results = await stage1_collect_responses(config, trading_prompt)
        
        # If no models responded successfully, return error
        if not stage1_results:
            error_decision = '{"action": "hold", "reasoning": "All council models failed to respond - rate limited. Try using fewer models or paid tier.", "size_percentage": 0.0, "leverage": 1, "stop_loss_price": null, "take_profit_price": null}'
            return error_decision, {
                "stage1": [],
                "stage2": [],
                "stage3": {"model": "error", "response": error_decision},
                "aggregate_rankings": [],
                "label_to_model": {},
                "rate_limited": True
            }
        
        # Cooldown between Stage 1 and Stage 2
        if has_free_models:
            logger.info(f"Free tier cooldown between stages: {stage_cooldown}s")
            await asyncio.sleep(stage_cooldown)
        
        # Stage 2: Collect rankings
        logger.info("Council Stage 2: Collecting rankings...")
        stage2_results, label_to_model = await stage2_collect_rankings(
            config, trading_prompt, stage1_results
        )
        
        # Calculate aggregate rankings
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
        
        # Cooldown between Stage 2 and Stage 3
        if has_free_models:
            await asyncio.sleep(stage_cooldown)
        
        # Stage 3: Synthesize final decision
        logger.info("Council Stage 3: Chairman synthesizing final decision...")
        stage3_result = await stage3_synthesize_final(
            config,
            trading_prompt,
            stage1_results,
            stage2_results
        )
        
        # Prepare deliberation metadata
        deliberation = {
            "stage1": stage1_results,
            "stage2": stage2_results,
            "stage3": stage3_result,
            "aggregate_rankings": aggregate_rankings,
            "label_to_model": label_to_model
        }
        
        return stage3_result['response'], deliberation
        
    except Exception as e:
        logger.error(f"Error in council deliberation: {e}")
        error_decision = f'{{"action": "hold", "reasoning": "Council error: {str(e)}", "size_percentage": 0.0, "leverage": 1, "stop_loss_price": null, "take_profit_price": null}}'
        return error_decision, {
            "stage1": [],
            "stage2": [],
            "stage3": {"model": "error", "response": error_decision},
            "aggregate_rankings": [],
            "label_to_model": {},
            "error": str(e)
        }

