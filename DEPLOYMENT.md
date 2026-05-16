# AI Virtual Finance — Deployment Guide

> **目标读者**：开发者、运维人员
> **读完本文你应该能回答**：如何搭建开发环境？如何打包发布？如何通过 GitHub Actions 自动化发布？

---

## 1. 部署概述

### 1.1 部署架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          部署架构                                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  开发环境 (venv)                                                         │
│      │                                                                   │
│      ├─ 本地开发、调试                                                    │
│      ├─ 运行测试                                                         │
│      └─ 生成可执行文件 (PyInstaller)                                      │
│                                                                          │
│  GitHub 仓库                                                             │
│      │                                                                   │
│      ├─ 代码托管                                                         │
│      ├─ Pull Request 审核流程                                            │
│      └─ GitHub Actions 自动化                                            │
│                                                                          │
│  发布流程 (GitHub Actions)                                               │
│      │                                                                   │
│      ├─ 自动测试                                                         │
│      ├─ 自动打包 (Windows/macOS/Linux)                                   │
│      └─ 发布到 GitHub Releases                                           │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 部署模式

| 模式 | 适用场景 | 说明 |
|---|---|---|
| **venv 开发环境** | 本地开发、调试 | 使用 Python 虚拟环境 |
| **PyInstaller 打包** | 分发给最终用户 | 生成独立可执行文件 |
| **GitHub Actions** | 自动化发布 | CI/CD 自动构建和发布 |

### 1.3 系统要求

| 组件 | 最低要求 | 推荐配置 |
|---|---|---|
| CPU | 2 核 | 4 核+ |
| 内存 | 4 GB | 8 GB+ |
| 磁盘 | 10 GB | 50 GB+ (SSD) |
| Python | 3.11+ | 3.12 |
| Git | 2.40+ | 最新版 |
| SQLite | 3.40+ | 3.45+ |

---

## 2. 本地开发环境 (venv)

### 2.1 环境准备

```bash
# 检查 Python 版本
python --version  # 需要 >= 3.11

# 检查 Git
git --version

# 检查 pip
pip --version
```

### 2.2 克隆仓库

```bash
# 克隆仓库
git clone https://github.com/<your-username>/ai-virtual-finance.git
cd ai-virtual-finance

# 查看远程仓库
git remote -v
```

### 2.3 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv .venv

# 激活虚拟环境
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1

# Windows (CMD)
.\.venv\Scripts\activate.bat

# 验证虚拟环境已激活
which python  # macOS/Linux
where python  # Windows
# 应该显示 .venv 目录下的 python
```

### 2.4 安装依赖

```bash
# 升级 pip
pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt

# 或使用 pyproject.toml（如果使用 Poetry）
pip install poetry
poetry install
```

### 2.5 配置文件

```bash
# 复制配置模板
cp config/fee_schedule.yaml.example config/fee_schedule.yaml
cp config/providers.yaml.example config/providers.yaml
cp config/context.yaml.example config/context.yaml
cp config/persistence.yaml.example config/persistence.yaml

# 创建 secrets.yaml（不要提交到 Git）
cat > config/secrets.yaml << 'EOF'
# API Keys - 不要提交到 Git
api_keys:
  openai: "${OPENAI_API_KEY}"
  anthropic: "${ANTHROPIC_API_KEY}"
EOF
```

### 2.6 设置环境变量

```bash
# macOS / Linux (添加到 ~/.bashrc 或 ~/.zshrc)
export OPENAI_API_KEY="sk-xxx"
export ANTHROPIC_API_KEY="sk-ant-xxx"
export FINANCE_API_KEYS='{"openai": "sk-xxx", "anthropic": "sk-ant-xxx"}'

# Windows (PowerShell)
$env:OPENAI_API_KEY="sk-xxx"
$env:ANTHROPIC_API_KEY="sk-ant-xxx"

# 或使用 .env 文件（需要 python-dotenv）
cat > .env << 'EOF'
OPENAI_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
EOF
```

### 2.7 运行项目

```bash
# 启动 TUI 模式
python -m src

# 启动 headless 模式
python -m src --headless --session demo --days 7

# dry-run 模式（不调用 LLM）
python -m src --dry-run --session test --days 1
```

### 2.8 验证环境

```bash
# 运行测试
pytest tests/ -x --tb=short

# 类型检查
mypy src/ --strict

# 代码风格检查
ruff check src/

# 格式化代码
ruff format src/
```

---

## 3. PyInstaller 打包

### 3.1 安装 PyInstaller

```bash
# 在虚拟环境中安装
pip install pyinstaller
```

### 3.2 打包配置

创建 `pyinstaller.spec` 文件：

```python
# pyinstaller.spec
# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=[],
    binaries=[],
    datas=[
        # 包含配置模板
        ('config/*.example', 'config'),
        # 包含必要的数据文件
        ('src/tui/themes', 'src/tui/themes'),
    ],
    hiddenimports=[
        'textual',
        'rich',
        'pydantic',
        'yaml',
        'decimal',
        'asyncio',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'numpy',
        'pandas',  # 如果不需要
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='finance',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # TUI 需要控制台
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
```

### 3.3 打包命令

```bash
# 单文件打包（推荐）
pyinstaller --onefile --name finance src/main.py

# 使用 spec 文件打包（更精细控制）
pyinstaller pyinstaller.spec

# 打包结果在 dist/ 目录
ls -la dist/
```

### 3.4 跨平台打包

PyInstaller 只能在当前平台打包：

| 目标平台 | 打包环境 |
|---|---|
| Windows .exe | Windows 系统 |
| macOS .app | macOS 系统 |
| Linux 可执行文件 | Linux 系统 |

**推荐**：使用 GitHub Actions 实现跨平台自动打包（见第 5 节）。

### 3.5 测试打包结果

```bash
# 运行打包后的可执行文件
./dist/finance --help

# 测试 TUI 模式
./dist/finance

# 测试 headless 模式
./dist/finance --headless --session test --days 1
```

---

## 4. GitHub 仓库管理

### 4.1 仓库结构

```
ai-virtual-finance/
├── .github/
│   ├── workflows/
│   │   ├── test.yml           # 测试工作流
│   │   └── release.yml        # 发布工作流
│   ├── PULL_REQUEST_TEMPLATE.md
│   └── ISSUE_TEMPLATE/
│       ├── bug_report.md
│       └── feature_request.md
├── src/
├── tests/
├── config/
├── docs/
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── pyinstaller.spec
└── README.md
```

### 4.2 分支策略

```
main                ← 稳定版本，只通过 PR 合并
  │
  ├─ develop        ← 开发分支，日常开发在此
  │   │
  │   ├─ feat/xxx   ← 新功能分支
  │   ├─ fix/xxx    ← Bug 修复分支
  │   ├─ refactor/xxx
  │   └─ docs/xxx
  │
  └─ release/vX.Y.Z ← 发布分支
```

### 4.3 Pull Request 流程

#### 步骤 1：创建功能分支

```bash
# 从 develop 创建分支
git checkout develop
git pull origin develop
git checkout -b feat/my-feature

# 或从 main 创建（如果是紧急修复）
git checkout main
git pull origin main
git checkout -b fix/urgent-fix
```

#### 步骤 2：开发和提交

```bash
# 开发代码...
# 运行测试
pytest tests/ -x --tb=short

# 代码检查
ruff check src/
mypy src/ --strict

# 提交（遵循 Conventional Commits）
git add .
git commit -m "feat(engine): add limit order support"

# 推送到远程
git push origin feat/my-feature
```

#### 步骤 3：创建 Pull Request

1. 访问 GitHub 仓库页面
2. 点击 "Compare & pull request"
3. 填写 PR 模板（见下方）
4. 等待 CI 通过和 Review

#### 步骤 4：PR 审核通过后合并

```bash
# 使用 GitHub 网页界面合并
# 或使用 gh CLI
gh pr merge --squash --delete-branch
```

### 4.4 Pull Request 模板

创建 `.github/PULL_REQUEST_TEMPLATE.md`：

```markdown
## 变更描述

<!-- 简要描述这个 PR 做了什么 -->

## 变更类型

- [ ] 🚀 新功能 (feat)
- [ ] 🐛 Bug 修复 (fix)
- [ ] 📝 文档更新 (docs)
- [ ] 🔨 重构 (refactor)
- [ ] ✅ 测试 (test)
- [ ] 🔧 配置/工具 (chore)

## 关联 Issue

<!-- 关联的 Issue 编号，如 Closes #123 -->

Closes #

## 测试

- [ ] 已添加/更新单元测试
- [ ] 已通过 `pytest tests/ -x`
- [ ] 已通过 `mypy src/ --strict`
- [ ] 已通过 `ruff check src/`

## 检查清单

- [ ] 代码遵循项目风格指南
- [ ] 已更新相关文档
- [ ] 提交消息遵循 Conventional Commits
- [ ] 没有引入新的 `print()` 调试语句
- [ ] 金额计算使用 `Decimal` 而非 `float`

## 截图（如适用）

<!-- 如果是 UI 变更，请附上截图 -->

## 其他说明

<!-- 任何需要 reviewer 注意的事项 -->
```

### 4.5 分支保护规则

在 GitHub 仓库 Settings → Branches 中配置：

```
main 分支保护规则：
☑ Require a pull request before merging
  ☑ Require approvals: 1
  ☑ Dismiss stale pull request approvals when new commits are pushed
☑ Require status checks to pass before merging
  ☑ Require branches to be up to date before merging
  ☑ Status checks: test, mypy, ruff
☑ Require linear history
☑ Include administrators
```

---

## 5. GitHub Actions 自动化

### 5.1 测试工作流

创建 `.github/workflows/test.yml`：

```yaml
name: Test

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main, develop]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, macos-latest, windows-latest]
        python-version: ['3.11', '3.12']

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}

      - name: Create virtual environment
        run: python -m venv .venv

      - name: Activate virtual environment (Linux/macOS)
        if: runner.os != 'Windows'
        run: source .venv/bin/activate

      - name: Activate virtual environment (Windows)
        if: runner.os == 'Windows'
        run: .\.venv\Scripts\activate

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run ruff
        run: ruff check src/

      - name: Run mypy
        run: mypy src/ --strict

      - name: Run tests
        run: pytest tests/ -x --tb=short --cov=src --cov-report=xml

      - name: Upload coverage
        if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.12'
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
```

### 5.2 发布工作流

创建 `.github/workflows/release.yml`：

```yaml
name: Build and Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

jobs:
  build:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            target: linux
            ext: ''
          - os: macos-latest
            target: macos
            ext: ''
          - os: windows-latest
            target: windows
            ext: '.exe'

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Create virtual environment
        run: python -m venv .venv

      - name: Activate virtual environment (Linux/macOS)
        if: runner.os != 'Windows'
        run: source .venv/bin/activate

      - name: Activate virtual environment (Windows)
        if: runner.os == 'Windows'
        run: .\.venv\Scripts\activate

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pyinstaller

      - name: Build executable
        run: |
          pyinstaller --onefile --name finance${{ matrix.ext }} src/main.py

      - name: Upload artifact
        uses: actions/upload-artifact@v4
        with:
          name: finance-${{ matrix.target }}
          path: dist/finance${{ matrix.ext }}

  release:
    needs: build
    runs-on: ubuntu-latest

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Download all artifacts
        uses: actions/download-artifact@v4
        with:
          path: dist/

      - name: Display structure of downloaded files
        run: ls -R dist/

      - name: Create Release
        uses: softprops/action-gh-release@v1
        with:
          files: |
            dist/finance-linux/finance
            dist/finance-macos/finance
            dist/finance-windows/finance.exe
          body: |
            ## Release Notes
            
            ### Changes
            - See [CHANGELOG.md](./CHANGELOG.md) for details.
            
            ### Downloads
            | Platform | File |
            |---|---|
            | Linux | `finance` |
            | macOS | `finance` |
            | Windows | `finance.exe` |
            
            ### Usage
            ```bash
            # Linux/macOS
            chmod +x finance
            ./finance
            
            # Windows
            finance.exe
            ```
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

### 5.3 发布流程

```bash
# 1. 确保 develop 分支所有测试通过
git checkout develop
pytest tests/ -x

# 2. 合并到 main
git checkout main
git merge develop

# 3. 更新版本号
# 编辑 pyproject.toml 中的 version

# 4. 更新 CHANGELOG.md

# 5. 提交版本更新
git add .
git commit -m "chore: release v0.1.0"

# 6. 创建 tag
git tag v0.1.0

# 7. 推送 tag（触发 GitHub Actions）
git push origin main --tags

# 8. GitHub Actions 自动构建并发布到 Releases
```

---

## 6. 配置文件管理

### 6.1 配置文件结构

```
config/
├── fee_schedule.yaml.example    # 手续费配置模板
├── providers.yaml.example       # Provider 注册模板
├── context.yaml.example         # 上下文管理参数模板
├── persistence.yaml.example     # 持久化配置模板
├── secrets.yaml.example         # API Key 模板
└── agents/                      # Agent 配置目录
    └── example.yaml.example
```

### 6.2 .gitignore 配置

```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/

# 打包
build/
dist/
*.egg-info/
*.egg
*.spec.bak

# 配置（敏感信息）
config/fee_schedule.yaml
config/providers.yaml
config/context.yaml
config/persistence.yaml
config/secrets.yaml
config/agents/*.yaml
!.example

# 数据和结果
data/
results/
*.db
*.sqlite

# IDE
.idea/
.vscode/
*.swp
*.swo

# 系统文件
.DS_Store
Thumbs.db

# 环境变量
.env
.env.local
```

---

## 7. 监控与日志

### 7.1 日志配置

```python
# src/config/logging.py
import logging
import logging.config
from pathlib import Path

LOG_DIR = Path("results/logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "format": '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "module": "%(name)s", "message": "%(message)s"}'
        },
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "standard",
            "level": "INFO"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": str(LOG_DIR / "app.log"),
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
            "formatter": "json",
            "level": "DEBUG"
        }
    },
    "root": {
        "handlers": ["console", "file"],
        "level": "INFO"
    }
}

def setup_logging():
    logging.config.dictConfig(LOGGING_CONFIG)
```

### 7.2 审计日志

```bash
# 查看实时日志
tail -f results/logs/app.log

# 查看错误日志
grep '"level": "ERROR"' results/logs/app.log

# 查看特定 Session 的日志
grep '"session_id": "demo"' results/logs/app.log
```

---

## 8. 备份与恢复

### 8.1 手动备份

```bash
# 备份数据库
cp data/finance.db backups/finance_$(date +%Y%m%d).db

# 备份配置
tar -czf backups/config_$(date +%Y%m%d).tar.gz config/

# 备份结果
tar -czf backups/results_$(date +%Y%m%d).tar.gz results/
```

### 8.2 自动备份脚本

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
if [ -f "data/finance.db" ]; then
    cp data/finance.db $BACKUP_DIR/finance_$DATE.db
fi

# 备份配置
tar -czf $BACKUP_DIR/config_$DATE.tar.gz config/ 2>/dev/null

# 清理旧备份（保留最近 7 天）
find $BACKUP_DIR -type f -mtime +7 -delete

echo "Backup completed: $DATE"
```

---

## 9. 故障排查

### 9.1 常见问题

| 问题 | 解决方案 |
|---|---|
| 虚拟环境激活失败 | 确保使用正确的激活命令（Windows 用 `.\.venv\Scripts\activate`） |
| 依赖安装失败 | 尝试 `pip install --upgrade pip` 后重新安装 |
| PyInstaller 打包失败 | 检查 `hiddenimports` 是否包含所有必要模块 |
| 运行时找不到配置文件 | 确保配置文件已从 `.example` 复制 |
| API Key 无效 | 检查环境变量是否正确设置 |

### 9.2 诊断命令

```bash
# 检查 Python 环境
python --version
which python
pip list

# 检查虚拟环境
echo $VIRTUAL_ENV

# 检查配置文件
ls -la config/

# 检查数据库
sqlite3 data/finance.db "PRAGMA integrity_check;"

# 检查日志
tail -100 results/logs/app.log
```

---

## 10. 检查清单

### 开发环境检查

```
□ Python >= 3.11 已安装
□ Git 已安装并配置
□ 虚拟环境已创建并激活
□ 依赖已安装
□ 配置文件已从模板复制
□ 环境变量已设置
□ 测试通过 (pytest tests/ -x)
□ 代码检查通过 (ruff check, mypy)
```

### 发布前检查

```
□ 所有测试通过
□ 代码检查通过
□ CHANGELOG.md 已更新
□ 版本号已更新
□ 文档已更新
□ PR 已审核通过
□ 已合并到 main 分支
□ Tag 已创建并推送
```

### 发布后检查

```
□ GitHub Actions 构建成功
□ GitHub Releases 已创建
□ 下载的可执行文件可正常运行
□ 文档链接正确
```

---

## 11. 参考文档

| 文档 | 说明 |
|---|---|
| [CONTRIBUTING.md](./CONTRIBUTING.md) | 协作流程、代码规范 |
| [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) | 故障排查指南 |
| [API.md](./API.md) | REST API 文档 |
| [CHANGELOG.md](./CHANGELOG.md) | 版本变更记录 |
