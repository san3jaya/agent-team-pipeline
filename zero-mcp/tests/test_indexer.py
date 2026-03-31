"""Tests for ``tools.indexer`` — the most thorough test module."""

from pathlib import Path


from zero_mcp.memory.store import VectorStore
from zero_mcp.tools.indexer import (
    _extract_go,
    _extract_php,
    _extract_python,
    _extract_ruby,
    _extract_rust,
    _extract_typescript,
    get_dependencies,
    index_project,
    query_project,
)


class TestIndexProject:
    def test_full_index(self, sample_project: Path, vector_store: VectorStore) -> None:
        result = index_project(str(sample_project), db_conn=vector_store.conn)
        assert result["indexed"] is True
        assert result["files"] > 0
        assert result["new"] > 0
        assert result["duration_ms"] >= 0

    def test_incremental_index_is_cached(
        self, sample_project: Path, vector_store: VectorStore
    ) -> None:
        index_project(str(sample_project), db_conn=vector_store.conn)
        result = index_project(str(sample_project), db_conn=vector_store.conn)
        assert result["cached"] is True
        assert result["new"] == 0
        assert result["updated"] == 0

    def test_force_reindexes_all(
        self, sample_project: Path, vector_store: VectorStore
    ) -> None:
        index_project(str(sample_project), db_conn=vector_store.conn)
        result = index_project(
            str(sample_project), force=True, db_conn=vector_store.conn
        )
        assert result["cached"] is False
        assert result["new"] > 0

    def test_nonexistent_dir_returns_error(self, vector_store: VectorStore) -> None:
        result = index_project("/nonexistent/42", db_conn=vector_store.conn)
        assert "error" in result

    def test_no_db_conn_returns_error(self) -> None:
        result = index_project("/tmp")
        assert "error" in result

    def test_skips_excluded_dirs(
        self, tmp_path: Path, vector_store: VectorStore
    ) -> None:
        root = tmp_path / "proj"
        root.mkdir()
        (root / "src").mkdir()
        (root / "src" / "app.py").write_text("class App: pass\n")
        nm = root / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "index.js").write_text("export default {}\n")

        result = index_project(str(root), db_conn=vector_store.conn)
        assert result["files"] == 1  # only app.py, not node_modules

    def test_removes_deleted_files(
        self, tmp_path: Path, vector_store: VectorStore
    ) -> None:
        root = tmp_path / "proj"
        root.mkdir()
        f = root / "temp.py"
        f.write_text("class Temp: pass\n")

        index_project(str(root), db_conn=vector_store.conn)
        assert query_project(str(root), db_conn=vector_store.conn)["files"]

        f.unlink()
        index_project(str(root), db_conn=vector_store.conn)
        assert len(query_project(str(root), db_conn=vector_store.conn)["files"]) == 0


class TestQueryProject:
    def test_query_all(self, sample_project: Path, vector_store: VectorStore) -> None:
        index_project(str(sample_project), db_conn=vector_store.conn)
        result = query_project(str(sample_project), db_conn=vector_store.conn)
        assert len(result["files"]) > 0

    def test_filter_by_file_type(
        self, sample_project: Path, vector_store: VectorStore
    ) -> None:
        index_project(str(sample_project), db_conn=vector_store.conn)
        result = query_project(
            str(sample_project), file_types=["python"], db_conn=vector_store.conn
        )
        for f in result["files"]:
            assert f["language"] == "python"

    def test_filter_by_path_pattern(
        self, sample_project: Path, vector_store: VectorStore
    ) -> None:
        index_project(str(sample_project), db_conn=vector_store.conn)
        result = query_project(
            str(sample_project), path_pattern="src/%", db_conn=vector_store.conn
        )
        for f in result["files"]:
            assert f["path"].startswith("src/")

    def test_free_text_query(
        self, sample_project: Path, vector_store: VectorStore
    ) -> None:
        index_project(str(sample_project), db_conn=vector_store.conn)
        result = query_project(
            str(sample_project), query="AuthService", db_conn=vector_store.conn
        )
        paths = [f["path"] for f in result["files"]]
        assert any("AuthService" in p for p in paths)

    def test_exports_included(
        self, sample_project: Path, vector_store: VectorStore
    ) -> None:
        index_project(str(sample_project), db_conn=vector_store.conn)
        result = query_project(
            str(sample_project), file_types=["typescript"], db_conn=vector_store.conn
        )
        # At least one TS file should have exports
        has_exports = any(f["exports"] for f in result["files"])
        assert has_exports


class TestGetDependencies:
    def test_imports_for_ts_file(
        self, sample_project: Path, vector_store: VectorStore
    ) -> None:
        index_project(str(sample_project), db_conn=vector_store.conn)
        result = get_dependencies(
            str(sample_project),
            "src/services/AuthService.ts",
            db_conn=vector_store.conn,
        )
        assert "../models/User" in result["imports"] or any(
            "User" in i for i in result["imports"]
        )

    def test_unknown_file_returns_error(
        self, sample_project: Path, vector_store: VectorStore
    ) -> None:
        index_project(str(sample_project), db_conn=vector_store.conn)
        result = get_dependencies(
            str(sample_project), "nonexistent.ts", db_conn=vector_store.conn
        )
        assert "error" in result

    def test_no_db_conn(self) -> None:
        result = get_dependencies("/tmp", "file.ts")
        assert "error" in result


class TestExtractTypescript:
    def test_exports(self) -> None:
        code = (
            "export class Foo {}\n"
            "export function bar() {}\n"
            "export const BAZ = 42;\n"
            "export type MyType = string;\n"
            "export interface IFace {}\n"
            "export enum Color { Red }\n"
        )
        exports, _ = _extract_typescript(code)
        names = {e["name"] for e in exports}
        assert {"Foo", "bar", "BAZ", "MyType", "IFace", "Color"} == names

    def test_imports(self) -> None:
        code = (
            "import { Foo } from './foo';\n"
            "import Bar from 'bar';\n"
            "const x = require('lodash');\n"
        )
        _, imports = _extract_typescript(code)
        paths = {i["path"] for i in imports}
        assert {"./foo", "bar", "lodash"} == paths

    def test_module_exports(self) -> None:
        code = "module.exports = MyClass\n"
        exports, _ = _extract_typescript(code)
        assert exports[0]["name"] == "MyClass"

    def test_default_export(self) -> None:
        code = "export default class Widget {}\n"
        exports, _ = _extract_typescript(code)
        assert exports[0]["name"] == "Widget"


class TestExtractPython:
    def test_classes_and_functions(self) -> None:
        code = (
            "class MyClass:\n"
            "    pass\n"
            "\n"
            "def my_function():\n"
            "    pass\n"
            "\n"
            "MAX_SIZE = 100\n"
        )
        exports, _ = _extract_python(code)
        names = {e["name"] for e in exports}
        assert {"MyClass", "my_function", "MAX_SIZE"} == names

    def test_imports(self) -> None:
        code = "from os.path import join\nimport sys\n"
        _, imports = _extract_python(code)
        paths = {i["path"] for i in imports}
        assert {"os.path", "sys"} == paths


class TestExtractPHP:
    def test_class_and_interface(self) -> None:
        code = (
            "<?php\n"
            "class UserController {}\n"
            "interface Loggable {}\n"
            "trait Cacheable {}\n"
            "function helper() {}\n"
        )
        exports, _ = _extract_php(code)
        names = {e["name"] for e in exports}
        assert {"UserController", "Loggable", "Cacheable", "helper"} == names

    def test_use_statements(self) -> None:
        code = "use App\\Models\\User;\nuse Illuminate\\Http\\Request;\n"
        _, imports = _extract_php(code)
        assert len(imports) == 2


class TestExtractGo:
    def test_exported_symbols(self) -> None:
        code = (
            "func ServeHTTP(w http.ResponseWriter) {}\n"
            "type Config struct {}\n"
            "func privateHelper() {}\n"
        )
        exports, _ = _extract_go(code)
        names = {e["name"] for e in exports}
        assert "ServeHTTP" in names
        assert "Config" in names
        assert "privateHelper" not in names

    def test_import_block(self) -> None:
        code = 'import (\n    "fmt"\n    "net/http"\n)\n'
        _, imports = _extract_go(code)
        paths = {i["path"] for i in imports}
        assert {"fmt", "net/http"} == paths


class TestExtractRust:
    def test_pub_symbols(self) -> None:
        code = (
            "pub fn process() {}\n"
            "pub struct Engine {}\n"
            "pub enum Color {}\n"
            "pub trait Drawable {}\n"
            "fn private_fn() {}\n"
        )
        exports, _ = _extract_rust(code)
        names = {e["name"] for e in exports}
        assert {"process", "Engine", "Color", "Drawable"} == names

    def test_use_imports(self) -> None:
        code = "use std::collections::HashMap;\n"
        _, imports = _extract_rust(code)
        assert len(imports) == 1
        assert "std::collections::HashMap" in imports[0]["path"]


class TestExtractRuby:
    def test_class_and_module(self) -> None:
        code = "class Parser\nend\nmodule Utils\nend\ndef top_level_method\nend\n"
        exports, _ = _extract_ruby(code)
        names = {e["name"] for e in exports}
        assert {"Parser", "Utils", "top_level_method"} == names

    def test_require(self) -> None:
        code = "require 'json'\nrequire_relative 'helpers'\n"
        _, imports = _extract_ruby(code)
        paths = {i["path"] for i in imports}
        assert {"json", "helpers"} == paths
