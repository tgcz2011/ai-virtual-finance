# AI Virtual Finance — Task Board

> **使用方式**：每个 `[ ]` 是一个可独立完成的子任务。做完一个勾一个。  
> **并行规则**：同一阶段内不带箭头依赖的任务可以分给不同人同时做。  
> **任务编号**：`[Phase][模块]-序号`，方便在 PR/Commit 中引用。
> **开发顺序**：从第 0 步开始，先搭建环境、部署验证，再进入业务开发。

---

## 开发顺序说明

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          推荐开发顺序                                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  第 0 步：环境与部署 ← 你从这里开始                                        │
│      │                                                                   │
│      ├─ 0.1 创建仓库                                                     │
│      ├─ 0.2 项目骨架                                                     │
│      ├─ 0.3 配置骨架                                                     │
│      ├─ 0.4 测试骨架                                                     │
│      └─ 0.5 Docker 部署验证                                              │
│                                                                          │
│  第 1 步：数据层                                                         │
│      │                                                                   │
│      ├─ 1.1 数据源抽象                                                   │
│      ├─ 1.2 Yahoo Finance                                                │
│      ├─ 1.3 Binance                                                      │
│      ├─ 1.4 交易日历                                                     │
│      └─ 1.5 数据缓存                                                     │
│                                                                          │
│  第 2-10 步：核心业务开发                                                 │
│      │                                                                   │
│      └─ ...（详见下文）                                                   │
│                                                                          │
│  第 11 步：集成与发布                                                     │
│      │                                                                   │
│      ├─ 端到端测试                                                       │
│      ├─ 确定性验证                                                       │
│      └─ 打 tag 发布                                                      │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

**为什么从部署开始？**

1. **先验证环境**：确保开发环境正确配置，避免后期因环境问题返工
2. **建立信心**：能跑起来是第一步，即使只是空壳
3. **持续验证**：每个阶段都能通过部署验证，确保代码可运行
4. **生产思维**：从一开始就考虑部署，而不是最后才想

---

### 开发工作流（开始编码前必读）

#### 推荐的开发节奏

```
┌────────────────────────────────────────────────────────────┐
│  改 3-5 行 → 保存 → LSP 诊断 (mypy/ruff)                   │
│      → 有错？→ 立刻修，不往下写                              │
│      → 无错 → pytest -x 对应模块                             │
│      → 有失败？→ 立刻修                                     │
│      → 全过 → git commit（小步提交，每完成一个 [ ] 就提交一次） │
└────────────────────────────────────────────────────────────┘
```

**一轮循环 ≤ 5 分钟**。超过说明改动太大，拆小。

#### 每个子任务完成后验证

每个 `[ ]` 标记的子任务完成后，必须运行对应的验证命令确认通过，才能勾选：

| 任务类型 | 验证命令 |
|---|---|
| 新数据源 | `poetry run python -c "from data.providers.xxx import XxxProvider; print(asyncio.run(XxxProvider().fetch_ohlcv('TEST', '1d', '2024-01-01', '2024-01-03')))"` |
| 新计算逻辑 | `poetry run pytest tests/test_{module}/ -x --tb=short -k test_{function}` |
| 新校验规则 | `poetry run pytest tests/test_validator/ -x --tb=short` |
| 新 TUI 页面 | `poetry run python -m src`（肉眼确认页面渲染正确） |
| 配置文件变更 | `poetry run python -c "from config.loader import ConfigLoader; ConfigLoader().validate()"` |

#### 提交前检查

```
□ ruff check src/
□ mypy src/ --strict
□ pytest tests/ -x --tb=short
□ git diff --check
□ grep -rn 'print(' src/ --include='*.py' | grep -v __init__  # 确认无调试 print 残留
```

---

## 第 0 步：仓库与环境

> 这部分是所有开发者的起点。全部完成后项目才可以开始编码。

### 0.1 创建 GitHub 仓库

- [ ] `[SETUP][GIT]-001` 在本地创建项目根目录 `ai-virtual-finance/`
- [ ] `[SETUP][GIT]-002` 用 `gh repo create ai-virtual-finance --private --push --remote origin --source .` 创建远程仓库（private，当前目录 push）
- [ ] `[SETUP][GIT]-003` 或在 GitHub Web 界面创建空仓库，本地 `git remote add origin <url>` 后 `git push -u origin main`
- [ ] `[SETUP][GIT]-004` 在 GitHub 仓库 Settings 中启用 branch protection：要求 main 分支必须通过 PR 合并
- [ ] `[SETUP][GIT]-005` 在 GitHub 仓库 Settings 中禁用直接 push 到 main

### 0.2 项目骨架

- [ ] `[SETUP][ENV]-001` 创建 `pyproject.toml`（Python >= 3.11, Poetry 格式），写入项目名、版本 0.1.0
- [ ] `[SETUP][ENV]-002` 创建 `.venv/`（`poetry install` 自动完成），所有依赖隔离在虚拟环境中
- [ ] `[SETUP][ENV]-003` 添加核心依赖：`textual`, `yfinance`, `ccxt`, `httpx`, `pydantic`, `rich`
- [ ] `[SETUP][ENV]-004` 添加开发依赖：`pytest`, `pytest-cov`, `hypothesis`, `mypy`, `ruff`
- [ ] `[SETUP][ENV]-005` 创建 `src/main.py` 空入口文件，`poetry run python -m src` 可执行
- [ ] `[SETUP][ENV]-006` 创建 `src/__init__.py` 和所有子模块 `__init__.py` 占位
- [ ] `[SETUP][ENV]-007` 创建 `.gitignore`（含 `.venv/`, `__pycache__/`, `*.pyc`, `.env`, `data/`, `results/`, `.DS_Store`）
- [ ] `[SETUP][ENV]-008` 创建 `README.md`：一句话项目简介 + 3 条快速开始命令
- [ ] `[SETUP][ENV]-009` 创建 docker-compose.yml 占位（P3 再用）
- [ ] `[SETUP][ENV]-010` 运行 `git add -A && git commit -m "chore: init project skeleton" && git push` 提交初始版本

### 0.3 配置骨架

- [ ] `[SETUP][CONFIG]-001` 创建 `config/` 目录，加 `.gitkeep`
- [ ] `[SETUP][CONFIG]-002` 创建 `config/fee_schedule.yaml.example`：手续费配置模板（空结构 + 注释）
- [ ] `[SETUP][CONFIG]-003` 创建 `config/providers.yaml.example`：Provider 注册模板（空结构 + 注释）
- [ ] `[SETUP][CONFIG]-004` 创建 `config/context.yaml.example`：上下文管理参数模板
- [ ] `[SETUP][CONFIG]-005` 创建 `config/persistence.yaml.example`：持久化配置模板
- [ ] `[SETUP][CONFIG]-006` 创建 `config/secrets.yaml`（已 gitignore），写入 `# API Keys go here` 注释
- [ ] `[SETUP][CONFIG]-007` 创建 `src/config/loader.py`：YAML 加载器，支持 `config/` 目录自动发现
- [ ] `[SETUP][CONFIG]-008` 实现 `config/loader.py` 的 `.get(type, key)` 方法：返回指定配置节的类型安全对象
- [ ] `[SETUP][CONFIG]-009` 提交：`git commit -m "feat: add config loader and templates"`

### 0.4 测试骨架

- [ ] `[SETUP][TEST]-001` 创建 `tests/` 目录结构：`test_data/`, `test_engine/`, `test_validator/`, `test_loan/`, `test_agent/`, `test_context/`, `test_persistence/`, `test_integration/`
- [ ] `[SETUP][TEST]-002` 创建 `conftest.py`：公共 fixture（mock market data、mock agent config）
- [ ] `[SETUP][TEST]-003` 配置 `pytest.ini`：`--strict-markers`, `--randomly-seed=42`
- [ ] `[SETUP][TEST]-004` 配置 `.coveragerc`：忽略 `__init__.py`、`tests/`、`config/`
- [ ] `[SETUP][TEST]-005` 跑一次 `pytest` 确认测试框架可运行（0 tests collected 但无报错）

### 0.5 GitHub 仓库配置

> **目标**：配置 GitHub 仓库的 PR 流程、Issue 模板、分支保护规则。  
> **参考文档**：DEPLOYMENT.md 第 4 节

- [ ] `[SETUP][GITHUB]-001` 创建 `.github/workflows/test.yml`：测试工作流（多平台、多 Python 版本）
- [ ] `[SETUP][GITHUB]-002` 创建 `.github/workflows/release.yml`：发布工作流（PyInstaller 打包）
- [ ] `[SETUP][GITHUB]-003` 创建 `.github/PULL_REQUEST_TEMPLATE.md`：PR 模板
- [ ] `[SETUP][GITHUB]-004` 创建 `.github/ISSUE_TEMPLATE/bug_report.md`：Bug 报告模板
- [ ] `[SETUP][GITHUB]-005` 创建 `.github/ISSUE_TEMPLATE/feature_request.md`：功能请求模板
- [ ] `[SETUP][GITHUB]-006` 在 GitHub 仓库 Settings 中配置分支保护规则（main 分支需要 PR 合并）
- [ ] `[SETUP][GITHUB]-007` 提交：`git commit -m "feat: add GitHub workflows and templates"`

### 0.6 PyInstaller 打包配置

> **目标**：配置 PyInstaller 打包，确保可以生成独立可执行文件。  
> **参考文档**：DEPLOYMENT.md 第 3 节

- [ ] `[SETUP][PYINSTALLER]-001` 创建 `requirements.txt`：从 pyproject.toml 导出依赖
- [ ] `[SETUP][PYINSTALLER]-002` 创建 `requirements-dev.txt`：开发依赖（pytest, mypy, ruff）
- [ ] `[SETUP][PYINSTALLER]-003` 创建 `pyinstaller.spec`：打包配置文件
- [ ] `[SETUP][PYINSTALLER]-004` 本地测试打包：`pyinstaller --onefile --name finance src/main.py`
- [ ] `[SETUP][PYINSTALLER]-005` 验证打包结果：运行 `./dist/finance --help`
- [ ] `[SETUP][PYINSTALLER]-006` 提交：`git commit -m "feat: add PyInstaller configuration"`

### 0.7 部署文档验证

- [ ] `[SETUP][DOCS]-001` 阅读 `DEPLOYMENT.md`，确认本地开发环境部署步骤可执行
- [ ] `[SETUP][DOCS]-002` 阅读 `TROUBLESHOOTING.md`，了解常见问题排查方法
- [ ] `[SETUP][DOCS]-003` 阅读 `API.md`，了解 REST API 设计
- [ ] `[SETUP][DOCS]-004` 提交：`git commit -m "docs: add deployment and troubleshooting guides"`

---

## 第 1 步：数据层

> **调试方式**：每实现一个 Provider，用 `poetry run python -c "from data.providers.xxx import ..."` 直接调用验证。  
> **提交前检查**：`mypy src/data/ --strict` + `pytest tests/test_data/ -x --tb=short`

### 1.1 数据源抽象

- [ ] `[P1][DATA]-001` 定义 `MarketDataProvider` Protocol：`fetch_ohlcv`, `validate_symbol`, `latest_price`
- [ ] `[P1][DATA]-002` 定义 `Ohlcv` 数据类：`symbol, timestamp, open, high, low, close, volume, quote_currency`
- [ ] `[P1][DATA]-003` 定义 `MarketData` Schema 完整版：含 `split_factor, dividend, data_quality, source` 字段
- [ ] `[P1][DATA]-004` 提交：`git commit -m "feat: define MarketDataProvider protocol and schemas"`

### 1.2 Yahoo Finance 数据源

- [ ] `[P1][DATA]-005` 添加 `yfinance` 到依赖
- [ ] `[P1][DATA]-006` 创建 `src/data/providers/yahoo.py`，实现 `MarketDataProvider`
- [ ] `[P1][DATA]-007` 实现 `fetch_ohlcv()`：支持 `1d` / `1h` 粒度，返回 `list[Ohlcv]`
- [ ] `[P1][DATA]-008` 实现 `validate_symbol()`：调用 yfinance.Ticker 检查是否存在
- [ ] `[P1][DATA]-009` 实现 `latest_price()`：获取当前最新价
- [ ] `[P1][DATA]-010` 处理边界情况：网络超时（重试 3 次）、股票退市（标记 `data_quality=delisted`）、拆股（读取 `splits`）
- [ ] `[P1][DATA]-011` 写单元测试：mock yfinance 返回值，验证 Provider 接口契约
- [ ] `[P1][DATA]-012` 注册 Yahoo 到 `config/providers.yaml`
- [ ] `[P1][DATA]-013` 提交：`git commit -m "feat: add Yahoo Finance data provider"`

### 1.3 Binance 加密货币数据源

- [ ] `[P1][DATA]-014` 添加 `ccxt` 到依赖
- [ ] `[P1][DATA]-015` 创建 `src/data/providers/binance.py`，实现 `MarketDataProvider`
- [ ] `[P1][DATA]-016` 实现 `fetch_ohlcv()`：通过 CCXT 获取 USDT 交易对 K 线
- [ ] `[P1][DATA]-017` 实现 `validate_symbol()`：查询 CCXT 市场列表
- [ ] `[P1][DATA]-018` 处理边界情况：交易所维护（标记 `data_quality=exchange_maintenance`）、交易对下线
- [ ] `[P1][DATA]-019` 写单元测试
- [ ] `[P1][DATA]-020` 注册 Binance 到 `config/providers.yaml`
- [ ] `[P1][DATA]-021` 提交：`git commit -m "feat: add Binance crypto data provider via CCXT"`

### 1.4 交易日历

- [ ] `[P1][DATA]-022` 创建 `src/data/calendar/market_calendar.py`
- [ ] `[P1][DATA]-023` 实现美股交易日历：排除周末 + 美股主要节假日（2024-2026 硬编码或使用 `pandas_market_calendars`）
- [ ] `[P1][DATA]-024` 实现加密货币日历：365 天全开放
- [ ] `[P1][DATA]-025` 实现 `is_trading_day(market, date)` / `next_trading_day(market, date)` / `previous_trading_day(market, date)`
- [ ] `[P1][DATA]-026` 提交：`git commit -m "feat: add market calendar (US stocks + crypto)"`

### 1.5 数据缓存

- [ ] `[P1][DATA]-027` 创建 `src/data/cache/market_cache.py`
- [ ] `[P1][DATA]-028` 实现 SQLite 缓存：`ohlcv_cache` 表，key=`symbol|granularity|date`
- [ ] `[P1][DATA]-029` 实现 TTL 策略：日线缓存 24h，1h 线缓存 2h
- [ ] `[P1][DATA]-030` 实现 `cache_first` 模式：有缓存先返回，后台异步刷新
- [ ] `[P1][DATA]-031` 提交：`git commit -m "feat: add market data cache with TTL"`

---

## 第 2 步：交易引擎核心

> **调试方式**：`pytest tests/test_engine/ -x --tb=short` 快速测订单生命周期。手续费用 `pytest --hypothesis-show-statistics` 跑随机测试。  
> **金额检查**：每次提交前 `grep -rn 'float' src/engine/ --include="*.py"` 确认没有 float 残留。  
> **提交前检查**：`mypy src/engine/ --strict` + `ruff check src/engine/`

### 2.1 订单系统

- [ ] `[P1][ENGINE]-001` 定义 `Order` 数据类：`order_id, agent_id, session_id, symbol, side, type, requested_qty, requested_price, status, timestamp`
- [ ] `[P1][ENGINE]-002` 定义订单状态枚举：`SUBMITTED → VALIDATING → PENDING → PARTIAL_FILL → FILLED → SETTLED → REJECTED`
- [ ] `[P1][ENGINE]-003` 定义 `Fill` 数据类：`order_id, filled_qty, filled_price, commission, slippage_cost, spread_cost, total_cost, commission_currency`
- [ ] `[P1][ENGINE]-004` 实现 `OrderManager`：`submit_order()`, `get_order()`, `cancel_order()`
- [ ] `[P1][ENGINE]-005` 实现市价单执行逻辑：以当前 mid_price 成交 ± 滑点
- [ ] `[P1][ENGINE]-006` 实现 `generate_order_id()`：UUID v4 字符串
- [ ] `[P1][ENGINE]-007` 实现幂等性检查：相同 `order_id` 的重复提交自动跳过
- [ ] `[P1][ENGINE]-008` 写单元测试：订单状态转换、重复提交、市价单滑点
- [ ] `[P1][ENGINE]-009` 提交：`git commit -m "feat: add order lifecycle management"`

### 2.2 持仓管理

- [ ] `[P1][ENGINE]-010` 定义 `Position` 数据类：`symbol, quantity, cost_basis, market_value, unrealized_pnl, currency, cost_basis_currency`
- [ ] `[P1][ENGINE]-011` 定义 `Portfolio` 数据类：`positions: dict[symbol, Position], cash_cny, cash_usd, loan_balance, total_nav`
- [ ] `[P1][ENGINE]-012` 实现 `PortfolioManager`：`add_position()`, `reduce_position()`, `update_market_value()`, `get_nav()`
- [ ] `[P1][ENGINE]-013` 实现持仓成本加权平均计算（买入增加成本，卖出按加权平均扣减）
- [ ] `[P1][ENGINE]-014` 实现浮动盈亏计算：`(current_price - avg_cost) × quantity`
- [ ] `[P1][ENGINE]-015` 写单元测试：多笔买入/卖出后的加权成本、浮动盈亏
- [ ] `[P1][ENGINE]-016` 提交：`git commit -m "feat: add portfolio and position management"`

### 2.3 手续费模型

- [ ] `[P1][ENGINE]-017` 定义 `FeeBreakdown` 数据类：`commission, stamp_duty, transfer_fee, slippage_cost, spread_cost, fx_cost, withholding_tax, total_cost, total_cost_cny`
- [ ] `[P1][ENGINE]-018` 定义 `FeeConfig` 数据类：从 `config/fee_schedule.yaml` 加载
- [ ] `[P1][ENGINE]-019` 实现美股手续费计算：per_share 佣金 + 滑点 + 价差 + 最低费用
- [ ] `[P1][ENGINE]-020` 实现加密货币手续费计算：百分比佣金 + 滑点 + 价差 + 最低费用
- [ ] `[P1][ENGINE]-021` 实现最低费用保证（美股 $0.99/笔，加密货币 $0.1/笔）
- [ ] `[P1][ENGINE]-022` 所有金额使用 `Decimal`，内建精度控制：加密货币 8 位，股票 2 位
- [ ] `[P1][ENGINE]-023` 写 hypothesis 随机测试：生成随机订单 + 随机市价，验证手续费不会导致负资产
- [ ] `[P1][ENGINE]-024` 提交：`git commit -m "feat: add fee calculation model"`

### 2.4 汇率损耗

- [ ] `[P1][ENGINE]-025` 定义 `ExchangeRateSnapshot` 数据类：`usd_cny_bid, usd_cny_ask, timestamp`
- [ ] `[P1][ENGINE]-026` 实现汇率获取：从 exchangerate-api 拉取每日 USD/CNY 中间价
- [ ] `[P1][ENGINE]-027` 实现银行买卖价差模拟：中间价 ± `spread` 配置值
- [ ] `[P1][ENGINE]-028` 实现跨币种换算：CNY→USD（卖出价）, USD→CNY（买入价），双向收损耗
- [ ] `[P1][ENGINE]-029` 实现汇率快照缓存：同一 tick 内所有 Agent 共享同一汇率
- [ ] `[P1][ENGINE]-030` 写单元测试：CNY→USD→CNY 循环换算验证损耗累积
- [ ] `[P1][ENGINE]-031` 提交：`git commit -m "feat: add FX rate with bid/ask spread simulation"`

### 2.5 美股分红预扣税

- [ ] `[P1][ENGINE]-032` 在 `FeeConfig` 中添加 `dividend_withholding_tax` 配置节
- [ ] `[P1][ENGINE]-033` 在 `fee_schedule.yaml` 中添加默认税率 30%
- [ ] `[P1][ENGINE]-034` 实现分红处理：除权日识别 → 计算税后分红 → USD 入账 → 结汇 CNY
- [ ] `[P1][ENGINE]-035` 写单元测试：分红金额 × 30% 预扣 = 税后入账
- [ ] `[P1][ENGINE]-036` 提交：`git commit -m "feat: add US stock dividend withholding tax (30%)"`

### 2.6 T+1 结算

- [ ] `[P1][ENGINE]-037` 定义 `SettlementQueue`：记录每笔卖出交易的 T+1 解锁日
- [ ] `[P1][ENGINE]-038` 实现 `daily_settle()`：扫描 SettlementQueue，到期资金转为可用
- [ ] `[P1][ENGINE]-039` 实现结算对账：`∑现金 + ∑持仓市值 + ∑贷款余额 = NAV`
- [ ] `[P1][ENGINE]-040` 写单元测试：T+0 卖出→资金不可用→T+1 解锁→可用
- [ ] `[P1][ENGINE]-041` 提交：`git commit -m "feat: add T+1 settlement"`

### 2.7 市场状态管理

- [ ] `[P1][ENGINE]-042` 定义 `MarketState` 数据类：`is_open, current_tick, trading_day, market_data_snapshot`
- [ ] `[P1][ENGINE]-043` 实现 `MarketStateManager`：`is_market_open(market)`, `current_snapshot()`, `advance_tick()`
- [ ] `[P1][ENGINE]-044` 交易日历集成：查询 `data/calendar/` 判断开闭市
- [ ] `[P1][ENGINE]-045` 实现停牌检测：连续无交易数据超过 3 个交易日标记停牌
- [ ] `[P1][ENGINE]-046` 提交：`git commit -m "feat: add market state management"`

---

## 第 3 步：校验层

> **调试方式**：每条校验规则独立可测。`pytest tests/test_validator/test_{rule_name}.py -x --tb=short`。  
> **关键检查**：用非法 JSON / 不存在标的 / 超限仓位 分别测试每条规则是否正确拒绝。  
> **提交前检查**：`mypy src/validator/ --strict`

### 3.1 校验框架

- [ ] `[P1][VALIDATOR]-001` 定义 `ValidationResult` 数据类：`passed: bool, rule_name: str, reason: str`
- [ ] `[P1][VALIDATOR]-002` 定义 `ValidationRule` Protocol：`validate(decision, context) → ValidationResult`
- [ ] `[P1][VALIDATOR]-003` 实现 `ValidatorChain`：按顺序执行规则链，遇 `REJECTED` 短路
- [ ] `[P1][VALIDATOR]-004` 定义 `ValidationContext`：含 `agent_id, portfolio, market_state, timestamp`
- [ ] `[P1][VALIDATOR]-005` 提交：`git commit -m "feat: add validator chain framework"`

### 3.2 JSON Schema 校验

- [ ] `[P1][VALIDATOR]-006` 定义 `JsonSchemaRule`：用 `pydantic` 校验 AI 输出是否符合 §8.2 Schema
- [ ] `[P1][VALIDATOR]-007` 实现校验：action 枚举、symbol 非空、confidence [0,1]、target_pct [0,1]
- [ ] `[P1][VALIDATOR]-008` 非法 JSON 时返回 `REJECTED` + 具体错误位置
- [ ] `[P1][VALIDATOR]-009` 写单元测试：合法 JSON 通过、缺字段拒绝、类型错误拒绝
- [ ] `[P1][VALIDATOR]-010` 提交：`git commit -m "feat: add JSON schema validation rule"`

### 3.3 标的校验

- [ ] `[P1][VALIDATOR]-011` 实现 `SymbolValidationRule`：检查标的在资产池白名单内
- [ ] `[P1][VALIDATOR]-012` 查询数据源 `validate_symbol()` 确认代码真实存在
- [ ] `[P1][VALIDATOR]-013` 拒绝不可交易标的（如指数代码 SPX 而非 SPY）
- [ ] `[P1][VALIDATOR]-014` 写单元测试：白名单内通过、不存在拒绝、停牌拒绝
- [ ] `[P1][VALIDATOR]-015` 提交：`git commit -m "feat: add symbol validation rule"`

### 3.4 交易时间校验

- [ ] `[P1][VALIDATOR]-016` 实现 `TradingTimeRule`：根据标的所属市场查询交易日历
- [ ] `[P1][VALIDATOR]-017` 非交易时间拒绝，记录 `reason=outside_trading_hours`
- [ ] `[P1][VALIDATOR]-018` 写单元测试：美股盘前拒绝、加密货币 24h 通过
- [ ] `[P1][VALIDATOR]-019` 提交：`git commit -m "feat: add trading time validation rule"`

### 3.5 风控校验

- [ ] `[P1][VALIDATOR]-020` 实现 `PositionLimitRule`：单标的 ≤ `max_position_pct`，总仓位 ≤ `max_total_position`
- [ ] `[P1][VALIDATOR]-021` 实现 `SufficientFundsRule`：买入总额 ≤ 可用资金 + 贷款额度
- [ ] `[P1][VALIDATOR]-022` 实现 `DrawdownLimitRule`：当前回撤 > `max_drawdown_limit` 时拒绝 + 切换 PAUSED
- [ ] `[P1][VALIDATOR]-023` 实现违规计数器：每次 violation 递增，触发阈值后 Agent 暂停
- [ ] `[P1][VALIDATOR]-024` 写单元测试：超限买入拒绝、回撤超限暂停
- [ ] `[P1][VALIDATOR]-025` 提交：`git commit -m "feat: add risk control validation rules"`

---

## 第 4 步：贷款模块

> **调试方式**：利息计算用 REPL 反复验证：`poetry run python -c "from decimal import Decimal; from loan.interest import InterestCalculator; print(InterestCalculator().daily_compound(Decimal('50000'), Decimal('0.06'), 30))"`  
> **边界情况**：测试贷款 → 亏光 → 再贷 → 再亏光的循环不会死锁。  
> **提交前检查**：`pytest tests/test_loan/ -x --tb=short` + `grep -rn float src/loan/`

- [ ] `[P1][LOAN]-001` 定义 `LoanAccount` 数据类：`agent_id, principal, interest_rate, accrued_interest, borrow_count, status`
- [ ] `[P1][LOAN]-002` 实现 `LoanManager.apply_loan()`：校验次数上限 → 发放 → 记录流水
- [ ] `[P1][LOAN]-003` 实现 `LoanManager.repay_loan()`：先息后本 → 更新余额 → 记录流水
- [ ] `[P1][LOAN]-004` 实现 `LoanManager.daily_accrue()`：所有未还贷款每日复利计息
- [ ] `[P1][LOAN]-005` 实现 `LoanManager.declare_bankruptcy()`：强制平仓 → 还贷 → 统计 NAV → LIQUIDATED
- [ ] `[P1][LOAN]-006` 实现自适应利率：首次贷款 6%，逾期 +3%，3 次以上 +2%，破产恢复 +5%
- [ ] `[P1][LOAN]-007` 写单元测试：贷款发放、利息日结、部分还款、破产清算
- [ ] `[P1][LOAN]-008` 提交：`git commit -m "feat: add loan management with adaptive interest"`

---

## 第 5 步：上下文管理系统

> **调试方式**：`pytest tests/test_context/ -x --tb=short -v` 验证各层上下文组装。  
> **Token 预算验证**：实现后检查 L2 滑动窗口的 token 数是否稳定在 4000 以内。  
> **提交前检查**：`mypy src/agent/context/ --strict`

### 5.1 L1 System Prompt

- [ ] `[P1][CONTEXT]-001` 创建 `src/agent/context/manager.py`
- [ ] `[P1][CONTEXT]-002` 定义 System Prompt 模板：角色定义 + 交易规则 + 格式约束 + 行为准则
- [ ] `[P1][CONTEXT]-003` 实现模板变量替换：`{style}`, `{initial_capital}`, `{session_name}`, `{day}`, `{asset_list}`, `{interval}`, `{max_loans}`
- [ ] `[P1][CONTEXT]-004` System Prompt 固定在 2000 tokens 以内，**永不截断**
- [ ] `[P1][CONTEXT]-005` 提交：`git commit -m "feat: add Layer 1 system prompt template"`

### 5.2 L2 滑动窗口

- [ ] `[P1][CONTEXT]-006` 定义 `WorkingContext` 数据结构：`list[dict]`，每轮一条 `{round, decision, feedback, timestamp}`
- [ ] `[P1][CONTEXT]-007` 实现滑动窗口追加：最新决策追加到末尾
- [ ] `[P1][CONTEXT]-008` 实现 Token 预算控制：当 L2 总 tokens > 阈值时，弹出最早条目
- [ ] `[P1][CONTEXT]-009` L2 格式化为可读文本：`[Round T-3] 决策: ... 反馈: ...`
- [ ] `[P1][CONTEXT]-010` 提交：`git commit -m "feat: add Layer 2 sliding window"`

### 5.3 L3 压缩摘要

- [ ] `[P1][CONTEXT]-011` 实现 `DailySummarizer`：收集当日决策 → 调用 LLM 生成日摘要
- [ ] `[P1][CONTEXT]-012` 实现 `WeeklySummarizer`：聚合 7 条日摘要 → 调用 LLM 生成周摘要
- [ ] `[P1][CONTEXT]-013` 实现 `MonthlySummarizer`：聚合 4-5 条周摘要 → 调用 LLM 生成月摘要
- [ ] `[P1][CONTEXT]-014` 实现规则引擎校验：摘要中的数据与真实交易记录比对一致性
- [ ] `[P1][CONTEXT]-015` 校验不通过时回退为结构化模板摘要（不含 LLM 幻觉风险）
- [ ] `[P1][CONTEXT]-016` 提交：`git commit -m "feat: add Layer 3 compressed summaries with LLM + validation"`

### 5.4 Prompt 动态调整

- [ ] `[P1][CONTEXT]-017` 实现状态检测：连续亏损天数、回撤幅度、贷款余额、NAV/initial 比率
- [ ] `[P1][CONTEXT]-018` 实现 Prompt 追加表：亏损 3 天追加警告、回撤 > 10% 追加减仓建议、贷款 > 0 追加利息提示
- [ ] `[P1][CONTEXT]-019` NAV < 20% initial 时追加破产选项说明
- [ ] `[P1][CONTEXT]-020` 已申报破产时替换为破产说明 prompt
- [ ] `[P1][CONTEXT]-021` 节假日/市场休市前追加估值说明
- [ ] `[P1][CONTEXT]-022` 提交：`git commit -m "feat: add dynamic prompt adjustment"`

### 5.5 上下文组装

- [ ] `[P1][CONTEXT]-023` 实现 `build_prompt()`：L1 + L3 + L2 + 当前状态 → 完整 messages 列表
- [ ] `[P1][CONTEXT]-024` 实现 `record_decision()`：决策追加到 L2 → L2 超阈触发 L3 压缩
- [ ] `[P1][CONTEXT]-025` 提交：`git commit -m "feat: add context assembly pipeline"`

### 5.6 记忆持久化

- [ ] `[P1][CONTEXT]-026` 实现 `MemoryStore.save()`：L2/L3 写入 `results/{session_id}/memory/agent_{id}/`
- [ ] `[P1][CONTEXT]-027` 实现 `MemoryStore.load()`：Session 恢复时重建三层上下文
- [ ] `[P1][CONTEXT]-028` 提交：`git commit -m "feat: add memory persistence for context layers"`

---

## 第 6 步：Agent 层

> **调试方式**：本地规则引擎（AGENT-015~019）不需要 LLM API，适合快速验证 Agent 决策循环。先用规则引擎调通再切 LLM。  
> **LLM Provider 测试**：mock HTTP 返回值，不要每次测试都真的调用 API。  
> **提交前检查**：`pytest tests/test_agent/ -x --tb=short` + `mypy src/agent/ --strict`

### 6.1 Agent 基类

- [ ] `[P1][AGENT]-001` 定义 `AgentConfig` 数据类：`id, name, initial_capital, max_position_pct, enable_loan, llm_config, decision_interval`
- [ ] `[P1][AGENT]-002` 定义 `AgentState` 数据类：`balance_cny, positions, open_orders, loan_info, nav, watermark, status`
- [ ] `[P1][AGENT]-003` 定义 Agent 状态枚举：`NORMAL / BORROWED / PAUSED / LIQUIDATED`
- [ ] `[P1][AGENT]-004` 实现 `BaseAgent`：`load_config()`, `get_state()`, `receive_decision()`, `update_state()`
- [ ] `[P1][AGENT]-005` 实现竞赛/独立模式标记：`agent.mode = competition | standalone` 影响排行榜参与
- [ ] `[P1][AGENT]-006` 提交：`git commit -m "feat: add agent base class with state machine"`

### 6.2 LLM Provider

- [ ] `[P1][AGENT]-007` 定义 `LLMProvider` Protocol：`chat(messages, temperature, max_tokens) → str`
- [ ] `[P1][AGENT]-008` 实现 `OpenAIProvider`：兼容 OpenAI API 格式
- [ ] `[P1][AGENT]-009` 实现 `AnthropicProvider`：兼容 Anthropic Messages API
- [ ] `[P1][AGENT]-010` 实现 `OllamaProvider`：本地模型调用
- [ ] `[P1][AGENT]-011` 实现 models.dev 自动配置：调用 models.dev API → 获取模型列表 → 填充 endpoint/context_length/pricing
- [ ] `[P1][AGENT]-012` 实现自定义模型手动配置表单数据结构：ID/名称/endpoint/model_name/context_length/API Key env/pricing
- [ ] `[P1][AGENT]-013` 实现错误处理：超时降级 HOLD、空返回降级 HOLD、JSON 解析失败重试一次
- [ ] `[P1][AGENT]-014` 提交：`git commit -m "feat: add LLM providers with models.dev auto-config"`

### 6.3 本地规则引擎

- [ ] `[P1][AGENT]-015` 创建 `src/agent/providers/rules_engine.py`
- [ ] `[P1][AGENT]-016` 实现简单移动均线策略：MA5 × MA20 金叉买入/死叉卖出
- [ ] `[P1][AGENT]-017` 实现 RSI 策略：RSI < 30 超卖买入，RSI > 70 超买卖出
- [ ] `[P1][AGENT]-018` 规则引擎输出格式与 LLM 一致（同 JSON Schema），确保校验层通用
- [ ] `[P1][AGENT]-019` 提交：`git commit -m "feat: add local rules engine strategy"`

### 6.4 排行榜

- [ ] `[P1][AGENT]-020` 定义 `LeaderboardEntry` 数据类：`agent_id, rank, total_return, sharpe, max_drawdown, win_rate, loan_count, score`
- [ ] `[P1][AGENT]-021` 实现排行榜计算：收益率 40% + Sharpe 25% + MaxDD 20% + 交易合理性 10% + 贷款率 5%
- [ ] `[P1][AGENT]-022` 独立模式 Agent 不参与排行榜排名
- [ ] `[P1][AGENT]-023` 支持按任意维度排序（收益率/Sharpe/MaxDD/WinRate）
- [ ] `[P1][AGENT]-024` 提交：`git commit -m "feat: add multi-dimensional leaderboard"`

### 6.5 API 用量统计

- [ ] `[P1][AGENT]-025` 定义 `APICallLog` 数据类：`provider, model, prompt_tokens, completion_tokens, total_tokens, cost, latency, agent_id, status, timestamp`
- [ ] `[P1][AGENT]-026` 实现 API 调用日志：每次 LLM 调用写一条 `APICallLog`
- [ ] `[P1][AGENT]-027` 实现费用估算：从 Provider pricing × token 用量计算
- [ ] `[P1][AGENT]-028` 输出 `usage_log.csv` / `cost_breakdown.csv` / `token_consumption.csv`
- [ ] `[P1][AGENT]-029` 提交：`git commit -m "feat: add API usage tracking and cost estimation"`

---

## 第 7 步：性能追踪

> **调试方式**：纯数学计算，不依赖外部服务。用固定序列测试每个 KPI 的数值是否正确。  
> **关键检查**：Sharpe Ratio 分母为 0（全部收益相同）的边界情况。  
> **提交前检查**：`pytest tests/test_analytics/ -x --tb=short`

### 7.1 KPI 计算

- [ ] `[P1][ANALYTICS]-001` 实现 `Total Return` 计算：`(final_nav - initial) / initial`
- [ ] `[P1][ANALYTICS]-002` 实现 `Annualized Return`：`(1 + TR)^(252/days) - 1`
- [ ] `[P1][ANALYTICS]-003` 实现 `Sharpe Ratio`：`mean(daily_return) / std(daily_return) × sqrt(252)`
- [ ] `[P1][ANALYTICS]-004` 实现 `Max Drawdown`：`max(peak - valley) / peak`
- [ ] `[P1][ANALYTICS]-005` 实现 `Win Rate`：`winning_trades / total_trades`
- [ ] `[P1][ANALYTICS]-006` 实现 `Profit Factor`：`gross_profit / gross_loss`
- [ ] `[P1][ANALYTICS]-007` 所有 KPI 输出 Decimal 精度 4 位
- [ ] `[P1][ANALYTICS]-008` 写单元测试：输入固定净值序列，验证 Sharpe/MaxDD 等计算正确
- [ ] `[P1][ANALYTICS]-009` 提交：`git commit -m "feat: add KPI calculation engine"`

### 7.2 时间序列导出

- [ ] `[P1][ANALYTICS]-010` 实现 `equity_curve_csv()`：每日 NAV 序列 → CSV
- [ ] `[P1][ANALYTICS]-011` 实现 `trade_log_csv()`：每笔交易明细 → CSV
- [ ] `[P1][ANALYTICS]-012` 实现 `daily_pnl_csv()`：每日 P&L → CSV
- [ ] `[P1][ANALYTICS]-013` 实现 `loan_log_csv()`：贷款还款流水 → CSV
- [ ] `[P1][ANALYTICS]-014` 实现 `summary_json()`：Session 整体统计 → JSON
- [ ] `[P1][ANALYTICS]-015` 提交：`git commit -m "feat: add time series export (CSV/JSON)"`

### 7.3 Benchmark 策略

- [ ] `[P1][ANALYTICS]-016` 实现 `BuyHoldBenchmark`：初始资金等权买入所有标的，持有至结束
- [ ] `[P1][ANALYTICS]-017` 实现 `DCABenchmark`：每 N 天定投固定金额
- [ ] `[P1][ANALYTICS]-018` Benchmark 输出格式与 Agent 一致，可同图对比
- [ ] `[P1][ANALYTICS]-019` 提交：`git commit -m "feat: add benchmark strategies (buy-hold, DCA)"`

---

## 第 8 步：持久化与容灾

> **调试方式**：`pytest tests/test_persistence/ -x --tb=short`。**必须手动测试断电恢复**：启动 → 运行 → `kill -9` → 重启 → 状态一致。  
> **关键检查**：WAL 模式是否启用（`sqlite3 test.db 'PRAGMA journal_mode;'` 返回 `wal`）。  
> **提交前检查**：`mypy src/persistence/ --strict`

- [ ] `[P1][PERSISTENCE]-001` 定义 SQLite Schema：`sessions`, `agents`, `orders`, `fills`, `positions`, `loans`, `market_cache` 表
- [ ] `[P1][PERSISTENCE]-002` 配置 `PRAGMA journal_mode=WAL` 启用 WAL 模式
- [ ] `[P1][PERSISTENCE]-003` 配置 `PRAGMA synchronous=FULL` 确保数据落盘
- [ ] `[P1][PERSISTENCE]-004` 每笔订单/每次结算封装为单个事务，失败自动回滚
- [ ] `[P1][PERSISTENCE]-005` 实现增量检查点（默认每 10 秒）：序列化 engine 变更到临时文件
- [ ] `[P1][PERSISTENCE]-006` 实现全量检查点（默认每 60 秒）：完整状态快照 + 校验
- [ ] `[P1][PERSISTENCE]-007` 实现 `checkpoint_interval` 和 `full_checkpoint_interval` 配置化（`config/persistence.yaml`）
- [ ] `[P1][PERSISTENCE]-008` 实现启动恢复：检测退出标记 → 加载检查点 → 回放未完成订单
- [ ] `[P1][PERSISTENCE]-009` 实现正常关闭流程：完成当前 tick → 写 CHECKPOINT_OK → 刷缓存
- [ ] `[P1][PERSISTENCE]-010` 实现启动时完整性校验：总账平衡、订单连续、时间戳单调
- [ ] `[P1][PERSISTENCE]-011` 实现 Session 备份：结束后压缩为 `.tar.gz`，保留最近 5 个
- [ ] `[P1][PERSISTENCE]-012` 写集成测试：启动 → 运行 → kill -9 → 重启 → 状态一致
- [ ] `[P1][PERSISTENCE]-013` 提交：`git commit -m "feat: add persistence and crash recovery"`

---

## 第 9 步：TUI 界面

> **调试方式**：`poetry run python -m src --dev` 启动 Textual DevTools，按 `Ctrl+D` 打开检查器（查看布局、样式、组件树）。  
> **每次新页面**：启动 TUI 肉眼确认渲染正确，检查快捷键是否注册。  
> **提交前检查**：TUI 不涉及金额计算，不需 mypy strict，但需 `ruff check src/tui/` 零 warning。

### 9.1 TUI 骨架

- [ ] `[P1][TUI]-001` 创建 `src/tui/app.py`：Textual App，页面路由
- [ ] `[P1][TUI]-002` 创建 `src/tui/screens/` 目录，每个页面一个文件
- [ ] `[P1][TUI]-003` 实现底部迷你提示栏：当前页面 4-6 个快捷键
- [ ] `[P1][TUI]-004` 实现命令面板：`Ctrl+P` 弹出，模糊搜索所有操作
- [ ] `[P1][TUI]-005` 实现完整菜单栏：`Alt+M` 展开/收起，鼠标可点击
- [ ] `[P1][TUI]-006` 实现暗色主题：金融终端风格配色（深色底 + 绿涨红跌）
- [ ] `[P1][TUI]-007` 实现亮色主题切换
- [ ] `[P1][TUI]-008` 实现窗口自适应：< 80 列隐藏图表，80-120 标准布局，> 120 丰富布局
- [ ] `[P1][TUI]-009` 提交：`git commit -m "feat: add TUI skeleton with routing and themes"`

### 9.2 Dashboard

- [ ] `[P1][TUI]-010` 实现总览面板：运行中 Session 列表、总资金、Agent 数
- [ ] `[P1][TUI]-011` 实现净值曲线 `EquityChart`：Braille 点阵折线图，多 Agent 叠加
- [ ] `[P1][TUI]-012` 实现持仓表格 `PositionTable`：按市值排序，浮动盈亏红/绿高亮
- [ ] `[P1][TUI]-013` 实现 KPI 卡片 `KPICards`：收益率/Sharpe/MaxDD
- [ ] `[P1][TUI]-014` 实现实时刷新：每秒轮询 engine 状态更新
- [ ] `[P1][TUI]-015` 提交：`git commit -m "feat: add TUI dashboard with equity chart"`

### 9.3 Session 管理

- [ ] `[P1][TUI]-016` 实现 Session 列表页：展示所有 Session 名称/状态/起止时间
- [ ] `[P1][TUI]-017` 实现 Session 创建向导：配置名称/资产池/时间范围/Agent
- [ ] `[P1][TUI]-018` 实现 Session 启动/停止/删除操作
- [ ] `[P1][TUI]-019` 提交：`git commit -m "feat: add session management screens"`

### 9.4 Agent 详情

- [ ] `[P1][TUI]-020` 实现 Agent 详情页：持仓明细、交易记录、实时 KPI
- [ ] `[P1][TUI]-021` 实现实时订单流 `OrderLog`：颜色区分买卖
- [ ] `[P1][TUI]-022` 实现盈亏柱状图 `DailyPnlBar`：半图形块渲染，绿涨红跌
- [ ] `[P1][TUI]-023` 实现资金信息卡：现金余额（CNY/USD）、贷款、NAV
- [ ] `[P1][TUI]-024` 提交：`git commit -m "feat: add agent detail screen"`

### 9.5 排行榜

- [ ] `[P1][TUI]-025` 实现排行榜页面：Agent 排名表格
- [ ] `[P1][TUI]-026` 实现多维度排序切换：Tab 在收益率/Sharpe/MaxDD 之间切换
- [ ] `[P1][TUI]-027` 实现点击跳转：选中 Agent 按 Enter 进入详情页
- [ ] `[P1][TUI]-028` 提交：`git commit -m "feat: add leaderboard screen"`

### 9.6 图表组件

- [ ] `[P1][TUI]-029` 实现 `DrawdownChart`：半图形块区域填充，红色标注最大回撤
- [ ] `[P1][TUI]-030` 实现 `WinLossPie`：Unicode 半饼图（░▒▓█），盈利/亏损/手续费占比
- [ ] `[P1][TUI]-031` 实现 `AssetAllocation`：半图形块堆叠，各标的权重变化
- [ ] `[P1][TUI]-032` 实现 `ReturnDistribution`：Braille + 半图形块混合直方图
- [ ] `[P1][TUI]-033` 实现 `ScatterPlot`：ASCII 字符散点图，风险-收益分布
- [ ] `[P1][TUI]-034` 每个图表支持 `Ctrl+E` 导出为 SVG
- [ ] `[P1][TUI]-035` 提交：`git commit -m "feat: add chart components"`

### 9.7 设置页面

- [ ] `[P1][TUI]-036` 实现 LLM Provider 配置：从 models.dev 自动获取模型列表
- [ ] `[P1][TUI]-037` 自定义模型表单：ID / endpoint / model_name / context_length / pricing 输入
- [ ] `[P1][TUI]-038` 实现 API Key 输入（密码框模式，不显示明文）
- [ ] `[P1][TUI]-039` 实现手续费配置界面：读取/写入 `fee_schedule.yaml`
- [ ] `[P1][TUI]-040` 实现数据源切换：Yahoo / Binance / AKShare 启用/禁用
- [ ] `[P1][TUI]-041` 提交：`git commit -m "feat: add settings screen with provider config"`

### 9.8 辅助功能

- [ ] `[P1][TUI]-042` 实现 `LogViewer`：分级别（INFO/WARN/ERROR）过滤，实时滚动
- [ ] `[P1][TUI]-043` 实现交易记录搜索页：按标的/日期/方向过滤
- [ ] `[P1][TUI]-044` 实现 Benchmark 对照页：Agent 净值 vs 基准净值
- [ ] `[P1][TUI]-045` 实现 `APICostChart` + `TokenUsageChart`：LLM 调用统计可视化
- [ ] `[P1][TUI]-046` 实现 `summary_json()` 的 TUI 展示：Session 全局统计面板
- [ ] `[P1][TUI]-047` 提交：`git commit -m "feat: add auxiliary screens (logs, trades, benchmark, API stats)"`

---

## 第 10 步：集成与确定性问题

> **调试方式**：全链路测试是最后的防线。先确保每个模块单独验证通过后再跑集成。  
> **确定性验证**：同一个 Session 跑 3 次，每次的输出文件 `md5sum` 必须完全相同。  
> **提交前检查**：全量 `pytest tests/ -x --tb=short` + `mypy src/ --strict` + `ruff check src/`

- [ ] `[P1][INTEGRATION]-001` 编写端到端集成测试：7 天历史数据 + 3 个标的 + 2 个 Agent
- [ ] `[P1][INTEGRATION]-002` 验证数据流：DATA → ENGINE → VALIDATOR → AGENT → ANALYTICS 全通
- [ ] `[P1][INTEGRATION]-003` 验证 3 次运行结果完全一致（固定随机种子）
- [ ] `[P1][INTEGRATION]-004` 验证断电恢复：启动 → 运行 → kill -9 → 重启 → 状态一致
- [ ] `[P1][INTEGRATION]-005` 提交：`git commit -m "test: add end-to-end integration and determinism tests"`
- [ ] `[P1][INTEGRATION]-006` 打 tag `v0.1.0`：`git tag v0.1.0 && git push --tags`

---

## Phase 2 任务概览

> P2 任务颗粒度与 P1 一致，每个可进一步拆分为 3-8 个子任务。

- [ ] `[P2][DATA]-001` AKShare A 股数据源实现（参考 P1 DATA-005~013）
- [ ] `[P2][ENGINE]-001` 限价单 / 止损单订单类型（参考 P1 ENGINE-004~008）
- [ ] `[P2][ENGINE]-002` 做空机制：融券/借币、强制平仓
- [ ] `[P2][ENGINE]-003` A 股市场规则：涨跌停、100 股起买
- [ ] `[P2][ENGINE]-004` 外汇汇率实时更新（定时拉取中国外汇交易中心牌价）
- [ ] `[P2][AGENT]-001` 多 Agent 并行执行引擎（共享市场快照，独立账户）
- [ ] `[P2][CONTEXT]-001` 摘要质量评分 + 压缩率自动调优
- [ ] `[P2][ANALYTICS]-001` Benchmark TUI 页面
- [ ] `[P2][ANALYTICS]-002` 扩展 KPI：Calmar Ratio、Sortino Ratio、VaR
- [ ] `[P2][VALIDATOR]-001` 前视偏差自动化检测
- [ ] `[P2][PERSISTENCE]-001` 回测加速（10x/100x）

---

## Phase 3 任务概览

- [ ] `[P3][ENGINE]-001` 分钟级回测，tick 级数据支持
- [ ] `[P3][AGENT]-001` 情绪/新闻数据接入（RSS / Fear & Greed）
- [ ] `[P3][AGENT]-002` LangChain / ReAct 框架集成
- [ ] `[P3][ANALYTICS]-001` 策略优化框架：参数扫描 + walk-forward
- [ ] `[P3][ANALYTICS]-002` Stress Test：极端行情模拟
- [ ] `[P3][TUI]-001` 实时模式：定时 tick + sleep/wake 机制
