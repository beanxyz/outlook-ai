# outlook-ai

AI-powered Outlook.com CLI assistant using Ollama

## Features

- 📧 Read and manage Outlook emails via Microsoft Graph API
- 🤖 AI-powered email summarization using local Ollama models
- 🏷️ Automatic email classification
- ✍️ AI draft replies
- 🌐 Email translation
- 🔍 Smart semantic search
- 📋 Extract action items from emails
- 📱 Telegram push notifications (VIP alerts + daily summary)
- ⏰ VIP rule engine (school/payment notifications)

## Installation

```bash
# Clone the repository
git clone https://github.com/beanxyz/outlook-ai.git
cd outlook-ai

# Install dependencies
pip install -e .
```

## Configuration (Microsoft Graph API)

1. Register an Azure AD Application:
   - Go to https://portal.azure.com/#view/Microsoft_AAD_IAM/ActiveDirectoryMenuBlade/RegisteredApps
   - Click "New registration"
   - Name: outlook-ai
   - Supported account types: Accounts in any organizational directory (multitenant)
   - Redirect URI: http://localhost

2. Add API Permissions:
   - Go to your app → API permissions
   - Add Microsoft Graph → Delegated permissions
   - Add: `Mail.Read`, `Mail.ReadWrite`, `User.Read`

3. Create Client Secret:
   - Go to Certificates & secrets
   - New client secret
   - Copy the secret value (not the ID)

4. Get your Tenant ID:
   - Go to Microsoft Entra admin center
   - Copy your Tenant ID

5. Configure .env:
```
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
OUTLOOK_EMAIL=your@live.com
```

### Telegram Push (Optional)

1. Create a Telegram Bot:
   - Open @BotFather on Telegram
   - Send /newbot to create a new bot
   - Copy the Bot Token

2. Get your Chat ID:
   - Open @userinfobot on Telegram
   - Send /start to get your Chat ID

3. Add to .env:
```
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

## Usage

```bash
# View recent emails
outlook-ai inbox

# View unread emails
outlook-ai unread

# Generate AI summary
outlook-ai summary -d 7 -c 10

# Classify emails
outlook-ai classify

# Search emails
outlook-ai search "meeting" --semantic

# Translate email
outlook-ai translate <uid> --lang en

# List folders
outlook-ai folders

# Run full scan with push notifications
outlook-ai run-now
```

## Commands

| Command | Description |
|---------|-------------|
| `inbox` | View recent emails |
| `unread` | View unread emails |
| `summary` | AI summary of recent emails |
| `classify` | Classify emails using AI |
| `search` | Search emails (with semantic option) |
| `translate` | Translate an email |
| `reply` | Draft an AI reply |
| `actions` | Extract action items |
| `folders` | List email folders |
| `models` | List available Ollama models |
| `config` | Configure settings |
| `run-now` | Full scan with push notifications |

## Push Notifications (run-now)

The `run-now` command performs a full email scan and sends push notifications:

```bash
# Run with default settings (3 days, 30 emails)
outlook-ai run-now

# Custom scan range
outlook-ai run-now -d 7 -c 50
```

### Push Triggers:

| Trigger | Description |
|---------|-------------|
| **VIP Email** | School/payment emails → Immediate Telegram push |
| **Daily Summary** | AI summary + stats → Telegram push |

### VIP Rules:

The VIP engine automatically detects:
- 🏫 School emails (Oakhill, Seesaw, Compass, etc.)
- 💰 Payment notifications (Flexischools, invoices, etc.)

You can customize rules in `~/.outlook-ai/vip_rules.yaml`.

## Requirements

- Python 3.10+
- Ollama running locally (http://localhost:11434)
- Microsoft 365 account

## Dependencies

- typer, rich, requests
- msal (for Microsoft Graph API)
- pydantic, python-dotenv
- pyyaml (for VIP rules config)

## License

MIT
