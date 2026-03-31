"""ONNX Runtime embedding model (MiniLM-L6-v2) with lazy loading and caching."""

from __future__ import annotations

import logging
from pathlib import Path

import numpy as np

from ..config.settings import (
    EMBEDDING_DIM,
    MODEL_DIR,
    MODEL_URL,
    TOKENIZER_URL,
)

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """Generate 384-dimensional sentence embeddings via ONNX Runtime.

    The ONNX model and HuggingFace tokenizer are downloaded on first use and
    cached in :data:`~zero_mcp.config.settings.MODEL_DIR`.  Subsequent
    invocations re-use the cached files.

    This class is designed to be instantiated *once* at server startup and
    injected into any component that needs embeddings.
    """

    def __init__(self, model_dir: Path | None = None) -> None:
        self._model_dir = model_dir or MODEL_DIR
        self._session: object | None = None  # ort.InferenceSession
        self._tokenizer: object | None = None  # tokenizers.Tokenizer

    # ── Public API ───────────────────────────────────────────────────────

    @property
    def is_loaded(self) -> bool:
        """Return ``True`` if the ONNX session and tokenizer are ready."""
        return self._session is not None and self._tokenizer is not None

    def embed(self, text: str) -> np.ndarray:
        """Return a normalised ``(384,)`` embedding for *text*."""
        self._load()

        encoded = self._tokenizer.encode(text)  # type: ignore[union-attr]
        input_ids = np.array([encoded.ids], dtype=np.int64)
        attention_mask = np.array([encoded.attention_mask], dtype=np.int64)
        token_type_ids = np.zeros_like(input_ids)

        outputs = self._session.run(  # type: ignore[union-attr]
            None,
            {
                "input_ids": input_ids,
                "attention_mask": attention_mask,
                "token_type_ids": token_type_ids,
            },
        )

        # Mean pooling over token embeddings
        token_embeddings = outputs[0]  # shape: (1, seq_len, 384)
        mask_expanded = attention_mask[:, :, np.newaxis].astype(np.float32)
        summed = np.sum(token_embeddings * mask_expanded, axis=1)
        counted = np.clip(np.sum(mask_expanded, axis=1), a_min=1e-9, a_max=None)
        embedding = (summed / counted).flatten()

        # L2 normalise
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding = embedding / norm

        return embedding

    def embed_batch(self, texts: list[str]) -> list[np.ndarray]:
        """Embed multiple texts.  Simple sequential loop for now."""
        return [self.embed(t) for t in texts]

    # ── Internals ────────────────────────────────────────────────────────

    def _ensure_model(self) -> tuple[Path, Path]:
        """Download model files if they are not already cached."""
        self._model_dir.mkdir(parents=True, exist_ok=True)
        model_path = self._model_dir / "model.onnx"
        tokenizer_path = self._model_dir / "tokenizer.json"

        if not model_path.exists():
            logger.info("Downloading ONNX model to %s …", model_path)
            try:
                import urllib.request

                urllib.request.urlretrieve(MODEL_URL, model_path)
            except Exception as exc:
                model_path.unlink(missing_ok=True)
                raise RuntimeError(
                    f"Failed to download ONNX model from {MODEL_URL}: {exc}"
                ) from exc

        if not tokenizer_path.exists():
            logger.info("Downloading tokenizer to %s …", tokenizer_path)
            try:
                import urllib.request

                urllib.request.urlretrieve(TOKENIZER_URL, tokenizer_path)
            except Exception as exc:
                tokenizer_path.unlink(missing_ok=True)
                raise RuntimeError(
                    f"Failed to download tokenizer from {TOKENIZER_URL}: {exc}"
                ) from exc

        return model_path, tokenizer_path

    def _load(self) -> None:
        """Lazy-load the ONNX session and tokenizer on first use."""
        if self._session is not None:
            return

        import onnxruntime as ort
        from tokenizers import Tokenizer

        model_path, tokenizer_path = self._ensure_model()
        self._session = ort.InferenceSession(
            str(model_path),
            providers=["CPUExecutionProvider"],
        )
        self._tokenizer = Tokenizer.from_file(str(tokenizer_path))
        logger.info(
            "Embedding model loaded (dim=%d) from %s",
            EMBEDDING_DIM,
            self._model_dir,
        )
