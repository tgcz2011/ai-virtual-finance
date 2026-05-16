# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [Unreleased]

### Added

- DEPLOYMENT.md - 完整部署指南（本地/Docker/生产环境）
- API.md - REST API 文档
- TROUBLESHOOTING.md - 故障排查指南
- spec.md 目录导航
- spec.md 安全章节（API Key 管理、日志脱敏）
- spec.md 性能约束章节
- CONTRIBUTING.md Git 提交消息规范
- CONTRIBUTING.md 代码风格指南

### Changed

- TASK.md 任务顺序调整：从 deployment 开始
- ARCHITECTURE.md 修复代码示例截断问题
- ARCHITECTURE.md 添加错误处理流程图

---

## [0.1.0] - 2024-XX-XX

### Added

#### 数据层 (Phase 1)

- `MarketDataProvider` Protocol 定义
- `Ohlcv` 和 `MarketData` 数据类
- Yahoo Finance 数据源实现 (`YahooFinanceProvider`)
- Binance 加密货币数据源实现 (`BinanceProvider`)
- 交易日历（美股 + 加密货币）
- 市场数据缓存（SQLite + TTL）

#### 交易引擎 (Phase 1)

- 订单生命周期管理（`OrderManager`）
- 持仓管理（`PortfolioManager`）
- 手续费计算模型（`FeeCalculator`）
- 汇率损耗模拟（银行买卖价差）
- 美股分红预扣税（30%）
- T+1 结算机制
- 市场状态管理（`MarketStateManager`）

#### 校验层 (Phase 1)

- 校验框架（`ValidatorChain`）
- JSON Schema 校验规则
- 标的校验规则
- 交易时间校验规则
- 风控校验规则（仓位限制、资金充足性）

#### 贷款模块 (Phase 1)

- 贷款管理器（`LoanManager`）
- 自适应利率计算
- 破产清算流程

#### 上下文管理 (Phase 1)

- L1 System Prompt 模板
- L2 滑动窗口
- L3 压缩摘要（LLM + 规则引擎校验）
- 动态 Prompt 调整

#### Agent 层 (Phase 1)

- Agent 基类与状态机
- LLM Provider（OpenAI / Anthropic / Ollama）
- models.dev 自动配置
- 本地规则引擎策略
- 多维度排行榜
- API 用量统计

#### 性能追踪 (Phase 1)

- KPI 计算（Return / Sharpe / MaxDD / WinRate）
- 时间序列导出（CSV/JSON）
- Benchmark 策略（Buy & Hold / DCA）

#### 持久化 (Phase 1)

- SQLite Schema（WAL 模式）
- 增量/全量检查点
- 断电恢复机制
- Session 备份

#### TUI 界面 (Phase 1)

- TUI 骨架（Textual App）
- Dashboard 页面
- Session 管理页面
- Agent 详情页面
- 排行榜页面
- 图表组件（Braille + 半图形块）
- 设置页面
- 辅助功能（日志、交易记录、Benchmark）

#### 集成测试 (Phase 1)

- 端到端集成测试
- 确定性验证（固定随机种子）
- 断电恢复测试

### Documentation

- spec.md - 系统规格说明
- ARCHITECTURE.md - 架构指南
- TASK.md - 任务分解
- CONTRIBUTING.md - 协作指南

---

## [0.2.0] - TBD

### Added

- AKShare A 股数据源
- 限价单 / 止损单订单类型
- 做空机制（融券/借币）
- A 股市场规则（涨跌停、100 股起买）
- 外汇汇率实时更新
- 多 Agent 并行执行引擎
- 摘要质量评分
- 扩展 KPI（Calmar / Sortino / VaR）
- 前视偏差自动化检测
- 回测加速（10x/100x）

---

## [0.3.0] - TBD

### Added

- 分钟级回测（tick 级数据）
- 情绪/新闻数据接入
- LangChain / ReAct 框架集成
- 策略优化框架（参数扫描）
- Stress Test（极端行情模拟）
- 实时模式（定时 tick）

---

## [1.0.0] - TBD

### Added

- 所有 Phase 完成
- API 稳定
- 完整文档
- 生产就绪

---

## Version History

| Version | Date | Milestone |
|---|---|---|
| v0.1.0 | TBD | Phase 1 MVP 完成 |
| v0.2.0 | TBD | Phase 2 功能 |
| v0.3.0 | TBD | Phase 3 功能 |
| v1.0.0 | TBD | 正式发布 |

---

## Release Notes Template

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- 新功能

### Changed
- 功能变更

### Deprecated
- 即将移除的功能

### Removed
- 已移除的功能

### Fixed
- Bug 修复

### Security
- 安全相关修复
```
