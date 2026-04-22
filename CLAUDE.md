# StockBook — Claude Development Guide

## Project Overview

股票買賣紀錄 web app，支援台股（.TW）和美股。顯示自選股清單、未實現/已實現損益、股息損益。
目標使用者：≤5 人。設計原則：簡單，不過度工程。

---

## Architecture

```
StockBook/
├── backend/         # Python FastAPI
├── frontend/        # Vite + React + TypeScript + Tailwind CSS
└── infra/           # GCP 部署設定
```

**後端**：FastAPI + SQLAlchemy (async) + PostgreSQL + APScheduler + yfinance  
**前端**：Vite + React + TypeScript + Tailwind CSS + React Query  
**部署**：Cloud Run（後端）+ Cloud SQL PostgreSQL + Firebase Hosting（前端）

---

## Development Commands

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# 啟動 dev server
uvicorn app.main:app --reload --port 8000

# 執行測試
pytest

# DB migration
alembic upgrade head
alembic revision --autogenerate -m "description"
```

### Frontend
```bash
cd frontend
npm install
npm run dev        # 啟動 dev server（port 5173）
npm run build      # 打包
npm run typecheck  # TypeScript 型別檢查
```

---

## Backend Conventions

### Project Structure
```
backend/app/
├── main.py              # FastAPI app factory, lifespan（scheduler 啟停）
├── config.py            # pydantic-settings，讀 .env
├── database.py          # asyncpg engine, AsyncSession, get_db dependency
├── models/              # SQLAlchemy ORM models
├── schemas/             # Pydantic request/response schemas
├── api/                 # Route handlers（thin，只呼叫 services）
│   └── deps.py          # get_current_user, get_db dependencies
├── services/            # 業務邏輯（純 Python，可單元測試）
└── scheduler/           # APScheduler jobs
```

### Rules
- Route handler 只做：驗證輸入 → 呼叫 service → 回傳 schema。不含業務邏輯。
- 業務邏輯全部在 `services/` 層，不依賴 FastAPI/HTTP。
- 所有 DB 操作使用 async SQLAlchemy（`AsyncSession`）。
- 金額欄位一律用 `NUMERIC(18,6)`，**不用 float**。
- 所有金額以原始貨幣儲存（USD 存 USD，TWD 存 TWD），P&L 計算時才換算。
- 台股 ticker 在進入 DB 前正規化：`2330` → `2330.TW`（在 `stock_service` 處理）。
- yfinance 呼叫一律用 `yf.download(tickers_list)` 批次，不逐一呼叫。

### Auth
- JWT Bearer token，`python-jose` + `passlib[bcrypt]`
- Phase 1：hardcoded seed user，從 `.env` 讀取（`SEED_USERNAME`, `SEED_PASSWORD`）
- `get_current_user` dependency 在 `api/deps.py`，所有需要認證的 endpoint 都注入此 dependency

### Error Handling
- HTTP 例外用 FastAPI 的 `HTTPException`
- Service 層丟 Python 例外（`ValueError`, `PermissionError`），由 route handler 轉換成 `HTTPException`

---

## Frontend Conventions

### Project Structure
```
frontend/src/
├── api/            # Axios client + 各模組 API 函式
│   └── client.ts   # Axios instance，token 注入，401 自動 refresh
├── components/
│   ├── ui/         # 基礎元件（Button, Input, Card, Modal）
│   └── layout/     # Navbar, BottomTabBar, PageShell
├── pages/          # 頁面元件
├── hooks/          # React Query hooks
├── context/        # AuthContext
└── types/          # TypeScript interfaces（對應後端 schema）
```

### Rules
- 所有 API 呼叫只透過 `src/api/` 的函式，不在元件內直接用 `axios`。
- Server state 用 React Query（`useQuery`, `useMutation`），不用 `useState` 儲存 API 資料。
- RWD：mobile-first，用 `lg:` prefix 處理桌面版差異。
- 手機版 table 改用 card list（`hidden sm:table` / `block sm:hidden`）。
- P&L 正數顯示綠色（`text-green-600`），負數顯示紅色（`text-red-600`）。
- JWT 存在 `localStorage`（Phase 1 可接受，使用者為固定少數人）。

---

## Database Schema（Quick Reference）

| Table | 說明 |
|-------|------|
| `users` | 使用者，含 `is_active`, `is_superuser` |
| `stocks` | 股票基本資料 + 最新價格快取 |
| `transactions` | 買賣紀錄，含 `fee` 欄位 |
| `dividends` | 股息紀錄 |
| `exchange_rates` | USD/TWD 匯率歷史（append-only） |
| `watchlist` | 使用者自選股（M:N，獨立 table） |

**所有 table 在 initial migration 一次建立**，即使 Phase 1 尚未使用所有 table。

---

## Testing

### Backend
- 測試框架：`pytest` + `pytest-asyncio` + `httpx`（AsyncClient）
- Test DB：使用獨立的 SQLite in-memory DB（`conftest.py` 建立 override dependency）
- **每個新增的 service 或 API endpoint 必須有對應的測試**
- 測試放在 `backend/tests/`，命名 `test_<module>.py`

```bash
pytest                    # 執行所有測試
pytest tests/test_auth.py # 執行單一檔案
pytest -v                 # 詳細輸出
```

### Key test cases to always cover
- Auth：登入成功、錯誤密碼、過期 token、未授權存取
- Stocks：ticker 正規化、價格更新
- Watchlist：新增/移除/重複新增

---

## Environment Variables

參考 `backend/.env.example`：

```env
DATABASE_URL=postgresql+asyncpg://stockbook:password@localhost:5432/stockbook
SECRET_KEY=your-256-bit-secret-here
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
SEED_USERNAME=admin
SEED_EMAIL=admin@stockbook.local
SEED_PASSWORD=changeme
PRICE_UPDATE_INTERVAL_MINUTES=5
ENABLE_SCHEDULER=true
ENVIRONMENT=development
BACKEND_CORS_ORIGINS=http://localhost:5173,https://your-app.web.app
```

---

## Roadmap（Phase Summary）

| Phase | 範圍 |
|-------|------|
| **1** | Auth API + Stock 股價取得 + Watchlist 顯示（前後端 + 部署） |
| **1.5** | Transactions + Dividends CRUD API（後端） |
| **2** | FIFO P&L 計算 + 所有前端頁面（Dashboard, Positions, Transactions, Dividends） |

詳細計畫見 `~/.claude/plans/indexed-skipping-summit.md`
