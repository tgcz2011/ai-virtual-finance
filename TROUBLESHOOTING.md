# AI Virtual Finance — Troubleshooting Guide

> **目标读者**：遇到问题的开发者、运维人员
> **读完本文你应该能回答**：常见问题如何排查？错误日志在哪里？如何恢复系统？

---

## 1. 快速诊断流程

```
┌─────────────────────────────────────────────────────────────────┐
│                      问题诊断流程                                  │
├─────────────────────────────────────────────────────────────────┤
│  1. 查看日志                                                      │
│     tail -f results/{session}/agent_audit.jsonl                  │
│     ↓                                                            │
│  2. 检查数据库                                                     │
│     sqlite3 data/finance.db "PRAGMA integrity_check;"            │
│     ↓                                                            │
│  3. 验证配置                                                       │
│     poetry run python -c "from config.loader import ConfigLoader │
│                           ConfigLoader().validate()"             │
│     ↓                                                            │
│  4. 运行 dry-run                                                   │
│     poetry run python -m src --dry-run --session test --days 1   │
│     ↓                                                            │
│  5. 检查依赖                                                       │
│     poetry install --sync                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. 常见问题分类

### 2.1 启动问题

#### 问题：`ModuleNotFoundError: No module named 'xxx'`

**原因**：依赖未安装或虚拟环境未激活

**解决方案**：

```bash
# 确保在项目目录
cd ai-virtual-finance

# 安装依赖
poetry install

# 或激活虚拟环境后运行
poetry shell
python -m src
```

---

#### 问题：`FileNotFoundError: config/fee_schedule.yaml`

**原因**：配置文件模板未复制

**解决方案**：

```bash
# 复制所有配置模板
cp config/fee_schedule.yaml.example config/fee_schedule.yaml
cp config/providers.yaml.example config/providers.yaml
cp config/context.yaml.example config/context.yaml
cp config/persistence.yaml.example config/persistence.yaml
```

---

#### 问题：`PermissionError: [Errno 13] Permission denied: 'data/finance.db'`

**原因**：数据目录权限问题

**解决方案**：

```bash
# 检查目录权限
ls -la data/

# 修复权限
chmod 755 data/
chmod 644 data/finance.db

# 或重新创建
rm -rf data/
mkdir -p data/
```

---

#### 问题：TUI 显示乱码或空白

**原因**：终端不支持 Unicode 或字体问题

**解决方案**：

```bash
# 方案 1: 使用 headless 模式
poetry run python -m src --headless --session demo --days 7

# 方案 2: 设置终端编码
export LANG=en_US.UTF-8
export LC_ALL=en_US.UTF-8

# 方案 3: 更换终端（推荐 iTerm2 / Windows Terminal）
```

---

### 2.2 数据库问题

#### 问题：`sqlite3.OperationalError: database is locked`

**原因**：WAL 模式未启用或并发写入冲突

**解决方案**：

```bash
# 检查 WAL 模式
sqlite3 data/finance.db "PRAGMA journal_mode;"
# 应返回 "wal"

# 如果不是 wal，手动启用
sqlite3 data/finance.db "PRAGMA journal_mode=WAL;"

# 检查是否有其他进程占用
lsof data/finance.db

# 清理锁文件
rm -f data/finance.db-wal data/finance.db-shm
```

---

#### 问题：`sqlite3.DatabaseError: database disk image is malformed`

**原因**：数据库文件损坏

**解决方案**：

```bash
# 1. 尝试修复
sqlite3 data/finance.db ".recover" > recover.sql
sqlite3 data/finance_fixed.db < recover.sql
mv data/finance_fixed.db data/finance.db

# 2. 如果有备份，恢复备份
cp /backups/finance_latest.db data/finance.db

# 3. 最坏情况：重新初始化
rm data/finance.db
poetry run python -m src --init-db
```

---

#### 问题：`sqlite3.IntegrityError: UNIQUE constraint failed`

**原因**：重复插入相同数据

**解决方案**：

```python
# 检查是否有重复数据
# 在代码中使用 UPSERT 或先查询后插入

# 示例：使用 INSERT OR IGNORE
cursor.execute("""
    INSERT OR IGNORE INTO orders (order_id, ...)
    VALUES (?, ...)
""", (order_id, ...))
```

---

### 2.3 数据源问题

#### 问题：`ConnectionError: Failed to fetch data from Yahoo Finance`

**原因**：网络问题或数据源不可用

**解决方案**：

```bash
# 1. 检查网络连接
curl -I https://query1.finance.yahoo.com

# 2. 使用缓存数据
poetry run python -m src --use-cache --session demo

# 3. 切换数据源
# 编辑 config/providers.yaml
data_providers:
  us_stocks:
    primary: alpha_vantage.AlphaVantageProvider  # 切换备用源
    fallback: yfinance.YahooFinanceProvider
```

---

#### 问题：`KeyError: 'AAPL'` 或标的数据缺失

**原因**：标的代码不存在或已退市

**解决方案**：

```bash
# 验证标的代码
poetry run python -c "
from data.providers.yahoo import YahooFinanceProvider
import asyncio
provider = YahooFinanceProvider()
print(asyncio.run(provider.validate_symbol('AAPL')))
"

# 检查数据质量标记
sqlite3 data/finance.db "
SELECT symbol, data_quality, timestamp 
FROM ohlcv_cache 
WHERE symbol = 'AAPL' 
ORDER BY timestamp DESC LIMIT 10
"
```

---

#### 问题：汇率数据获取失败

**原因**：汇率 API 不可用

**解决方案**：

```bash
# 1. 检查汇率 API
curl "https://api.exchangerate-api.com/v4/latest/USD"

# 2. 使用固定汇率（测试用）
# 编辑 config/fee_schedule.yaml
exchange_rates:
  fixed_mode: true
  usd_cny: 7.25

# 3. 手动更新汇率缓存
poetry run python -c "
from engine.settlement.fx import FxConverter
fx = FxConverter()
fx.update_cache()
"
```

---

### 2.4 Agent 决策问题

#### 问题：`LLM API Error: Rate limit exceeded`

**原因**：API 调用频率超限

**解决方案**：

```bash
# 1. 降低决策频率
# 编辑 config/agents/momentum-v1.yaml
decision_interval: "1d"  # 从 1h 改为 1d

# 2. 添加重试和退避
# 代码中已实现，检查日志确认

# 3. 切换到本地规则引擎
# 编辑 config/agents/momentum-v1.yaml
llm:
  provider_id: rules_engine  # 使用本地策略
```

---

#### 问题：`JSONDecodeError: Expecting value`

**原因**：LLM 返回非 JSON 格式

**解决方案**：

```bash
# 1. 查看原始返回
tail -100 results/demo/agent_audit.jsonl | jq 'select(.event == "llm_response")'

# 2. 检查 System Prompt 是否包含格式要求
cat config/agents/momentum-v1.yaml | grep -A 20 "system_prompt"

# 3. 增强格式约束
# 在 System Prompt 中添加：
# "你必须返回严格的 JSON 格式，不要包含任何其他文字。"
```

---

#### 问题：Agent 决策全部 HOLD

**原因**：置信度阈值过高或市场条件不满足

**解决方案**：

```bash
# 1. 检查 Agent 配置
cat config/agents/momentum-v1.yaml | grep min_confidence

# 2. 降低置信度阈值
min_confidence: 0.50  # 从 0.60 降到 0.50

# 3. 检查校验规则是否过严
tail -100 results/demo/agent_audit.jsonl | jq 'select(.event == "validation_rejected")'

# 4. 查看决策理由
tail -100 results/demo/agent_audit.jsonl | jq 'select(.event == "decision") | .rationale'
```

---

#### 问题：`ValidationError: target_pct exceeds max_position_pct`

**原因**：Agent 尝试超过仓位限制

**解决方案**：

```bash
# 1. 检查当前持仓
sqlite3 data/finance.db "
SELECT symbol, quantity, market_value_cny 
FROM positions 
WHERE agent_id = 'momentum-v1'
"

# 2. 调整仓位限制
# 编辑 config/agents/momentum-v1.yaml
max_position_pct: 0.30  # 从 0.20 提高到 0.30

# 3. 检查是否需要先卖出
# Agent 应该先 SELL 再 BUY
```

---

### 2.5 性能问题

#### 问题：系统运行缓慢

**原因**：数据量大、缓存未命中、内存不足

**解决方案**：

```bash
# 1. 检查数据库大小
du -h data/finance.db

# 2. 清理旧缓存
sqlite3 data/finance.db "DELETE FROM ohlcv_cache WHERE timestamp < datetime('now', '-30 days')"

# 3. 重建索引
sqlite3 data/finance.db "REINDEX"

# 4. 增加数据库缓存
# 编辑 config/persistence.yaml
database:
  cache_size: -128000  # 128MB

# 5. 检查内存使用
docker stats finance-engine  # Docker 环境
ps aux | grep python         # 本地环境
```

---

#### 问题：内存占用持续增长

**原因**：内存泄漏或缓存未清理

**解决方案**：

```bash
# 1. 监控内存
watch -n 5 'ps aux | grep python | grep -v grep'

# 2. 减少检查点间隔
# 编辑 config/persistence.yaml
checkpoints:
  incremental_interval: 5  # 从 10 秒改为 5 秒

# 3. 限制历史数据范围
# 启动时指定较短的时间范围
poetry run python -m src --session demo --days 7  # 而不是 --days 365

# 4. 重启服务释放内存
docker-compose restart finance-engine
```

---

### 2.6 持久化问题

#### 问题：断电后数据丢失

**原因**：WAL 模式未启用或检查点未写入

**解决方案**：

```bash
# 1. 确认 WAL 模式
sqlite3 data/finance.db "PRAGMA journal_mode;"

# 2. 手动触发检查点
sqlite3 data/finance.db "PRAGMA wal_checkpoint(TRUNCATE);"

# 3. 检查同步模式
sqlite3 data/finance.db "PRAGMA synchronous;"
# 应该是 2 (FULL) 或 3 (EXTRA)

# 4. 恢复数据
poetry run python -m src --recover --checkpoint results/demo/checkpoint_latest.json
```

---

#### 问题：`CheckpointError: Checkpoint file corrupted`

**原因**：检查点文件损坏

**解决方案**：

```bash
# 1. 检查检查点文件
cat results/demo/checkpoint_latest.json | python -m json.tool

# 2. 使用上一个检查点
ls -lt results/demo/checkpoint_*.json
cp results/demo/checkpoint_20240115_100000.json results/demo/checkpoint_latest.json

# 3. 从数据库恢复
poetry run python -m src --recover-from-db --session demo
```

---

### 2.7 Docker 问题

#### 问题：容器启动后立即退出

**原因**：配置错误或依赖缺失

**解决方案**：

```bash
# 查看容器日志
docker logs finance-engine

# 常见错误及解决：
# 1. 配置文件缺失
docker run -v $(pwd)/config:/app/config ...

# 2. 权限问题
docker run --user $(id -u):$(id -g) ...

# 3. 端口占用
docker run -p 8081:8080 ...  # 换个端口
```

---

#### 问题：容器内无法访问网络

**原因**：网络配置问题

**解决方案**：

```bash
# 1. 检查网络模式
docker network ls
docker inspect finance-engine | grep NetworkMode

# 2. 使用 host 网络模式
docker run --network host ...

# 3. 检查 DNS
docker exec finance-engine ping google.com

# 4. 配置 DNS
docker run --dns 8.8.8.8 ...
```

---

#### 问题：容器磁盘空间不足

**原因**：日志或数据文件过大

**解决方案**：

```bash
# 1. 检查磁盘使用
docker system df

# 2. 清理未使用资源
docker system prune -a

# 3. 限制日志大小
# docker-compose.yml
logging:
  driver: "json-file"
  options:
    max-size: "100m"
    max-file: "5"

# 4. 挂载外部存储
docker run -v /external/data:/app/data ...
```

---

## 3. 日志分析

### 3.1 日志位置

```
results/{session_id}/
├── agent_audit.jsonl       # 全量审计日志
├── checkpoint_*.json       # 检查点文件
├── equity_curve_*.csv      # 净值曲线
├── trade_log_*.csv         # 交易记录
└── summary.json            # 汇总统计
```

### 3.2 常用日志查询

```bash
# 查看所有错误
cat results/demo/agent_audit.jsonl | jq 'select(.level == "ERROR")'

# 查看特定 Agent 的操作
cat results/demo/agent_audit.jsonl | jq 'select(.agent_id == "momentum-v1")'

# 查看被拒绝的订单
cat results/demo/agent_audit.jsonl | jq 'select(.event == "order_rejected")'

# 统计错误类型
cat results/demo/agent_audit.jsonl | jq -r '.error_code' | sort | uniq -c

# 查看最近 1 小时的日志
find results/ -name "*.jsonl" -mmin -60 -exec cat {} \; | jq '.'

# 实时监控
tail -f results/demo/agent_audit.jsonl | jq 'select(.level == "WARN" or .level == "ERROR")'
```

### 3.3 日志级别说明

| 级别 | 含义 | 示例 |
|---|---|---|
| DEBUG | 详细调试信息 | 函数调用、变量值 |
| INFO | 正常操作信息 | 订单提交、决策完成 |
| WARN | 警告但不影响运行 | 校验拒绝、API 限流 |
| ERROR | 错误需要关注 | 数据获取失败、数据库错误 |
| CRITICAL | 严重错误 | 系统崩溃、数据损坏 |

---

## 4. 诊断命令速查

### 4.1 系统状态

```bash
# Python 版本
python --version

# 依赖检查
poetry check
poetry show --tree

# 环境变量
env | grep FINANCE

# 磁盘空间
df -h

# 内存使用
free -h
```

### 4.2 数据库诊断

```bash
# 完整性检查
sqlite3 data/finance.db "PRAGMA integrity_check;"

# 表结构
sqlite3 data/finance.db ".schema"

# 表大小
sqlite3 data/finance.db "
SELECT name, 
       (pgsize * pgcount) / 1024 / 1024 as size_mb
FROM dbstat 
GROUP BY name 
ORDER BY size_mb DESC
"

# 查询性能
sqlite3 data/finance.db "EXPLAIN QUERY PLAN SELECT * FROM orders WHERE agent_id = 'xxx'"

# WAL 状态
sqlite3 data/finance.db "PRAGMA wal_checkpoint;"
```

### 4.3 网络诊断

```bash
# 测试 Yahoo Finance
curl -I "https://query1.finance.yahoo.com/v8/finance/chart/AAPL"

# 测试 Binance
curl -I "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"

# 测试汇率 API
curl "https://api.exchangerate-api.com/v4/latest/USD" | jq '.rates.CNY'

# DNS 解析
nslookup query1.finance.yahoo.com
```

### 4.4 进程诊断

```bash
# 查找 Python 进程
ps aux | grep python

# 查看进程资源
top -p $(pgrep -f "python -m src")

# 跟踪系统调用
strace -p <pid> -e trace=network

# 打开的文件
lsof -p <pid>
```

---

## 5. 恢复操作

### 5.1 从检查点恢复

```bash
# 列出可用检查点
ls -lt results/demo/checkpoint_*.json

# 恢复
poetry run python -m src --recover --checkpoint results/demo/checkpoint_20240115_100000.json

# 验证恢复结果
poetry run python -c "
from persistence.checkpoint import CheckpointManager
mgr = CheckpointManager('results/demo')
print(mgr.validate())
"
```

### 5.2 从备份恢复

```bash
# 恢复数据库
cp /backups/finance_20240115.db data/finance.db

# 恢复配置
tar -xzf /backups/config_20240115.tar.gz -C ./

# 恢复结果
tar -xzf /backups/results_20240115.tar.gz -C ./
```

### 5.3 重置系统

```bash
# ⚠️ 危险操作：清除所有数据
rm -rf data/ results/

# 重新初始化
poetry run python -m src --init-db
cp config/*.example config/
# 编辑配置文件...
```

---

## 6. 获取帮助

### 6.1 信息收集

在报告问题前，请收集以下信息：

```bash
# 系统信息
uname -a
python --version
poetry --version

# 错误日志（最近 100 行）
tail -100 results/*/agent_audit.jsonl > error_log.txt

# 配置文件（脱敏后）
cat config/*.yaml | sed 's/sk-[a-zA-Z0-9]*/sk-***/g' > config_dump.txt

# 数据库状态
sqlite3 data/finance.db ".schema" > db_schema.txt
sqlite3 data/finance.db "PRAGMA integrity_check;" > db_check.txt

# 复现步骤
# 1. 执行了什么命令
# 2. 期望什么结果
# 3. 实际什么结果
```

### 6.2 报告渠道

| 问题类型 | 渠道 | 格式 |
|---|---|---|
| Bug 报告 | GitHub Issues | Bug Report 模板 |
| 功能建议 | GitHub Discussions | Feature Request |
| 安全问题 | security@example.com | 私密邮件 |
| 文档问题 | 提交 PR | 修改对应 .md 文件 |

### 6.3 Issue 模板

```markdown
## Bug 报告

### 环境信息
- OS: [e.g. macOS 14.0]
- Python: [e.g. 3.11.5]
- Poetry: [e.g. 1.7.0]
- 项目版本: [e.g. v0.1.0]

### 问题描述
[简洁描述问题]

### 复现步骤
1. 执行 `poetry run python -m src ...`
2. 观察到错误...

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
