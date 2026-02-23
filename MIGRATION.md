# Migration Guide: PicoClaw (Go) → pytoclaw (Python)

This guide helps existing PicoClaw (Go) users migrate to pytoclaw.

## What Changed

| Aspect | Go (PicoClaw) | Python (pytoclaw) |
|--------|---------------|-------------------|
| Binary | Single `picoclaw` binary | `pip install pytoclaw` or Docker |
| Config format | `config.json` | `config.yaml` (YAML preferred, JSON still supported) |
| Config location | `~/.picoclaw/config.json` | `~/.pytoclaw/config.yaml` |
| Workspace | `~/.picoclaw/workspace/` | `~/.pytoclaw/workspace/` |
| CLI framework | Cobra | Typer |
| Package manager | Go modules | pip/pipx |

## Step-by-Step Migration

### 1. Install pytoclaw

```bash
pip install pytoclaw

# Or with channel support
pip install pytoclaw[telegram,discord,slack]

# Or from source
git clone https://github.com/gburachas/pytoclaw.git
cd pytoclaw && pip install -e ".[dev,telegram,discord,slack]"
```

### 2. Convert Configuration

Your Go `config.json` needs to be converted to YAML format. The structure is similar but not identical.

**Go config.json (before):**
```json
{
  "providers": {
    "default": "anthropic/claude-sonnet-4-20250514",
    "list": [
      {
        "name": "anthropic",
        "kind": "anthropic",
        "apiKeyEnv": "ANTHROPIC_API_KEY"
      }
    ]
  },
  "agents": {
    "default": "main",
    "list": [
      {
        "name": "main",
        "model": "anthropic/claude-sonnet-4-20250514"
      }
    ]
  }
}
```

**pytoclaw config.yaml (after):**
```yaml
providers:
  default: "anthropic/claude-sonnet-4-20250514"
  list:
    - name: anthropic
      kind: anthropic
      api_key_env: ANTHROPIC_API_KEY

agents:
  default: main
  list:
    - name: main
      model: "anthropic/claude-sonnet-4-20250514"
```

Key differences:
- `apiKeyEnv` → `api_key_env` (snake_case)
- `baseUrl` → `base_url`
- `maxTokens` → `max_tokens`
- All field names use snake_case (Python convention)
- YAML uses `true`/`false` instead of JSON booleans (both work)

### 3. Copy Workspace Files

Your workspace files (IDENTITY.md, SOUL.md, memory, sessions, skills) are fully compatible:

```bash
# Copy workspace to new location
cp -r ~/.picoclaw/workspace/ ~/.pytoclaw/workspace/
```

These files work unchanged:
- `IDENTITY.md` — Agent identity prompt
- `SOUL.md` — Base personality prompt
- `AGENT.md` — Agent-specific instructions
- `USER.md` — User preferences
- `memory/MEMORY.md` — Long-term memory
- `memory/daily/` — Daily notes
- `sessions/` — Conversation sessions (JSON)
- `skills/` — Installed skills

### 4. Update Environment Variables

Environment variables remain the same:
- `ANTHROPIC_API_KEY`
- `OPENAI_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `DISCORD_BOT_TOKEN`
- `SLACK_BOT_TOKEN` / `SLACK_APP_TOKEN`

### 5. CLI Command Mapping

| Go Command | Python Command | Notes |
|-----------|---------------|-------|
| `picoclaw` | `pytoclaw agent` | Interactive chat |
| `picoclaw onboard` | `pytoclaw onboard` | Same |
| `picoclaw gateway` | `pytoclaw gateway` | Same |
| `picoclaw status` | `pytoclaw status` | Same |
| `picoclaw version` | `pytoclaw version` | Same |
| `picoclaw auth login` | `pytoclaw auth login` | Same |
| `picoclaw cron list` | `pytoclaw cron list` | Same |
| `picoclaw skills list` | `pytoclaw skills list` | Same |

### 6. Docker Migration

**Go (before):**
```bash
docker run --rm -v ~/.picoclaw:/root/.picoclaw picoclaw:latest
```

**Python (after):**
```bash
docker run --rm -v ~/.pytoclaw:/root/.pytoclaw pytoclaw:latest
```

## What's New in pytoclaw

Features added in the Python port:

1. **YAML config** — More readable configuration format
2. **Better error messages** — Pydantic validation with detailed error descriptions
3. **croniter support** — Standard cron expressions for job scheduling
4. **Richer CLI** — Typer with auto-completion and rich formatting

## Known Differences

1. **No single binary** — pytoclaw requires Python 3.11+ runtime (use Docker for isolation)
2. **Startup time** — Slightly slower than Go binary (~1-2s vs instant)
3. **Memory usage** — Higher baseline (~30-50 MB vs ~10 MB)
4. **GitHub Copilot provider** — Not yet ported (P2 priority)
5. **migrate command** — OpenClaw import not yet ported

## Troubleshooting

**Q: My sessions don't load?**
A: Session JSON format is compatible. Ensure you copied `~/.picoclaw/workspace/sessions/` to `~/.pytoclaw/workspace/sessions/`.

**Q: Provider fails to connect?**
A: Check that API keys are set in your environment. Run `pytoclaw auth login` to reconfigure.

**Q: Channel not starting?**
A: Install channel dependencies: `pip install pytoclaw[telegram]` (or discord, slack).

**Q: Config validation errors?**
A: Field names changed to snake_case. Run `pytoclaw onboard` to generate a fresh config.
