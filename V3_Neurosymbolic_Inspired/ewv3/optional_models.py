"""Optional on-prem sentence-transformers adapters.

These adapters are imported without loading third-party libraries. Constructing
one requires the optional `sentence-transformers` package and an available
local model directory or explicitly permitted model cache.
"""
from __future__ import annotations

import math
from dataclasses import replace

from .ports import SearchHit, SourceUnit


class SentenceTransformerEmbedder:
    def __init__(self, model_path: str, *, device: str = "cpu",
                 local_files_only: bool = True, batch_size: int = 32) -> None:
        if batch_size < 1:
            raise ValueError("batch_size must be positive")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise RuntimeError(
                "semantic retrieval requires the optional sentence-transformers package"
            ) from exc
        self.model = SentenceTransformer(model_path, device=device,
                                         local_files_only=local_files_only)
        self.version = f"sentence-transformers:{model_path}:{device}"
        self.batch_size = batch_size

    def _encode(self, method: str, text: str) -> tuple[float, ...]:
        vector = getattr(self.model, method)(text, normalize_embeddings=True,
                                             convert_to_numpy=True, show_progress_bar=False)
        return tuple(float(value) for value in vector.tolist())

    def embed(self, text: str) -> tuple[float, ...]:
        return self._encode("encode", text)

    def embed_query(self, text: str) -> tuple[float, ...]:
        return self._encode("encode_query", text)

    def embed_document(self, text: str) -> tuple[float, ...]:
        return self._encode("encode_document", text)

    def embed_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        # SentenceTransformers batches internally, avoiding one model dispatch
        # per sentence while preserving deterministic source-window ordering.
        method = "encode_document" if callable(getattr(self.model, "encode_document", None)) else "encode"
        vectors = getattr(self.model, method)(
            list(texts), normalize_embeddings=True, convert_to_numpy=True,
            show_progress_bar=False, batch_size=self.batch_size,
        )
        return tuple(tuple(float(value) for value in row) for row in vectors.tolist())


class SentenceTransformerReranker:
    def __init__(self, model_path: str, *, device: str = "cpu",
                 local_files_only: bool = True) -> None:
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise RuntimeError(
                "neural reranking requires the optional sentence-transformers package"
            ) from exc
        self.model = CrossEncoder(model_path, device=device,
                                  local_files_only=local_files_only)
        self.version = f"cross-encoder:{model_path}:{device}"

    def rerank(self, query: str, hits: tuple[SearchHit, ...], *,
               sources: tuple[SourceUnit, ...], limit: int) -> tuple[SearchHit, ...]:
        pairs = [(query, hit.excerpt) for hit in hits]
        scores = self.model.predict(pairs, show_progress_bar=False)
        if len(scores) != len(hits):
            raise ValueError("cross-encoder returned a different number of scores than candidates")
        rescored = []
        for hit, raw_score in zip(hits, scores):
            score = float(raw_score)
            if not math.isfinite(score):
                raise ValueError("cross-encoder returned a non-finite score")
            rescored.append(replace(hit, score=score,
                                    score_semantics="reranker_raw_score"))
        rescored.sort(key=lambda hit: (-hit.score, hit.source_id,
                                       hit.representation_id, hit.start_offset))
        return tuple(rescored[:limit])


class LocalCLIPImageTextEncoder:
    """On-prem CLIP encoder for text-to-image retrieval of document regions.

    `content_ref` must be a local image path. A visual backend may provide a
    page crop in structural_context['bounding_box'] as pixel coordinates.
    """
    def __init__(self, model_path: str, *, device: str = "cpu",
                 local_files_only: bool = True) -> None:
        try:
            import torch
            from transformers import AutoProcessor, CLIPModel
        except ImportError as exc:
            raise RuntimeError("local visual retrieval requires torch and transformers") from exc
        self.torch = torch
        self.processor = AutoProcessor.from_pretrained(
            model_path, local_files_only=local_files_only,
        )
        self.model = CLIPModel.from_pretrained(
            model_path, local_files_only=local_files_only,
        ).to(device).eval()
        self.device = device
        self.version = f"clip:{model_path}:{device}"

    def _vector(self, features) -> tuple[float, ...]:
        if hasattr(features, "pooler_output"):
            features = features.pooler_output
        if isinstance(features, tuple):
            features = features[0]
        vector = self.torch.nn.functional.normalize(features, p=2, dim=-1)[0]
        return tuple(float(x) for x in vector.detach().cpu().tolist())

    def embed_text(self, text: str) -> tuple[float, ...]:
        inputs = self.processor(text=[text], return_tensors="pt", padding=True)
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with self.torch.inference_mode():
            features = self.model.get_text_features(**inputs)
        return self._vector(features)

    def embed_image(self, content_ref: str,
                    structural_context: dict[str, object]) -> tuple[float, ...]:
        from PIL import Image

        with Image.open(content_ref) as opened:
            image = opened.convert("RGB")
            box = structural_context.get("bounding_box")
            if isinstance(box, (tuple, list)) and len(box) == 4:
                image = image.crop(tuple(int(value) for value in box))
            inputs = self.processor(images=image, return_tensors="pt")
        inputs = {key: value.to(self.device) for key, value in inputs.items()}
        with self.torch.inference_mode():
            features = self.model.get_image_features(**inputs)
        return self._vector(features)
