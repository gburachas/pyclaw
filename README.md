# pytoclaw

Ultra-lightweight personal AI assistant — Python port of [PicoClaw](https://github.com/sipeed/picoclaw).

## Features

- **Multi-provider**: OpenAI, Anthropic, Groq, Ollama, DeepSeek, OpenRouter, and more
- **Tool system**: File I/O, shell execution, web search, scheduling
- **Persistent memory**: Long-term + session-based conversation memory
- **Multi-agent**: Multiple agents with workspace isolation
- **Extensible**: Skills marketplace, subagent spawning

## Quick Start

```bash
# Install
pip install -e .

# First-time setup
pytoclaw onboard

# Start chatting
pytoclaw agent

# One-shot mode
pytoclaw agent "What time is it?"
```

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Lint
ruff check src/

# Type check
mypy src/pytoclaw/
```

## License

MIT
