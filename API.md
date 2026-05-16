# AI Virtual Finance — REST API Documentation

> **版本**: v0.1.0
> **Base URL**: `http://127.0.0.1:8080/api`（仅本地监听）
> **目标读者**: 需要外部脚本集成或 TUI 内部调用的开发者

---

## 1. 概述

### 1.1 设计原则

- **仅本地监听**：API 服务只绑定 `127.0.0.1`，不暴露到外网
- **无认证**：本地使用，无需认证机制
- **RESTful 风格**：遵循 REST 设计规范
- **JSON 响应**：所有响应均为 JSON 格式

### 1.2 启动 API 服务

```bash
# 启动带 API 服务的模式
poetry run python -m src --api --port 8080

# 或在 headless 模式下
poetry run python -m src --headless --api --port 8080
```

### 1.3 通用响应格式

#### 成功响应

```json
{
  "success": true,
  "data": { ... },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### 错误响应

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid symbol: XXX",
    "details": { ... }
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 1.4 HTTP 状态码

| 状态码 | 含义 |
|---|---|
| 200 | 成功 |
| 201 | 创建成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 409 | 冲突（如重复创建） |
| 500 | 服务器内部错误 |

---

## 2. Session 管理

### 2.1 列出所有 Session

```
GET /api/sessions
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "sessions": [
      {
        "id": "demo-2024-01",
        "name": "Demo Session",
        "status": "running",
        "start_date": "2024-01-01",
        "end_date": "2024-01-31",
        "initial_capital_cny": 100000.00,
        "agent_count": 3,
        "asset_pool": ["AAPL", "BTC/USDT", "SPY"],
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T10:30:00Z"
      }
    ],
    "total": 1
  }
}
```

### 2.2 获取 Session 详情

```
GET /api/sessions/{session_id}
```

**路径参数**:

| 参数 | 类型 | 说明 |
|---|---|---|
| `session_id` | string | Session ID |

**响应示例**:

```json
{
  "success": true,
  "data": {
    "id": "demo-2024-01",
    "name": "Demo Session",
    "status": "running",
    "start_date": "2024-01-01",
    "end_date": "2024-01-31",
    "initial_capital_cny": 100000.00,
    "asset_pool": ["AAPL", "BTC/USDT", "SPY"],
    "config": {
      "decision_interval": "1d",
      "max_agents": 10,
      "enable_loan": true
    },
    "statistics": {
      "total_trades": 45,
      "total_nav_cny": 125000.00,
      "best_agent": "momentum-v1",
      "worst_agent": "value-v1"
    },
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 2.3 创建 Session

```
POST /api/sessions
```

**请求体**:

```json
{
  "name": "New Session",
  "start_date": "2024-02-01",
  "end_date": "2024-02-28",
  "initial_capital_cny": 100000.00,
  "asset_pool": ["AAPL", "TSLA", "BTC/USDT"],
  "config": {
    "decision_interval": "1d",
    "enable_loan": true,
    "max_loan_times": 3
  }
}
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "id": "new-session-2024-02",
    "name": "New Session",
    "status": "created",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### 2.4 启动 Session

```
POST /api/sessions/{session_id}/start
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "id": "demo-2024-01",
    "status": "running",
    "started_at": "2024-01-15T10:30:00Z"
  }
}
```

### 2.5 停止 Session

```
POST /api/sessions/{session_id}/stop
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "id": "demo-2024-01",
    "status": "stopped",
    "stopped_at": "2024-01-15T10:30:00Z"
  }
}
```

### 2.6 删除 Session

```
DELETE /api/sessions/{session_id}
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "id": "demo-2024-01",
    "deleted": true
  }
}
```

---

## 3. Agent 管理

### 3.1 列出 Session 内所有 Agent

```
GET /api/sessions/{session_id}/agents
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "agents": [
      {
        "id": "momentum-v1",
        "name": "动量突破策略",
        "mode": "competition",
        "status": "NORMAL",
        "nav_cny": 125000.00,
        "return_pct": 0.25,
        "sharpe": 1.85,
        "max_drawdown": 0.08,
        "win_rate": 0.65,
        "loan_balance_cny": 0,
        "created_at": "2024-01-01T00:00:00Z"
      }
    ],
    "total": 1
  }
}
```

### 3.2 获取 Agent 详情

```
GET /api/sessions/{session_id}/agents/{agent_id}
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "id": "momentum-v1",
    "name": "动量突破策略",
    "mode": "competition",
    "status": "NORMAL",
    "config": {
      "initial_capital_cny": 100000.00,
      "max_position_pct": 0.20,
      "max_total_position": 0.80,
      "enable_loan": true,
      "max_loan_times": 3,
      "llm": {
        "provider_id": "openai-gpt4",
        "temperature": 0.7,
        "max_tokens": 2000
      }
    },
    "state": {
      "nav_cny": 125000.00,
      "cash_cny": 50000.00,
      "cash_usd": 5000.00,
      "loan_balance_cny": 0,
      "positions": [
        {
          "symbol": "AAPL",
          "quantity": 100,
          "cost_basis_cny": 70000.00,
          "market_value_cny": 75000.00,
          "unrealized_pnl_cny": 5000.00
        }
      ]
    },
    "performance": {
      "return_pct": 0.25,
      "sharpe": 1.85,
      "max_drawdown": 0.08,
      "win_rate": 0.65,
      "profit_factor": 2.1,
      "total_trades": 45,
      "winning_trades": 29,
      "losing_trades": 16
    }
  }
}
```

### 3.3 添加 Agent 到 Session

```
POST /api/sessions/{session_id}/agents
```

**请求体**:

```json
{
  "id": "value-v1",
  "name": "价值投资策略",
  "mode": "competition",
  "config": {
    "max_position_pct": 0.15,
    "enable_loan": false,
    "llm": {
      "provider_id": "anthropic-claude",
      "temperature": 0.5
    }
  }
}
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "id": "value-v1",
    "name": "价值投资策略",
    "status": "created",
    "created_at": "2024-01-15T10:30:00Z"
  }
}
```

### 3.4 移除 Agent

```
DELETE /api/sessions/{session_id}/agents/{agent_id}
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "id": "value-v1",
    "deleted": true
  }
}
```

---

## 4. Agent 数据查询

### 4.1 获取 Agent 净值曲线

```
GET /api/sessions/{session_id}/agents/{agent_id}/equity
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `start_date` | string | Session 开始日期 | 起始日期 |
| `end_date` | string | Session 结束日期 | 结束日期 |

**响应示例**:

```json
{
  "success": true,
  "data": {
    "agent_id": "momentum-v1",
    "equity_curve": [
      {"date": "2024-01-01", "nav_cny": 100000.00},
      {"date": "2024-01-02", "nav_cny": 101500.00},
      {"date": "2024-01-03", "nav_cny": 99800.00}
    ]
  }
}
```

### 4.2 获取 Agent 交易记录

```
GET /api/sessions/{session_id}/agents/{agent_id}/trades
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `start_date` | string | - | 起始日期 |
| `end_date` | string | - | 结束日期 |
| `symbol` | string | - | 标的过滤 |
| `side` | string | - | 方向过滤（BUY/SELL） |
| `limit` | int | 100 | 返回条数限制 |
| `offset` | int | 0 | 偏移量 |

**响应示例**:

```json
{
  "success": true,
  "data": {
    "agent_id": "momentum-v1",
    "trades": [
      {
        "order_id": "ord-001",
        "timestamp": "2024-01-15T10:30:00Z",
        "symbol": "AAPL",
        "side": "BUY",
        "quantity": 100,
        "filled_price_usd": 178.50,
        "total_cost_cny": 129500.00,
        "commission_cny": 65.00,
        "slippage_cny": 130.00,
        "fx_cost_cny": 390.00
      }
    ],
    "total": 45,
    "limit": 100,
    "offset": 0
  }
}
```

### 4.3 获取 Agent 持仓

```
GET /api/sessions/{session_id}/agents/{agent_id}/positions
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "agent_id": "momentum-v1",
    "positions": [
      {
        "symbol": "AAPL",
        "quantity": 100,
        "cost_basis_usd": 175.00,
        "cost_basis_cny": 126875.00,
        "current_price_usd": 178.50,
        "market_value_cny": 129500.00,
        "unrealized_pnl_cny": 2625.00,
        "unrealized_pnl_pct": 0.0207,
        "weight_pct": 0.15
      }
    ],
    "cash_cny": 50000.00,
    "cash_usd": 5000.00,
    "total_nav_cny": 125000.00
  }
}
```

### 4.4 获取 Agent 贷款记录

```
GET /api/sessions/{session_id}/agents/{agent_id}/loans
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "agent_id": "momentum-v1",
    "loans": [
      {
        "loan_id": "loan-001",
        "timestamp": "2024-01-10T00:00:00Z",
        "action": "BORROW",
        "amount_cny": 30000.00,
        "interest_rate": 0.06,
        "accrued_interest_cny": 49.32,
        "status": "ACTIVE"
      },
      {
        "loan_id": "repay-001",
        "timestamp": "2024-01-20T00:00:00Z",
        "action": "REPAY",
        "amount_cny": 15000.00,
        "principal_cny": 14850.00,
        "interest_cny": 150.00
      }
    ],
    "outstanding_balance_cny": 15000.00,
    "total_borrowed_cny": 30000.00,
    "remaining_borrow_count": 2
  }
}
```

---

## 5. 决策与操作

### 5.1 手动触发 Agent 决策

```
POST /api/sessions/{session_id}/agents/{agent_id}/decision
```

**请求体**:

```json
{
  "force": false,
  "dry_run": false
}
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "agent_id": "momentum-v1",
    "decision": {
      "action": "BUY",
      "symbol": "AAPL",
      "target_pct": 0.15,
      "confidence": 0.82,
      "rationale": "MACD金叉 + RSI超卖"
    },
    "execution": {
      "order_id": "ord-002",
      "status": "FILLED",
      "filled_qty": 100,
      "filled_price_usd": 178.50,
      "total_cost_cny": 129500.00
    },
    "timestamp": "2024-01-15T10:30:00Z"
  }
}
```

### 5.2 手动提交决策（跳过 LLM）

```
POST /api/sessions/{session_id}/agents/{agent_id}/manual-decision
```

**请求体**:

```json
{
  "action": "BUY",
  "symbol": "AAPL",
  "target_pct": 0.10,
  "rationale": "手动测试买入"
}
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "agent_id": "momentum-v1",
    "decision": {
      "action": "BUY",
      "symbol": "AAPL",
      "target_pct": 0.10
    },
    "validation": {
      "passed": true,
      "rules_checked": 5
    },
    "execution": {
      "order_id": "ord-003",
      "status": "FILLED"
    }
  }
}
```

---

## 6. 排行榜

### 6.1 获取 Session 排行榜

```
GET /api/sessions/{session_id}/leaderboard
```

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `sort_by` | string | `return` | 排序字段（return/sharpe/max_dd/win_rate） |
| `order` | string | `desc` | 排序方向（asc/desc） |

**响应示例**:

```json
{
  "success": true,
  "data": {
    "session_id": "demo-2024-01",
    "leaderboard": [
      {
        "rank": 1,
        "agent_id": "momentum-v1",
        "name": "动量突破策略",
        "return_pct": 0.25,
        "sharpe": 1.85,
        "max_drawdown": 0.08,
        "win_rate": 0.65,
        "score": 85.5
      },
      {
        "rank": 2,
        "agent_id": "value-v1",
        "name": "价值投资策略",
        "return_pct": 0.15,
        "sharpe": 1.20,
        "max_drawdown": 0.05,
        "win_rate": 0.70,
        "score": 72.3
      }
    ],
    "sort_by": "return",
    "order": "desc",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

---

## 7. Benchmark 对照

### 7.1 获取 Benchmark 数据

```
GET /api/sessions/{session_id}/benchmark
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "session_id": "demo-2024-01",
    "benchmarks": [
      {
        "id": "buy-hold",
        "name": "Buy & Hold",
        "return_pct": 0.12,
        "sharpe": 0.95,
        "max_drawdown": 0.10,
        "equity_curve": [...]
      },
      {
        "id": "dca",
        "name": "DCA (每周定投)",
        "return_pct": 0.08,
        "sharpe": 0.75,
        "max_drawdown": 0.06,
        "equity_curve": [...]
      }
    ],
    "agents_summary": [
      {
        "agent_id": "momentum-v1",
        "return_pct": 0.25,
        "vs_buy_hold": 0.13
      }
    ]
  }
}
```

---

## 8. 市场数据

### 8.1 获取当前市场快照

```
GET /api/market/snapshot
```

**查询参数**:

| 参数 | 类型 | 说明 |
|---|---|---|
| `symbols` | string | 标的列表，逗号分隔 |

**响应示例**:

```json
{
  "success": true,
  "data": {
    "timestamp": "2024-01-15T16:00:00-05:00",
    "snapshot": {
      "AAPL": {
        "close": 178.50,
        "volume": 52341200,
        "high_52w": 199.62,
        "low_52w": 164.08
      },
      "BTC/USDT": {
        "close": 42000.00,
        "volume_24h": 28500000000
      }
    },
    "exchange_rate": {
      "usd_cny_bid": 7.15,
      "usd_cny_ask": 7.25,
      "timestamp": "2024-01-15T00:00:00Z"
    }
  }
}
```

### 8.2 获取历史数据

```
GET /api/market/history/{symbol}
```

**路径参数**:

| 参数 | 类型 | 说明 |
|---|---|---|
| `symbol` | string | 标的代码 |

**查询参数**:

| 参数 | 类型 | 默认值 | 说明 |
|---|---|---|---|
| `granularity` | string | `1d` | 粒度（1d/1h/5m） |
| `start_date` | string | - | 起始日期 |
| `end_date` | string | - | 结束日期 |

**响应示例**:

```json
{
  "success": true,
  "data": {
    "symbol": "AAPL",
    "granularity": "1d",
    "ohlcv": [
      {
        "timestamp": "2024-01-15T00:00:00Z",
        "open": 177.00,
        "high": 179.50,
        "low": 176.50,
        "close": 178.50,
        "volume": 52341200
      }
    ]
  }
}
```

---

## 9. 系统状态

### 9.1 健康检查

```
GET /api/health
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "version": "0.1.0",
    "uptime_seconds": 86400,
    "components": {
      "database": "ok",
      "cache": "ok",
      "market_data": "ok"
    }
  }
}
```

### 9.2 系统指标

```
GET /api/metrics
```

**响应示例**:

```json
{
  "success": true,
  "data": {
    "sessions": {
      "total": 5,
      "running": 2,
      "stopped": 3
    },
    "agents": {
      "total": 10,
      "active": 6
    },
    "database": {
      "size_mb": 125,
      "tables": {
        "orders": 1500,
        "fills": 1500,
        "positions": 50
      }
    },
    "api_calls": {
      "total": 5000,
      "total_cost_usd": 15.50,
      "avg_latency_ms": 250
    }
  }
}
```

---

## 10. 错误码参考

| 错误码 | HTTP 状态码 | 说明 |
|---|---|---|
| `VALIDATION_ERROR` | 400 | 请求参数验证失败 |
| `INVALID_SYMBOL` | 400 | 标的代码无效 |
| `INVALID_ACTION` | 400 | 操作类型无效 |
| `INSUFFICIENT_FUNDS` | 400 | 资金不足 |
| `POSITION_LIMIT` | 400 | 仓位超限 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `SESSION_NOT_FOUND` | 404 | Session 不存在 |
| `AGENT_NOT_FOUND` | 404 | Agent 不存在 |
| `CONFLICT` | 409 | 资源冲突 |
| `SESSION_RUNNING` | 409 | Session 正在运行 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |

---

## 11. 使用示例

### Python 示例

```python
import httpx
import asyncio

BASE_URL = "http://127.0.0.1:8080/api"

async def main():
    async with httpx.AsyncClient() as client:
        # 获取所有 Session
        resp = await client.get(f"{BASE_URL}/sessions")
        sessions = resp.json()["data"]["sessions"]
        print(f"Found {len(sessions)} sessions")
        
        # 创建新 Session
        resp = await client.post(f"{BASE_URL}/sessions", json={
            "name": "Test Session",
            "start_date": "2024-01-01",
            "end_date": "2024-01-31",
            "initial_capital_cny": 100000,
            "asset_pool": ["AAPL", "BTC/USDT"]
        })
        session_id = resp.json()["data"]["id"]
        print(f"Created session: {session_id}")
        
        # 触发决策
        resp = await client.post(
            f"{BASE_URL}/sessions/{session_id}/agents/momentum-v1/decision",
            json={"dry_run": True}
        )
        print(f"Decision: {resp.json()}")

asyncio.run(main())
```

### cURL 示例

```bash
# 获取 Session 列表
curl http://127.0.0.1:8080/api/sessions

# 创建 Session
curl -X POST http://127.0.0.1:8080/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","start_date":"2024-01-01","end_date":"2024-01-31","initial_capital_cny":100000,"asset_pool":["AAPL"]}'

# 获取排行榜
curl http://127.0.0.1:8080/api/sessions/demo-2024-01/leaderboard?sort_by=return

# 健康检查
curl http://127.0.0.1:8080/api/health
```
