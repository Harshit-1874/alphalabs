<!-- 234a73d2-cec8-4d99-b069-dc8d5357a1c0 55764077-ef0a-4571-a312-d6ba2c49c8fb -->
# Council Mode for Trading Decisions

## Backend Implementation

### 1. Core Council Service (`backend/services/llm_council/`)

Create new council service modules based on your reference code:

- **`__init__.py`** - Package initialization
- **`config.py`** - Council configuration (models list, chairman model)
- **`openrouter.py`** - OpenRouter API client for parallel queries
- **`council.py`** - 3-stage orchestration (collect, rank, synthesize)

Key adaptations for trading context:

- Stage 1: Each model analyzes market data and provides trading decision
- Stage 2: Models rank each other's decisions based on risk/reward analysis  
- Stage 3: Chairman synthesizes final trading decision (action, size, stop-loss, take-profit)

### 2. Council-Enabled AI Trader (`backend/services/ai_council_trader.py`)

Create `AICouncilTrader` class that:

- Inherits from or wraps `AITrader` behavior
- Implements `get_decision()` method that runs full 3-stage council
- Returns `AIDecision` object (same interface as `AITrader`)
- Includes metadata about all stages for frontend display

### 3. Database Schema Updates

Add council mode configuration to `test_sessions` table:

```sql
ALTER TABLE test_sessions ADD COLUMN council_mode BOOLEAN DEFAULT FALSE;
ALTER TABLE test_sessions ADD COLUMN council_models JSONB;
ALTER TABLE test_sessions ADD COLUMN council_chairman_model VARCHAR(100);
```

Update `ai_thoughts` table to store council deliberation:

```sql
ALTER TABLE ai_thoughts ADD COLUMN council_stage1 JSONB;
ALTER TABLE ai_thoughts ADD COLUMN council_stage2 JSONB;
ALTER TABLE ai_thoughts ADD COLUMN council_metadata JSONB;
```

### 4. API Schema Updates (`backend/schemas/arena_schemas.py`)

Add to `BacktestStartRequest`:

```python
council_mode: bool = False
council_models: Optional[List[str]] = None  # e.g., ["openai/gpt-4", "anthropic/claude-3.5-sonnet"]
council_chairman_model: Optional[str] = None
```

### 5. Backtest Engine Integration (`backend/services/trading/backtest_engine/`)

**`engine.py`** - Modify `start_backtest()`:

- Accept new council parameters
- Conditionally instantiate `AICouncilTrader` instead of `AITrader` when `council_mode=True`
- Pass council config to session state

**`session_state.py`** - Add fields:

```python
council_mode: bool = False
council_config: Optional[Dict[str, Any]] = None
```

**`processor.py`** - No changes needed (works through same `get_decision()` interface)

### 6. Performance Optimizations

- Council mode forces longer decision intervals (minimum 5 candles)
- Add timeout handling for slow council responses (60s vs 20s for single model)
- Parallel API calls in Stage 1 and Stage 2 to minimize latency

## Frontend Implementation

### 7. Backtest Config UI (`frontend/components/arena/backtest/backtest-config.tsx`)

Add prominent Council Mode section after Advanced Settings:

**Council Mode Toggle Card** (always visible):

- Large toggle switch with gradient background
- "🧠 Council Mode" heading with badge "EXPERIMENTAL"
- Description: "Let multiple AI models debate and collaborate on each trading decision"
- Prominent visual indicator when enabled

**Council Configuration Panel** (shown when enabled):

- Model selector (multi-select dropdown)
  - Default: 3 models pre-selected (Claude Sonnet, GPT-4, Gemini Pro)
  - Show model badges with colors
- Chairman model selector (single select)
  - Default: Gemini Pro
- Info card: "⚡ Council mode takes 3-5x longer but provides more robust decisions"
- Auto-adjust decision interval to minimum 5 candles when council mode enabled

### 8. Promotional Banner (`frontend/components/arena/council-mode-banner.tsx`)

Create eye-catching banner component:

- Gradient background (purple to blue)
- Icon animation (rotating brain or sparkles)
- Text: "✨ Try Council Mode - Multiple AI minds, better trading decisions"
- CTA button: "Enable Council Mode"
- Dismissible but reappears periodically

Show banner:

- At top of backtest config page when council mode OFF
- On backtest results page with suggestion to retry with council mode

### 9. Battle Screen Council Display (`frontend/components/arena/backtest/battle-screen.tsx`)

When council mode active, enhance AI Thought panel:

**Stage Visualization**:

- Tabbed interface: "Stage 1: Individual Responses" | "Stage 2: Rankings" | "Stage 3: Final Decision"
- Stage 1: Show all model responses with avatars/icons
- Stage 2: Show ranking matrix and aggregate scores
- Stage 3: Highlight final synthesized decision with chairman badge
- Visual flow diagram showing deliberation process

**Compact Mode**:

- Show final decision by default
- "View Council Deliberation" expandable section

### 10. Forward Test Info Card (`frontend/components/arena/forward/forward-test-config.tsx`)

Add info banner at top:

```tsx
<Alert variant="info">
  <Info className="h-4 w-4" />
  <AlertDescription>
    🚀 Council Mode for Forward Testing coming soon! Currently available in Backtest mode.
  </AlertDescription>
</Alert>
```

### 11. Type Definitions (`frontend/types/arena.ts`)

Add council-related types:

```typescript
interface CouncilConfig {
  enabled: boolean;
  models: string[];
  chairmanModel: string;
}

interface CouncilDeliberation {
  stage1: Array<{model: string; response: string}>;
  stage2: Array<{model: string; ranking: string}>;
  stage3: {model: string; response: string};
  metadata: {
    aggregateRankings: Array<{model: string; averageRank: number}>;
  };
}
```

## Migration & Configuration

### 12. Database Migration (`backend/migrations/0XX_add_council_mode.sql`)

Create migration for schema changes.

### 13. Configuration Defaults (`backend/config.py`)

Add council settings:

```python
# Council Mode Configuration
COUNCIL_DEFAULT_MODELS: List[str] = [
    "anthropic/claude-3.5-sonnet",
    "openai/gpt-4o", 
    "google/gemini-2.0-flash-001"
]
COUNCIL_CHAIRMAN_MODEL: str = "google/gemini-2.0-flash-001"
COUNCIL_DECISION_TIMEOUT: int = 60  # seconds
```

## Testing & Documentation

### 14. Testing Strategy

- Unit tests for council service modules
- Integration test for council-enabled backtest
- Frontend component tests for council UI
- Manual testing with real API calls (use cheap models in dev)

### 15. Documentation

- Update API docs with new council parameters
- Add user guide for council mode feature
- Document model selection best practices
- Add performance considerations guide

### To-dos

- [ ] Create council service modules (config, openrouter, council logic)
- [ ] Implement AICouncilTrader class with trading-specific adaptations
- [ ] Create migration and update models for council mode fields
- [ ] Update arena_schemas.py with council configuration fields
- [ ] Integrate council trader into backtest engine and session state
- [ ] Add council mode toggle and configuration panel to backtest config
- [ ] Create promotional council mode banner component
- [ ] Enhance battle screen to show 3-stage council deliberation
- [ ] Add coming soon info card to forward test page
- [ ] Add TypeScript types for council configuration and data