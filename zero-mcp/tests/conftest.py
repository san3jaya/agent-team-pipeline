"""Shared pytest fixtures for zero-mcp tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pytest

from zero_mcp.config.settings import EMBEDDING_DIM
from zero_mcp.memory.embeddings import EmbeddingModel
from zero_mcp.memory.store import VectorStore


# ─────────────────────────────────────────────────────────────────────────────
# Mock embedding model — deterministic, no ONNX download
# ─────────────────────────────────────────────────────────────────────────────


class MockEmbeddingModel(EmbeddingModel):
    """Deterministic embedding model that hashes text into a 384-dim vector.

    Produces normalised vectors so cosine similarity behaves realistically.
    Identical texts produce identical embeddings.
    """

    def __init__(self) -> None:
        # Do NOT call super().__init__() — we bypass ONNX entirely.
        self._session = "mock"  # satisfies is_loaded
        self._tokenizer = "mock"

    def embed(self, text: str) -> np.ndarray:
        digest = hashlib.sha256(text.encode()).digest()
        # Expand the 32-byte digest to fill 384 floats deterministically
        rng = np.random.RandomState(int.from_bytes(digest[:4], "little"))
        vec = rng.randn(EMBEDDING_DIM).astype(np.float32)
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        return [self.embed(t) for t in texts]

    def _load(self) -> None:
        pass  # no-op


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_embedding_model() -> MockEmbeddingModel:
    """A fake :class:`EmbeddingModel` that needs no ONNX download."""
    return MockEmbeddingModel()


@pytest.fixture()
def tmp_db(tmp_path: Path) -> Path:
    """Return a path to a temporary SQLite database."""
    return tmp_path / "test_data.db"


@pytest.fixture()
def vector_store(tmp_db: Path, mock_embedding_model: MockEmbeddingModel) -> VectorStore:
    """A :class:`VectorStore` backed by a temp DB and mock embeddings."""
    return VectorStore(db_path=tmp_db, embedding_model=mock_embedding_model)


@pytest.fixture()
def sample_project(tmp_path: Path) -> Path:
    """Create a temporary directory tree with sample source files for indexer tests."""
    root = tmp_path / "sample_project"
    root.mkdir()

    # TypeScript
    ts_dir = root / "src" / "services"
    ts_dir.mkdir(parents=True)
    (ts_dir / "AuthService.ts").write_text(
        "import { User } from '../models/User';\n"
        "import jwt from 'jsonwebtoken';\n"
        "\n"
        "export class AuthService {\n"
        "  async login() {}\n"
        "}\n"
        "\n"
        "export function validateToken(token: string): boolean {\n"
        "  return true;\n"
        "}\n"
    )

    models_dir = root / "src" / "models"
    models_dir.mkdir(parents=True)
    (models_dir / "User.ts").write_text(
        "export interface UserDTO {\n"
        "  id: number;\n"
        "}\n"
        "\n"
        "export class User {\n"
        "  name: string = '';\n"
        "}\n"
    )

    # Python
    py_dir = root / "backend"
    py_dir.mkdir()
    (py_dir / "app.py").write_text(
        "from flask import Flask\n"
        "from .models import db\n"
        "\n"
        "APP_NAME = 'demo'\n"
        "\n"
        "class Application:\n"
        "    pass\n"
        "\n"
        "def create_app():\n"
        "    return Flask(__name__)\n"
    )

    # PHP
    php_dir = root / "app" / "Http" / "Controllers"
    php_dir.mkdir(parents=True)
    (php_dir / "UserController.php").write_text(
        "<?php\n"
        "\n"
        "namespace App\\Http\\Controllers;\n"
        "\n"
        "use App\\Models\\User;\n"
        "use Illuminate\\Http\\Request;\n"
        "\n"
        "class UserController extends Controller\n"
        "{\n"
        "    public function index() {}\n"
        "}\n"
    )

    # Go
    go_dir = root / "cmd"
    go_dir.mkdir()
    (go_dir / "main.go").write_text(
        "package main\n"
        "\n"
        "import (\n"
        '    "fmt"\n'
        '    "net/http"\n'
        ")\n"
        "\n"
        "func ServeHTTP(w http.ResponseWriter, r *http.Request) {\n"
        '    fmt.Fprintln(w, "hello")\n'
        "}\n"
        "\n"
        "type Config struct {\n"
        "    Port int\n"
        "}\n"
    )

    # Rust
    rs_dir = root / "src"
    (rs_dir / "lib.rs").write_text(
        "use std::collections::HashMap;\n"
        "\n"
        "pub fn process(data: &str) -> String {\n"
        "    data.to_uppercase()\n"
        "}\n"
        "\n"
        "pub struct Engine {\n"
        "    state: HashMap<String, String>,\n"
        "}\n"
    )

    # Ruby
    rb_dir = root / "lib"
    rb_dir.mkdir()
    (rb_dir / "parser.rb").write_text(
        "require 'json'\n"
        "require_relative 'helpers'\n"
        "\n"
        "class Parser\n"
        "  def parse(input)\n"
        "    JSON.parse(input)\n"
        "  end\n"
        "end\n"
        "\n"
        "module Utils\n"
        "  def self.format(val) end\n"
        "end\n"
    )

    # A file that should be skipped (binary extension)
    (root / "logo.png").write_bytes(b"\x89PNG fake")

    return root
