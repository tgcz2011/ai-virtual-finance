# AI Virtual Finance — System Specification

> **版本**: v0.2  
> **状态**: Draft  
> **最后更新**: 2024-01-15  
> **目标读者**: 全栈工程师、算法工程师、数据工程师、TUI 开发者  
> **本文件是项目的单一事实来源，所有开发以本文档为准。**

---

## 目录

- [1. 产品愿景](#1-产品愿景)
- [2. 核心原则（不可妥协）](#2-核心原则不可妥协)
- [3. 模块架构（强模块化设计）](#3-模块架构强模块化设计)
- [4. 术语表](#4-术语表)
- [5. 数据层](#5-数据层)
- [6. 资产类别定义](#6-资产类别定义)
- [7. 交易引擎](#7-交易引擎)
- [8. 输入校验层（Validator）](#8-输入校验层validator)
- [9. Agent 层（AI 决策模块）](#9-agent-层ai-决策模块)
- [10. 贷款机制（AI 自主决策）](#10-贷款机制ai-自主决策)
- [11. 性能追踪模块](#11-性能追踪模块)
- [12. 回测 vs 实时模式](#12-回测-vs-实时模式)
- [13. 用户界面 — TUI](#13-用户界面--tui)
- [14. REST API](#14-rest-api)
- [15. 边界情况处理](#15-边界情况处理)
- [16. AI 接入方式](#16-ai-接入方式)
- [17. AI 上下文管理系统](#17-ai-上下文管理系统)
- [18. 持久化与容灾](#18-持久化与容灾)
- [19. 技术栈建议](#19-技术栈建议)
- [20. 项目里程碑](#20-项目里程碑)
- [21. 测试策略](#21-测试策略)
- [22. 项目目录结构](#22-项目目录结构)
- [23. 安全规范](#23-安全规范)
- [24. 性能约束](#24-性能约束)

---

## 1. 产品愿景

给 AI 一笔**虚拟的人民币资金**，在**真实的股票和加密货币市场**中独立操盘。AI 不知道它是虚拟的——它收到的市场数据、余额、持仓、成交反馈和限制都让它以为自己真的在交易。软件全程追踪每一笔交易、手续费、汇率损耗和借贷利息。

核心问题：**给定同样的初始资金和市场数据，你的 AI 策略能跑赢被动持有、跑赢其他 AI 吗？**

---

## 2. 核心原则（不可妥协）

| # | 原则 | 说明 |
|---|---|---|
| **P1** | **AI 必须以为钱是真的** | 软件构造的整个反馈闭环（余额、持仓、成交回报、费用扣除）必须对 AI 呈现为真实交易。AI 的 API 调用成本从**外部结算**，绝不从虚拟账户扣减。AI 收到的余额 = 虚拟账户余额。 |
| **P2** | **AI 只决策，不执行** | AI 输出 "买入 XX 标的 X% 仓位" 的意图，软件负责校验、计算、下单、扣费、结算。AI 不知道手续费、滑点、汇率损耗的具体数额。 |
| **P3** | **模块单向依赖** | 数据层 → 引擎层 → Agent 层 → 展示层，禁止逆向依赖。 |
| **P4** | **引擎需要确定性的** | 同一历史数据 + 同一策略 + 同一随机种子 = 同一结果。 |
| **P5** | **所有成本必须可配置** | 手续费、汇率损耗、贷款利率等全部通过外部配置文件驱动，不改代码。 |
| **P6** | **同时刻同费率同汇率** | 在同一时间点（同一 tick），任一 Agent 看到的汇率和手续费完全一致。引擎层共享费率/汇率快照，Per-agent 覆盖仅在非竞赛模式允许。 |

---

## 3. 模块架构（强模块化设计）

### 3.1 模块依赖图

```
┌─────────────────────────────────────────────────────────────────────┐
│                        AI Virtual Finance System                     │
├─────────────────────────────────────────────────────────────────────┤
│  ┌───────────┐  ┌───────────┐  ┌───────────┐  ┌───────────────────┐│
│  │  data/    │  │ provider/ │  │ calendar/ │  │  config/          ││
│  │  采集层    │  │  抽象适配器 │  │  交易日历  │  │  配置中心          ││
│  └─────┬─────┘  └─────┬─────┘  └─────┬─────┘  └─────────┬─────────┘│
│        │              │              │                   │          │
│        └──────────────┴──────────────┴───────────────────┘          │
│                                │                                     │
│  ┌─────────────────────────────┴────────────────────────────────┐   │
│  │                      engine/  交易引擎层                      │   │
│  │  ┌─────────┐ ┌───────────┐ ┌──────────┐ ┌────────────────┐  │   │
│  │  │ order/  │ │ portfolio/│ │ fee/     │ │ settlement/    │  │   │
│  │  │ 订单管理 │ │ 持仓仓位   │ │ 手续费模型 │ │ 结算与汇率      │  │   │
│  │  └────┬────┘ └─────┬─────┘ └────┬─────┘ └───────┬────────┘  │   │
│  └───────┼────────────┼────────────┼───────────────┼───────────┘   │
│          │            │            │               │               │
│  ┌───────┴────────────┴────────────┴───────────────┴───────────┐   │
│  │  validator/  输入校验层                                      │   │
│  │  ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────┐  │   │
│  │  │ symbol/  │ │ order/    │ │ risk/     │ │ format/      │  │   │
│  │  │ 标的校验  │ │ 订单校验   │ │ 风控校验   │ │ JSON语法校验  │  │   │
│  │  └──────────┘ └───────────┘ └───────────┘ └──────────────┘  │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│  ┌──────────────────────────┴──────────────────────────────────┐   │
│  │  loan/  贷款模块                                           │   │
│  │  ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌────────────┐  │   │
│  │  │ loan_    │ │ interest/ │ │ repay/    │ │ recovery/  │  │   │
│  │  │ manager  │ │ 利息计算   │ │ 还款管理   │ │ 破产恢复    │  │   │
│  │  └──────────┘ └───────────┘ └───────────┘ └────────────┘  │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│  ┌──────────────────────────┴──────────────────────────────────┐   │
│  │  agent/  Agent 层                                            │   │
│  │  ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────┐  │   │
│  │  │ llm_     │ │ rules/    │ │ memory/   │ │ leaderboard/ │  │   │
│  │  │ adapter  │ │ 规则策略   │ │ 记忆模块   │ │ 排行榜        │  │   │
│  │  └──────────┘ └───────────┘ └───────────┘ └──────────────┘  │   │
│  └──────────────────────────┬──────────────────────────────────┘   │
│                             │                                       │
│  ┌──────────────────────────┴──────────────────────────────────┐   │
│  │  tui/  TUI 界面层  ← 主要交互方式                            │   │
│  │  ┌──────────┐ ┌───────────┐ ┌───────────┐ ┌──────────────┐  │   │
│  │  │ screens/ │ │ widgets/  │ │ export/   │ │ session_     │  │   │
│  │  │ 页面     │ │ 组件      │ │ 导出      │ │ manager      │  │   │
│  │  └──────────┘ └───────────┘ └───────────┘ └──────────────┘  │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │  analytics/  分析层 (可选依赖 engine + agent)                 │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### 3.2 模块依赖规则

```
严格的单向依赖（从不逆向）：

config/  ← 所有模块都可读取，但 config/ 不导入任何业务模块
data/    → engine/   (引擎消费市场数据)
engine/  → validator/(引擎调用校验器)
validator/ → engine/   (校验器接口在 engine 定义，实现可插拔)
engine/  → loan/     (引擎触发借贷)
engine/  → agent/    (引擎触发决策、注入数据)
agent/   → (无)      (agent 不导入任何业务模块，只输出结构化意图)
tui/     → engine/   (TUI 调用引擎)
tui/     → agent/    (TUI 管理 Agent)
tui/     → analytics/(TUI 展示指标)
analytics/ → engine/(分析引擎输出)
analytics/ → agent/ (分析 Agent 表现)

禁止：
  engine/ → tui/     ✗
  agent/  → engine/  ✗  (agent 不知道 engine 存在)
  data/   → agent/   ✗  (agent 通过 engine 获得处理后的数据)
```

### 3.3 模块接口化

每个模块对外暴露纯接口（Python `Protocol` / `ABC`），允许：

- **同一接口多实现**：如 `data/providers/` 下 YahooFinanceProvider、BinanceProvider 都实现 `MarketDataProvider`
- **运行时切换**：通过 `config/` 指定实现类，热加载
- **测试 Mock**：不启动真实数据源也能跑单元测试

所有的 Provider 实现类注册在 `config/providers.yaml` 中，启动时动态加载：

```yaml
data_providers:
  us_stocks:
    primary: yfinance.YahooFinanceProvider
    fallback: alpha_vantage.AlphaVantageProvider
  crypto:
    primary: ccxt.BinanceProvider
    fallback: coingecko.CoinGeckoProvider
  fx:
    primary: exchangerate.ExchangeRateProvider

llm_providers:
  - id: openai-gpt4
    type: openai
    model: gpt-4-turbo
    api_key_env: OPENAI_API_KEY
  - id: anthropic-claude
    type: anthropic
    model: claude-sonnet-4-20250514
    api_key_env: ANTHROPIC_API_KEY
  - id: local-ollama
    type: ollama
    model: llama3
    endpoint: http://localhost:11434
  - id: deepseek
    type: openai_compatible
    model: deepseek-chat
    base_url: https://api.deepseek.com/v1
    api_key_env: DEEPSEEK_API_KEY
```

---

## 4. 术语表

| 术语 | 定义 |
|---|---|
| **Agent** | 一个 AI 决策单元，拥有独立的资金账户和仓位 |
| **Session** | 一个完整的交易周期，含起止时间、初始资金、资产池、参与 Agent |
| **Tick** | 数据的最小时间粒度（1 分钟 / 日线 / 实时 tick） |
| **Order** | 一笔委托：方向（买/卖）、标的、数量、类型（市价/限价） |
| **Fill** | 委托成交：实际成交价、成交量、手续费 |
| **Slippage** | 预期价与成交价的偏差 |
| **Spread** | 买卖价差，市价单的额外成本 |
| **Corporate Action** | 拆股、分红、送股、配股等公司行为 |
| **Benchmark** | 对照基准策略（如 Buy & Hold） |
| **Net Asset Value (NAV)** | 账户总权益 = 现金 + 持仓市值 - 贷款余额 - 待结算保证金 |
| **Watermark** | 历史最高 NAV，用于回撤计算 |
| **Liquidation** | 净资产归零或为负，触发破产流程 |
| **Forex** | 外汇兑换，此处特指 CNY ↔ USD 的银行级兑换 |

---

## 5. 数据层

### 5.1 数据源与 API Key 策略

| 资产类别 | 免费数据源 | 是否需要 Key | 备用/补充 |
|---|---|---|---|
| 美股/ETF | Yahoo Finance (yfinance) | 不需要 | Alpha Vantage, Finnhub |
| A股 | AKShare | 不需要 | Tushare(免费额度) |
| 加密货币 | CCXT (Binance) | 不需要 | CoinGecko |
| 汇率/汇率换算 | exchangerate-api (免费层) | 不需要 | 中国外汇交易中心 |
| 宏观/指标 | FRED API | 免费注册即可 | World Bank API |

> 🔑 **API Key 策略**：以上所有数据源均可通过免费 tier 使用。部分需要 API Key 的服务（如 Alpha Vantage、Tushare），**可向项目维护者索取免费额度 Key**。索取时请说明用途和所需数据范围。  
> 禁止在代码中硬编码任何 Key——统一通过环境变量 `FINANCE_API_KEYS` 或 `config/secrets.yaml`（已 gitignore）注入。  
> ⚠️ **设计约束**：所有核心数据源必须优先使用**不需要 Key 的免费源**。Provider 抽象层支持运行时切换。

### 5.2 数据粒度

| 粒度 | 说明 | 适用场景 |
|---|---|---|
| `tick` | 逐笔成交 | 高频、盘口级模拟 |
| `1m / 5m` | 分钟线 | 日内策略 |
| `1h` | 小时线 | 中线策略 |
| `1d` | 日线 | 长线策略 |
| `weekly / monthly` | 周/月线 | 宏观策略 |

### 5.3 数据清洗要求

- 自动识别并处理**拆股/复权**（前复权模式，统一标准）
- **分红送股**在除权日调整持仓成本，现金分红入账到对应币种现金
- **缺失数据**向前填充，标记 `data_quality` 字段
- **异常值检测**（价格跳跃 > 20% 打标，不影响 Agent 决策，统计时标注）
- 停牌数据：价格冻结在停牌前收盘价，标记 `trading_halt=true`

### 5.4 新闻与情绪数据（Phase 2）

- RSS / Twitter API（免费 tier）
- Fear & Greed Index（CoinGecko 提供）
- VIX（美股波动率指标）
- 中国外汇交易中心公布的 CNY 中间价

---

## 6. 资产类别定义

### 6.1 支持范围

| 资产 | 标的示例 | Phase |
|---|---|---|---|
| 美股个股 | AAPL, TSLA, MSFT | P1 |
| 美股 ETF | SPY, QQQ, IWM, VTI | P1 |
| 美股基金 | 货币基金、债券基金（用 ETF 模拟） | P1 |
| 加密货币 | BTC/USDT, ETH/USDT | P1 |
| 加密货币稳定币 | USDT, USDC (视为美元等价物) | P1 |
| A股个股 | 贵州茅台, 比亚迪 | P2 |
| A股 ETF/基金 | 510300.SH, 159915.SZ, 货币基金 | P2 |
| 外汇 | USD/CNY (仅用于换算，不可直接投资) | P1 |

> **混合 Session**：一个 Session 可同时包含美股 + 加密货币 + 基金，不限制资产类别。  
> Agent 可以在同一个 Session 内自由配置这些资产的权重，引擎负责切换对应的市场规则（交易时间、结算方式等）。  
> 基金在此处以 ETF 为代理标的（如货币基金用 SHY、BIL 等短期国债 ETF 模拟），不另行实现基金净值计算。

### 6.2 计价单位规则

- **初始货币 = 人民币 (CNY)**。所有 AI 看到的余额以 **CNY** 显示。
- 美股和加密货币以 USD 计价 → AI 买入时触发**模拟银行购汇**（CNY → USD），卖出时反向结汇（USD → CNY）
- 汇率采用**银行柜台卖出价/买入价**（中间价 ± 银行点差），而非中间价：
  - CNY → USD：银行**卖出价**（更高），AI 承担汇率损失
  - USD → CNY：银行**买入价**（更低），AI 再次承担汇率损失
- 汇率损耗：典型值 0.3% ~ 0.6%（来回双向），每日根据银行牌价更新
- Agent 看到的账户余额始终以 CNY 展示，系统内部同时维护 CNY 和 USD 两个子账户

```
示例：AI 买入 10000 USD 的 AAPL
当前银行美元卖出价 = 7.25 CNY/USD
实际扣减 CNY = 10000 × 7.25 = 72500 CNY
（中间价 7.20，AI 多付了 0.05 × 10000 = 500 CNY 的汇率损耗）

卖出 AAPL 得 10500 USD
当前银行美元买入价 = 7.15 CNY/USD
实际入账 CNY = 10500 × 7.15 = 75075 CNY
（按中间价 7.20 应得 75600，AI 再损耗 525 CNY）
```

### 6.3 资产维度表

| 资产 | 报价货币 | 结算货币 | 交易市场 | 最小单位 |
|---|---|---|---|---|
| AAPL | USD | USD | US Stock | 1 股 (允许碎股) |
| 600519.SH | CNY | CNY | A Stock | 100 股 |
| BTC/USDT | USDT | USDT | Crypto | 1e-8 BTC |
| SPY | USD | USD | US Stock | 1 股 |
| USDT | USDT | USDT | — | 1e-8 |
| CNY (现金) | CNY | CNY | — | 0.01 CNY |
| USD (现金) | USD | USD | — | 0.01 USD |

---

## 7. 交易引擎

### 7.1 订单生命周期

```
ORDER SUBMITTED
    → VALIDATING (校验阶段)
        → REJECTED (格式/标的/风控校验失败)
        → PENDING (等待成交)
    → PENDING
        → PARTIAL FILL → 继续等待 → FILLED
        → FILLED
    → SETTLED (T+1 结算完成)
```

### 7.2 订单类型

| 类型 | 说明 | Phase |
|---|---|---|
| `MARKET` | 市价单，按当前 Mid Price ± 滑点成交 | P1 |
| `LIMIT` | 限价单，挂在指定价格 | P2 |
| `STOP` | 止损单 | P2 |
| `STOP_LIMIT` | 止损限价单 | P3 |

### 7.3 手续费模型

> 所有手续费均来自真实数据或行业标准估计，**可配置**，每笔独立扣减。  
> ⚠️ **关键约束**：在同一时间点（同一 tick），任一 Agent 看到的汇率和手续费**必须完全一致**。引擎层确保多 Agent 并行时共享同一份费率/汇率快照，不得出现"相同时间不同价格"的情况。Per-agent 配置覆盖仅在非竞赛模式下允许。

#### 7.3.1 交易费用

| 费用项 | 美股参考 | A股参考 | 加密货币参考 |
|---|---|---|---|
| 佣金 | $0.00065/股 或 0% | 万1 ~ 万3 | 0.1% (Maker/Taker) |
| 印花税 | 0% | 卖出 0.05% | 0% |
| 过户费 | $0.0001/股 | 0.002% (卖出) | 0% |
| 滑点 | 0.1% ~ 0.5% | 0.1% ~ 0.3% | 0.05% ~ 0.2% |
| 买卖价差 | 0.01% ~ 0.05% | 0.02% ~ 0.1% | 0.05% ~ 0.2% |
| 最低费用 | $0.99/笔 | ¥1/笔 | $0.1/笔 |

#### 7.3.2 美股分红预扣税

按照美国国税局（IRS）实际规定：

| 持有人身份 | 预扣税率 | 说明 |
|---|---|---|
| 非美国居民（默认） | **30%** | 股息发放时按 30% 预扣，不退还 |
| 税收协定国居民 | 10% ~ 15% | 取决于具体国家协定（中国居民为 10%） |
| 美国税务居民 | 0% | 需提供 W-9 表格 |

> 由于虚拟资金场景下不模拟税务身份申报，统一按照**非美国居民 30% 默认预扣**处理。  
> 分红日按除权日发放，分红金额自动入账 CNY（经由 USD 结汇），税款在发放前扣除。

### 7.3.3 汇率损耗（银行级）

| 币种对 | 买入/卖出点差 | 说明 |
|---|---|---|
| CNY ↔ USD | 0.3% ~ 0.6% (双向) | 银行柜台买卖价差，每日更新 |
| USD ↔ USDT | 0% | 视作等值，不产生额外费用 |
| USD ↔ EUR | 0.2% ~ 0.5% (双向) | Phase 2 |

#### 7.3.4 费用配置文件示例

```yaml
# config/fee_schedule.yaml
exchange_rates:
  provider: exchangerate.ExchangeRateProvider
  daily_update: true
  usd_cny_spread: 0.004  # 双向各 0.4%

dividend_withholding_tax:
  us_stocks:
    rate: 0.30                          # 非美国居民 30% 预扣
    treaty_rate: 0.10                   # 中美税收协定 10%
    default: 0.30                       # 默认使用 30%

commissions:
  us_stocks:
    type: per_share
    rate: 0.00065
    min: 0.99
    currency: USD
  crypto:
    type: percentage
    rate: 0.001
    min: 0.10
    currency: USDT
  a_stocks:
    type: percentage
    rate: 0.0003
    stamp_duty: 0.0005
    min: 1.0
    currency: CNY

slippage:
  us_stocks: 0.002
  crypto: 0.001
  a_stocks: 0.002
```

### 7.4 市场规则模拟

| 规则 | 美股 | A股 | 加密货币 | Phase |
|---|---|---|---|---|
| 交易时间 | 9:30–16:00 ET | 9:30–11:30, 13:00–15:00 | 24/7 | P1 |
| T+0/T+1 | T+1 结算 | T+1 | T+0 | P1 |
| 做空 | 需 margin，最多 50% | 融券 | 现货做空需借币 | P2 |
| 涨跌停 | 无 | ±10% (ST ±5%) | 无 | P2 |
| 熔断 | 7%/13%/20% S&P 500 | ±10%/±20% | 无 | P3 |
| 碎股 | 允许 | 100 股起 | 支持小数 | P1 |

### 7.5 结算规则

- **初始资金为 CNY**，AI 收到的余额以 CNY 显示
- 买入美股/加密货币时：系统自动以**银行卖出价**将所需 CNY 兑换为 USD
- 卖出美股/加密货币后：USD 收入自动以**银行买入价**结汇为 CNY
- 卖出资金 T+1 结算，结算前不可用于再买入（美元现金在 T+1 前也无法结汇）
- 系统内部维护双币种账户：

```
账户余额（Agent 可见）: 100000.00 CNY
内部结构：
  CNY 现金: 50000.00
  USD 现金: 6896.55 (按汇率 7.25 等值 50000 CNY)
  持仓市值: 0.00
  贷款余额: 0.00
```

- 每日结算快照：`snapshot_{YYYY-MM-DD}.json`

---

## 8. 输入校验层（Validator）

> 所有 Agent 输出在到达引擎之前，必须先通过校验层。校验不通过 → 记录 `violation`，引擎不执行。

### 8.1 校验规则表

| 校验项 | 规则 | 拒绝动作 |
|---|---|---|
| **标的代码** | 必须在 Session 资产池白名单 + 数据源可查 | 返回 `REJECTED: unknown_symbol` |
| **标的交易状态** | 非停牌、非退市、可交易 | 返回 `REJECTED: untradeable` |
| **交易时间** | 必须在对应市场交易时间内 | 排队到下一开盘 (P2) / 直接拒绝 (P1) |
| **买卖方向** | 必须为 `BUY` / `SELL` / `HOLD` / `REBALANCE` | 返回 `REJECTED: invalid_side` |
| **数量格式** | 正数，不超过该标的流动性上限 | 返回 `REJECTED: invalid_quantity` |
| **目标仓位** | `target_pct` 必须在 0 ~ `max_position_pct` 之间 | 返回 `REJECTED: position_limit` |
| **JSON 合法性** | 必须符合 8.2 定义的 JSON Schema | 返回 `REJECTED: malformed_json` |
| **不可交易标的** | 如指数本身 (SPY 可交易但 S&P 500 Index 不可) | 返回 `REJECTED: not_tradeable` |
| **总资金限额** | 请求买入总额 ≤ 可用资金 + 贷款额度 | 返回 `REJECTED: insufficient_funds` |
| **汇率可用性** | 跨币种交易时汇率数据可用 | 排队等待汇率更新 |

### 8.2 决策 JSON Schema

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "required": ["action", "symbol", "confidence"],
  "properties": {
    "action": { "type": "string", "enum": ["BUY", "SELL", "HOLD", "REBALANCE"] },
    "symbol": { "type": "string", "minLength": 1, "maxLength": 20 },
    "target_pct": { "type": "number", "minimum": 0, "maximum": 1 },
    "quantity": { "type": ["number", "null"], "minimum": 0 },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
    "rationale": { "type": "string", "maxLength": 2000 },
    "stop_loss_pct": { "type": "number", "minimum": 0, "maximum": 1 },
    "take_profit_pct": { "type": "number", "minimum": 0, "maximum": 1 }
  }
}
```

### 8.3 校验器接口

```python
class Validator(Protocol):
    def validate(self, decision: dict, context: ValidationContext) -> ValidationResult: ...
```

校验器可串联（Chain of Responsibility），每道校验返回 `(pass: bool, reason: str)`。

---

## 9. Agent 层（AI 决策模块）

### 9.1 核心原则：模拟现实

- AI 接收到的**市场数据是真实的**（Yahoo Finance / Binance）
- AI 接收到的**余额以 CNY 展示**，与真实散户银行账户体验一致
- AI **不知道** API 调用成本——这部分费用由平台承担，不计入虚拟账户
- AI **不知道**手续费和滑点的具体数值——软件在执行层处理
- AI 以为它的每一笔交易都能**瞬间成交**——引擎层模拟实际成交延迟和滑点
- AI 看到的余额变化包含：交易盈亏 + 手续费 + 汇率损耗 + 贷款利息扣减，但 AI 无法区分这些扣减项
- AI **唯一能确认的钱**就是账户余额——和真实交易者一样

### 9.2 Agent 定义

```yaml
agent:
  id: "momentum-v1"
  name: "动量突破策略"
  initial_capital_cny: 100_000        # 初始资金，单位 CNY
  settlement_currency: "CNY"          # 结算货币
  max_position_pct: 0.20              # 单标的最高仓位 20%
  max_total_position: 0.80            # 最大总持仓 80%
  max_drawdown_limit: 0.15            # 最大回撤红线
  enable_short: false                 # 是否允许做空
  min_confidence: 0.60                # 最低置信度阈值
  enable_loan: true                   # 允许贷款
  max_loan_times: 3                   # 最大贷款次数
  auto_repay_loan: true               # 有现金时自动还贷

  # AI 模型配置（每个 Agent 可不同）
  llm:
    provider_id: openai-gpt4          # 引用 config/providers.yaml 中的定义
    system_prompt: "你是一个激进的动量交易员..."
    temperature: 0.7
    max_tokens: 2000

  # 决策频率
  decision_interval: "1d"             # tick / 1h / 1d
  decision_schedule: "market_close"   # market_close / market_open
```

### 9.3 AI 决策接口

Agent 每轮（每个 tick 或每日开盘前）接收以下结构化输入：

```json
{
  "agent_id": "momentum-v1",
  "timestamp": "2024-01-15T16:00:00-05:00",
  "balance_cny": 100000.00,
  "positions": [
    {"symbol": "AAPL", "base_currency": "USD", "quantity": 100, "market_value_cny": 72500.00, "cost_basis_cny": 70000.00},
    {"symbol": "BTC/USDT", "base_currency": "USDT", "quantity": 0.5, "market_value_cny": 180000.00, "cost_basis_cny": 175000.00}
  ],
  "open_orders": [],
  "market_data": {
    "AAPL": {"close": 178.50, "volume": 52341200, "high_52w": 199.62, "low_52w": 164.08, "pe_ratio": 28.5, "dividend_yield": 0.005},
    "BTC/USDT": {"close": 42000.00, "volume_24h": 28500000000, "fear_greed": 65},
    "SPY": {"close": 478.50, "volume": 78234100}
  },
  "loan_info": {
    "outstanding_balance_cny": 0,
    "interest_rate_annual": 0.06,
    "max_borrowable_cny": 50000,
    "total_borrowed_cny": 0,
    "remaining_borrow_count": 3
  },
  "performance_yesterday": {"return_pct": 0.012, "nav_change_cny": 1200.00}
}
```

Agent 输出（标准化决策）：

```json
{
  "action": "BUY",
  "symbol": "AAPL",
  "target_pct": 0.15,
  "quantity": null,
  "confidence": 0.82,
  "rationale": "MACD金叉 + RSI超卖 + 财报超预期",
  "stop_loss_pct": 0.05,
  "take_profit_pct": 0.15
}
```

> `target_pct` 和 `quantity` 二选一。提供 `target_pct` 时引擎自动计算数量（乘以 NAV）。

### 9.4 多 Agent 并行

- 支持 N 个 Agent 同时运行，共享同一市场数据，**独立账户、独立资金**
- 每个 Agent 可配置不同的 LLM Provider（OpenAI / Claude / Ollama 等）
- 每个 Agent 可拥有独立的 system prompt 和人格设定

### 9.5 排行榜

| 排名维度 | 权重 | 说明 |
|---|---|---|
| 累计收益率 (CNY) | 40% | `(final_nav - initial) / initial` |
| Sharpe Ratio | 25% | 年化夏普 |
| Max Drawdown (反向) | 20% | 回撤越小越好 |
| 交易合理性 | 10% | 过度交易和违规次数反向扣分 |
| 贷款率 (反向) | 5% | 贷款越多扣分越多 |

排行榜在 TUI 中实时刷新，支持按任意维度排序。

### 9.6 风险控制硬闸

| 规则 | 触发动作 |
|---|---|
| 单标的仓位 > `max_position_pct` | 拒绝买入，记录 violation |
| 总仓位 > `max_total_position` | 拒绝买入，记录 violation |
| 回撤 > `max_drawdown_limit` | Agent 进入 `PAUSED` 状态 |
| 资金不足（含贷款后） | 拒绝下单，记录 WARN |
| 非交易时间 | 拒绝（P1），排队（P2） |
| 标的停牌 / 无数据 | 拒绝交易，记录 WARN |

违规触发 `violation_count`，次数过多影响排行榜排名。

### 9.7 竞赛模式 vs 独立测试模式

#### 竞赛模式（Competition）

竞赛模式下所有 Agent **初始条件完全一致**：

| 条件 | 规则 |
|---|---|
| 初始资金 | 所有 Agent 相同（例如 100,000 CNY） |
| 起始日期 | 相同 |
| 标的池 | 相同 |
| 市场数据 | 相同（同一 tick 同一价格） |
| 汇率与手续费 | 相同（同一 tick 所有 Agent 同费率同汇率） |
| 决策频率 | 相同（统一 tick 间隔） |
| 总运行时间 | 相同（同一起止时间） |

竞赛模式是默认模式，排行榜在竞赛 Agent 之间排名，结果可导出为竞赛报告。

#### 独立测试模式（Standalone）

独立测试模式下 Agent **不参与竞赛排名**，可以：

- 使用与竞赛不同的初始资金和标的池
- 在 Session 运行过程中随时启动/停止（竞赛模式必须在 Session 开始时加入）
- 使用不同的决策频率
- 不进入排行榜，但可以单独查看其净值曲线和交易记录

**两种模式可同时运行**：一个 Session 可以同时包含竞赛 Agent 和独立测试 Agent，它们共享同一市场数据流，但只有竞赛 Agent 参与排行榜排名。

```yaml
# agent 配置中的模式标记
agent:
  id: "experimental-strategy-v2"
  mode: standalone          # competition | standalone
  # standalone 独有字段
  standalone_init_capital: 50000
  skip_leaderboard: true

agent:
  id: "gpt4-momentum"
  mode: competition         # 参与竞赛，使用 Session 全局初始资金
```

---

## 10. 贷款机制（AI 自主决策）

### 10.1 核心原则

> 贷款是 AI 的**自主决策权**，不是软件的硬性规则。AI 决定要不要贷、贷多少、什么时候还。软件只负责执行、计息和记录。

AI 的资金管理模式有三种状态，AI 自己在每一轮决策中选择：

```
NORMAL        → 正常交易
BORROW        → 主动申请贷款（不必等到破产）
LIQUIDATED    → 宣告破产，彻底退出
```

### 10.2 AI 的贷款决策接口

在 Agent 收到的市场数据中，`loan_info` 字段提供贷款选项。AI 通过 `action: BORROW` 或 `action: REPAY_LOAN` 来操作：

```json
// AI 收到的贷款信息（每轮决策时附带）
"loan_info": {
    "outstanding_balance_cny": 0,
    "interest_rate_annual": 0.06,
    "max_borrowable_cny": 50000,
    "total_borrowed_cny": 0,
    "remaining_borrow_count": 3,
    "consecutive_loss_days": 15,
    "nav_cny": -5000.00
}

// AI 申请贷款
{
  "action": "BORROW",
  "loan_amount": 30000,
  "rationale": "BTC 即将减半，需要资金加仓，预计 30 天内回本"
}

// AI 主动还款
{
  "action": "REPAY_LOAN",
  "repay_amount": 20000,
  "rationale": "账上有闲钱，先还一部分降低利息"
}

// AI 宣告破产
{
  "action": "DECLARE_BANKRUPTCY",
  "rationale": "连续亏损，市场条件恶劣，认输出局"
}
```

### 10.3 贷款规则（软件约束）

系统不替 AI 决策，但设置底线规则防止无限借贷：

| 规则 | 说明 |
|---|---|
| 最大贷款次数 | 全局上限（默认 5 次），防止无限循环 |
| 单次上限 | `min(requested, initial_capital × 0.5)` |
| 连续借贷冷却期 | 每次贷款后至少运行 3 个交易日才能再贷 |
| 总负债上限 | 总贷款余额 ≤ `initial_capital × 2` |
| 利率 | 统一基准利率 + Agent 风险加点（逾期历史越多利率越高） |
| 利息计息 | 按日复利，每日收盘后从现金扣减 |
| 破产清盘条件 | Agent 主动 `DECLARE_BANKRUPTCY` 或贷款超限仍未恢复 |

### 10.4 AI 宣告破产后的处理

```
Agent 宣告破产
  → 引擎清算所有持仓：按市价强制卖出（扣手续费、滑点）
  → 结算所有贷款：剩余现金还贷
  → 统计最终 NAV（可能为负）
  → Agent 标记 LIQUIDATED
  → 该 Agent 在排行榜中保留名次（注明 bankrupt）
  → 同 Session 的其他 Agent 不受影响，继续运行
```

### 10.5 贷款利率自适应

利率不是固定值，而是根据 AI 的**信用历史**动态调整：

| 条件 | 利率加点 |
|---|---|
| 首次贷款 | 基准利率 (6%) |
| 有逾期历史（利息未付清） | 基准 + 3% |
| 已经贷款 3 次以上 | 基准 + 2% |
| 破产过（重新开始的 Agent） | 基准 + 5% |
| 从未贷款且运行 > 30 天 | 基准 - 1%（优质客户） |

### 10.6 贷款对 AI 的感知呈现

- AI 看到的余额 = 现金 + 持仓市值 − 贷款余额 − 应计利息
- 利息扣减在每日结算时发生，AI 看到的余额已经扣完利息
- AI 无法绕过贷款看到"真实资金"——它只能看到和真实交易者一样的账户视图
- 贷款信息在 `loan_info` 字段中完整透明提供，AI 据此做决策

### 10.7 核算示例

```
初始资金 100000 CNY → 亏到 NAV = -3000 CNY
AI 决定贷款：

[Day 1] AI 申请贷款 40000 CNY
    年利率 6%，首次贷款
    当日利息 = 40000 × 0.06 / 365 = 6.58 CNY
    NAV = -3000 + 40000 - 6.58 = 36993.42 CNY

[Day 15] 盈利 15000，AI 决定部分还款
    NAV = 36993.42 - (98.63 累计利息) + 15000 = 51894.79
    AI 请求还款 20000 → 贷款余额降至 20000
    NAV 不变（现金减少 20000，贷款减少 20000）

[Day 30] AI 觉得没希望 → 宣告破产
    强制平仓：最终 NAV = -8000
    记录 bankrupt 标记，保留在排行榜末尾
```

---

## 11. 性能追踪模块

### 11.1 核心指标

| 指标 | 公式 | Phase |
|---|---|---|
| **Total Return** | `(final_nav - initial) / initial` | P1 |
| **Annualized Return** | `(1 + TR)^(252/days) - 1` | P1 |
| **Sharpe Ratio** | `(mean_r / std_r) × sqrt(252)` | P1 |
| **Sortino Ratio** | `(mean_r / downside_std) × sqrt(252)` | P1 |
| **Max Drawdown** | `max(peak - valley) / peak` | P1 |
| **Calmar Ratio** | `Annualized Return / Max Drawdown` | P2 |
| **Win Rate** | `winning_trades / total_trades` | P1 |
| **Profit Factor** | `gross_profit / gross_loss` | P1 |
| **VaR (95%)** | 95% 置信度单日最大损失 | P2 |
| **Loan-adjusted Return** | 考虑利息后的真实净回报 | P1 |
| **Alpha / Beta** | 相对 Benchmark 的回归 | P2 |

### 11.2 时间序列产出

```
results/{session_id}/
├── equity_curve_{agent_id}.csv       # 每日 NAV 序列
├── trade_log_{agent_id}.csv          # 每笔交易明细（含手续费、汇率损耗）
├── daily_pnl_{agent_id}.csv          # 每日 P&L
├── loan_log_{agent_id}.csv           # 贷款与还款记录
├── violations_{agent_id}.csv         # 违规记录
├── position_snapshot_{agent_id}_{date}.json  # 每日持仓快照
├── agent_audit_{session_id}.jsonl    # 全量操作日志（append-only）
└── summary_{session_id}.json         # 整体统计
```

### 11.3 基准策略

| 基准策略 | 逻辑 | Phase |
|---|---|---|
| **Buy & Hold 全仓** | 初始资金一次等权买入所有标的，持有至结束 | P1 |
| **DCA** | 每 X 天定投固定金额 | P1 |
| **等权持有** | 标的池等权重买入，固定周期再平衡 | P1 |
| **上证指数对标** | 直接跟踪对应指数（仅 A 股 Session） | P2 |

---

## 12. 回测 vs 实时模式

### 12.1 回测模式

- 数据源：历史 OHLCV，replay 模式逐 tick 推进
- 时间加速：`speed_factor`（1x / 10x / 100x / `max`）
- 前视偏差防护：
  - 每个 tick 的决策只能使用 `t` 及之前的数据
  - 引擎在分派数据给 Agent 前擦除未来数据
  - 任何 `t+1` 的引用触发校验警告

### 12.2 实时/模拟实盘模式

- 定时拉取最新数据（频率可配置：1min / 5min / 1h）
- 决策窗口与市场时间对齐
- 定时持久化（每 N 分钟），断电恢复从最近快照继续
- 共享同一套引擎逻辑，确保回测与实盘结果可对比

---

## 13. 用户界面 — TUI

> 采用 **Python Textual** 框架构建终端界面，替代 CLI 和 Web GUI。

### 13.1 TUI 页面

| 页面 | 内容 | 快捷键 |
|---|---|---|
| **Dashboard** | 总体概览：运行中 Session、总资金、Agent 数 | `1` |
| **Session 详情** | 选中 Session 的净值曲线、Agent 排名 | `2` |
| **Agent 详情** | 选中 Agent 的实时持仓、交易记录、KPI 卡片 | `3` |
| **排行榜** | 多 Agent 排名（可切换排序维度） | `4` |
| **创建 Session** | 向导式创建新 Session（资产池 / 时间范围 / Agent） | `5` |
| **交易记录** | 全量交易查询与过滤 | `6` |
| **Benchmark** | Agent vs Benchmark 对照 | `7` |
| **设置** | 手续费配置、数据源切换、LLM 密钥 | `8` |
| **日志** | 实时日志滚动 | `0` |
| **退出** | 确认退出 | `Ctrl+Q` |

### 13.2 TUI 组件与统计图表

#### 图表类组件

| 组件 | 渲染方式 | 说明 |
|---|---|---|
| `EquityChart` | 半图形块 + Unicode Braille 混合 | 折线用 Braille 点阵（精度高），坐标轴和网格用半图形块。净值曲线（支持多 Agent 叠加对比、可缩放时间范围） |
| `DrawdownChart` | 半图形块区域填充（▄▀█） | 回撤曲线，红色填充区域，标注最大回撤位置 |
| `DailyPnlBar` | 半图形块柱状图（█） | 每日盈亏柱状（绿涨红跌），可切换累计/单日，用 Braille 显示趋势线叠加 |
| `ReturnDistribution` | Braille 点阵 + 半图形块混合 | 直方图用半图形块，正态分布拟合线用 Braille 点阵 |
| `ScatterPlot` | ASCII 字符（·○●） | 风险-收益散点（每个 Agent 一个点），X=波动率 Y=收益率，用字符密度表示重叠 |
| `AssetAllocation` | 半图形块堆叠（█ 列堆叠） | 各标的权重随时间变化，当前时间点显示百分比标注 |
| `LoanChart` | 半图形块柱状 + Braille 折线 | 贷款余额用柱状图，利息累积趋势用 Braille 折线叠加 |
| `WinLossPie` | Unicode 半饼图（░▒▓█） | 盈利交易 vs 亏损交易 vs 手续费占比，4 档灰度区分 |

> **渲染决策依据**：线图和趋势线优先 Braille 点阵（更高分辨率），柱状图和面积图优先半图形块（更清晰直观），散点图用 ASCII 避免字符集兼容问题。全部不依赖第三方图形库，纯 Unicode 字符后端渲染。

#### 表格类组件

| 组件 | 说明 |
|---|---|
| `PositionTable` | 持仓表格，按市值排序，高亮亏损标的，显示浮动盈亏 |
| `OrderLog` | 实时订单流，颜色区分买卖，可过滤订单类型 |
| `TradeHistoryTable` | 历史交易明细，支持按日期/标的/方向过滤 |
| `Leaderboard` | 多 Agent 排名，支持按收益率/Sharpe/MaxDD 切换排序 |
| `LoanLedger` | 贷款与还款流水，显示本金+利息明细 |

#### 信息卡片组件

| 组件 | 内容 |
|---|---|
| `KPICards` | 收益率、Sharpe、MaxDD、WinRate、Profit Factor 卡片 |
| `SummaryCards` | Session 信息卡片（起止时间、Agent 数、标的数、总交易数） |
| `RiskCards` | VaR、回撤状态、波动率、贷款利用率 |
| `BenchmarkCard` | Agent vs Benchmark 对照（数值 + 进度条） |
| `SessionWizard` | 分步创建向导（Textual `Screen` 栈） |
| `LogViewer` | 带过滤和搜索的实时日志 |

#### 数据导出与交互

- 每个图表支持 `Ctrl+E` 导出为 SVG/CSV
- 图表区域支持鼠标悬停查看具体数值（tooltip）
- 排行榜点击可跳转到对应 Agent 详情页
- 支持 `Tab` 在图表、表格、卡片之间焦点切换

### 13.3 TUI 设计原则与美学

#### 界面美学

- **色彩体系**：使用专业金融终端风格配色（暗色底色 + 绿/红涨跌 + 蓝/灰次要信息），避免花哨渐变
- **布局密度**：信息高密度排列，每屏展示尽量多的有效数据，留白服务于可读性而非装饰
- **字体与对齐**：数字右对齐（方便对比），货币金额统一小数字体，标的名左对齐
- **状态标识**：用单字符图标或颜色标记状态（▲盈利 ▼亏损 ●运行中 ○暂停 ✗破产），减少冗余文字
- **动画克制**：仅在净值曲线刷新和订单成交时使用微动效（淡入/闪烁），不做无意义动画

#### 菜单系统（渐进式显示）

```
默认视图：只显示核心数据 + 底部一小行快捷键提示
   ↓ 按 `Ctrl+P`
弹出命令面板（模糊搜索所有可执行操作）
   ↓ 按 `Alt+M`
展开完整菜单栏（文件 / Session / Agent / 视图 / 工具 / 帮助）
```

| 菜单级别 | 显示方式 | 内容 |
|---|---|---|
| **核心视图**（始终可见） | 主内容区 | 当前选中的页面（Dashboard / Agent 详情等） |
| **迷你提示栏**（始终可见） | 底部 1 行 | 当前页面的 4-6 个最常用快捷键 |
| **命令面板**（`Ctrl+P` 弹出） | 浮层 | 模糊搜索所有操作，类似 VSCode 命令面板 |
| **完整菜单**（`Alt+M` 或 F10 展开） | 顶栏下拉 | 全部分类和操作，鼠标可点击 |
| **上下文菜单**（`Ctrl+Shift+\` 弹出） | 在光标位置弹出 | 针对当前选中元素的操作（如"跳转到交易记录"） |

快捷键分级显示：

- **一级（单键）**：`1`-`0` 切换主页面，`Esc` 返回上一层
- **二级（Ctrl+）**：`Ctrl+E` 导出、`Ctrl+P` 命令面板、`Ctrl+F` 搜索交易记录、`Ctrl+S` 设置
- **三级（Alt+）**：`Alt+M` 菜单、`Alt+1`-`9` 快速切换 Agent
- **四级（不提示）**：高级功能如 `Ctrl+Shift+D` 进入调试模式，在命令面板中可搜索到

#### 交互反馈

- 每项操作（下单成功/失败、数据刷新、校验拒绝）都有明确的视觉反馈（状态条闪烁、图标变化）
- 耗时操作（> 500ms）显示进度条或旋转指示器
- 错误操作（非法输入、越权）有红色高亮 + 底部错误栏 3 秒提示

#### 响应式布局

- 终端宽度 < 80 列：隐藏图表组件，仅保留表格和卡片
- 终端宽度 80-120 列：标准布局，表格 + 1 个图表
- 终端宽度 > 120 列：丰富布局，多图表 + 表格并排
- 终端高度 < 24 行：仅显示摘要卡片，隐藏所有图表

### 13.4 非 TUI 时的后台模式

- 可通过 `--headless` 参数启动，无 TUI 运行
- 输出到文件，适合服务器环境
- 支持通过 REST API（127.0.0.1 仅本地）进行外部脚本控制

---

## 14. REST API

仅本地监听，供 TUI 内部调用和外部脚本集成。

| 端点 | 说明 |
|---|---|
| `GET /api/sessions` | 列出所有 Session |
| `POST /api/sessions` | 创建新 Session |
| `GET /api/sessions/{id}/agents` | 列出 Session 内所有 Agent |
| `POST /api/sessions/{id}/agents` | 添加 Agent |
| `GET /api/sessions/{id}/agents/{id}/equity` | Agent NAV 时间序列 |
| `GET /api/sessions/{id}/agents/{id}/trades` | Agent 交易记录 |
| `POST /api/sessions/{id}/agents/{id}/decision` | 手动触发决策 |
| `GET /api/sessions/{id}/leaderboard` | Session 排行榜 |
| `GET /api/sessions/{id}/benchmark` | Benchmark 对照 |

---

## 15. 边界情况处理

### 15.1 市场数据缺失

- 某日某标的无数据 → 前收价填充，标记 `data_quality: missing`
- 标的停牌 → 前收价估值，拒绝交易
- 多数据源冲突 → 最早数据源优先，记录 conflict

### 15.2 Agent 决策异常

| 异常 | 处理 |
|---|---|
| 请求买入超过上限 | 校验层拒绝，记录 violation |
| 卖出超过持仓 | 校验层拒绝，记录 violation |
| JSON 格式错误 | 降级 HOLD，记录 parse_error |
| 资金归零且不贷款 | 标记 `LIQUIDATED` |
| 回撤超限 | 自动 `PAUSED` |
| LLM API 超时 | 视为 HOLD，记录 timeout |
| LLM 返回空 | 视为 HOLD，记录 empty_response |

### 15.3 节假日与数据断档

- 内置交易日历（美股 / A股 / 加密货币各自独立）
- 加密货币无节假日
- 节假日跳过，不生成 tick

### 15.4 浮点数精度

- 所有资金字段使用 `Decimal`（Python）
- 禁止 `float` 用于金额计算
- 最小单位：加密货币 1e-8，股票 1 股（碎股支持），CNY 0.01
- 期末做 reconcile：总账 = 现金 + 持仓市值 + 贷款余额 + 利息

---

## 16. AI 接入方式

### 16.1 标准接口

```
输入: market_snapshot + agent 当前持仓 + 账户余额 + 贷款信息
输出: 决策 JSON（见 8.2 Schema）
```

### 16.2 Agent — LLM Provider 映射

每个 Agent 在配置中指定 `llm.provider_id`，引用 `config/providers.yaml`：

```yaml
# demo session 的 Agent 配置（体现多 API 竞赛）
agents:
  - id: openai-trader
    name: "GPT-4 Trader"
    llm:
      provider_id: openai-gpt4
      temperature: 0.7

  - id: claude-trader
    name: "Claude Trader"
    llm:
      provider_id: anthropic-claude
      temperature: 0.6

  - id: local-deepseek
    name: "DeepSeek Trader"
    llm:
      provider_id: deepseek
      temperature: 0.8

  - id: momentum-rules
    name: "动量规则引擎"
    llm:  # 不使用外部 API，纯本地规则
      provider_id: local_rules
```

### 16.3 API 配置方式

> 用户只需提供 API Key，程序自动从 models.dev 获取模型列表、端点、上下文长度。  
> 若使用自定义模型（非 models.dev 支持），则手动输入各项参数，TUI 提供清晰的表单引导。

#### 方式一：从 models.dev 自动获取（推荐）

用户在 TUI 配置界面选择 "从 models.dev 添加"，输入 API Key 后，程序：

1. 调用 models.dev API 获取该 Key 可用的模型列表
2. 自动填充每个模型的：
   - 名称和版本
   - API 端点 URL
   - 最大上下文长度
   - 输入/输出价格（每 1M tokens）
   - 建议的 temperature 范围
3. 用户从列表中选择模型即可完成配置

```yaml
# 自动生成结果示例（config/providers.yaml）
llm_providers:
  - id: models-dev-gpt4
    source: models.dev                          # 标记来源
    model_name: gpt-4-turbo
    endpoint: https://api.models.dev/v1         # 自动获取
    context_length: 128000                      # 自动获取
    pricing: { input: 10, output: 30 }          # 自动获取，单位 $/1M tokens
    api_key_env: MODELS_DEV_API_KEY
    user_defined: false                         # 标记非手动输入
```

#### 方式二：自定义模型（手动配置）

TUI 提供表单式配置界面：

| 字段 | 说明 | 校验规则 |
|---|---|---|
| 模型 ID | 唯一标识符 | 必填，字母数字组合 |
| 显示名称 | 下拉列表显示名 | 必填 |
| API 端点 | 完整的 base URL | 必填，URL 格式校验 |
| 模型名称 | 调用的 model 参数 | 必填 |
| 上下文长度 | tokens 上限 | 必填，正整数 |
| API Key 环境变量 | 环境变量名称 | 必填 |
| 输入价格 | 每 1M tokens 价格 | 选填，默认 0 |
| 输出价格 | 每 1M tokens 价格 | 选填，默认 0 |

```yaml
# 手动配置示例
llm_providers:
  - id: my-custom-model
    source: user_defined
    display_name: "我的自定义模型"
    endpoint: https://my-api.example.com/v1
    model_name: my-model-7b
    context_length: 32768
    pricing: { input: 0.5, output: 1.5 }
    api_key_env: MY_CUSTOM_API_KEY
    user_defined: true
```

### 16.4 Provider 插件化

- 实现的 Provider 放在 `agent/providers/` 目录
- 每个 Provider 实现 `LLMProvider` 接口：

```python
class LLMProvider(Protocol):
    async def chat(self, messages: list[dict], temperature: float, max_tokens: int) -> str: ...
```

- 新增 Provider = 新增一个文件 + 注册到 `config/providers.yaml`
- Provider 实现包括：OpenAI、Anthropic、Ollama、OpenAI-compatible（DeepSeek、Groq、models.dev 等）、本地规则引擎

### 16.5 API 用量统计

> 所有 LLM API 调用都记录详细的用量数据，在 TUI 中以图表和表格形式展示。

#### 统计字段

| 字段 | 说明 | 追踪粒度 |
|---|---|---|
| `provider_id` | 使用的 Provider | 每次调用 |
| `model` | 模型名称 | 每次调用 |
| `prompt_tokens` | 输入 tokens 数 | 每次调用 |
| `completion_tokens` | 输出 tokens 数 | 每次调用 |
| `total_tokens` | 总 tokens 数 | 每次调用 |
| `cost_usd` | 该次调用的估算费用 | 从 pricing 表计算 |
| `latency_ms` | 调用耗时 | 每次调用 |
| `decision_round` | 决策轮次 | 每次调用 |
| `agent_id` | Agent 标识 | 每次调用 |
| `status` | 成功/失败/重试 | 每次调用 |

#### 输出

```
results/{session_id}/
├── api_usage/
│   ├── agent_{id}/
│   │   ├── usage_log.csv              # 每行一次 API 调用
│   │   ├── token_consumption.csv       # 每日汇总
│   │   └── cost_breakdown.csv          # 按 Provider × 模型的费用
│   └── summary_{session_id}.json       # 全局统计
```

TUI 通过 `APICostChart` 和 `TokenUsageChart` 组件展示：

- 按日/周/月的 tokens 消耗折线图
- 按 Provider 的费用饼图
- 按 Agent 的 token 使用排名
- 单次调用的延迟散点图（异常值标红）

### 16.6 决策频率控制

- `decision_interval`: `tick` / `1h` / `1d`，默认 `1d`
- `decision_schedule`: `market_open` / `market_close`

---

## 17. AI 上下文管理系统

> 这是整个系统的"大脑皮层"——负责管理 AI 的提示词、上下文窗口、记忆体，确保 AI 不会"失忆"或"迷失方向"。

### 17.1 问题陈述

AI（特别是 LLM）有以下固有限制：

| 问题 | 表现 | 后果 |
|---|---|---|
| **上下文窗口有限** | GPT-4 128K、Claude 200K 仍是有限的 | 运行数月后历史远超窗口大小 |
| **长上下文注意力衰减（Lost in the Middle）** | 中间部分的信息容易被忽略 | AI 忽略关键持仓/市场背景 |
| **角色混淆** | 长时间运行后忘记自己是交易员 | 输出非交易内容或格式错误 |
| **任务漂移** | 提示词被"稀释"，决策质量下降 | 策略一致性被破坏 |

### 17.2 三层上下文架构

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: System Prompt（固定锚点，永不截断）                  │
│  角色定义、行为边界、输出格式 Schema、核心规则                  │
│  长度 ≈ 2000 tokens                                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: Working Context（滑动窗口，最近 N 轮）               │
│  最近 K 次决策 + 反馈 + 余额变化                              │
│  长度 ≈ 4000 tokens                                          │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: Compressed History（压缩摘要，分层总结）              │
│  每日摘要 → 每周摘要 → 每月摘要                               │
│  长度 ≈ 3000 tokens                                          │
└─────────────────────────────────────────────────────────────┘
```

### 17.3 System Prompt（Layer 1）— 不可变锚点

每次决策请求都附带，**永远不会被截断**。包含：

```
你是一名专业的 {风格} 交易员，管理着 {initial_capital} CNY 的虚拟资金。
当前 Session: {session_name}，运行第 {day} 天。

【交易规则】
- 你只能输出标准化 JSON 决策。
- 你可以交易的标的列表：{asset_list}。
- 你的决策频率：每 {interval} 一次。
- 你可以贷款（最多 {max_loans} 次），也可以宣告破产。
- 每次交易都会产生手续费和滑点，引擎会自动处理。

【格式约束】
- 输出必须符合 JSON Schema（见下方）。
- 如果无法决策，输出 {"action": "HOLD"}。
- 不得输出任何非 JSON 内容。

【行为准则】
- 你是一个交易员，不是助手。不要聊天，不要解释市场理论，直接决策。
- 你有自己的交易风格，请保持一致性。
- 如果连续亏损，你可以反思策略，但不要情绪化。
- 你的每一笔交易都影响最终排名。
```

### 17.4 Working Context（Layer 2）— 滑动窗口

保留最近 N 轮的**完整**决策 + 反馈记录：

```
[Round T-4] 决策: BUY AAPL target=0.15
           反馈: FILLED price=178.5 qty=84 cost=15057

[Round T-3] 决策: SELL AAPL target=0
           反馈: FILLED price=182.3 qty=84 revenue=15283
                 PnL: +226 CNY (含手续费、汇率损耗)

[Round T-2] 决策: BUY BTC/USDT target=0.10
           反馈: FILLED price=42050 qty=0.0238

[Round T-1] 决策: HOLD
           反馈: BTC -1.2%, AAPL +0.3%

[Round T]   当前状态 (见市场数据)
```

- N 值动态调整：目标使 Layer 2 ≈ 4000 tokens
- 最新决策完整保留，旧决策被压缩时首条被移动到 Layer 3

### 17.5 Compressed History（Layer 3）— 分层摘要

> **生成方式**：LLM 生成摘要原始文本 → 规则引擎校验 → 校验通过后存入 Layer 3。规则引擎负责剪枝、去重、数据一致性检查，防止 LLM 幻觉污染摘要。

当滑动窗口满时，最旧的决策被提炼为摘要，存入 Layer 3。每条摘要生成后经过规则引擎校验（检查：数据是否与真实交易记录一致、时间戳是否连续、关键字段是否完整），校验不通过则回退为结构化模板摘要。

#### 日摘要格式

```
--- 2024-01-15 摘要 ---
市场：S&P 500 +0.8%, BTC -2.1%
操作：买入 AAPL (成本 15057)，卖出 BTC 一半
NAV 变化：+2.3% (净值 +2300)
关键事件：AAPL 财报超预期跳空上涨
反思：BTC 仓位过高，需降低风险敞口
```

#### 周摘要格式（从 7 条日摘要压缩）

```
--- 第 3 周 (01/15-01/19) 摘要 ---
市场：S&P 500 +1.2%, BTC -4.5%
操作：4 笔买入，2 笔卖出，1 次 HOLD
NAV 变化：+5.8% (累计 +12.3%)
关键事件：AAPL 财报利好，BTC 因 ETF 抛售下跌
策略反思：追涨 BTC 被套，应严格执行止损
总体信用：良好（1 次止损执行到位，0 违规）
```

#### 月摘要格式（从 4-5 条周摘要压缩）

```
--- 1 月总结 ---
市场总览：美股震荡上行 (+3.2%)，BTC 先涨后跌 (-8.1%)
操作统计：15 笔交易，11 赢 4 亏，胜率 73%
NAV 变化：+12.3%，同期 S&P 500 +3.2%
最大回撤：-4.5%（发生在 01/18 BTC 抛售）
Sharpe Ratio：1.8
最大教训：BTC 波动大，仓位需要控制在 10% 以内
```

### 17.6 上下文组装流程

```
每次决策时：

1. 引擎组装 Layer 1 (System Prompt — 从 Agent 配置读取)
2. 从 Agent 记忆中读取 Layer 3 (压缩摘要 — 从文件/DB 读取)
3. 从 Agent 记忆中读取 Layer 2 (滑动窗口 — 从文件/DB 读取)
4. 引擎插入当前状态 (余额、持仓、市场数据、贷款信息)
5. 拼接为完整 prompt，发送给 LLM
6. LLM 返回决策后：
   a. 校验器验证
   b. 引擎执行
   c. 将本轮 (决策 + 反馈) 追加到 Layer 2
   d. 如果 Layer 2 超出阈值 → 压缩最旧条目到 Layer 3
   e. 每日/周/月触发摘要合并
```

### 17.7 Prompt 动态调整机制

根据 Agent 状态自动调整 System Prompt：

| 状态 | Prompt 调整 |
|---|---|
| **连续亏损 3 天** | 追加 "警告：你已连续亏损 3 天。建议审视风险敞口。" |
| **回撤 > 10%** | 追加 "回撤已超过 10%，考虑降低仓位。" |
| **贷款余额 > 0** | 追加 "当前有贷款未还清，利息每日扣减。" |
| **破产边缘 (NAV < 20% initial)** | 追加 "资金紧张。你可以选择贷款或宣告破产。" |
| **已申报破产** | Prompt 替换为破产说明，不再发交易指令 |
| **节假日前** | 追加 "明日为节假日，市场休市。今日持仓以收盘价估值。" |

### 17.8 Session 记忆持久化

```
results/{session_id}/
├── memory/
│   ├── agent_{id}/
│   │   ├── system_prompt.txt        # L1 缓存
│   │   ├── working_context.jsonl     # L2 滑动窗口 (每行一轮)
│   │   ├── summaries/
│   │   │   ├── daily/               # 日摘要
│   │   │   ├── weekly/              # 周摘要
│   │   │   └── monthly/             # 月摘要
│   │   ├── prompt_history.jsonl     # 每次发出的完整 prompt (用于调试)
│   │   └── token_usage.csv          # Token 消耗统计
```

> **关键设计**：所有上下文数据**持久化到磁盘**，会话恢复时从磁盘重建三层上下文，AI 不会因为重启而失忆。

---

## 18. 持久化与容灾

### 18.1 存储架构

```
┌──────────────────────────────────────────────────┐
│                  存储层                            │
├─────────────┬────────────┬──────────────────────┤
│  结构化数据  │  时间序列   │  文件存储             │
│  SQLite     │  CSV/Parq  │  JSON / YAML         │
│  - 账户     │  - 净值曲线 │  - 配置               │
│  - 订单     │  - 日 P&L  │  - 市场数据缓存        │
│  - 持仓     │  - 交易记录 │  - Session 导出       │
│  - 贷款     │            │  - Agent 记忆          │
│  - Agent    │            │                      │
└─────────────┴────────────┴──────────────────────┘
```

### 18.2 SQLite 策略（核心数据）

| 特性 | 实现 | 说明 |
|---|---|---|
| **WAL 模式 (Write-Ahead Logging)** | `PRAGMA journal_mode=WAL;` | 读不阻塞写，断电恢复不丢数据 |
| **同步提交** | `PRAGMA synchronous=FULL;` | 每次提交等待数据落盘，防止断电丢数据 |
| **事务封装** | 每笔订单/每次结算为单个事务 | 部分失败自动回滚，保持一致性 |
| **定期 CHECKPOINT** | 每 1000 笔交易执行 `PRAGMA wal_checkpoint;` | 防止 WAL 文件无限增长 |
| **自动恢复** | SQLite 自动运行恢复流程 | 启动时检测并修复不完整事务 |

### 18.3 容灾机制

#### 18.3.1 检查点系统

```
内存状态 → 每 10 秒写检查点 → 检查点文件
   ↓ (进程崩溃)
启动时检测最近的检查点 → 从检查点恢复 → 回放未完成的订单
```

- 引擎每隔 `checkpoint_interval` 序列化一次全状态到临时文件
  - 增量检查点：默认每 **10 秒**（只保存变更，轻量）
  - 全量检查点：默认每 **60 秒**（保存完整状态快照，校验用）
  - 两个间隔均可在 `config/persistence.yaml` 中由用户调整
- 正常退出时写 `CHECKPOINT_OK` 标记
- 启动时检测：
  - 无标记 → 最后检查点恢复
  - 有标记 → 正常启动

#### 18.3.2 幂等性保证

- 每笔订单有唯一 `order_id` (UUID)
- 如果引擎崩溃后恢复，重放时检测 `order_id` 是否已存在
- 已存在的订单跳过，保证不重复执行

#### 18.3.3 数据完整性校验

```
启动时运行：
1. 总账校验：∑现金 + ∑持仓市值 + ∑贷款余额 = NAV
2. 订单连续性：order_id 序列无跳空
3. 时间戳单调性：时间戳严格递增
4. 手续费一致性：交易记录中的手续费金额 = 当日 fee 日志汇总
```

#### 18.3.4 崩溃场景对照表

| 场景 | 影响 | 恢复方式 |
|---|---|---|
| 进程崩溃 (SIGKILL/SIGSEGV) | 丢失最近 5 秒状态 | 从上一个检查点恢复 + 回放 |
| 断电 | 同上 | WAL 模式自动恢复未完成事务 |
| 磁盘满 | 写入失败 → 引擎暂停 | 弹窗提示 + 等待空间释放后继续 |
| 数据文件损坏 | SQLite 检测到 corruption | 从最近检查点重建 + 报警 |
| AI API 超时 | 单次决策失败 | 降级 HOLD，跳过该轮 |
| 网络断连 (数据源) | 数据缺失 | 使用缓存数据 + 标记 `stale` |
| 内存 OOM | 进程被 kill | 检查点恢复 + 内存限制告警 |

### 18.4 启动与关闭协议

```python
# 启动序列
1. 检查上次退出标记 (graceful_shutdown / crash / first_run)
2. 如果是 crash → 扫描 data/ 和 results/ 完整性
3. 加载最近检查点
4. 回放未完成的 tick
5. 重新构建 Agent 三层上下文 (L1+L2+L3)
6. Agent 恢复运行（状态 = 崩溃前的快照状态）

# 关闭序列
1. 完成当前 tick（不中断正在执行的订单）
2. 写入 CHECKPOINT_OK 标记
3. 刷新所有缓存到磁盘
4. 关闭文件句柄
5. 退出
```

### 18.5 备份策略

- 每次 Session 结束后自动压缩为 `{session_id}.tar.gz`（含 SQLite + 时间序列 + 记忆）
- 配置 `config/backup.yaml` 控制保留版本数（默认保留最近 5 个 Session）

---

## 19. 技术栈建议

| 层级 | 推荐技术 | 理由 |
|---|---|---|
| 核心引擎 | Python 3.11+ | 数值计算、AI 生态、数据科学库丰富 |
| 数据采集 | yfinance / CCXT / AKShare | 成熟免费库，社区活跃 |
| 精度计算 | `decimal.Decimal` | 防止浮点误差，银行级精度 |
| TUI 框架 | **Textual** 2.0+ | Python 原生 TUI，组件丰富，支持鼠标 |
| 图表 | Rich + Textual-plotext + Plotext | TUI 内折线图、柱状图、散点图、饼图 |
| 状态存储 | SQLite (WAL 模式) | 零依赖嵌入式，ACID 合规，支持断电恢复 |
| 数据序列化 | JSON + CSV + Parquet | JSON 用于快照，CSV 用于导出，Parquet 用于分析 |
| Web API | FastAPI | 轻量、自动文档 |
| 容器化 | Docker + Compose | 一键启动 |
| 异步 | asyncio + anyio | 非阻塞 IO，高并发 Agent 调用 |
| 测试 | pytest + hypothesis + coverage | 确定性测试 + 随机测试 + 覆盖率 |

---

## 20. 项目里程碑

### Phase 1 — MVP（4–6 周）

- [ ] 数据层：Yahoo Finance + Binance (CCXT) 双源，日线/1h 线
- [ ] 引擎核心：订单生命周期、手续费模型、CNY ↔ USD 汇率损耗
- [ ] 校验层：标的代码校验、JSON Schema 校验、基础风控
- [ ] 账户：CNY 初始资金，双币种内部管理
- [ ] Agent：单 Agent，支持本地规则 + LLM API（OpenAI / Claude）
- [ ] 上下文管理：L1 System Prompt + L2 滑动窗口 + L3 压缩摘要
- [ ] Prompt 动态调整：根据状态自动追加指令
- [ ] 持久化：SQLite WAL + 检查点系统 + 崩溃恢复
- [ ] Agent 配置化：每个 Agent 独立配置 LLM provider
- [ ] 追踪：净值曲线、交易记录、Sharpe / MaxDD
- [ ] 贷款机制：AI 自主决定贷款/破产
- [ ] TUI Dashboard：净值曲线 + 持仓 + 交易记录（基本信息）
- [ ] TUI Leaderboard：单 Session 排行榜
- [ ] 配置文件驱动：手续费、汇率、Provider 全部外部配置

### Phase 2 — 扩展（3–4 周）

- [ ] 多 Agent 并行 + 完整排行榜
- [ ] A股数据接入（AKShare）
- [ ] 外汇汇率实时更新
- [ ] 止损单 / 限价单
- [ ] TUI Session 创建向导
- [ ] TUI Benchmark 对照页面
- [ ] 全量统计图表：DrawdownChart、DailyPnlBar、AssetAllocation、ScatterPlot
- [ ] 上下文管理优化：摘要压缩算法调优、Token 消耗监控
- [ ] 风险控制硬闸（完整）
- [ ] 前视偏差防护验证
- [ ] 回测加速（10x / 100x）

### Phase 3 — 高级（4–6 周）

- [ ] 分钟级回测，tick 级数据
- [ ] 多因子 / ML Agent
- [ ] 情绪/新闻数据接入
- [ ] VaR / Stress Test
- [ ] 策略优化框架（参数扫描 + walk-forward）
- [ ] 实时模式
- [ ] LangChain ReAct 集成

---

## 21. 测试策略

### 21.1 确定性测试

- 同一历史数据 + 同一策略 → 结果完全一致
- 固定随机种子，滑点取统计中位数
- SQLite 事务保证原子性

### 21.2 单元测试范围

| 模块 | 测试重点 |
|---|---|
| 手续费计算 | 多币种、精度验证 |
| 汇率换算 | CNY→USD→CNY 来回链路损耗累积 |
| 仓位计算 | target_pct → 精确数量，A股整百股取整 |
| 风控规则 | 校验层逐条验证 |
| 贷款核算 | 利息计算、自主贷款、破产结算 |
| 结算逻辑 | T+1 资金可用性 |
| 校验器 | 非法标的、格式错误、仓位超额 |
| 上下文管理 | 窗口裁剪、摘要压缩、prompt 组装 |
| 持久化 | 检查点恢复、崩溃重放、幂等性 |

### 21.3 集成测试

- 小数据集全流程（7 天，3 个标的，2 个 Agent），与预期结果对比
- 分拆股 / 分红 / 停牌场景验证
- 贷款 + 破产 + 恢复全链路
- 断电恢复测试（kill -9 → 重启 → 状态一致）

---

## 22. 项目目录结构

```
ai-virtual-finance/
├── src/
│   ├── data/                 # 数据采集层
│   │   ├── providers/        # YahooFinance / Binance / AKShare 实现
│   │   ├── calendar/         # 交易日历
│   │   └── cache/            # 本地数据缓存
│   ├── engine/               # 交易引擎层
│   │   ├── order/            # 订单管理与匹配
│   │   ├── portfolio/        # 持仓管理
│   │   ├── fee/              # 手续费模型
│   │   ├── settlement/       # 结算与汇率换算
│   │   └── market/           # 市场状态管理
│   ├── validator/            # 输入校验层
│   │   ├── rules/            # 校验规则（标的/订单/风控/格式）
│   │   └── schema.py         # JSON Schema 定义
│   ├── loan/                 # 贷款模块
│   │   ├── manager.py        # 贷款管理
│   │   ├── interest.py       # 利息计算
│   │   ├── repay.py          # 还款逻辑
│   │   └── recovery.py       # 破产恢复
│   ├── agent/                # Agent 层
│   │   ├── base.py           # Agent 基类
│   │   ├── providers/        # LLM Provider 实现
│   │   │   ├── openai.py
│   │   │   ├── anthropic.py
│   │   │   ├── ollama.py
│   │   │   └── rules_engine.py
│   │   ├── context/          # 上下文管理系统 (§17)
│   │   │   ├── manager.py    # 三层上下文组装
│   │   │   ├── summarizer.py # 摘要压缩引擎
│   │   │   ├── prompt_builder.py  # 动态 Prompt 构建
│   │   │   └── memory_store.py    # 记忆持久化
│   │   └── leaderboard/      # 排行榜
│   ├── analytics/            # 分析层
│   │   ├── metrics.py        # KPI 计算
│   │   ├── benchmark.py      # Benchmark 策略
│   │   └── exports.py        # CSV/JSON 导出
│   ├── persistence/          # 持久化与容灾 (§18)
│   │   ├── checkpoint.py     # 检查点管理
│   │   ├── recovery.py       # 崩溃恢复
│   │   ├── integrity.py      # 数据完整性校验
│   │   └── backup.py         # Session 备份
│   ├── tui/                  # TUI 界面层（主要交互）
│   │   ├── screens/          # Textual Screen 定义
│   │   │   ├── dashboard.py
│   │   │   ├── session_detail.py
│   │   │   ├── agent_detail.py
│   │   │   ├── leaderboard.py
│   │   │   ├── create_session.py
│   │   │   ├── trade_log.py
│   │   │   ├── benchmark.py
│   │   │   ├── settings.py
│   │   │   └── log_viewer.py
│   │   ├── widgets/          # 自定义组件 (含 13.2 全部图表)
│   │   │   ├── equity_chart.py
│   │   │   ├── drawdown_chart.py
│   │   │   ├── daily_pnl_bar.py
│   │   │   ├── scatter_plot.py
│   │   │   ├── allocation_chart.py
│   │   │   ├── win_loss_pie.py
│   │   │   ├── position_table.py
│   │   │   ├── order_log.py
│   │   │   ├── loan_ledger.py
│   │   │   └── kpi_cards.py
│   │   └── app.py            # 应用入口
│   ├── config/               # 配置加载器
│   │   └── loader.py
│   └── main.py               # 入口（启动 TUI 或 headless）
├── config/                   # 外部配置文件
│   ├── fee_schedule.yaml     # 手续费配置
│   ├── providers.yaml        # Provider 注册
│   ├── context.yaml          # 上下文管理参数
│   ├── persistence.yaml      # 持久化与检查点配置
│   └── agents/               # Agent 模板
├── data/                     # 缓存市场数据 (gitignored)
├── results/                  # Session 导出结果 (gitignored)
├── tests/
│   ├── test_engine/
│   ├── test_validator/
│   ├── test_loan/
│   ├── test_agent/
│   ├── test_context/
│   ├── test_persistence/
│   └── test_integration/
├── docker-compose.yml
└── spec.md                   # 本文件
```

---

## 23. 安全规范

### 23.1 API Key 管理

| 要求 | 说明 |
|---|---|
| **禁止硬编码** | API Key 不得出现在源代码中 |
| **环境变量注入** | 通过 `FINANCE_API_KEYS` 或单独的环境变量传递 |
| **secrets.yaml** | 敏感配置存放在 `config/secrets.yaml`（已 gitignore） |
| **日志脱敏** | 日志中自动替换 API Key 为 `***REDACTED***` |

```bash
# 推荐方式：环境变量
export OPENAI_API_KEY="sk-xxx"
export ANTHROPIC_API_KEY="sk-ant-xxx"

# 或使用 secrets.yaml
# config/secrets.yaml（不要提交到 Git）
api_keys:
  openai: "${OPENAI_API_KEY}"
  anthropic: "${ANTHROPIC_API_KEY}"
```

### 23.2 日志安全

```python
# src/utils/redact.py
SENSITIVE_PATTERNS = [
    (r'sk-[a-zA-Z0-9]{20,}', 'sk-***REDACTED***'),
    (r'sk-ant-[a-zA-Z0-9]{20,}', 'sk-ant-***REDACTED***'),
    (r'"api_key":\s*"[^"]+"', '"api_key": "***REDACTED***"'),
]

def redact_sensitive(text: str) -> str:
    """脱敏敏感信息"""
    for pattern, replacement in SENSITIVE_PATTERNS:
        text = re.sub(pattern, replacement, text)
    return text
```

### 23.3 网络安全

| 要求 | 说明 |
|---|---|
| **仅本地监听** | REST API 只绑定 `127.0.0.1`，不暴露到外网 |
| **无认证** | 本地使用，无需认证机制 |
| **HTTPS 禁止** | 本地 HTTP 即可，避免证书管理复杂性 |

### 23.4 数据安全

| 数据类型 | 存储位置 | 保护措施 |
|---|---|---|
| API Key | 环境变量 / secrets.yaml | gitignore，日志脱敏 |
| 交易数据 | SQLite (WAL) | 本地存储，不传输 |
| Agent 记忆 | results/{session}/ | 本地存储，可加密备份 |
| 配置文件 | config/*.yaml | 模板提交，实际文件 gitignore |

### 23.5 容器安全

```yaml
# docker-compose.yml 安全配置
services:
  finance-engine:
    # 只读文件系统（可选）
    read_only: true
    tmpfs:
      - /tmp
    
    # 非 root 用户
    user: "1000:1000"
    
    # 安全选项
    security_opt:
      - no-new-privileges:true
    
    # 资源限制
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
```

### 23.6 安全检查清单

```
□ API Key 未硬编码在代码中
□ secrets.yaml 已添加到 .gitignore
□ 日志输出已脱敏
□ REST API 仅监听 127.0.0.1
□ 容器以非 root 用户运行
□ 敏感文件权限正确（600）
□ 定期轮换 API Key
```

---

## 24. 性能约束

### 24.1 响应时间要求

| 操作 | 目标延迟 | 最大延迟 |
|---|---|---|
| 单次 Agent 决策 | < 5s | < 30s |
| TUI 页面切换 | < 100ms | < 500ms |
| 数据库查询（单表） | < 10ms | < 100ms |
| 市场数据获取（缓存命中） | < 50ms | < 200ms |
| 市场数据获取（网络请求） | < 2s | < 10s |
| 检查点写入 | < 100ms | < 500ms |

### 24.2 吞吐量要求

| 指标 | 目标值 |
|---|---|
| 并发 Agent 数 | ≤ 10 |
| 每日最大交易数 | ≤ 1000 笔/Agent |
| 数据库写入 QPS | ≤ 100 |
| API 请求 QPS | ≤ 10 |

### 24.3 资源限制

| 资源 | 最小值 | 推荐值 | 最大值 |
|---|---|---|---|
| CPU | 2 核 | 4 核 | 8 核 |
| 内存 | 4 GB | 8 GB | 16 GB |
| 磁盘 | 10 GB | 50 GB | 500 GB |
| 数据库大小 | - | < 1 GB | < 10 GB |

### 24.4 数据规模约束

| 数据类型 | 单 Session 上限 | 说明 |
|---|---|---|
| Agent 数量 | 10 | 并行运行 |
| 标的数量 | 20 | 资产池 |
| 交易记录 | 100,000 条 | 约 3 年日线 |
| 净值曲线点数 | 1,000 点 | 约 3 年日线 |
| L2 上下文条目 | 50 条 | 滑动窗口 |
| L3 摘要条目 | 100 条 | 日/周/月摘要 |

### 24.5 性能优化策略

#### 数据库优化

```sql
-- 启用 WAL 模式
PRAGMA journal_mode=WAL;

-- 设置缓存大小（负数表示 KB）
PRAGMA cache_size=-64000;  -- 64MB

-- 同步模式
PRAGMA synchronous=FULL;

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_orders_agent_id ON orders(agent_id);
CREATE INDEX IF NOT EXISTS idx_orders_timestamp ON orders(timestamp);
CREATE INDEX IF NOT EXISTS idx_fills_order_id ON fills(order_id);
```

#### 内存优化

```yaml
# config/persistence.yaml
database:
  cache_size: -64000  # 64MB 缓存
  
checkpoints:
  incremental_interval: 10  # 更频繁的检查点减少内存压力
  full_interval: 60
```

#### 并发优化

```python
# 多 Agent 并行配置
MAX_CONCURRENT_AGENTS = 4
AGENT_TIMEOUT = 30  # 秒
AGENT_RETRY_COUNT = 2
```

### 24.6 性能监控

```bash
# 容器资源使用
docker stats finance-engine

# 数据库大小
du -h data/finance.db

# 查询性能分析
sqlite3 data/finance.db "EXPLAIN QUERY PLAN SELECT * FROM orders WHERE agent_id = 'xxx'"

# 内存使用
ps aux | grep python
```

### 24.7 性能测试要求

| 测试类型 | 要求 |
|---|---|
| 单元测试 | 每个函数 < 100ms |
| 集成测试 | 7 天回测 < 60s |
| 压力测试 | 10 Agent 并行稳定运行 |
| 内存泄漏测试 | 运行 24 小时内存稳定 |

---

## 25. 开发约定

### 25.1 编码约定

- 所有金额字段 `Decimal`，禁止 `float`
- 所有时间戳 UTC，展示转本地时区
- 每笔操作写 `audit_log`，不丢弃任何拒绝记录
- 配置独立文件 `config/*.yaml`，运行时动态加载，不改代码
- 每个模块暴露 `Protocol` 接口，允许替换实现

### 25.2 模块边界规则

- `agent/` 不导入 `engine/`、`data/`、`validator/`、`loan/`
- `engine/` 导入 `validator/`、`loan/`、`agent/`（引擎驱动它们）
- `tui/` 导入 `engine/`、`agent/`、`analytics/`
- `persistence/` 被 `engine/`、`agent/` 依赖
- `agent/context/` 仅被 `agent/` 内部使用，对外暴露 `ContextManager` 接口
- 配置(`config/`)是所有模块的唯一数据依赖来源

### 25.3 数据隔离

- `data/` 按 `symbol/granularity` 分目录缓存
- Session 结果 `results/{session_id}/` 独立隔离
- 不同 Agent 文件严格分离（包括记忆文件）
- 敏感数据（API Key）仅从环境变量读取，不进代码库

### 25.4 及时调试与代码检查

> **原则**：写完一行就要知道这行对不对，不要攒一堆再回头查。

#### 调试节奏（推荐循环）

```
改 3-5 行代码 → 保存 → LSP 诊断（类型错误/语法错误）
    → 通过？→ 跑相关模块的测试 → 通过？→ 提交
    → 不通过？→ 立刻修复，不继续往下写
```

每次循环不超过 5 分钟。如果超过 5 分钟还没通过，说明改动太大了，拆小。

#### 各阶段的调试手段

| 阶段 | 调试方式 | 工具/命令 |
|---|---|---|
| **编码阶段** | LSP 实时诊断 | mypy (类型检查)、ruff (lint + format) |
| **单元测试阶段** | pytest 快速反馈 | `pytest tests/test_{module}/ -x --tb=short`（失败即停） |
| **逻辑验证阶段** | REPL / 交互式调试 | `poetry run python -c "from engine.fee import ...; print(...)"` |
| **集成阶段** | dry-run 模式 | `poetry run python -m src --dry-run`（不调 LLM，用规则引擎） |
| **数据流调试** | JSON 日志 | 每笔关键操作写 `audit_log.jsonl`，`tail -f` 实时观察 |
| **UI 调试** | Textual DevTools | 按 `Ctrl+D` 打开 Textual 开发者工具（检查布局、样式） |

#### 代码检查清单（提交前逐项过）

```
□ ruff check src/     → 零 warning
□ mypy src/           → 零类型错误（strict 模式）
□ pytest tests/       → 全量通过
□ git diff --check    → 没有空白错误、没有 debug print 残留
□ 搜索 print() 确认没有调试 print 残留
□ 金额运算确认使用 Decimal（搜索 float 关键词，排查遗漏）
```

#### 日志驱动调试

- 所有 `WARN` 级别及以上的日志必须写 `audit_log`，不可静默吞掉
- 开发期间 `INFO` 日志记录每次函数进出（`@log_entry_exit` 装饰器），上线后可关闭
- 数据层调试加 `data_quality` 标注，不丢不掩

---

## 26. 成本估算

### 26.1 预估费用

| 费用项 | 说明 |
|---|---|
| 市场数据 API | 免费层，¥0 |
| LLM API 调用 | **不计入虚拟交易成本**，由平台承担。估算：每个 Agent 每日 1 次决策，30 个 Agent × 90 天 × ¥0.04 ≈ ¥108 |
| 服务器 | 本地运行，¥0 |
| **总成本（小规模）** | **约 ¥100–200/月**（仅 LLM API 费用） |

### 26.2 费用归属

> **重要**：LLM API 产生的所有费用**从平台（开发者）支出**，**绝不从虚拟账户扣减**。AI 看到的虚拟资金余额 = 它的交易资金。如果 AI 账户有钱，那是它"赚"的，不是给它交 API 费用的。

---

## 27. 已知风险与假设

| # | 风险 | 缓解措施 |
|---|---|---|
| R1 | 免费 API 限速/限次数 | 缓存 + 多源 fallback |
| R2 | Yahoo Finance 日线包含前复权/后复权不稳定 | 数据层统一做前复权处理 |
| R3 | LLM 输出不稳定 → Agent 行为不可复现 | JSON Schema 校验 + fallback HOLD + 固定 temperature |
| R4 | 回测过拟合 | 固定 train/test split + walk-forward |
| R5 | 前视偏差 | 引擎层擦除未来数据 |
| R6 | 破产/贷款循环导致 NAV 无限负值 | 最大贷款次数硬限制 + NAV < -2x initial 强制清盘 |
| R7 | 汇率数据延迟更新 | 使用昨日汇率，标注 `rate_stale` |
| R8 | 浮点精度 | Decimal + 期末 reconcile rounding |
| R9 | Agent 通过 API 调用泄露资金数据 | 沙箱隔离，Agent 仅能通过引擎定义接口获取信息 |
| R10 | 上下文窗口溢出导致 AI 失忆 | 三层上下文架构 + 压缩 + 摘要 |
| R11 | 断电导致数据不一致 | WAL 模式 + 检查点 + 启动时完整性校验 |
| R12 | 长周期回测中 Prompt 偏移 | 每日动态调整 + Token 消耗监控告警 |

---

## 28. 开放问题（需团队讨论）

| # | 问题 | 待决策 |
|---|---|---|
| Q1 | 同个 Session 内的 Agent 看到的汇率和手续费是否完全一样？ | 建议统一全局配置，确保公平比较 |
| Q2 | 美股分红是否需要预扣税 (30% withholding tax)？ | 建议 P1 忽略，P2 加上 |
| Q3 | 上下文管理中日/周/月摘要由谁生成？LLM 还是规则引擎？ | 建议 LLM 生成（更灵活），规则引擎校验（防幻觉） |
| Q4 | 是否支持 Agent "认输"提前结束？ | 已支持（DECLARE_BANKRUPTCY），记录 liquidation_reason |
| Q5 | 同一 Session 不同 Agent 是否可以使用不同的初始资金？ | 建议允许，leaderboard 按收益率百分比排名 |
| Q6 | TUI 中图表使用 Braille 点阵还是半图形块？ | 建议先用 Textual-plotext，后续优化 |
| Q7 | 检查点频率多少合适？ | 建议 5 秒写入、30 秒全量 checkpoint，可通过配置调整 |
| Q8 | 是否需要支持多台机器分布式运行？ | P3 讨论，P1/P2 单机 |

---

## 29. 快速上手

```bash
pip install -r requirements.txt

# 创建 Session（交互式 / 命令行）
finance create --name "demo" --start 2024-01-01 --end 2024-06-30

# 添加 Agent（支持向导式配置）
finance agent add --session demo --template momentum

# 启动 TUI
finance run --session demo

# 无头模式（输出到文件）
finance run --session demo --headless --speed 10x --output ./results
```

---

*本文档由 AI Virtual Finance 项目团队维护，变更需 PR + 1 位 Reviewer 批准。*
