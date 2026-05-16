# AI Virtual Finance — Contributing Guide

> **目标读者**：项目团队成员  
> **读完本文你应该能回答**：怎么搭建开发环境？PR 流程是什么？代码怎么 review？spec 改了谁负责？

---

## 1. 开发环境

### 1.1 核心原则：环境隔离

> **这个项目的依赖和其他项目完全隔离**，不得污染系统的 Python 环境，也不得被其他项目污染。  
> 所有依赖安装在项目自己的虚拟环境中，离开项目目录不产生任何影响。

### 1.2 前置要求

| 工具 | 版本 | 用途 |
|---|---|---|
| Python | ≥ 3.11 | 核心语言 |
| Poetry | ≥ 1.7 | **推荐的依赖管理工具**，自动创建隔离虚拟环境 |
| Git | ≥ 2.40 | 版本控制 |
| SQLite | ≥ 3.40 | 嵌入式数据库（通常系统自带） |
| GitHub CLI (gh) | ≥ 2.40 | 仓库管理、PR 操作 |

> 没有 Poetry？先装：`pip install poetry`（仅此一条命令装到系统级，其他的全进虚拟环境）

### 1.3 隔离机制说明

| 机制 | 效果 |
|---|---|
| `poetry install` | 在项目目录下创建 `.venv/`，所有依赖装在里面 |
| `poetry shell` 或 `poetry run` | 自动激活/使用隔离的虚拟环境 |
| `pyproject.toml` | 锁定依赖版本，精确可复现 |
| `poetry.lock` | 锁定传递依赖，每次安装完全一致 |

> 如需使用 pip 替代 Poetry，请先 `python -m venv .venv` 创建虚拟环境，然后 `source .venv/bin/activate` 激活，再 `pip install -r requirements.txt`。

### 1.4 首次搭建

```bash
# 克隆
git clone <repo-url>
cd ai-virtual-finance

# 安装依赖（自动创建隔离虚拟环境 .venv/）
poetry install
# 或: pip install -r requirements.txt（需先 python -m venv .venv && source .venv/bin/activate）

# 复制配置模板
cp config/fee_schedule.yaml.example config/fee_schedule.yaml
cp config/providers.yaml.example config/providers.yaml

# 设置 API Key（可选，部分数据源不需要 Key）
export FINANCE_API_KEYS='{"models_dev": "your-key-here"}'

# 验证隔离生效：下面的命令应该在 .venv 内执行
poetry run pytest

# 启动 TUI
poetry run python -m src

# （可选）激活虚拟环境进入交互模式
poetry shell
# 退出: exit
```

### 1.5 依赖管理规则

- 核心协议（`data/`、`engine/`、`agent/` 的基础接口）：**不允许引入第三方库**
- 实现层（具体 Provider 等）：按需引入，在 `pyproject.toml` 的 `[tool.poetry.extras]` 中标记 optional
- TUI 层：可以引入 Textual 及插件，但需要评估体积
- 数据分析（analytics/）：可以引入 numpy/pandas，但尽量避免

### 1.6 代码检查工具配置

```toml
# pyproject.toml 中配置

[tool.ruff]
target-version = "py311"
line-length = 120
select = ["E", "F", "I", "N", "W", "UP", "ANN", "B", "C4", "SIM"]
ignore = ["ANN101"]  # self 参数不需要类型注解

[tool.mypy]
strict = true
python_version = "3.11"
disallow_untyped_defs = true
warn_return_any = true
no_implicit_optional = true

[tool.pytest.ini_options]
addopts = "--strict-markers --randomly-seed=42 -x --tb=short"
testpaths = ["tests"]
```

```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.3.0
    hooks:
      - id: ruff
        args: [--fix, --exit-zero]
      - id: ruff-format
  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.8.0
    hooks:
      - id: mypy
        args: [--strict]
        additional_dependencies: [pydantic]
  - repo: local
    hooks:
      - id: debug-print-check
        name: Check for debug print statements
        entry: bash -c '! grep -rn "print(" src/ --include="*.py" | grep -v "__init__"'
        language: system
        stages: [commit]
      - id: float-check
        name: Check for float in financial calculations
        entry: bash -c '! grep -rn "float" src/engine/ src/loan/ --include="*.py"'
        language: system
        stages: [commit]
```

安装 pre-commit 后，每次 `git commit` 自动跑检查，不通过不能提交。

---

## 2. 分支策略

```
main                ← 稳定版本，只合入已 review 的 PR
  ├─ feat/xxx       ← 新功能（如 feat/data-alphavantage-provider）
  ├─ fix/xxx        ← 修 bug（如 fix/fee-division-by-zero）
  ├─ refactor/xxx   ← 重构（如 refactor/validator-chain）
  └─ docs/xxx       ← 文档（如 docs/add-context-diagram）
```

- **禁止**直接推 `main`。所有变更通过 PR。
- 分支名小写 + 连字符，前缀标明类型。
- 一个分支只做一件事。

---

## 3. PR 流程

### 3.1 提交流程

```bash
# 1. 从最新的 main 拉分支
git checkout main
git pull
git checkout -b feat/my-feature

# 2. 实现代码 + 测试
#    ... 写代码 ...

# 3. 本地验证
pytest tests/          # 全量测试通过
python -m src --dry-run # 引擎 dry-run 验证

# 4. 提交
git add -A
git commit -m "feat: 添加 Alpha Vantage 数据源提供商"
git push origin feat/my-feature

# 5. 创建 PR (GitHub / GitLab)
```

### 3.2 PR 模板

```markdown
## 变更内容
<一句话描述>

## 关联模块
- [ ] data/providers
- [ ] engine
- [ ] validator
- [ ] loan
- [ ] agent
- [ ] analytics
- [ ] tui
- [ ] persistence
- [ ] config
- [ ] docs

## 测试覆盖
- [ ] 单元测试已添加/更新
- [ ] 集成测试通过
- [ ] 手动验证（描述验证步骤）

## 代码检查（提交前必须过）
- [ ] `ruff check src/ --fix` 零 warning
- [ ] `mypy src/ --strict` 零类型错误
- [ ] `pytest tests/ -x --tb=short` 全部通过
- [ ] `git diff --check` 无空白错误
- [ ] 已搜索并清理调试用 `print()` 残留
- [ ] 金额运算使用 `Decimal`（`grep float src/engine/ src/loan/` 无意外结果）

## 破坏性变更
- [ ] 无
- [ ] 有（描述兼容性处理）

## 对应 spec 章节
<填写此 PR 涉及 spec.md 的章节号>

## 检查清单
- [ ] 不使用 float 计算金额
- [ ] Protocol 接口未破坏
- [ ] 配置向后兼容
- [ ] audit_log 有相应记录
```

### 3.3 Review 要求

| 类型 | 最少 Reviewer | 等待时间 |
|---|---|---|
| 紧急 bug 修复 | 1 人 | ≥ 2 小时 |
| 新功能 | 1 人 | ≥ 24 小时 |
| 架构变更 | 2 人 | ≥ 48 小时 |
| 纯文档 | 0 人 | 无要求 |

### 3.4 Review 检查清单

Reviewer 逐项确认：

```markdown
- [ ] 金额使用 Decimal（搜索 "float" 确认没有遗漏）
- [ ] 时间戳使用 UTC（搜索 "datetime.now()" 排除本地时间依赖）
- [ ] 所有失败路径写了 audit_log
- [ ] 新配置项添加到了 .example 文件
- [ ] 测试覆盖率 ≥ 80%（新代码）
- [ ] 没有引入新的顶级依赖（如果有，评估了体积）
- [ ] spec.md 相关章节已同步更新（或另开 docs PR）
```

---

## 4. 测试要求

### 4.1 测试策略总结

| 层级 | 工具 | 要求 |
|---|---|---|
| 单元测试 | pytest | 每个模块覆盖率 ≥ 80% |
| 属性测试 | hypothesis | 金额计算模块必须覆盖 |
| 集成测试 | pytest + SQLite | 端到端数据流（7 天 + 3 标的 + 2 Agent） |
| 确定性测试 | pytest --randomly-seed=42 | 同一输入必须同一输出 |

### 4.2 运行测试

```bash
# 全量
pytest

# 特定模块
pytest tests/test_validator/

# 带覆盖率
pytest --cov=src --cov-report=term-missing

# 确定性测试（固定种子）
pytest --randomly-seed=42
```

### 4.3 哪些必须写测试（不可妥协）

- 所有 `fee/` 下的计算函数
- 所有 `settlement/` 下的换算函数
- 所有 `validator/rules/` 下的校验规则
- 所有 `loan/` 下的利息计算
- 所有 `persistence/` 下的恢复逻辑

### 4.4 及时调试实践

> **不要攒代码。改几行就验证几行。**

#### 推荐节奏

```
改 3-5 行 → 存盘 → mypy（自动）→ ruff（自动）→ pytest 相关模块 → 通过？→ git commit
                                                                  → 不通过？→ 立刻修
```

一轮循环控制在 5 分钟以内。

#### 实用调试命令

```bash
# 快速验证单个函数（不启动整个应用）
poetry run python -c "from decimal import Decimal; from engine.fee import FeeCalculator; ..."

# 实时跟踪审计日志
tail -f results/demo/agent_audit.jsonl | jq 'select(.level == "ERROR")'

# dry-run 模式（不调 LLM，纯引擎验证）
poetry run python -m src --dry-run --session demo --days 7

# Textual DevTools 调试 UI
poetry run python -m src --dev
# 在 TUI 中按 Ctrl+D 打开检查器

# hypothesis 随机测试（反复跑发现边界情况）
pytest tests/test_engine/test_fee.py --hypothesis-show-statistics --count=1000
```

#### 需要避免的调试习惯

| ❌ 不要做 | ✅ 应该做 |
|---|---|
| 改 50 行后才跑一次 | 改 3-5 行就验证 |
| 用 `print()` 跟踪数据流 | 写 `audit_log` + `tail -f` 观察 |
| 出了一次正确就不再验证 | 每次改完都跑一遍 hypothesis 随机测试 |
| 跳过 mypy 类型检查（"反正能跑"） | 保持 mypy strict 模式零错误 |
| 提交前不查 diff | `git diff --check` + 肉眼过一遍变更 |

---

## 5. spec.md 更新规范

`spec.md` 是项目的单一事实来源。任何影响系统行为的变更都必须同步更新 spec。

### 更新时机

| 变更类型 | 必须更新 spec？ |
|---|---|
| 修复 bug（行为未改变） | 不需要 |
| 新增校验规则 | 需要更新 §8.1 校验规则表 |
| 新增数据源 | 需要更新 §5.1 数据源表 |
| 新增 TUI 图表 | 需要更新 §13.2 组件表 |
| 新增 LLM Provider | 需要更新 §16.3 / §16.4 |
| 修改费用模型 | 需要更新 §7.3 |
| 重构但不改行为 | 不需要 |

### 更新方式

- 小修改（1-2 处）：直接在 PR 中附带 spec 变更
- 大修改（跨多章）：单独开一个 `docs/spec-update-xxx` PR
- spec 变更必须经过 1 人 review

---

## 6. 沟通约定

| 场景 | 渠道 |
|---|---|
| 日常开发交流 | 项目群聊 / Issue 评论 |
| 架构决策 | 在 PR 中发起讨论，必要时开会 |
| Bug 报告 | GitHub Issues（模板） |
| 需求讨论 | Issue + 会后更新 spec |

### 设计讨论原则

- 先读 `spec.md` 对应章节
- 先读 `ARCHITECTURE.md` 对应接口定义
- 然后提 Issue，附上你的理解和方案
- 不要在群里直接问"这个怎么做"——先尝试写 10 行伪代码

---

## 7. 发布流程

```
main 累积 N 个 PR → 打 tag v0.x.x → 生成 CHANGELOG
    ↓
  可选: 打包为 Docker 镜像
    ↓
  更新 README（如果需要）
```

版本号语义：

| 版本 | 含义 |
|---|---|
| v0.1.x | Phase 1 MVP 范围内的小改进/bug 修复 |
| v0.2.x | Phase 2 功能 |
| v0.3.x | Phase 3 功能 |
| v1.0.0 | 所有 Phase 完成，API 稳定 |

---

## 8. Git 提交消息规范

### 8.1 Conventional Commits 格式

本项目采用 [Conventional Commits](https://www.conventionalcommits.org/) 规范：

```
<type>(<scope>): <subject>

<body>

<footer>
```

### 8.2 Type 类型

| Type | 说明 | 示例 |
|---|---|---|
| `feat` | 新功能 | `feat(engine): add limit order support` |
| `fix` | Bug 修复 | `fix(fee): correct decimal precision in commission calculation` |
| `docs` | 文档更新 | `docs: update deployment guide` |
| `style` | 代码格式（不影响功能） | `style: format with ruff` |
| `refactor` | 重构（不是新功能也不是修复） | `refactor(validator): extract common validation logic` |
| `test` | 添加/修改测试 | `test(engine): add hypothesis tests for fee calculation` |
| `chore` | 构建/工具/依赖更新 | `chore: update dependencies` |
| `perf` | 性能优化 | `perf(db): add index on orders.timestamp` |
| `ci` | CI 配置变更 | `ci: add GitHub Actions workflow` |

### 8.3 Scope 范围

| Scope | 对应模块 |
|---|---|
| `data` | 数据层 |
| `engine` | 交易引擎 |
| `validator` | 校验层 |
| `loan` | 贷款模块 |
| `agent` | Agent 层 |
| `context` | 上下文管理 |
| `analytics` | 分析层 |
| `tui` | TUI 界面 |
| `persistence` | 持久化 |
| `config` | 配置 |
| `api` | REST API |
| `docs` | 文档 |

### 8.4 提交消息示例

```bash
# 新功能
feat(engine): add T+1 settlement mechanism

Implement T+1 settlement for US stocks:
- Add SettlementQueue to track pending settlements
- Implement daily_settle() to unlock settled funds
- Add integration tests for settlement flow

Closes #123

# Bug 修复
fix(fee): correct decimal precision in commission calculation

The commission was being rounded incorrectly, causing
discrepancies in the total cost calculation.

Fixes #456

# 文档更新
docs: add deployment guide for Docker Compose

Add comprehensive deployment documentation including:
- Local development setup
- Docker deployment
- Production configuration

# 重构
refactor(validator): extract common validation logic

Move shared validation utilities to base class to reduce
code duplication across validation rules.
```

### 8.5 提交前检查

```bash
# 确保提交消息格式正确
git commit -m "feat(engine): add new feature"

# 或使用交互式提交
git commit
# 编辑器中填写：
# feat(engine): add new feature
# 
# Detailed description here...
```

---

## 9. 代码风格指南

### 9.1 命名规范

| 类型 | 规范 | 示例 |
|---|---|---|
| **模块** | 小写下划线 | `fee_calculator.py` |
| **类** | 大驼峰 | `FeeCalculator` |
| **函数/方法** | 小写下划线 | `calculate_commission()` |
| **常量** | 大写下划线 | `MAX_POSITION_PCT` |
| **私有属性** | 单下划线前缀 | `_internal_state` |
| **Protocol** | 大驼峰 + Protocol 后缀 | `MarketDataProvider(Protocol)` |
| **数据类** | 大驼峰 | `Order`, `Fill`, `Position` |

### 9.2 类型注解

```python
# 所有函数必须有类型注解
def calculate_fee(
    order: Order,
    fee_config: FeeConfig,
    exchange_rate: ExchangeRateSnapshot
) -> FeeBreakdown:
    """计算订单手续费"""
    ...

# 使用 typing 模块的类型
from typing import Protocol, Optional, Union
from decimal import Decimal

# 复杂类型使用类型别名
PositionDict = dict[str, Position]
PriceMap = dict[str, Decimal]

# Protocol 定义
class MarketDataProvider(Protocol):
    async def fetch_ohlcv(
        self,
        symbol: str,
        granularity: str,
        start_date: date,
        end_date: date
    ) -> list[Ohlcv]: ...
```

### 9.3 文档字符串

```python
def calculate_sharpe_ratio(
    returns: list[Decimal],
    risk_free_rate: Decimal = Decimal("0.02")
) -> Decimal:
    """
    计算夏普比率。
    
    Args:
        returns: 每日收益率列表
        risk_free_rate: 无风险利率（年化），默认 2%
    
    Returns:
        年化夏普比率
    
    Raises:
        ValueError: 如果 returns 为空
    
    Example:
        >>> returns = [Decimal("0.01"), Decimal("-0.005"), Decimal("0.02")]
        >>> sharpe = calculate_sharpe_ratio(returns)
    """
    if not returns:
        raise ValueError("returns cannot be empty")
    
    mean_return = sum(returns) / len(returns)
    std_return = (sum((r - mean_return) ** 2 for r in returns) / len(returns)).sqrt()
    
    if std_return == 0:
        return Decimal("0")
    
    return (mean_return - risk_free_rate / 252) / std_return * (252 ** 0.5)
```

### 9.4 导入顺序

```python
# 1. 标准库
import asyncio
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, Optional

# 2. 第三方库
import httpx
from pydantic import BaseModel

# 3. 本地模块
from config.loader import ConfigLoader
from engine.order import Order
from engine.fee import FeeCalculator
```

### 9.5 代码组织

```python
# 模块顶部结构
"""
模块文档字符串
"""

# 1. 导入
import ...

# 2. 常量
MAX_POSITION_PCT = 0.20
DEFAULT_SLIPPAGE = Decimal("0.002")

# 3. 数据类/异常
class InsufficientFundsError(Exception):
    """资金不足异常"""
    pass

# 4. Protocol/ABC
class FeeCalculator(Protocol):
    ...

# 5. 实现类
class DefaultFeeCalculator:
    ...

# 6. 辅助函数
def _round_to_tick(price: Decimal, tick_size: Decimal) -> Decimal:
    ...

# 7. 主函数（如果有）
def main() -> None:
    ...
```

### 9.6 禁止事项

```python
# ❌ 禁止：使用 float 计算金额
total = 100.0 * 1.05  # 错误

# ✅ 正确：使用 Decimal
from decimal import Decimal
total = Decimal("100") * Decimal("1.05")

# ❌ 禁止：类型注解使用 any
def process(data: any) -> any:  # 错误
    ...

# ✅ 正确：明确类型
def process(data: dict[str, Decimal]) -> list[Order]:
    ...

# ❌ 禁止：空 except 块
try:
    ...
except Exception:
    pass  # 错误

# ✅ 正确：记录异常
try:
    ...
except Exception as e:
    logger.error(f"处理失败: {e}")
    raise

# ❌ 禁止：硬编码配置
API_URL = "https://api.example.com"  # 错误

# ✅ 正确：从配置读取
api_url = config.get("api", "url")
```

### 9.7 代码检查配置

```toml
# pyproject.toml

[tool.ruff]
target-version = "py311"
line-length = 120
select = [
    "E",   # pycodestyle errors
    "F",   # pyflakes
    "I",   # isort
    "N",   # pep8-naming
    "W",   # pycodestyle warnings
    "UP",  # pyupgrade
    "ANN", # flake8-annotations
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
    "SIM", # flake8-simplify
]
ignore = ["ANN101", "ANN102"]  # self/cls 不需要类型注解

[tool.mypy]
strict = true
python_version = "3.11"
disallow_untyped_defs = true
warn_return_any = true
no_implicit_optional = true
plugins = ["pydantic.mypy"]
```

---

## 10. Issue 模板

### 10.1 Bug 报告模板

```markdown
## Bug 报告

### 环境信息
- OS: [e.g. macOS 14.0 / Ubuntu 22.04]
- Python: [e.g. 3.11.5]
- Poetry: [e.g. 1.7.0]
- 项目版本: [e.g. v0.1.0]

### 问题描述
[简洁描述问题]

### 复现步骤
1. 执行 `...`
2. 观察到 `...`

### 期望行为
[应该发生什么]

### 实际行为
[实际发生了什么]

### 日志/截图
```
[粘贴相关日志]
```

### 其他信息
[任何其他有助于解决问题的信息]
```

### 10.2 功能请求模板

```markdown
## 功能请求

### 功能描述
[清晰描述你希望添加的功能]

### 使用场景
[描述什么场景下需要这个功能]

### 建议实现
[可选：描述你认为可行的实现方式]

### 替代方案
[可选：描述你考虑过的替代方案]

### 其他信息
[任何其他相关信息]
```

---

## 11. 联系与支持
