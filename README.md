# outlook-ai

AI-powered Outlook.com CLI assistant using Ollama

## 功能特性

- 📧 通过 Microsoft Graph API 读取和管理 Outlook 邮件
- 🤖 使用本地 Ollama 模型进行 AI 邮件摘要
- 🏷️ 自动邮件分类
- ✍️ AI 草拟回复
- 🌐 邮件翻译
- 🔍 智能语义搜索
- 📋 从邮件中提取待办事项
- 📱 Telegram 推送通知（VIP 提醒 + 每日摘要）
- ⏰ VIP 规则引擎（学校/缴费通知）

## 项目结构

```
outlook-ai/
├── src/outlook_ai/          # 主代码目录
│   ├── __main__.py           # 入口点，支持 `python -m outlook_ai` 运行
│   ├── cli.py                # 命令行界面 - 所有命令入口
│   ├── config.py             # 配置管理 - 读取 .env 和配置文件
│   ├── models.py             # 数据模型 - Email, EmailClassification 等
│   ├── prompts.py            # AI 提示词模板
│   ├── utils.py              # 工具函数
│   │
│   ├── mail.py               # IMAP 邮件客户端（旧版）
│   ├── graph.py              # Microsoft Graph API 客户端（新版）
│   ├── ai.py                 # Ollama AI 处理模块
│   ├── cache.py              # SQLite 缓存
│   ├── vip.py                # VIP 规则引擎
│   ├── auth.py               # 认证相关
│   │
│   └── integrations/         # 集成模块
│       ├── telegram.py       # Telegram 推送
│       ├── notion.py         # Notion 集成
│       └── calendar.py       # 日历集成
│
├── tests/                    # 测试目录
│   ├── test_ai.py
│   ├── test_mail.py
│   ├── test_cache.py
│   ├── test_graph.py
│   ├── test_telegram.py
│   └── test_vip.py
│
└── pyproject.toml            # 项目配置
```

### 核心模块说明

| 文件 | 功能 |
|------|------|
| `cli.py` | 命令行入口，定义所有命令（inbox, summary, classify 等） |
| `config.py` | 管理配置，支持从 .env 文件读取，设置默认值 |
| `models.py` | 数据结构：Email, EmailClassification, VIPMatch, ActionItem |
| `graph.py` | Microsoft Graph API 客户端，读取邮件、搜索、标记已读 |
| `ai.py` | Ollama AI 模块：摘要、分类、翻译、提取待办 |
| `vip.py` | VIP 规则引擎，匹配学校/缴费邮件 |
| `cache.py` | SQLite 本地缓存，避免重复处理 |
| `integrations/telegram.py` | Telegram 机器人推送 |

## 安装

```bash
# 克隆仓库
git clone https://github.com/beanxyz/outlook-ai.git
cd outlook-ai

# 安装依赖
pip install -e .
```

## 配置 (Microsoft Graph API)

1. 注册 Azure AD 应用:
   - 访问 https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/RegisteredApps
   - 点击 "New registration"
   - 名称: outlook-ai
   - 支持的账户类型: Accounts in any organizational directory (multitenant)
   - 重定向 URI: http://localhost

2. 添加 API 权限:
   - 进入应用 → API permissions
   - 添加 Microsoft Graph → Delegated permissions
   - 添加: `Mail.Read`, `User.Read`

3. 创建客户端密钥:
   - 进入 Certificates & secrets
   - 新建客户端密钥
   - 复制密钥值（不是 ID）

4. 获取租户 ID:
   - 进入 Microsoft Entra admin center
   - 复制租户 ID

5. 配置 .env:
```
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
OUTLOOK_EMAIL=your@live.com
```

### Telegram 推送 (可选)

1. 创建 Telegram 机器人:
   - 在 Telegram 打开 @BotFather
   - 发送 /newbot 创建新机器人
   - 复制 Bot Token

2. 获取 Chat ID:
   - 在 Telegram 打开 @userinfobot
   - 发送 /start 获取 Chat ID

3. 添加到 .env:
```
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

### 可配置关键词

可以在 .env 中自定义分类关键词：

```bash
SPAM_KEYWORDS=casino,winner,prize,bonus
BILL_KEYWORDS=payment,invoice,receipt,due
WORK_KEYWORDS=linkedin,job,hiring,resume
NOTIFICATION_SENDERS=flexischools,westpac,notification
```

## 使用方法

```bash
# 查看最近邮件
outlook-ai inbox

# 查看未读邮件
outlook-ai unread

# 生成 AI 摘要
outlook-ai summary -d 7 -c 10

# 分类邮件
outlook-ai classify

# 搜索邮件
outlook-ai search "meeting" --semantic

# 翻译邮件
outlook-ai translate <uid> --lang en

# 列出文件夹
outlook-ai folders

# 运行完整扫描并推送通知
outlook-ai run-now
```

## 命令说明

| 命令 | 说明 |
|------|------|
| `inbox` | 查看最近邮件 |
| `unread` | 查看未读邮件 |
| `summary` | AI 摘要 |
| `classify` | AI 分类 |
| `search` | 搜索邮件（支持语义） |
| `translate` | 翻译邮件 |
| `reply` | AI 草拟回复 |
| `actions` | 提取待办事项 |
| `folders` | 列出邮件文件夹 |
| `models` | 列出可用 Ollama 模型 |
| `config` | 配置设置 |
| `run-now` | 完整扫描并推送通知 |

## 推送通知 (run-now)

`run-now` 命令执行完整邮件扫描并发送推送通知：

```bash
# 使用默认设置（3 天，30 封邮件）
outlook-ai run-now

# 自定义扫描范围
outlook-ai run-now -d 7 -c 50
```

### 推送触发条件:

| 触发条件 | 说明 |
|----------|------|
| **VIP 邮件** | 学校/缴费邮件 → 立即 Telegram 推送 |
| **每日摘要** | AI 摘要 + 统计 → Telegram 推送 |

### VIP 规则:

VIP 引擎自动检测：
- 🏫 学校邮件 (Oakhill, Seesaw, Compass 等)
- 💰 缴费通知 (Flexischools, 发票等)

可以在 `~/.outlook-ai/vip_rules.yaml` 自定义规则。

## 要求

- Python 3.10+
- 本地运行 Ollama (http://localhost:11434)
- Microsoft 365 账户

## 依赖

- typer, rich, requests
- msal (用于 Microsoft Graph API)
- pydantic, python-dotenv
- pyyaml (用于 VIP 规则配置)

## 测试

```bash
# 运行所有测试
python -m pytest tests/ -v
```

## License

MIT
