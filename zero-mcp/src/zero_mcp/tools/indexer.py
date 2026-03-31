"""Codebase indexer: walk, parse exports/imports, store in SQLite.

Three public entry-points:

* :func:`index_project` — build or incrementally refresh the file index.
* :func:`query_project` — query indexed files with optional filters.
* :func:`get_dependencies` — return the import/dependency graph for one file.
"""

from __future__ import annotations

import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

from ..config.settings import (
    EXCLUDED_DIRS,
    EXCLUDED_EXTENSIONS,
    EXTENSION_TO_LANGUAGE,
    FILE_ROLE_PATTERNS,
)

logger = logging.getLogger(__name__)

# Filesystem locations that should never be indexed or queried.
_SENSITIVE_ROOTS = {"/etc", "/proc", "/sys", "/dev"}
_SENSITIVE_HOME_DIRS = {".ssh", ".aws", ".gnupg"}


def _validate_project_path(resolved: Path) -> None:
    """Raise :class:`ValueError` if *resolved* points to a sensitive location.

    Checks against system directories (``/etc``, ``/proc``, …) and
    home-directory secret folders (``.ssh``, ``.aws``, ``.gnupg``).
    """
    resolved_str = str(resolved)
    for sensitive in _SENSITIVE_ROOTS:
        if resolved_str == sensitive or resolved_str.startswith(sensitive + "/"):
            raise ValueError(f"Refusing to operate on sensitive path: {resolved}")
    for secret_dir in _SENSITIVE_HOME_DIRS:
        if f"/{secret_dir}" in resolved_str:
            raise ValueError(
                f"Refusing to operate on path containing sensitive directory "
                f"'{secret_dir}': {resolved}"
            )


# ═══════════════════════════════════════════════════════════════════════════════
# Public API
# ═══════════════════════════════════════════════════════════════════════════════


def index_project(
    project_path: str,
    force: bool = False,
    db_conn: sqlite3.Connection | None = None,
) -> dict:
    """Build or refresh the codebase index for *project_path*.

    Uses file *mtime* for incremental updates: only files whose modification
    time has changed since the last index run are re-processed.

    Args:
        project_path: Absolute path to the project root directory.
        force: When ``True``, re-index every file regardless of mtime.
        db_conn: Existing SQLite connection (with tables already created).
            Required — callers are expected to pass the shared
            :class:`~zero_mcp.memory.store.VectorStore` connection.

    Returns:
        ``{"indexed": True, "files": int, "new": int, "updated": int,
           "cached": bool, "duration_ms": int}``
    """
    if db_conn is None:
        return {"error": "db_conn is required"}

    root = Path(project_path).resolve()
    if not root.is_dir():
        return {"error": f"Not a directory: {project_path}"}

    _validate_project_path(root)

    project_key = str(root)
    start = time.monotonic()

    # Gather existing index state  {relative_path: (id, modified_at)}
    existing: dict[str, tuple[int, str]] = {}
    if not force:
        rows = db_conn.execute(
            "SELECT id, file_path, modified_at FROM project_files "
            "WHERE project_path = ?",
            (project_key,),
        ).fetchall()
        for row in rows:
            existing[row[1]] = (row[0], row[2])

    new_count = 0
    updated_count = 0
    total_files = 0
    seen_paths: set[str] = set()

    for file_path in _walk_project(root):
        rel = str(file_path.relative_to(root))
        seen_paths.add(rel)
        total_files += 1

        mtime_iso = _mtime_iso(file_path)
        language = _detect_language(file_path)
        role = _detect_role(rel)
        size_bytes = file_path.stat().st_size

        if rel in existing and not force:
            file_id, old_mtime = existing[rel]
            if old_mtime == mtime_iso:
                continue  # unchanged — skip
            # File was modified → update
            db_conn.execute(
                "UPDATE project_files SET language=?, role=?, size_bytes=?, "
                "modified_at=?, indexed_at=datetime('now') "
                "WHERE id=?",
                (language, role, size_bytes, mtime_iso, file_id),
            )
            _reindex_symbols(db_conn, file_id, file_path, language)
            updated_count += 1
        else:
            # New file
            cursor = db_conn.execute(
                "INSERT OR REPLACE INTO project_files "
                "(project_path, file_path, language, role, size_bytes, modified_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (project_key, rel, language, role, size_bytes, mtime_iso),
            )
            file_id = cursor.lastrowid
            _reindex_symbols(db_conn, file_id, file_path, language)  # type: ignore[arg-type]
            new_count += 1

    # Remove files that no longer exist on disk
    for rel, (file_id, _) in existing.items():
        if rel not in seen_paths:
            db_conn.execute("DELETE FROM project_files WHERE id=?", (file_id,))

    db_conn.commit()
    elapsed_ms = int((time.monotonic() - start) * 1000)

    return {
        "indexed": True,
        "files": total_files,
        "new": new_count,
        "updated": updated_count,
        "cached": new_count == 0 and updated_count == 0,
        "duration_ms": elapsed_ms,
    }


def query_project(
    project_path: str,
    query: str | None = None,
    file_types: list[str] | None = None,
    path_pattern: str | None = None,
    db_conn: sqlite3.Connection | None = None,
) -> dict:
    """Query the project index with optional filters.

    Args:
        project_path: Absolute project root.
        query: Free-text substring search against file paths and export names.
        file_types: Restrict to these languages (e.g. ``["typescript", "python"]``).
        path_pattern: SQL ``LIKE`` pattern applied to ``file_path``
            (e.g. ``"src/services/%"``).
        db_conn: Shared SQLite connection.

    Returns:
        ``{"files": [{"path", "language", "role", "exports", "size", "modified"}, …]}``
    """
    if db_conn is None:
        return {"error": "db_conn is required"}

    resolved = Path(project_path).resolve()
    _validate_project_path(resolved)
    project_key = str(resolved)
    conditions = ["pf.project_path = ?"]
    params: list[object] = [project_key]

    if file_types:
        placeholders = ", ".join("?" for _ in file_types)
        conditions.append(f"pf.language IN ({placeholders})")
        params.extend(file_types)

    if path_pattern:
        conditions.append("pf.file_path LIKE ?")
        params.append(path_pattern)

    where = " AND ".join(conditions)

    sql = (
        f"SELECT pf.id, pf.file_path, pf.language, pf.role, "
        f"pf.size_bytes, pf.modified_at "
        f"FROM project_files pf WHERE {where} "
        f"ORDER BY pf.file_path"
    )
    rows = db_conn.execute(sql, params).fetchall()

    files: list[dict] = []
    for row in rows:
        file_id, fpath, lang, role, size, modified = row

        # Fetch exports for this file
        exports_rows = db_conn.execute(
            "SELECT name, kind FROM file_exports WHERE file_id = ?",
            (file_id,),
        ).fetchall()
        exports = [{"name": e[0], "kind": e[1]} for e in exports_rows]

        entry = {
            "path": fpath,
            "language": lang,
            "role": role,
            "exports": exports,
            "size": size,
            "modified": modified,
        }

        # Optional: free-text filtering (against path + export names)
        if query:
            q_lower = query.lower()
            searchable = (
                fpath.lower() + " " + " ".join(e["name"].lower() for e in exports)
            )
            if q_lower not in searchable:
                continue

        files.append(entry)

    return {"files": files}


def get_dependencies(
    project_path: str,
    file_path: str,
    db_conn: sqlite3.Connection | None = None,
) -> dict:
    """Return the import graph for a specific file.

    Returns:
        ``{"imports": [str], "imported_by": [str], "related": [str]}``
    """
    if db_conn is None:
        return {"error": "db_conn is required"}

    resolved = Path(project_path).resolve()
    _validate_project_path(resolved)
    project_key = str(resolved)

    # Find the file
    row = db_conn.execute(
        "SELECT id FROM project_files WHERE project_path = ? AND file_path = ?",
        (project_key, file_path),
    ).fetchone()

    if not row:
        return {
            "error": f"File not indexed: {file_path}",
            "imports": [],
            "imported_by": [],
            "related": [],
        }

    file_id = row[0]

    # What this file imports
    import_rows = db_conn.execute(
        "SELECT import_path FROM file_imports WHERE file_id = ?",
        (file_id,),
    ).fetchall()
    imports = [r[0] for r in import_rows]

    # What imports this file (reverse lookup)
    imported_by_rows = db_conn.execute(
        "SELECT pf.file_path FROM file_imports fi "
        "JOIN project_files pf ON fi.file_id = pf.id "
        "WHERE fi.import_path LIKE ? AND pf.project_path = ?",
        (f"%{file_path}%", project_key),
    ).fetchall()
    imported_by = [r[0] for r in imported_by_rows if r[0] != file_path]

    # Related = union of imports + imported_by (deduplicated)
    related = sorted(set(imports) | set(imported_by))

    return {
        "imports": imports,
        "imported_by": imported_by,
        "related": related,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# File tree walking
# ═══════════════════════════════════════════════════════════════════════════════


def _walk_project(root: Path) -> list[Path]:
    """Recursively collect indexable files under *root*, respecting exclusions."""
    results: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root, topdown=True):
        # Prune excluded directories in-place
        dirnames[:] = [
            d
            for d in dirnames
            if d not in EXCLUDED_DIRS
            and not d.startswith(".")
            and not d.endswith(".egg-info")
        ]

        for fname in filenames:
            fpath = Path(dirpath) / fname
            ext = fpath.suffix.lower()
            if ext in EXCLUDED_EXTENSIONS:
                continue
            # Skip hidden files
            if fname.startswith("."):
                continue
            # Only index files whose extension we recognise
            if ext in EXTENSION_TO_LANGUAGE:
                results.append(fpath)

    return results


# ═══════════════════════════════════════════════════════════════════════════════
# Detection helpers
# ═══════════════════════════════════════════════════════════════════════════════


def _detect_language(path: Path) -> str | None:
    """Return the language string for *path* based on its extension."""
    return EXTENSION_TO_LANGUAGE.get(path.suffix.lower())


def _detect_role(rel_path: str) -> str | None:
    """Heuristic role detection from a relative file path."""
    lower = rel_path.lower()
    for pattern, role in FILE_ROLE_PATTERNS:
        if pattern in lower:
            return role
    return None


def _mtime_iso(path: Path) -> str:
    """Return the file's modification time as an ISO-8601 string."""
    ts = path.stat().st_mtime
    return datetime.fromtimestamp(ts, tz=timezone.utc).isoformat()


# ═══════════════════════════════════════════════════════════════════════════════
# Symbol extraction (re-index exports + imports for one file)
# ═══════════════════════════════════════════════════════════════════════════════


def _reindex_symbols(
    conn: sqlite3.Connection,
    file_id: int,
    file_path: Path,
    language: str | None,
) -> None:
    """Delete old exports/imports for *file_id* and re-extract them."""
    conn.execute("DELETE FROM file_exports WHERE file_id = ?", (file_id,))
    conn.execute("DELETE FROM file_imports WHERE file_id = ?", (file_id,))

    try:
        content = file_path.read_text(errors="replace")
    except OSError:
        return

    extractor = _EXTRACTORS.get(language)
    if extractor is None:
        return

    exports, imports = extractor(content)

    for exp in exports:
        conn.execute(
            "INSERT OR IGNORE INTO file_exports (file_id, name, kind, line_number) "
            "VALUES (?, ?, ?, ?)",
            (file_id, exp["name"], exp["kind"], exp.get("line")),
        )
    for imp in imports:
        conn.execute(
            "INSERT INTO file_imports (file_id, import_path, raw_import) "
            "VALUES (?, ?, ?)",
            (file_id, imp["path"], imp["raw"]),
        )


# ═══════════════════════════════════════════════════════════════════════════════
# Per-language parsers
# ═══════════════════════════════════════════════════════════════════════════════


def _extract_typescript(content: str) -> tuple[list[dict], list[dict]]:
    """Extract exports and imports from TypeScript / JavaScript source."""
    exports: list[dict] = []
    imports: list[dict] = []

    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()

        # Exports: export class/function/const/type/interface/enum
        m = re.match(
            r"export\s+(?:default\s+)?(?:abstract\s+)?"
            r"(class|function|const|let|var|type|interface|enum)\s+"
            r"(\w+)",
            stripped,
        )
        if m:
            kind = m.group(1)
            if kind in ("let", "var"):
                kind = "const"
            exports.append({"name": m.group(2), "kind": kind, "line": lineno})
            continue

        # module.exports
        m = re.match(r"module\.exports\s*=\s*(\w+)", stripped)
        if m:
            exports.append(
                {"name": m.group(1), "kind": "module_export", "line": lineno}
            )
            continue

        # Imports: import ... from '...'
        m = re.match(r"import\s+.*\s+from\s+['\"](.+?)['\"]", stripped)
        if m:
            imports.append({"path": m.group(1), "raw": stripped})
            continue

        # require(...)
        m = re.search(r"require\s*\(\s*['\"](.+?)['\"]\s*\)", stripped)
        if m:
            imports.append({"path": m.group(1), "raw": stripped})

    return exports, imports


def _extract_python(content: str) -> tuple[list[dict], list[dict]]:
    """Extract top-level classes, functions, and imports from Python source."""
    exports: list[dict] = []
    imports: list[dict] = []

    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()

        # Top-level class
        if line.startswith("class "):
            m = re.match(r"class\s+(\w+)", stripped)
            if m:
                exports.append({"name": m.group(1), "kind": "class", "line": lineno})
            continue

        # Top-level function
        if line.startswith("def "):
            m = re.match(r"def\s+(\w+)", stripped)
            if m:
                exports.append({"name": m.group(1), "kind": "function", "line": lineno})
            continue

        # Top-level constant (UPPER_CASE = ...)
        m = re.match(r"^([A-Z][A-Z0-9_]+)\s*[:=]", line)
        if m:
            exports.append({"name": m.group(1), "kind": "constant", "line": lineno})
            continue

        # import X / from X import Y
        m = re.match(r"from\s+([\w.]+)\s+import", stripped)
        if m:
            imports.append({"path": m.group(1), "raw": stripped})
            continue

        m = re.match(r"import\s+([\w.]+)", stripped)
        if m:
            imports.append({"path": m.group(1), "raw": stripped})

    return exports, imports


def _extract_php(content: str) -> tuple[list[dict], list[dict]]:
    """Extract classes, interfaces, traits, and use statements from PHP."""
    exports: list[dict] = []
    imports: list[dict] = []

    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()

        # class / interface / trait / enum
        m = re.match(
            r"(?:abstract\s+|final\s+)?"
            r"(class|interface|trait|enum)\s+(\w+)",
            stripped,
        )
        if m:
            exports.append({"name": m.group(2), "kind": m.group(1), "line": lineno})
            continue

        # Standalone function (outside class)
        m = re.match(r"function\s+(\w+)\s*\(", stripped)
        if m:
            exports.append({"name": m.group(1), "kind": "function", "line": lineno})
            continue

        # use statements
        m = re.match(r"use\s+([\w\\]+)", stripped)
        if m:
            imports.append({"path": m.group(1), "raw": stripped})

    return exports, imports


def _extract_go(content: str) -> tuple[list[dict], list[dict]]:
    """Extract exported (capitalised) symbols and imports from Go source."""
    exports: list[dict] = []
    imports: list[dict] = []

    in_import_block = False
    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()

        # Import block
        if stripped.startswith("import ("):
            in_import_block = True
            continue
        if in_import_block:
            if stripped == ")":
                in_import_block = False
                continue
            m = re.match(r'["\s]*(?:\w+\s+)?"(.+?)"', stripped)
            if m:
                imports.append({"path": m.group(1), "raw": stripped})
            continue

        # Single import
        m = re.match(r'import\s+"(.+?)"', stripped)
        if m:
            imports.append({"path": m.group(1), "raw": stripped})
            continue

        # Exported func / type / const / var (starts with uppercase)
        m = re.match(r"func\s+(?:\(\w+\s+\*?\w+\)\s+)?([A-Z]\w*)\s*\(", stripped)
        if m:
            exports.append({"name": m.group(1), "kind": "function", "line": lineno})
            continue

        m = re.match(r"type\s+([A-Z]\w*)\s+(struct|interface)", stripped)
        if m:
            exports.append({"name": m.group(1), "kind": m.group(2), "line": lineno})
            continue

    return exports, imports


def _extract_rust(content: str) -> tuple[list[dict], list[dict]]:
    """Extract ``pub`` symbols and ``use`` imports from Rust source."""
    exports: list[dict] = []
    imports: list[dict] = []

    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()

        # pub fn / pub struct / pub enum / pub trait / pub type / pub const
        m = re.match(
            r"pub(?:\s*\(crate\))?\s+(fn|struct|enum|trait|type|const)\s+(\w+)",
            stripped,
        )
        if m:
            exports.append({"name": m.group(2), "kind": m.group(1), "line": lineno})
            continue

        # use ...;
        m = re.match(r"use\s+([\w:]+(?:::\{[^}]+\})?)", stripped)
        if m:
            imports.append({"path": m.group(1), "raw": stripped})

    return exports, imports


def _extract_ruby(content: str) -> tuple[list[dict], list[dict]]:
    """Extract classes, modules, and top-level defs from Ruby source."""
    exports: list[dict] = []
    imports: list[dict] = []

    for lineno, line in enumerate(content.splitlines(), 1):
        stripped = line.strip()

        m = re.match(r"(class|module)\s+(\w+(?:::\w+)*)", stripped)
        if m:
            exports.append({"name": m.group(2), "kind": m.group(1), "line": lineno})
            continue

        # Top-level def (not indented)
        if line.startswith("def "):
            m = re.match(r"def\s+(\w+[!?]?)", stripped)
            if m:
                exports.append({"name": m.group(1), "kind": "function", "line": lineno})
            continue

        # require / require_relative
        m = re.match(r"require(?:_relative)?\s+['\"](.+?)['\"]", stripped)
        if m:
            imports.append({"path": m.group(1), "raw": stripped})

    return exports, imports


# ── Extractor dispatch table ─────────────────────────────────────────────────

_EXTRACTORS: dict[
    str | None,
    type[None] | type[tuple[list[dict], list[dict]]],  # just for annotation
] = {  # type: ignore[assignment]
    "typescript": _extract_typescript,
    "javascript": _extract_typescript,  # same syntax
    "python": _extract_python,
    "php": _extract_php,
    "go": _extract_go,
    "rust": _extract_rust,
    "ruby": _extract_ruby,
}
