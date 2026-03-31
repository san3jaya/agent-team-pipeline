"""MCP server — registers all Phase 2 tools and manages shared state."""

from __future__ import annotations

import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from . import __version__
from .memory.embeddings import EmbeddingModel
from .memory.store import VectorStore
from .tools import drift, indexer, patterns, routing, skills

logger = logging.getLogger(__name__)

app = Server("zero-mcp")

# Shared state — lazily initialised on first tool call.
_store: VectorStore | None = None
_model: EmbeddingModel | None = None


def _get_store() -> VectorStore:
    """Return the shared :class:`VectorStore`, creating it on first access."""
    global _store, _model
    if _store is None:
        _model = EmbeddingModel()
        _store = VectorStore(embedding_model=_model)
    return _store


def _get_model() -> EmbeddingModel:
    """Return the shared :class:`EmbeddingModel`."""
    _get_store()  # ensures _model is initialised
    assert _model is not None
    return _model


# ─────────────────────────────────────────────────────────────────────────────
# Tool definitions
# ─────────────────────────────────────────────────────────────────────────────

_TOOLS: list[Tool] = [
    Tool(
        name="patterns_search",
        description="Search stored patterns by semantic similarity.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query text"},
                "top_k": {
                    "type": "integer",
                    "default": 3,
                    "description": "Max results to return",
                },
                "project": {"type": "string", "description": "Optional project scope"},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="patterns_store",
        description="Store a new pattern from a successful pipeline.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Pattern name"},
                "context": {
                    "type": "string",
                    "description": "When this pattern applies",
                },
                "approach": {"type": "string", "description": "What worked"},
                "outcome": {"type": "string", "description": "Result"},
                "project": {"type": "string", "description": "Optional project scope"},
            },
            "required": ["name", "context", "approach", "outcome"],
        },
    ),
    Tool(
        name="patterns_prune",
        description="Prune old / unused patterns.",
        inputSchema={
            "type": "object",
            "properties": {
                "max_age_days": {"type": "integer", "default": 90},
            },
        },
    ),
    Tool(
        name="drift_check",
        description="Check if code changes drift from the original task.",
        inputSchema={
            "type": "object",
            "properties": {
                "task_description": {"type": "string"},
                "changed_files": {"type": "array", "items": {"type": "string"}},
                "diff_summary": {"type": "string"},
            },
            "required": ["task_description", "changed_files", "diff_summary"],
        },
    ),
    Tool(
        name="model_recommend",
        description="Recommend a model tier for the given agent and task.",
        inputSchema={
            "type": "object",
            "properties": {
                "agent": {"type": "string"},
                "task_classification": {"type": "string"},
                "task_description": {"type": "string"},
            },
            "required": ["agent", "task_classification"],
        },
    ),
    Tool(
        name="skills_discover",
        description="Scan project for AI tool skills and project markers.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
                "query": {
                    "type": "string",
                    "description": "Optional semantic search query",
                },
            },
            "required": ["project_path"],
        },
    ),
    Tool(
        name="project_index",
        description="Build or refresh the codebase index for faster exploration.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
                "force": {"type": "boolean", "default": False},
            },
            "required": ["project_path"],
        },
    ),
    Tool(
        name="project_query",
        description="Query the project index — find files by type, path, or query.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
                "query": {"type": "string"},
                "file_types": {"type": "array", "items": {"type": "string"}},
                "path_pattern": {"type": "string"},
            },
            "required": ["project_path"],
        },
    ),
    Tool(
        name="project_dependencies",
        description="Get import/dependency graph for a specific file.",
        inputSchema={
            "type": "object",
            "properties": {
                "project_path": {"type": "string"},
                "file_path": {"type": "string"},
            },
            "required": ["project_path", "file_path"],
        },
    ),
    Tool(
        name="health",
        description="Server health check.",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="reset",
        description="Reset all data (destructive).",
        inputSchema={
            "type": "object",
            "properties": {
                "confirm": {"type": "boolean"},
            },
            "required": ["confirm"],
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[Tool]:
    """Return the list of available MCP tools."""
    return _TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    """Dispatch an incoming tool call to the appropriate handler."""
    try:
        result = _dispatch(name, arguments)
    except Exception as exc:
        logger.exception("Tool %s failed", name)
        result = {"error": str(exc)}

    return [TextContent(type="text", text=json.dumps(result, default=str))]


def _dispatch(name: str, args: dict[str, Any]) -> dict:
    """Route a tool call to its implementation and return the result dict."""
    store = _get_store()
    model = _get_model()

    if name == "patterns_search":
        return patterns.search(
            store,
            query=args["query"],
            top_k=args.get("top_k", 3),
            project=args.get("project"),
        )

    if name == "patterns_store":
        return patterns.store(
            store,
            name=args["name"],
            context=args["context"],
            approach=args["approach"],
            outcome=args["outcome"],
            project=args.get("project"),
        )

    if name == "patterns_prune":
        return patterns.prune(
            store,
            max_age_days=args.get("max_age_days", 90),
        )

    if name == "drift_check":
        return drift.check(
            model,
            task_description=args["task_description"],
            changed_files=args["changed_files"],
            diff_summary=args["diff_summary"],
        )

    if name == "model_recommend":
        return routing.recommend(
            agent=args["agent"],
            task_classification=args["task_classification"],
            task_description=args.get("task_description"),
        )

    if name == "skills_discover":
        return skills.discover(
            project_path=args["project_path"],
            query=args.get("query"),
            embedding_model=model,
        )

    if name == "project_index":
        return indexer.index_project(
            project_path=args["project_path"],
            force=args.get("force", False),
            db_conn=store.conn,
        )

    if name == "project_query":
        return indexer.query_project(
            project_path=args["project_path"],
            query=args.get("query"),
            file_types=args.get("file_types"),
            path_pattern=args.get("path_pattern"),
            db_conn=store.conn,
        )

    if name == "project_dependencies":
        return indexer.get_dependencies(
            project_path=args["project_path"],
            file_path=args["file_path"],
            db_conn=store.conn,
        )

    if name == "health":
        return {
            "status": "ok",
            "version": __version__,
            "db_size": store.get_db_size(),
            "pattern_count": store.get_pattern_count(),
        }

    if name == "reset":
        if not args.get("confirm"):
            return {"reset": False, "reason": "confirm must be true"}
        store.conn.execute("DELETE FROM file_imports")
        store.conn.execute("DELETE FROM file_exports")
        store.conn.execute("DELETE FROM project_files")
        store.conn.execute("DELETE FROM mcp_calls")
        store.conn.execute("DELETE FROM steps")
        store.conn.execute("DELETE FROM sessions")
        store.conn.execute("DELETE FROM patterns")
        store.conn.commit()
        return {"reset": True}

    return {"error": f"Unknown tool: {name}"}


# ─────────────────────────────────────────────────────────────────────────────
# Entry-point
# ─────────────────────────────────────────────────────────────────────────────


async def main() -> None:
    """Run the MCP server over stdio."""
    logger.info("Starting zero-mcp v%s", __version__)
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options(),
        )
