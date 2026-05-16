# AI Virtual Finance — Architecture Guide

> **目标读者**：新加入项目的开发者  
> **读完本文你应该能回答**：代码怎么跑起来的？一个 AI 决策从输入到执行穿过哪些模块？我的第一个 PR 改哪里？

---

## 1. 端到端数据流：一个 AI 决策的完整生命周期

下面是一个 AI Agent 做出 "买入 AAPL" 决策后，系统内部发生的事情：

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     一次 AI 决策的完整生命周期                              │
└─────────────────────────────────────────────────────────────────────────┘

  市场数据到达 (tick)
        │
        ▼
┌───────────────────┐
│  1. data/provider  │  从 Yahoo Finance / Binance 拉取最新 OHLCV
│  获取市场数据       │  缓存到 data/cache/
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  2. engine/market  │  格式化数据为统一 MarketData Schema
│  市场状态更新       │  更新当前 tick 的快照
└────────┬──────────┘
         │
         ▼
┌────────────────────────────────────┐
│  3. agent/context/prompt_builder    │  拼接三层上下文:
│  构建 Prompt                        │  L1 System Prompt (固定)
│                                     │  L2 Working Context (最近 N 轮)
│                                     │  L3 Compressed History (摘要)
│                                     │  + 当前余额/持仓/市场数据
└────────┬───────────────────────────┘
         │
         ▼
┌───────────────────┐
│  4. agent/providers│  调用 LLM (OpenAI/Claude/Ollama...)
│  调用 AI           │  传入 prompt, 获取 JSON 输出
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  5. validator/     │  校验 AI 输出:
│  输入校验           │  - JSON Schema 是否合法?
│                     │  - 标的代码是否存在?
│                     │  - 交易时间是否合规?
│                     │  - 仓位是否超限?
│                     │  不通过 → 记录 violation, 跳过
└────────┬──────────┘
         │ (通过)
         ▼
┌───────────────────┐
│  6. engine/order   │  创建订单, 计算:
│  执行订单           │  - 实际成交价 (滑点)
│                     │  - 手续费 (佣金 + 印花税 + 过户费)
│                     │  - 汇率损耗 (CNY↔USD 银行买卖价差)
│                     │  - 分红预扣税 (美股 30%)
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  7. engine/portfolio│  更新持仓:
│  更新持仓           │  - 现金变化 (CNY + USD 双账户)
│                     │  - 标的数量/成本
│                     │  - 浮动盈亏
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  8. engine/settlement│  T+1 结算 (如果适用)
│  结算               │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  9. analytics/     │  更新 KPI:
│  性能追踪           │  - 净值曲线
│                     │  - Sharpe / MaxDD / WinRate
│                     │  - 排行榜排名
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│ 10. persistence/   │  写入:
│  持久化             │  - SQLite (账户/订单/持仓)
│                     │  - CSV (净值/交易记录)
│                     │  - JSON (Agent 记忆 L2+L3)
│                     │  - 检查点 (每 10s)
└────────────────────┘

  完成, 等待下一个 tick
```

---

## 2. 核心模块接口（Python Protocol）

> 以下是每个模块对外暴露的核心接口。新人实现模块时，**只需满足这些 Protocol**。

### 2.1 数据提供器 `data/providers/`

```python
class MarketDataProvider(Protocol):
    """市场数据提供器接口"""
    
    async def fetch_ohlcv(
        self, 
        symbol: str, 
        granularity: str,       # "1d" | "1h" | "5m"
        start_date: date,
        end_date: date
    ) -> list[Ohlcv]: ...
    
    async def validate_symbol(self, symbol: str) -> bool:
        """检查标的代码是否有效"""
    
    async def latest_price(self, symbol: str) -> float: ...
```

**实现者注意**：提供一个 YahooFinanceProvider、一个 BinanceProvider。每个文件独立，注册到 `config/providers.yaml` 即可使用。

### 2.2 校验器 `validator/`

```python
class ValidationRule(Protocol):
    """校验规则接口。一条规则只做一件事。"""
    
    async def validate(
        self, 
        decision: dict, 
        context: ValidationContext
    ) -> ValidationResult:
        """返回 (passed: bool, reason: str)"""

# 内置规则链 (Chain of Responsibility)
rules_chain = [
    JsonSchemaRule,          # 8.2 Schema 校验
    SymbolValidationRule,    # 标的代码查询数据源
    TradingTimeRule,         # 交易时间检查
    PositionLimitRule,       # 仓位上限
    SufficientFundsRule,     # 资金充足
]
```

**实现者注意**：新增一个规则 = 写一个 class 实现 `ValidationRule` + 注册到 `rules_chain`。每条规则独立测试。

### 2.3 手续费计算器 `engine/fee/`

```python
class FeeCalculator(Protocol):
    """手续费计算器——所有公式在此集中管理"""
    
    def calculate(
        self,
        order: Order,
        fee_config: FeeConfig,   # 从 config/fee_schedule.yaml 加载
        exchange_rate: ExchangeRateSnapshot
    ) -> FeeBreakdown:
        """
        返回:
        - commission: 佣金
        - stamp_duty: 印花税
        - transfer_fee: 过户费
        - slippage_cost: 滑点成本
        - spread_cost: 买卖价差
        - fx_cost: 汇率损耗
        - withholding_tax: 预扣税 (分红)
        - total_cost: 合计
        - total_cost_cny: 折算为 CNY 的总成本
        """
```

**实现者注意**：这是最容易出 bug 的模块（浮点精度、多币种换算）。必须用 `Decimal`，必须写 hypotheses 随机测试。

### 2.4 Agent 上下文管理器 `agent/context/`

```python
class ContextManager(Protocol):
    """三层上下文组装器"""
    
    async def build_prompt(self, agent: Agent, state: AgentState) -> list[dict]:
        """
        返回: 完整的 messages 列表，可直接发送给 LLM
        - messages[0]: system prompt (Layer 1)
        - messages[1..n-1]: 历史 (Layer 2 + Layer 3)
        - messages[n]: 当前状态
        """
    
    async def record_decision(
        self, 
        agent_id: str, 
        decision: dict, 
        feedback: dict
    ) -> None:
        """记录决策到 L2，触发 L3 压缩如果需要"""
    
    async def summarize_daily(self, agent_id: str) -> str:
        """LLM 生成日摘要 → 规则引擎校验 → 存入 summaries/daily/"""
```

**实现者注意**：这是系统的"大脑皮层"——管理 Token 预算、上下文窗口、摘要压缩。性能关键路径。pt (Layer 1)
        - messages[1..n-1]: 历史 (Layer 2 + Layer 3)
        - messages[n]: 当前状态
        """
    
    async def record_decision(
        self, 
        agent_id: str, 
        decision: dict, 
        feedback: dict
    ) -> None:
        """记录决策到 L2，触发 L3 压缩如果需要"""
    
    async def summarize_daily(self, agent_id: str) -> str:
        """LLM 生成日摘要 → 规则引擎校验 → 存入 summaries/daily/"""
```

**实现者注意**：这是系统的"大脑皮层"——管理 Token 预算、上下文窗口、摘要压缩。性能关键路径。

### 2.5 贷款管理器 `loan/`

```python
class LoanManager(Protocol):
    """贷款全生命周期管理"""
    
    async def apply_loan(self, agent_id: str, amount: Decimal) -> LoanResult:
        """AI 申请贷款 → 校验 → 发放"""
    
    async def repay_loan(self, agent_id: str, amount: Decimal) -> RepayResult:
        """AI 主动还款"""
    
    async def declare_bankruptcy(self, agent_id: str) -> BankruptcyResult:
        """AI 宣告破产 → 强制平仓 → 结算贷款"""
    
    async def daily_accrue(self) -> None:
        """所有 Agent 每日利息结算"""
```

**实现者注意**：利息计算用复利 `Decimal`，不要用 float。破产清算顺序：平仓 → 还贷 → 统计。

---

## 3. 目录导航：新人版

```
ai-virtual-finance/
│
├── ARCHITECTURE.md     ← 你在看这里
├── CONTRIBUTING.md     ← 协作流程
├── TASK.md             ← 开发任务分解
├── spec.md             ← 完整需求规格（最终依据）
│
├── config/             ← 所有外部配置（运行时加载，不改代码）
│   ├── fee_schedule.yaml
│   ├── providers.yaml
│   ├── context.yaml
│   ├── persistence.yaml
│   └── agents/
│
├── src/                ← 源代码
│   ├── main.py         ← 入口: python -m src (启动 TUI 或 headless)
│   │
│   ├── data/           ← ⭐ 新人友好模块: 独立、测试简单
│   │   ├── providers/  ←    实现 YahooFinanceProvider 等
│   │   └── calendar/   ←     交易日历
│   │
│   ├── engine/         ← 🔥 核心模块: 需要仔细写测试
│   │   ├── order/      ←     订单管理
│   │   ├── portfolio/  ←     持仓
│   │   ├── fee/        ←     手续费（最易出 bug）
│   │   ├── settlement/ ←     结算与汇率
│   │   └── market/     ←     市场状态
│   │
│   ├── validator/      ← ⭐ 新人友好: 每条规则独立
│   │   └── rules/      ←     加一条规则 = 加一个文件
│   │
│   ├── loan/           ← 中等难度: 利息计算需谨慎
│   │
│   ├── agent/          ← 🔥 核心: 与 LLM 交互
│   │   ├── providers/  ←     各种 LLM 适配器
│   │   ├── context/    ←     三层上下文管理
│   │   └── leaderboard/
│   │
│   ├── analytics/      ← ⭐ 新人友好: 纯计算，无副作用
│   │
│   ├── persistence/    ← 一次写好，很少改
│   │
│   ├── tui/            ← 🎨 独立 UI 层
│   │   ├── screens/
│   │   └── widgets/
│   │
│   └── config/         ← 加载器
│
├── tests/              ← 项目规模的测试
│
├── data/               ← 缓存 (gitignored)
└── results/            ← 导出 (gitignored)
```

---

## 4. 你的第一个 PR

### 适合新人的任务（标注 ⭐ 的模块）

**PR 1: 添加一个新的校验规则**  
文件：`src/validator/rules/max_daily_trade_rule.py`  
耗时：1-2 小时  
测试：校验器单元测试已有，只需为新增规则加几条 case

**PR 2: 添加一个数据源**  
文件：`src/data/providers/alphavantage_provider.py`  
耗时：2-3 小时  
测试：mock 返回数据，验证 Provider 接口契约

**PR 3: 在 TUI 上加一个新图表**  
文件：`src/tui/widgets/allocation_chart.py`  
耗时：3-4 小时  
前置依赖：analytics 模块提供数据

### 着手方式

```bash
# 1. 看 TASK.md 找一个标记为 "good first issue" 的任务
# 2. 读 spec.md 中对应章节了解需求
# 3. 读 ARCHITECTURE.md 中对应模块的接口定义
# 4. 找 tests/ 下对应模块的测试文件看测试风格
# 5. 实现 → 写测试 → 跑 pytest → 提 PR
```

---

## 5. 开发工作流：调试与代码检查

### 5.1 推荐的开发循环

> 金融计算最怕"攒了一周代码才发现中间算错了"。**改 3 行就验证 3 行。**

```
┌──────────────────────────────────────────────────────────────────┐
│                    5 分钟开发循环                                   │
├──────────────────────────────────────────────────────────────────┤
│  ① 改 3-5 行代码                                                  │
│  ② 保存 → mypy 类型检查 + ruff lint（编辑器通常自动触发）             │
│  ③ 有错误？→ 回到 ①                                              │
│  ④ 无错误 → pytest tests/对应模块 -x（失败即停）                    │
│  ⑤ 有失败？→ 回到 ①                                              │
│  ⑥ 全通过 → git commit（小步提交，每通过一个子任务就提交一次）        │
└──────────────────────────────────────────────────────────────────┘
```

**关键指标**：一轮循环 ≤ 5 分钟。超过说明改动太大，拆小。

### 5.2 各模块的调试入口

| 模块 | 快速验证命令 | 说明 |
|---|---|---|
| `data/providers/` | `poetry run python -c "from data.providers.yahoo import YahooFinanceProvider; print(asyncio.run(YahooFinanceProvider().fetch_ohlcv('AAPL', '1d', '2024-01-01', '2024-01-07')))"` | 直接调用 Provider，看返回数据是否合法 |
| `engine/fee/` | `poetry run pytest tests/test_engine/test_fee.py -x -v --tb=short` | 手续费计算最容易出浮点错误，优先跑 hypothesis 测试 |
| `engine/settlement/` | `poetry run python -c "from decimal import Decimal; from engine.settlement.fx import FxConverter; fx = FxConverter(); print(fx.cny_to_usd(Decimal('10000')))"` | 验证汇率换算链 |
| `validator/` | `poetry run pytest tests/test_validator/ -x -v` | 每条规则独立测试，快速定位 |
| `loan/` | `poetry run python -c "from loan.interest import InterestCalculator; print(InterestCalculator().daily_compound(Decimal('50000'), Decimal('0.06'), 30))"` | 30 天复利验证 |
| `agent/context/` | `poetry run pytest tests/test_context/ -x -v` | 上下文组装逻辑 |
| `tui/` | `poetry run python -m src --dev` | `--dev` 启用 Textual DevTools |

### 5.3 audit_log：系统的黑匣子

所有模块共享同一个 audit_log 机制。调试时先看 log：

```bash
tail -f results/{session_id}/agent_audit.jsonl | jq 'select(.level == "WARN" or .level == "ERROR")'
```

审计日志记录每个关键操作：订单提交/成交/拒绝、费用扣除、汇率锁定、贷款发放/还款、Agent 状态变更。  
调试时先查 log，不猜。

### 5.4 代码检查清单（提交前置）

```
□ ruff check src/ --fix
□ mypy src/ --strict
□ pytest tests/ -x --tb=short
□ git diff --check       # 空白错误
□ grep -rn 'print(' src/ --include='*.py' | grep -v '__init__'  # 调试 print
□ grep -rn 'float' src/engine/ src/loan/   # 金额 float 误用
```

### 5.5 dry-run 模式

实现后，任何引擎变更都必须通过 dry-run 验证：

```bash
poetry run python -m src --dry-run --session demo --days 7
```

dry-run 模式：
- 不调用外部 LLM（使用本地规则引擎）
- 使用缓存数据（不拉取新数据）
- 输出完整交易流水 + 最终净值
- 与上次 dry-run 结果对比，确保无回归

---

## 6. 设计决策记录

| 决策 | 选择 | 原因 |
|---|---|---|
| 精度 | `Decimal` 而非 `float` | 银行级精度，浮点误差在金融场景不可接受 |
| 配置驱动 | YAML 文件，运行时加载 | 改策略不改代码，适合试验 |
| TUI 而非 CLI/GUI | Textual | 跨平台、零依赖、键盘高效、不需要浏览器 |
| SQLite WAL 模式 | 嵌入式数据库 | 零运维、ACID 事务、断电恢复 |
| 上下文三层架构 | L1 固定 + L2 滑动 + L3 摘要 | 解决 LLM 上下文窗口有限 + Lost in the Middle 问题 |
| 图表渲染 | Braille + 半图形块混合 | 折线用 Braille（高分辨率），柱状用方块（清晰），不依赖第三方图形库 |
| CNY 基准 | 初始资金人民币 | 模拟中国散户真实体验（银行购汇损耗） |

---

## 7. 错误处理流程

### 7.1 错误分类与处理策略

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        错误处理流程图                                      │
└─────────────────────────────────────────────────────────────────────────┘

  输入/操作
      │
      ▼
  ┌─────────────┐
  │  参数校验    │
  └──────┬──────┘
         │
    ┌────┴────┐
    │ 校验通过？│
    └────┬────┘
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    │         ▼
    │   ┌─────────────┐
    │   │ 记录 violation│
    │   │ 返回 REJECTED │
    │   └─────────────┘
    │
    ▼
  ┌─────────────┐
  │  执行操作    │
  └──────┬──────┘
         │
    ┌────┴────┐
    │ 执行成功？│
    └────┬────┘
         │
    ┌────┴────┐
    │         │
   YES       NO
    │         │
    │         ▼
    │   ┌─────────────┐
    │   │ 错误类型判断  │
    │   └──────┬──────┘
    │          │
    │    ┌─────┼─────┬─────────┐
    │    │     │     │         │
    │    ▼     ▼     ▼         ▼
    │  可恢复  可重试  致命错误   外部错误
    │    │     │     │         │
    │    ▼     ▼     ▼         ▼
    │  回滚   重试N次 停止引擎   降级处理
    │    │     │     │         │
    │    └─────┴─────┴─────────┘
    │          │
    │          ▼
    │    ┌─────────────┐
    │    │ 写入错误日志  │
    │    │ 通知上层/用户 │
    │    └─────────────┘
    │
    ▼
  ┌─────────────┐
  │ 写入审计日志 │
  │ 返回成功结果 │
  └─────────────┘
```

### 7.2 错误类型与处理

| 错误类型 | 示例 | 处理策略 |
|---|---|---|
| **可恢复错误** | 余额不足、仓位超限 | 拒绝操作，记录 violation，继续运行 |
| **可重试错误** | 网络超时、API 限流 | 指数退避重试，最多 3 次 |
| **致命错误** | 数据库损坏、内存溢出 | 停止引擎，保存检查点，报警 |
| **外部错误** | 数据源不可用、LLM API 失败 | 降级处理（使用缓存/HOLD），标记 `stale` |

### 7.3 各模块错误处理

#### 数据层错误

```python
async def fetch_ohlcv(self, symbol: str, ...) -> list[Ohlcv]:
    for attempt in range(MAX_RETRIES):
        try:
            data = await self._fetch_from_source(symbol)
            return self._parse_ohlcv(data)
        except NetworkError as e:
            if attempt < MAX_RETRIES - 1:
                await asyncio.sleep(2 ** attempt)  # 指数退避
                continue
            # 最后一次重试失败，使用缓存或标记缺失
            cached = await self._get_cached_data(symbol)
            if cached:
                cached.data_quality = "stale"
                return cached
            raise DataUnavailableError(f"无法获取 {symbol} 数据")
```

#### 引擎层错误

```python
async def execute_order(self, order: Order) -> Fill:
    try:
        # 1. 校验
        validation = await self.validator.validate(order)
        if not validation.passed:
            await self.audit_log.record("ORDER_REJECTED", order, validation)
            raise ValidationError(validation.reason)
        
        # 2. 执行（事务包装）
        async with self.db.transaction():
            fill = await self._execute_in_transaction(order)
            await self.audit_log.record("ORDER_FILLED", order, fill)
            return fill
            
    except InsufficientFundsError:
        # 可恢复：拒绝订单，继续运行
        await self.audit_log.record("INSUFFICIENT_FUNDS", order)
        raise
    except DatabaseError as e:
        # 致命：停止引擎
        await self.checkpoint.save_emergency()
        await self.alert.send(f"数据库错误: {e}")
        raise FatalError("引擎停止")
```

#### Agent 层错误

```python
async def make_decision(self, state: AgentState) -> Decision:
    try:
        response = await self.llm_provider.chat(
            messages=self.context.build_prompt(state),
            timeout=30
        )
        decision = self._parse_response(response)
        return decision
        
    except LLMTimeoutError:
        # 降级：返回 HOLD
        await self.audit_log.record("LLM_TIMEOUT", agent_id=self.id)
        return Decision(action="HOLD", rationale="LLM 超时")
        
    except LLMRateLimitError:
        # 降级：使用本地规则引擎
        await self.audit_log.record("LLM_RATE_LIMIT", agent_id=self.id)
        return self.rules_engine.decide(state)
        
    except JSONParseError as e:
        # 降级：返回 HOLD，记录原始响应
        await self.audit_log.record("LLM_PARSE_ERROR", 
                                     agent_id=self.id, 
                                     raw_response=response)
        return Decision(action="HOLD", rationale=f"解析失败: {e}")
```

### 7.4 审计日志格式

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "level": "ERROR",
  "event": "ORDER_REJECTED",
  "agent_id": "momentum-v1",
  "session_id": "demo-2024-01",
  "details": {
    "order_id": "ord-001",
    "symbol": "AAPL",
    "reason": "insufficient_funds",
    "available": 50000,
    "required": 75000
  },
  "stack_trace": "..."
}
```

### 7.5 错误恢复检查清单

```
□ 所有错误都写入了 audit_log
□ 可恢复错误不会导致引擎停止
□ 致命错误触发了紧急检查点
□ 外部错误有降级方案
□ 重试逻辑有指数退避
□ 超时设置合理（避免无限等待）
□ 用户收到了明确的错误提示
```

---

## 8. 版本信息

| 项目 | 值 |
|---|---|
| 文档版本 | v0.2 |
| 最后更新 | 2024-01-15 |
| 对应 spec 版本 | v0.2 |
| 对应代码版本 | v0.1.0 |
