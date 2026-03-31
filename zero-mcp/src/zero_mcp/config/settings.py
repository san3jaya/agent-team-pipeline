"""Path constants, model settings, and project-wide configuration for zero-mcp."""

from pathlib import Path

# ── Directories ──────────────────────────────────────────────────────────────

CACHE_DIR: Path = Path.home() / ".cache" / "zero-mcp"
DB_PATH: Path = CACHE_DIR / "data.db"
MODEL_DIR: Path = CACHE_DIR / "models"

# ── Embedding model ──────────────────────────────────────────────────────────

MODEL_NAME = "all-MiniLM-L6-v2"
MODEL_URL = (
    f"https://huggingface.co/sentence-transformers/{MODEL_NAME}"
    "/resolve/main/onnx/model.onnx"
)
TOKENIZER_URL = (
    f"https://huggingface.co/sentence-transformers/{MODEL_NAME}"
    "/resolve/main/tokenizer.json"
)
EMBEDDING_DIM = 384

# ── Pattern defaults ─────────────────────────────────────────────────────────

MAX_PATTERNS = 500
DEFAULT_TOP_K = 3
DEFAULT_MIN_SCORE = 0.3

# ── Language detection ───────────────────────────────────────────────────────

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".py": "python",
    ".pyi": "python",
    ".php": "php",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".java": "java",
    ".kt": "kotlin",
    ".swift": "swift",
    ".cs": "csharp",
    ".c": "c",
    ".cpp": "cpp",
    ".h": "c",
    ".hpp": "cpp",
    ".vue": "vue",
    ".svelte": "svelte",
    ".dart": "dart",
    ".lua": "lua",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".css": "css",
    ".scss": "scss",
    ".less": "less",
    ".html": "html",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".toml": "toml",
    ".md": "markdown",
    ".sql": "sql",
    ".graphql": "graphql",
    ".gql": "graphql",
    ".proto": "protobuf",
    ".dockerfile": "dockerfile",
}

# ── File-role heuristics ─────────────────────────────────────────────────────
# Maps path substrings (lowercased) to a role label used by the indexer.

FILE_ROLE_PATTERNS: list[tuple[str, str]] = [
    ("test", "test"),
    ("spec", "test"),
    ("__test__", "test"),
    ("migration", "migration"),
    ("seed", "seed"),
    ("factory", "factory"),
    ("fixture", "fixture"),
    ("controller", "controller"),
    ("handler", "controller"),
    ("model", "model"),
    ("entity", "model"),
    ("schema", "model"),
    ("service", "service"),
    ("provider", "service"),
    ("repository", "repository"),
    ("middleware", "middleware"),
    ("route", "route"),
    ("router", "route"),
    ("view", "view"),
    ("template", "view"),
    ("component", "component"),
    ("hook", "hook"),
    ("util", "utility"),
    ("helper", "utility"),
    ("lib", "library"),
    ("config", "config"),
    ("setting", "config"),
    (".env", "config"),
    ("type", "type"),
    ("interface", "type"),
    ("dto", "type"),
    ("command", "command"),
    ("job", "job"),
    ("queue", "job"),
    ("event", "event"),
    ("listener", "event"),
    ("subscriber", "event"),
    ("exception", "exception"),
    ("error", "exception"),
]

# ── Default exclusion patterns for the indexer ───────────────────────────────
# Directories and file patterns that should always be skipped during indexing.

EXCLUDED_DIRS: set[str] = {
    "node_modules",
    "vendor",
    ".git",
    "__pycache__",
    ".pycache",
    "dist",
    "build",
    ".venv",
    "venv",
    ".env",
    ".tox",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".next",
    ".nuxt",
    ".output",
    ".turbo",
    ".svelte-kit",
    "coverage",
    ".coverage",
    "htmlcov",
    "target",  # Rust / Java
    "out",
    "bin",
    "obj",
    ".idea",
    ".vscode",
    ".DS_Store",
    "Thumbs.db",
    ".cache",
    "tmp",
    ".tmp",
    "logs",
    ".vercel",
    ".netlify",
    ".serverless",
    ".terraform",
    ".angular",
    "bower_components",
    "jspm_packages",
    ".parcel-cache",
    ".sass-cache",
    "eggs",
    ".egg-info",
    "site-packages",
    ".eggs",
    "sdist",
    "wheels",
    "pip-wheel-metadata",
}

EXCLUDED_EXTENSIONS: set[str] = {
    ".pyc",
    ".pyo",
    ".class",
    ".o",
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".bin",
    ".dat",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".wasm",
    ".map",
    ".min.js",
    ".min.css",
    ".lock",
    ".ico",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".webp",
    ".mp3",
    ".mp4",
    ".wav",
    ".ogg",
    ".ttf",
    ".woff",
    ".woff2",
    ".eot",
    ".otf",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".bz2",
    ".7z",
    ".rar",
}

# ── Project marker files (for skills discovery) ─────────────────────────────

PROJECT_MARKERS: dict[str, str] = {
    "package.json": "node",
    "composer.json": "php",
    "Cargo.toml": "rust",
    "go.mod": "go",
    "pyproject.toml": "python",
    "setup.py": "python",
    "requirements.txt": "python",
    "Gemfile": "ruby",
    "pom.xml": "java",
    "build.gradle": "java",
    "build.gradle.kts": "kotlin",
    "Package.swift": "swift",
    "pubspec.yaml": "dart",
    "mix.exs": "elixir",
    "Makefile": "make",
    "CMakeLists.txt": "cmake",
    "docker-compose.yml": "docker",
    "docker-compose.yaml": "docker",
    "Dockerfile": "docker",
    ".terraform": "terraform",
    "serverless.yml": "serverless",
}

# ── AI tool skill directories ───────────────────────────────────────────────

SKILL_DIRECTORIES: list[dict[str, str]] = [
    {"path": ".ai/skills", "tool": "generic"},
    {"path": ".opencode/skills", "tool": "opencode"},
    {"path": ".claude/skills", "tool": "claude-code"},
    {"path": ".cursor/rules", "tool": "cursor"},
    {"path": ".github/copilot-instructions.md", "tool": "copilot"},
    {"path": ".windsurfrules", "tool": "windsurf"},
    {"path": ".devin", "tool": "devin"},
]


def ensure_dirs() -> None:
    """Create required cache directories if they do not already exist."""
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
