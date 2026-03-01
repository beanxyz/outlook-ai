# outlook-ai Project Guidelines

## Project Overview

AI-powered Outlook.com CLI assistant using Ollama for local LLM processing. Provides email management, AI summarization, classification, and Telegram push notifications.

## Tech Stack

- **Python**: 3.10+
- **CLI Framework**: Typer + Rich
- **AI**: Ollama (local LLM) - default model: qwen2.5:14b
- **Email**: Microsoft Graph API (OAuth2)
- **Push**: Telegram Bot API
- **Data**: Pydantic for models, SQLite for cache, YAML for config
- **Auth**: MSAL (Microsoft Authentication Library)

## Project Structure

```
outlook-ai/
├── src/outlook_ai/
│   ├── __main__.py         # Entry point
│   ├── cli.py              # Typer CLI commands
│   ├── config.py           # Configuration management
│   ├── models.py           # Pydantic data models
│   ├── ai.py               # Ollama LLM processing
│   ├── mail.py             # IMAP mail client
│   ├── graph.py            # Microsoft Graph API client
│   ├── vip.py              # VIP rule engine
│   ├── cache.py            # SQLite cache
│   ├── prompts.py          # AI prompt templates
│   ├── utils.py            # Helper functions
│   ├── auth.py             # Authentication helpers
│   └── integrations/
│       ├── telegram.py      # Telegram push
│       ├── notion.py       # Notion integration
│       └── calendar.py     # Microsoft Calendar
├── tests/                  # Test files
├── README.md
├── pyproject.toml
└── .env.example
```

## Code Standards

### Data Models
- Use Pydantic `BaseModel` for all data structures
- Use `Field()` for default factories on mutable types
- Use `str, Enum` for enum types (e.g., `Priority(str, Enum)`)

### Type Hints
- Always use type hints for function parameters and return values
- Use `Optional[T]` instead of `T | None` for compatibility
- Use `TYPE_CHECKING` for circular imports

### CLI
- Use Typer with `@app.command()` decorator
- Use Rich `Console()` for colored output
- Use `Panel`, `Table`, `box` for formatted output

### Error Handling
- Use try/except with specific exception types
- Log errors with `logging.getLogger(__name__)`
- Return user-friendly error messages

### Configuration
- All config via `~/.outlook-ai/.env`
- Use `Config` class in `config.py` with Pydantic
- Load via `get_config()` singleton pattern

## Authentication

### Microsoft Graph API
Required environment variables:
```
AZURE_CLIENT_ID=<app registration client ID>
AZURE_CLIENT_SECRET=<client secret>
AZURE_TENANT_ID=<tenant ID>
OUTLOOK_EMAIL=your@live.com
```

Setup:
1. Register app in Azure Portal
2. Add API permissions: Mail.Read, Mail.ReadWrite, User.Read
3. Create client secret
4. Use MSAL for OAuth2 flow (handled in `graph.py`)

### Telegram Bot
```
TELEGRAM_TOKEN=<bot token>
TELEGRAM_CHAT_ID=<your chat ID>
```

## Key Constraints

1. **Ollama Required**: Must have Ollama running at `http://localhost:11434`
2. **Microsoft 365**: Requires valid Microsoft 365 account
3. **VIP Rules**: Stored in `~/.outlook-ai/vip_rules.yaml`
4. **Cache**: SQLite at `~/.outlook-ai/cache.db`

## Important Patterns

### Email Model
```python
class Email(BaseModel):
    uid: str
    subject: str
    sender: str
    sender_name: Optional[str] = None
    sender_email: Optional[str] = None
    to: List[str] = Field(default_factory=list)
    # ...
```

### CLI Command Pattern
```python
from outlook_ai.config import get_config

@app.command()
def my_command(count: int = typer.Option(10, "--count")):
    config = get_config()
    # ... implementation
```

### Integration Pattern
```python
from outlook_ai.integrations.telegram import TelegramPusher

pusher = TelegramPusher(
    token=config.telegram_token,
    chat_id=config.telegram_chat_id
)
pusher.push_vip_email(email, vip_match, summary)
```

## Dependencies

```
typer>=0.9.0
rich>=13.0.0
requests>=2.31.0
msal>=1.24.0
python-dotenv>=1.0.0
pydantic>=2.0.0
pyyaml>=6.0.0
```

## Notes

- Default model: `qwen2.5:14b` (configurable)
- Default scan: 3 days, 30 emails
- VIP rules: YAML-based, auto-creates default config
- Telegram markdown: Limited, use basic formatting
