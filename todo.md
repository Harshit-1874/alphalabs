# AlphaLab Frontend ↔ Backend Integration Plan

## Missing Backend Work (Must Implement)

- **Trading sessions & results (`backend/services/trading/*`, `backend/api/arena.py`, `backend/api/results.py`)**
- Backtest engine never writes `TestResult` rows—`_complete_backtest()` returns `result_{session}` instead of persisting via a ResultService. Fix persistence, compute equity curve / drawdown / Sharpe / profit factor, and update related `TestSession` + `Agent` stats.
- `TestSession.current_equity`, `current_pnl_pct`, `max_drawdown_pct`, `elapsed_seconds`, `open_position` are never updated, so `/api/arena/backtest/{id}` returns zeros. Update the engine loop to push runtime stats into the DB and broadcast them over websockets.
- Forward-testing API routes are missing entirely even though `ForwardEngine` exists—add `/api/arena/forward/start|active|{id}|stop` endpoints mirroring the spec and wire them into `ForwardEngine` (including auto-stop + countdown events).
- TODOs in `arena.py` (bull/crash date presets, elapsed seconds, result_id, final equity) must be resolved; also ensure `TestSession` stores `date_preset`, `playback_speed`, `safety_mode`, `allow_leverage` from the request.

- **WebSockets & controls (`backend/websocket/handlers.py`, `websocket/events.py`)**
- Handlers currently authenticate with `jwt.decode(..., verify_signature=False)` and ignore client commands (TODO). Implement proper Clerk token verification (reuse `verify_clerk_token`), add pause/resume/stop command handling, heartbeat pings, and surface errors to the client.
- Expose configurable WS base URL (env-driven) so the frontend can point to dev/prod clusters instead of the hard-coded `wss://api.alphalab.io` string returned today.

- **Results & insights (`backend/api/results.py`)**
- Endpoints still query `TestSession` instead of `TestResult`, returning placeholder metrics (`mode="standard"`, `total_trades=0`, etc.). After ResultService exists, switch queries to `TestResult` with joins to `Agent` and include full metrics, pagination metadata, and certificate flags.
- Implement `/api/results/{id}/export`, `/trades`, `/reasoning` to stream large payloads (paginate trades, allow candle filters). Align schemas with `frontend/types/result.ts`.

- **Model configuration & API persistence (`backend/api/api_keys.py`, `backend/services/agent_service.py`)**
- Add endpoints to set default keys (`POST /api/api-keys/{id}/set-default`), expose provider metadata (`GET /api/models` returning the curated list in `frontend/lib/dummy-data.ts`), and validate agents’ `model` values against the user’s available models.
- Ensure `AgentService.create_agent` enforces custom-indicator schema (per `CUSTOM_INDICATOR_SCHEMA.md`) and that `Agent` records are hydrated with encrypted API keys.

- **Market data & asset catalogue (`backend/api/data.py`, `services/market_data_service.py`)**
- `/api/data/assets` and `/timeframes` only return string lists; the UI expects `{ id, name, icon, available }` and `{ id, name, minutes }`. Return structured payloads sourced from a single definition so both backend validation (`ASSET_TICKER_MAP`) and frontend options stay in sync.
- Expand `MarketDataService.ASSET_TICKER_MAP` to cover every asset the UI exposes and add metadata (min/max lookback, status). Provide an endpoint for date presets/playback speeds so the arena config page stops duplicating constants.

- **Certificates, exports, and storage (`backend/services/certificate_service.py`, `utils/storage.py`, `.kiro/specs` tasks 19–26)**
- Finish Supabase bucket setup (certificates + exports), document env vars (`STORAGE_BUCKET`, `CERTIFICATE_BASE_URL`, `EXPORT_EXPIRY_HOURS`), and register global error handlers (Phase 9 Task 19) so certificate generation failures propagate cleanly.
- Ensure certificate PDF/image generation streams files and exposes `GET /api/certificates/{id}/pdf|image` plus public verification at `/api/certificates/verify/{code}`.

- **Notifications, dashboard, and quick start (`backend/services/dashboard_service.py`, `notification_service.py`, `api/notifications.py`, `api/dashboard.py`)**
- Verify the services return the richer structures the UI needs (trend deltas, activity details, unread counts). Add pagination and filtering to `/api/notifications` so the sidebar bell can query new items efficiently.
- Hook dashboard stats/activity to `TestResult`, `TestSession`, and `Notification` tables instead of relying on mocks.

- **Future considerations**
- Once the integration is live, add the Phase 11 unit/API tests, observability, and monitoring; they are not required for an end-to-end launch but will harden the platform later.

## Frontend Integration Plan

- **Shared API layer (`frontend/lib/api.ts`, hooks)**
- Centralize domain-specific hooks (agents, arena, dashboard, results, notifications, settings) to use `useApi`. Map backend snake_case payloads to the frontend types in `frontend/types/*` and deprecate `lib/dummy-data.ts` once real data flows in.
- Introduce envs for `NEXT_PUBLIC_API_URL` and `NEXT_PUBLIC_WS_URL`, and ensure Clerk tokens accompany both HTTP and WS requests.

- **Agents & API keys (`frontend/components/agents/*`, `hooks/use-api-keys.ts`)**
- Replace dummy agents in Zustand with live data from `GET /api/agents`. Hook creation/edit flows to `POST/PUT /api/agents`, wiring custom indicators and prompts. After backend exposes `/api/models`, populate model pickers dynamically.
- Use the API-key endpoints (list/create/validate/delete/set-default) to power the settings page; surface `models_available` from validation so users can bind models to agents confidently.

- **Dashboard & notifications (`components/dashboard/*`, sidebar bell)**
- Fetch `GET /api/dashboard/stats|activity|quick-start` on the dashboard route (server component or RSC). Replace mock `StatsCardRow`, `RecentActivity`, `QuickStartGuide`, and `LiveSessionsPanel` props with API payloads; the live sessions panel should merge `/api/arena/forward/active` responses with WebSocket updates.
- Hook the notification bell to `/api/notifications` and `/api/notifications/unread-count`, enabling mark-read endpoints for the popover actions.

- **Arena (backtest & forward) (`components/arena/*`, `app/dashboard/arena/*`)**
- Backtest config should call `/api/data/assets`, `/api/data/timeframes`, and `/api/data/presets` (new) to populate dropdowns, then `POST /api/arena/backtest/start`. Store the returned session (ID + ws URL) in Zustand and navigate to `battle-screen`, which connects to `wss.../ws/backtest/{id}?token=...` for candle / AI / stats events and uses the REST status endpoint for fallbacks.
- Implement Pause/Resume/Stop buttons by calling `/api/arena/backtest/{id}/pause|resume|stop`. For forward tests, mirror the same flow once the backend endpoints exist, and subscribe to countdown / live-position events.

- **Results & analytics (`components/results/*`, `app/dashboard/results/*`)**
- Results list: fetch `/api/results` with filters (search, type, result, agent, pagination). Replace dummy stats cards with `/api/results/stats`.
- Result detail page: gather `/api/results/{id}`, `/trades`, `/reasoning`, `/api/certificates/{resultId?}` and feed charts/tables. Wire the Export and Certificate buttons to `/api/export` + `/api/certificates` endpoints, handling async status polling.

- **Certificates & sharing (`components/results/certificate-preview.tsx`, `components/results/share-result.tsx`)**
- On certificate creation, trigger `POST /api/certificates` and display the returned verification + download URLs. Use the verification endpoint for public share pages.

- **Market data & indicators (charts, agent builder)**
- Charts and the indicator buffet should consume `/api/data/candles` + `/api/data/indicators` instead of `generateDummyCandles`. Cache responses client-side per asset/timeframe to minimize latency.
- Provide an endpoint or static JSON for `INDICATOR_CATEGORIES` so both agent creation and backend validation use identical identifiers.

- **Settings & profile (`app/dashboard/settings/*`)**
- Connect theme/sidebar prefs to `/api/users/me/settings` and user profile fields (timezone) to `/api/users/me`. Use optimistic updates with rollback on failure.

## Trading / Testing Pipeline (End-to-End)

1. **Agent & model setup**: User saves an agent via `POST /api/agents`, which stores model (`Agent.model`), mode, indicator set, custom indicator JSON, and the encrypted API key reference. The API key itself lives in `api_keys` with masked prefixes and validation status pulled from OpenRouter via `/api/api-keys/{id}/validate`.
2. **Data preparation**: When a backtest starts, `BacktestEngine` loads historical candles through `MarketDataService` (in-memory cache → DB cache → yfinance). Indicators are batch-calculated via `IndicatorCalculator`, honoring Monk-mode restrictions and any custom formulas.
3. **Prompt assembly & LLM call**: For each candle, `AITrader` builds a JSON-only prompt combining the candle snapshot, indicator values, current position (from `PositionManager`), and account equity, then streams a decision from OpenRouter (model defined per agent). Retry, timeout, and circuit-breaker guards live in `utils.retry`.
4. **Decision execution**: `PositionManager` enforces sizing, leverage, safety mode, and auto stop-loss/take-profit logic. Trades are persisted in `trades`, AI thoughts in `ai_thoughts`, and each action is broadcast as a WebSocket `EventType` (`CANDLE`, `AI_THINKING`, `AI_DECISION`, `POSITION_*`, `STATS_UPDATE`).
5. **Result materialization**: On completion (manual stop or natural end), a ResultService (to be implemented) must aggregate stats (PnL %, PnL $, win/loss counts, Sharpe, drawdown, equity curve, holding times) into `test_results`, link to the originating `test_session`, bump agent stats, emit `ActivityLog` + `Notification`, and return the new `result_id` to both REST and WebSocket clients.
6. **Certificates & exports**: Profitable `TestResult`s can be sent to `CertificateService`, which renders PDFs/images, stores them in Supabase, and exposes public verification URLs. Users can request exports that gather agent configs, trades, reasoning traces, etc., packaged via `ExportService` and `utils/storage`.
7. **Forward testing**: `ForwardEngine` polls `MarketDataService.get_latest_candle`, enforces next-candle countdowns, applies auto-stop rules, and mirrors the same AI/position/result flow while streaming `COUNTDOWN_UPDATE` events. Email/webhook notifications (TODOs in `forward_engine.py`) must be completed for production use.

## Implementation Todos

1. **result-persistence** – Build ResultService, update backtest/forward engines, and switch `/api/results/*` to real data.
2. **arena-forward-api** – Add forward-test routes + wire them to `ForwardEngine`, including WS URLs and status polling.
3. **ws-auth-controls** – Harden WebSocket auth, implement client command handling, and expose configurable WS origins.
4. **data-catalog-sync** – Serve structured assets/timeframes/indicator catalogs from the backend and refactor frontend config forms to consume them.
5. **certs-exports-storage** – Finish Supabase bucket configuration, env docs, global error handlers, and certificate/download endpoints.
6. **dashboard-notifications** – Connect dashboard + notification UIs to their services, ensuring pagination, unread counts, and activity feeds derive from real tables.
7. **frontend-api-migration** – Replace `lib/dummy-data` usage across dashboard/agents/arena/results/settings with API + websocket data, using typed hooks and Zustand only for transient UI state.
8. **docs-env-refresh** – Update `.env.example`, README, and setup docs to capture new env vars, storage steps, and integration flows so teams can reproduce the end-to-end system.


Once these pieces land, the UI can drop all mocked props, and AlphaLab will run full production-grade loops from model configuration through live testing, certification, and analytics.