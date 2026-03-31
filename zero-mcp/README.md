# zero-mcp

MCP server for the **Zero** multi-agent orchestration system. Provides vector memory, drift detection, model routing, skill discovery, and codebase indexing — all running locally with zero LLM API calls.

## Installation

```bash
# Recommended: run directly via uvx (auto-installs Python + dependencies)
uvx zero-mcp

# Or install with pip / uv
pip install zero-mcp
```

## MCP Registration

### OpenCode (`~/.config/opencode/config.toml`)

```toml
[mcp.zero]
type = "stdio"
command = "uvx"
args = ["zero-mcp"]
```

### Claude Code (`~/.claude/claude_desktop_config.json`)

```json
{
  "mcpServers": {
    "zero": {
      "command": "uvx",
      "args": ["zero-mcp"]
    }
  }
}
```

### GitHub Copilot (`.vscode/mcp.json`)

```json
{
  "servers": {
    "zero": {
      "command": "uvx",
      "args": ["zero-mcp"]
    }
  }
}
```

### Cursor (`~/.cursor/mcp.json`)

```json
{
  "mcpServers": {
    "zero": {
      "command": "uvx",
      "args": ["zero-mcp"]
    }
  }
}
```

### Windsurf (`~/.windsurf/mcp.json`)

```json
{
  "mcpServers": {
    "zero": {
      "command": "uvx",
      "args": ["zero-mcp"]
    }
  }
}
```

## Available Tools (Phase 2)

| Tool | Description |
|------|-------------|
| `patterns_search` | Semantic search over stored patterns |
| `patterns_store` | Store a new pattern with embedding |
| `patterns_prune` | Remove old/low-relevance patterns |
| `drift_check` | Check if code changes drift from the task |
| `model_recommend` | Recommend a model tier for an agent |
| `skills_discover` | Scan project for AI tool skills and markers |
| `project_index` | Build or refresh the codebase index |
| `project_query` | Query indexed files by type, path, or text |
| `project_dependencies` | Get import/dependency graph for a file |
| `health` | Server health check |
| `reset` | Reset all data (destructive) |

## Development

```bash
cd zero-mcp
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Architecture

- **Memory layer**: `embeddings.py` → `similarity.py` → `store.py`
- **Tools layer**: `patterns.py`, `drift.py`, `routing.py`, `skills.py`, `indexer.py`
- **Server layer**: `server.py` registers MCP tools, initializes shared state
- **Config**: `settings.py` (paths/constants), `pricing.py` (model costs)

All data is stored locally in `~/.cache/zero-mcp/`. The ONNX embedding model (~22 MB) is downloaded on first use.

## License

See the root repository LICENSE file.
