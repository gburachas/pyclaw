# Migration Guide: PicoClaw (Go) → pyclaw (Python)

This guide helps existing PicoClaw (Go) users migrate to pyclaw.

## What Changed

| Aspect | Go (PicoClaw) | Python (pyclaw) |
|--------|---------------|-------------------|
| Binary | Single `picoclaw` binary | `pip install pyclaw` or Docker |
| Config format | `config.json` | `config.yaml` (YAML preferred, JSON still supported) |
| Config location | `~/.picoclaw/config.json` | `~/.pyclaw/config.yaml` |
| Workspace | `~/.picoclaw/workspace/` | `~/.pyclaw/workspace/` |
| CLI framework | Cobra | Typer |
| Package manager | Go modules | pip/pipx |

## Step-by-Step Migration

### 1. Install pyclaw

```bash
pip install pyclaw

# Or with channel support
pip install pyclaw[telegram,discord,slack]

# Or from source
git clone https://github.com/gburachas/pyclaw.git
cd pyclaw && pip install -e ".[dev,telegram,discord,slack]"
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

**pyclaw config.yaml (after):**
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
cp -r ~/.picoclaw/workspace/ ~/.pyclaw/workspace/
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
| `picoclaw` | `pyclaw agent` | Interactive chat |
| `picoclaw onboard` | `pyclaw onboard` | Same |
| `picoclaw gateway` | `pyclaw gateway` | Same |
| `picoclaw status` | `pyclaw status` | Same |
| `picoclaw version` | `pyclaw version` | Same |
| `picoclaw auth login` | `pyclaw auth login` | Same |
| `picoclaw cron list` | `pyclaw cron list` | Same |
| `picoclaw skills list` | `pyclaw skills list` | Same |

### 6. Docker Migration

**Go (before):**
```bash
docker run --rm -v ~/.picoclaw:/root/.picoclaw picoclaw:latest
```

**Python (after):**
```bash
docker run --rm -v ~/.pyclaw:/root/.pyclaw pyclaw:latest
```

## What's New in pyclaw

Features added in the Python port:

1. **YAML config** — More readable configuration format
2. **Better error messages** — Pydantic validation with detailed error descriptions
3. **croniter support** — Standard cron expressions for job scheduling
4. **Richer CLI** — Typer with auto-completion and rich formatting

## Known Differences

1. **No single binary** — pyclaw requires Python 3.11+ runtime (use Docker for isolation)
2. **Startup time** — Slightly slower than Go binary (~1-2s vs instant)
3. **Memory usage** — Higher baseline (~30-50 MB vs ~10 MB)
4. **GitHub Copilot provider** — Not yet ported (P2 priority)
5. **migrate command** — OpenClaw import not yet ported

## Troubleshooting

**Q: My sessions don't load?**
A: Session JSON format is compatible. Ensure you copied `~/.picoclaw/workspace/sessions/` to `~/.pyclaw/workspace/sessions/`.

**Q: Provider fails to connect?**
A: Check that API keys are set in your environment. Run `pyclaw auth login` to reconfigure.

**Q: Channel not starting?**
A: Install channel dependencies: `pip install pyclaw[telegram]` (or discord, slack).

**Q: Config validation errors?**
A: Field names changed to snake_case. Run `pyclaw onboard` to generate a fresh config.
