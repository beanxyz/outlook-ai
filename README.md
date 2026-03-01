# outlook-ai

AI-powered Outlook.com CLI assistant using Ollama

## Features

- 📧 Read and manage Outlook emails via IMAP or Microsoft Graph API
- 🤖 AI-powered email summarization using local Ollama models
- 🏷️ Automatic email classification
- ✍️ AI draft replies
- 🌐 Email translation
- 🔍 Smart semantic search
- 📋 Extract action items from emails

## Installation

```bash
# Clone the repository
git clone https://github.com/beanxyz/outlook-ai.git
cd outlook-ai

# Install dependencies
pip install -e .
```

## Configuration

### Option 1: IMAP (App Password)

1. Create an app password for your Microsoft account:
   - Go to https://account.microsoft.com/security
   - Enable 2FA if not already enabled
   - Create an app password

2. Set up configuration:
```bash
outlook-ai config --email your@live.com --password xxxx-xxxx-xxxx-xxxx --save
```

### Option 2: Microsoft Graph API (OAuth)

Set these environment variables:
```
AZURE_CLIENT_ID=your-client-id
OUTLOOK_EMAIL=your@live.com
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

## Requirements

- Python 3.10+
- Ollama running locally (http://localhost:11434)

## License

MIT
