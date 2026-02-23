# pytoclaw

Ultra-lightweight personal AI assistant — Python port of [PicoClaw](https://github.com/sipeed/picoclaw).

## Features

- **Multi-provider LLM**: OpenAI, Anthropic Claude, Groq, Ollama, DeepSeek, OpenRouter, and more
- **Fallback chains**: Automatic failover between providers with cooldown tracking
- **20+ built-in tools**: File I/O, shell execution, web search/fetch, cron scheduling, subagent spawning, hardware I2C/SPI
- **Multi-channel**: Telegram, Discord, Slack, WhatsApp, LINE, DingTalk, Feishu, WeCom, OneBot/QQ, MaixCAM
- **Persistent memory**: Long-term (MEMORY.md) + daily notes + session-based conversation history
- **Multi-agent**: Multiple agents with workspace isolation, route-based dispatching
- **Extensible**: Skills marketplace, subagent spawning with allowlists
- **Services**: Heartbeat monitoring, cron job scheduling, USB device detection
- **Sandboxed execution**: 30+ dangerous command deny patterns for safe shell access

## Installation

### From source (recommended for development)

```bash
git clone https://github.com/gburachas/pytoclaw.git
cd pytoclaw
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,telegram,discord,slack]"
```

### pip install

```bash
pip install pytoclaw
```

### With specific channel support

```bash
# Telegram only
pip install pytoclaw[telegram]

# Discord only
pip install pytoclaw[discord]

# Slack only
pip install pytoclaw[slack]

# All channels
pip install pytoclaw[telegram,discord,slack]
```

### Docker

```bash
docker build -t pytoclaw:latest .
docker run --rm -v ~/.pytoclaw:/root/.pytoclaw pytoclaw:latest
```

## Quick Start

```bash
# First-time setup — creates workspace, configures provider
pytoclaw onboard

# Interactive chat
pytoclaw agent

# One-shot mode
pytoclaw agent "What files are in the current directory?"

# Start multi-channel gateway
pytoclaw gateway
```

## Configuration

pytoclaw uses YAML configuration. Default location: `~/.pytoclaw/config.yaml`

```yaml
providers:
  default: "anthropic/claude-sonnet-4-20250514"
  list:
    - name: anthropic
      kind: anthropic
      api_key_env: ANTHROPIC_API_KEY
    - name: openai
      kind: openai
      api_key_env: OPENAI_API_KEY

agents:
  default: main
  list:
    - name: main
      model: "anthropic/claude-sonnet-4-20250514"
      workspace: ~/.pytoclaw/workspace

channels:
  telegram:
    enabled: true
    token_env: TELEGRAM_BOT_TOKEN

tools:
  exec:
    enabled: true
    timeout_seconds: 30
    deny_enabled: true
```

## CLI Commands

| Command | Description |
|---------|-------------|
| `pytoclaw onboard` | First-run setup wizard |
| `pytoclaw agent [MESSAGE]` | Interactive chat or one-shot mode |
| `pytoclaw gateway` | Start multi-channel gateway server |
| `pytoclaw status` | Show agent/provider status |
| `pytoclaw version` | Show version |
| `pytoclaw auth login` | Add provider credentials |
| `pytoclaw auth logout` | Remove provider credentials |
| `pytoclaw cron list` | List scheduled jobs |
| `pytoclaw cron add` | Add a cron job |
| `pytoclaw skills list` | List installed skills |

### In-Chat Slash Commands

| Command | Description |
|---------|-------------|
| `/help` | Show available commands |
| `/model [name]` | Switch LLM model |
| `/tools` | List available tools |
| `/clear` | Clear conversation history |

## Architecture

```
┌─────────────────────────────────────────────┐
│                    CLI / Gateway              │
├───────────┬───────────┬───────────┬──────────┤
│ Telegram  │ Discord   │ Slack     │ ...      │  ← Channels
├───────────┴───────────┴───────────┴──────────┤
│              Message Bus (asyncio.Queue)       │
├──────────────────────────────────────────────┤
│              Agent Loop                       │
│  ┌──────────┐ ┌───────────┐ ┌─────────────┐ │
│  │ Context   │ │ Session   │ │ Memory      │ │
│  │ Builder   │ │ Manager   │ │ Store       │ │
│  └──────────┘ └───────────┘ └─────────────┘ │
├──────────────────────────────────────────────┤
│  Provider Layer (Fallback Chain)              │
│  ┌──────────┐ ┌───────────┐ ┌─────────────┐ │
│  │ Anthropic │ │ OpenAI    │ │ Ollama/etc  │ │
│  └──────────┘ └───────────┘ └─────────────┘ │
├──────────────────────────────────────────────┤
│  Tool Registry                                │
│  file_tools │ exec │ web │ cron │ hardware   │
├──────────────────────────────────────────────┤
│  Services: Heartbeat │ Cron │ Device Monitor  │
└──────────────────────────────────────────────┘
```

## Development

```bash
# Install with all dev + channel dependencies
make dev

# Run tests
make test

# Run tests with coverage
make test-cov

# Lint
make lint

# Auto-fix lint issues
make lint-fix

# Type check
make typecheck

# Clean build artifacts
make clean
```

## Project Structure

```
src/pytoclaw/
├── models.py              # Core Pydantic data models
├── protocols.py           # Abstract interfaces (LLMProvider, Tool, Channel)
├── config/                # YAML/JSON config loading
├── providers/             # LLM provider adapters + fallback chain
├── tools/                 # Built-in tools (file, exec, web, cron, hardware)
├── agent/                 # Agent loop, registry, context builder
├── session/               # Session persistence
├── memory/                # Long-term + daily memory store
├── bus/                   # Async message bus
├── routing/               # Multi-agent route resolver
├── channels/              # Chat platform adapters
├── services/              # Background services (heartbeat, cron, devices)
└── cli/                   # Typer CLI commands
```

## Requirements

- Python 3.11+
- An LLM API key (Anthropic, OpenAI, or compatible provider)

## License

MIT
