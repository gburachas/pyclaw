# pyclaw

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
git clone https://github.com/gburachas/pyclaw.git
cd pyclaw
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev,telegram,discord,slack]"
```

### pip install

```bash
pip install pyclaw
```

### With specific channel support

```bash
# Telegram only
pip install pyclaw[telegram]

# Discord only
pip install pyclaw[discord]

# Slack only
pip install pyclaw[slack]

# All channels
pip install pyclaw[telegram,discord,slack]
```

### Docker

```bash
docker build -t pyclaw:latest .
docker run --rm -v ~/.pyclaw:/root/.pyclaw pyclaw:latest
```

## Quick Start

```bash
# First-time setup — creates workspace, configures provider
pyclaw onboard

# Interactive chat
pyclaw agent

# One-shot mode
pyclaw agent "What files are in the current directory?"

# Start multi-channel gateway
pyclaw gateway
```

## Configuration

pyclaw uses YAML configuration. Default location: `~/.pyclaw/config.yaml`

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
      workspace: ~/.pyclaw/workspace

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
| `pyclaw onboard` | First-run setup wizard |
| `pyclaw agent [MESSAGE]` | Interactive chat or one-shot mode |
| `pyclaw gateway` | Start multi-channel gateway server |
| `pyclaw status` | Show agent/provider status |
| `pyclaw version` | Show version |
| `pyclaw auth login` | Add provider credentials |
| `pyclaw auth logout` | Remove provider credentials |
| `pyclaw cron list` | List scheduled jobs |
| `pyclaw cron add` | Add a cron job |
| `pyclaw skills list` | List installed skills |

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
src/pyclaw/
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
