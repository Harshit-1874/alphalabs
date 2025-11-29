# AlphaLab Backend Specification
## Index & Quick Reference

---

## 📑 DOCUMENT INDEX

| # | Document | Purpose |
|---|----------|---------|
| 01 | [01-database-schema.md](./01-database-schema.md) | Supabase/PostgreSQL schema design |
| 02 | [02-api-endpoints.md](./02-api-endpoints.md) | FastAPI REST endpoints |
| 03 | [03-websocket-events.md](./03-websocket-events.md) | Real-time WebSocket protocols |
| 04 | [04-implementation-guide.md](./04-implementation-guide.md) | Code structure & key implementations |

---

## 🏗️ ARCHITECTURE OVERVIEW

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              ALPHALAB ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐ │
│  │                  │         │                  │         │                  │ │
│  │   NEXT.JS        │◄───────►│   FASTAPI        │◄───────►│   SUPABASE       │ │
│  │   FRONTEND       │  REST   │   BACKEND        │  SQL    │   POSTGRES       │ │
│  │                  │  + WS   │                  │         │                  │ │
│  └──────────────────┘         └──────────────────┘         └──────────────────┘ │
│          │                           │                            │             │
│          │                           │                            │             │
│          ▼                           ▼                            ▼             │
│  ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐ │
│  │                  │         │                  │         │                  │ │
│  │   CLERK          │         │   OPENROUTER     │         │   SUPABASE       │ │
│  │   AUTH           │         │   AI MODELS      │         │   STORAGE        │ │
│  │                  │         │                  │         │                  │ │
│  └──────────────────┘         └──────────────────┘         └──────────────────┘ │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## 📊 DATABASE TABLES SUMMARY

| Table | Purpose | Key Columns |
|-------|---------|-------------|
| `users` | User accounts (Clerk sync) | clerk_id, email, plan |
| `user_settings` | Preferences, risk limits | theme, default_capital, max_leverage |
| `api_keys` | Encrypted OpenRouter keys | encrypted_key, status, is_default |
| `agents` | AI trading agent configs | name, mode, model, strategy_prompt |
| `test_sessions` | Active/completed tests | type, status, asset, timeframe |
| `trades` | Individual trade records | entry_price, exit_price, pnl_pct |
| `ai_thoughts` | AI reasoning log | reasoning, decision, confidence |
| `test_results` | Finalized test metrics | total_pnl_pct, win_rate, sharpe_ratio |
| `certificates` | Shareable proof of results | verification_code, share_url |
| `notifications` | User alerts | type, title, is_read |
| `activity_log` | Dashboard activity feed | activity_type, description |
| `market_data_cache` | Historical OHLCV data | asset, timeframe, OHLCV |

---

## 🔗 API ROUTES SUMMARY

### User & Settings
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/users/sync` | Sync user from Clerk |
| GET | `/api/users/me` | Get current user |
| GET/PUT | `/api/users/me/settings` | User settings |

### API Keys
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/api-keys` | List keys |
| POST | `/api/api-keys` | Create key |
| POST | `/api/api-keys/{id}/validate` | Test validity |
| DELETE | `/api/api-keys/{id}` | Delete key |

### Agents
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/agents` | List agents |
| POST | `/api/agents` | Create agent |
| GET/PUT/DELETE | `/api/agents/{id}` | Agent CRUD |
| POST | `/api/agents/{id}/duplicate` | Clone agent |

### Arena (Testing)
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/arena/backtest/start` | Start backtest |
| POST | `/api/arena/backtest/{id}/pause` | Pause |
| POST | `/api/arena/backtest/{id}/stop` | Stop |
| POST | `/api/arena/forward/start` | Start forward test |
| GET | `/api/arena/forward/active` | List active sessions |
| POST | `/api/arena/forward/{id}/stop` | Stop |

### Results
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/results` | List results |
| GET | `/api/results/stats` | Aggregate stats |
| GET | `/api/results/{id}` | Full detail |
| GET | `/api/results/{id}/trades` | Trade list |
| GET | `/api/results/{id}/reasoning` | AI thoughts |

### Certificates
| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/certificates` | Generate certificate |
| GET | `/api/certificates/{id}/pdf` | Download PDF |
| GET | `/api/certificates/verify/{code}` | Public verify |

### Dashboard
| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/dashboard/stats` | Overview stats |
| GET | `/api/dashboard/activity` | Activity feed |

---

## 🔌 WEBSOCKET EVENTS SUMMARY

### Backtest Events (Server → Client)
| Event | Trigger |
|-------|---------|
| `session_initialized` | Ready to run |
| `candle` | New candle + indicators |
| `ai_thinking` | Reasoning stream |
| `ai_decision` | Final decision |
| `position_opened` | Trade opened |
| `position_closed` | Trade closed |
| `stats_update` | Stats changed |
| `session_completed` | Test finished |

### Client → Server Actions
| Action | Purpose |
|--------|---------|
| `pause` | Pause backtest |
| `resume` | Resume backtest |
| `stop` | Stop test |
| `change_speed` | Adjust playback |

---

## 🔐 AUTHENTICATION FLOW

```
1. User logs in via Clerk (Frontend)
2. Frontend receives Clerk JWT token
3. Frontend sends token in Authorization header
4. Backend verifies JWT using Clerk JWKS
5. Backend extracts user_id from token
6. Backend queries Supabase for user record
7. Request proceeds with user context
```

---

## 📦 KEY DEPENDENCIES

| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.109.0 | Web framework |
| supabase | 2.3.0 | Database client |
| PyJWT | 2.8.0 | JWT verification |
| cryptography | 42.0.0 | API key encryption |
| pandas | 2.1.4 | Data processing |
| ta-lib | 0.4.28 | Technical indicators |
| reportlab | 4.0.8 | PDF generation |

---

## 🚀 QUICK START

```bash
# 1. Clone and setup
cd backend
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\activate on Windows
pip install -r requirements.txt

# 2. Configure environment
cp env.example .env
# Edit .env with your credentials

# 3. Run migrations
python migrations/migrate.py

# 4. Start server
uvicorn app:app --reload --port 5000
```

---

## 📝 IMPLEMENTATION CHECKLIST

### Phase 1: Core Setup
- [x] Project structure
- [x] Supabase connection
- [x] Clerk authentication
- [x] Database migrations
- [X] Basic user endpoints

### Phase 2: Agent Management
- [ ] API key encryption
- [ ] Agent CRUD endpoints
- [ ] Agent validation

### Phase 3: Trading Engine
- [x] Indicator calculator
- [x] AI trader integration
- [x] Position manager
- [x] Backtest engine

### Phase 4: WebSocket
- [x] Connection manager
- [ ] Backtest WebSocket
- [ ] Forward test WebSocket
- [ ] Price feed

### Phase 5: Results & Certificates
- [ ] Result generation
- [ ] Certificate PDF
- [ ] Public verification
- [ ] Export functionality

### Phase 6: Polish
- [ ] Error handling
- [ ] Rate limiting
- [ ] Logging
- [ ] Testing

---

**Start with:** [01-database-schema.md](./01-database-schema.md)

