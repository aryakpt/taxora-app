import asyncio
import threading
from typing import Protocol


class Embedder(Protocol):
    async def embed(self, text: str) -> list[float]: ...


class LocalEmbedder:
    """Multilingual sentence embeddings computed on this machine with fastembed (ONNX, CPU).

    The model (~220 MB) downloads on first use and is cached afterwards. No text leaves the server.
    """

    def __init__(self, model_name: str):
        self.model_name = model_name
        self._model = None
        self._lock = threading.Lock()

    def _load(self):
        with self._lock:
            if self._model is None:
                from fastembed import TextEmbedding

                self._model = TextEmbedding(model_name=self.model_name)
        return self._model

    async def embed(self, text: str) -> list[float]:
        def encode() -> list[float]:
            return next(iter(self._load().embed([text]))).tolist()

        return await asyncio.to_thread(encode)
