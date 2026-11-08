"""Exact, lexical, semantic, and fused retrieval adapters.

The bundled retriever is dependency-free. Semantic vectors and visual/image
search are injected through ports; this module never substitutes fake vectors
for a missing production model.
"""
from __future__ import annotations

import hashlib
import math
import re
from collections import OrderedDict
from collections import Counter
from dataclasses import dataclass, replace
from typing import Callable, Iterable

import docstruct

from .contracts import SourceRepresentation, SourceUnit
from .ports import CandidateReranker, CorpusRetriever, ImageTextEmbedder, SearchHit, TextEmbedder


def iter_representations(source: SourceUnit) -> tuple[SourceRepresentation, ...]:
    if source.representations:
        return tuple(r for r in source.representations if r.searchable and r.readiness == "ready")
    if not source.text:
        return ()
    return (SourceRepresentation(source.representation_id, "text", source.text,
                                 source.metadata, source.searchable, source.readiness),)


def _terms(text: str) -> set[str]:
    return {x.casefold() for x in re.findall(r"[A-Za-z0-9][A-Za-z0-9._:-]*", text)}


_FILLER = frozenset("""a an and are as at be been being but by can could did do does for from had has have how if in into
is it its of on or our shall should so than that the their there these they this those to was we were what when where
which who whom why will with would not no any all each both either also then than during after before about around
between over under up out per via within without you your""".split())
# Words that frame a request or question rather than describe the incident.
_FRAMING = frozenset("""please provide provided provides provide retrieve retrieved request requested requests include included
including includes indicate indicates indicating indicated show shows showing shown record records recorded recording
entry entries document documents documented documenting detail details information relevant specific specifically
any whether otherwise relative regarding concerning related report reports data note notes""".split())


def _stem(word: str) -> str:
    """Light suffix stripping, applied up to twice (readings -> reading -> read)."""
    for _ in range(2):
        for suffix, replacement in (("ies", "y"), ("ing", ""), ("ed", ""), ("es", ""), ("s", "")):
            if word.endswith(suffix) and len(word) - len(suffix) >= 3 and not word.endswith("ss"):
                word = word[: len(word) - len(suffix)] + replacement
                break
        else:
            break
    return word


def content_terms(text: str) -> frozenset[str]:
    """Stemmed content words. Filler and request-framing words are dropped; identifiers that contain
    a digit (tags, times, document numbers) are kept whole and also as parts, so IV-RB3-17 matches itself."""
    out: set[str] = set()
    for token in re.findall(r"[A-Za-z0-9][A-Za-z0-9._:-]*", text):
        token = token.casefold().rstrip(".:-_")
        pieces = [p for p in re.split(r"[._:-]+", token) if p]
        if any(ch.isdigit() for ch in token) and len(pieces) > 1:
            out.add(token)
        for piece in pieces:
            if piece in _FILLER or piece in _FRAMING or len(piece) < 2:
                continue
            out.add(piece if any(ch.isdigit() for ch in piece) else _stem(piece))
    return frozenset(out)


def _sentence_spans(text: str) -> Iterable[tuple[int, int]]:
    """Yield exact sentence/line spans; offsets remain relative to source rendition."""
    boundaries = tuple(re.finditer(r"(?<=[.!?])\s+|\n+", text))
    start = 0
    for boundary in boundaries:
        end = boundary.start()
        while start < end and text[start].isspace():
            start += 1
        if end > start:
            yield start, end
        start = boundary.end()
    end = len(text)
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if end > start:
        yield start, end


def _sentence_span(text: str, start: int, end: int, *, max_chars: int = 800) -> tuple[int, int]:
    for left, right in _sentence_spans(text):
        if left <= start < right or left < end <= right:
            if right - left <= max_chars:
                return left, right
            return max(left, start - max_chars // 2), min(right, start + max_chars // 2)
    return start, end


@dataclass(frozen=True, slots=True)
class PassageUnit:
    """One evidence passage with the words and labels it inherits from its document structure."""
    start: int
    end: int
    text: str
    terms: frozenset[str]
    context_terms: frozenset[str]
    context: dict


_UNIT_CACHE: OrderedDict[str, tuple[PassageUnit, ...]] = OrderedDict()


def passage_units(text: str) -> tuple[PassageUnit, ...]:
    """Evidence passages of a text rendition, read through docstruct (cached by content)."""
    key = hashlib.sha256(text.encode("utf-8")).hexdigest()
    if key in _UNIT_CACHE:
        _UNIT_CACHE.move_to_end(key)
        return _UNIT_CACHE[key]
    structure = docstruct.parse(text)
    details = content_terms(" ".join(structure.details))
    title = content_terms(structure.title)
    units = []
    for passage in structure.evidence():
        before, after = structure.neighbours(passage)
        context_terms = title | content_terms(passage.section) | details
        if passage.table_header:
            context_terms |= content_terms(" ".join(passage.table_header))
        units.append(PassageUnit(passage.start, passage.end, passage.text, content_terms(passage.text),
                                 context_terms, {
            "passage_kind": passage.kind, "document_title": structure.title,
            "section": passage.section, "readable_text": passage.readable(),
            "document_details": list(structure.details),
            "before": before.readable() if before else "", "after": after.readable() if after else "",
            "structure_version": structure.version}))
    _UNIT_CACHE[key] = tuple(units)
    while len(_UNIT_CACHE) > 2_000:
        _UNIT_CACHE.popitem(last=False)
    return _UNIT_CACHE[key]


class InMemoryRetriever:
    """Exact/lexical fallback over text and text-bearing document renditions."""
    version = "ewv3-inmemory-exact-lexical-4"

    def __init__(self, *, min_shared: int = 2, context_weight: float = 0.5) -> None:
        if min_shared < 1:
            raise ValueError("min_shared must be at least 1")
        if not 0 <= context_weight <= 1:
            raise ValueError("context_weight must be between 0 and 1")
        self.min_shared = min_shared
        self.context_weight = context_weight

    def search(self, query: str, *, channel: str, sources: tuple[SourceUnit, ...], limit: int):
        if channel not in {"exact", "lexical"}:
            raise NotImplementedError(
                f"InMemoryRetriever does not implement {channel!r}; inject semantic or modality-specific search"
            )
        query_terms = frozenset()
        weight: dict[str, float] = {}
        total_weight = 1.0
        if channel == "lexical":
            query_terms = content_terms(query)
            if not query_terms:
                return ()
            document_frequency: Counter = Counter()
            count = 0
            for source in sources:
                for rep in iter_representations(source):
                    for unit in passage_units(rep.text):
                        document_frequency.update(unit.terms)
                        count += 1
            weight = {t: math.log(1 + (count + 1) / (document_frequency.get(t, 0) + 1)) for t in query_terms}
            total_weight = sum(weight.values()) or 1.0
        hits = []
        for source in sources:
            for rep in iter_representations(source):
                if channel == "exact":
                    position = rep.text.casefold().find(query.casefold())
                    if position < 0:
                        continue
                    start, end = position, position + len(query)
                    score = 1.0
                    start, end = _sentence_span(rep.text, start, end)
                    hits.append(SearchHit(source.source_id, rep.representation_id,
                                          start, end, score, channel,
                                          rep.text[start:end], rep.structural_context,
                                          rep.modality, score_semantics="exact_match"))
                else:
                    # Rank evidence passages (sentences, table rows) independently.
                    # Scoring at whole-document level can point at an unrelated
                    # passage in that same document, which breaks relevance and
                    # attribution. Terms are content words (filler dropped,
                    # stemmed) weighted by rarity; a passage must share at least
                    # `min_shared` of them, counting words it inherits from its
                    # title, section heading, table header and details block.
                    for unit in passage_units(rep.text):
                        overlap = query_terms & unit.terms
                        inherited = (query_terms & unit.context_terms) - overlap
                        if not overlap or len(overlap) + len(inherited) < min(self.min_shared, len(query_terms)):
                            continue
                        score = (sum(weight[t] for t in overlap)
                                 + self.context_weight * sum(weight[t] for t in inherited)) / total_weight
                        hits.append(SearchHit(source.source_id, rep.representation_id,
                                              unit.start, unit.end, score, channel, unit.text,
                                              {**rep.structural_context, **unit.context}, rep.modality,
                                              score_semantics="lexical_overlap"))
        hits.sort(key=lambda h: (-h.score, h.source_id, h.representation_id, h.start_offset))
        return tuple(hits[:limit])


class BM25Retriever:
    """Dependency-free BM25 over sentence and table-row representations."""
    version = "ewv3-bm25-k1-1.5-b-0.75-v2"

    def __init__(self, *, k1: float = 1.5, b: float = 0.75) -> None:
        if k1 <= 0 or not 0 <= b <= 1:
            raise ValueError("BM25 requires k1 > 0 and b in [0, 1]")
        self.k1 = k1
        self.b = b

    def search(self, query: str, *, channel: str, sources: tuple[SourceUnit, ...], limit: int):
        if channel != "bm25":
            raise NotImplementedError("BM25Retriever only implements bm25 search")
        query_terms = content_terms(query)
        documents = []
        for source in sources:
            for rep in iter_representations(source):
                for unit in passage_units(rep.text):
                    # Content words of the passage, plus inherited structure words once each.
                    tokens = list(unit.terms) + list(unit.context_terms - unit.terms)
                    if tokens:
                        documents.append((source, rep, unit, Counter(tokens)))
        if not documents or not query_terms:
            return ()
        df = Counter()
        for *_prefix, frequencies in documents:
            df.update(frequencies.keys())
        average_length = sum(sum(doc[-1].values()) for doc in documents) / len(documents)
        n_docs = len(documents)
        hits = []
        for source, rep, unit, frequencies in documents:
            if not query_terms & unit.terms:
                continue  # structure words alone never make a passage relevant
            length = sum(frequencies.values())
            score = 0.0
            for term in query_terms:
                tf = frequencies.get(term, 0)
                if not tf:
                    continue
                inverse = math.log(1 + (n_docs - df[term] + 0.5) / (df[term] + 0.5))
                denominator = tf + self.k1 * (1 - self.b + self.b * length / max(average_length, 1e-9))
                score += inverse * (tf * (self.k1 + 1)) / denominator
            if score > 0:
                hits.append(SearchHit(source.source_id, rep.representation_id,
                                      unit.start, unit.end, score, "bm25", unit.text,
                                      {**rep.structural_context, **unit.context}, rep.modality,
                                      score_semantics="bm25_score"))
        hits.sort(key=lambda h: (-h.score, h.source_id, h.representation_id, h.start_offset or 0))
        return tuple(hits[:limit])


class DenseVectorRetriever:
    """Semantic sentence retrieval using an injected embedding model.

    The implementation owns ranking and exact offsets, while the caller chooses
    and versions the actual embedding model (including an on-prem model).
    """
    def __init__(self, embedder: TextEmbedder) -> None:
        self.embedder = embedder
        self.version = f"ewv3-dense-{embedder.version}"
        self._cache: OrderedDict[str, tuple[float, ...]] = OrderedDict()
        self.max_cache_entries = 10_000

    def _embed(self, text: str, *, task: str) -> tuple[float, ...]:
        key = hashlib.sha256(f"{task}\0{text}".encode("utf-8")).hexdigest()
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        task_encoder = getattr(self.embedder, f"embed_{task}", None)
        vector = task_encoder(text) if callable(task_encoder) else self.embedder.embed(text)
        self._cache[key] = tuple(vector)
        while len(self._cache) > self.max_cache_entries:
            self._cache.popitem(last=False)
        return self._cache[key]

    def _embed_documents(self, texts: tuple[str, ...]) -> tuple[tuple[float, ...], ...]:
        """Embed uncached document windows in one batch when the adapter supports it."""
        keys = [hashlib.sha256(f"document\0{text}".encode("utf-8")).hexdigest()
                for text in texts]
        missing_by_key: dict[str, str] = {}
        for key, text in zip(keys, texts):
            if key not in self._cache:
                missing_by_key.setdefault(key, text)
            else:
                self._cache.move_to_end(key)

        missing_keys = tuple(missing_by_key)
        missing_texts = tuple(missing_by_key.values())
        computed: dict[str, tuple[float, ...]] = {}
        if missing_texts:
            batch_encoder = getattr(self.embedder, "embed_documents", None)
            if callable(batch_encoder):
                vectors = tuple(tuple(vector) for vector in batch_encoder(missing_texts))
                if len(vectors) != len(missing_texts):
                    raise ValueError("embed_documents returned a different number of vectors than inputs")
            else:
                vectors = tuple(self._embed(text, task="document") for text in missing_texts)
                # _embed caches the fallback results itself.
                missing_keys = ()
            for key, vector in zip(missing_keys, vectors):
                computed[key] = vector
                self._cache[key] = vector
                while len(self._cache) > self.max_cache_entries:
                    self._cache.popitem(last=False)

        return tuple(computed[key] if key in computed else self._cache[key] for key in keys)

    @staticmethod
    def _cosine(left: tuple[float, ...], right: tuple[float, ...]) -> float:
        if not left or len(left) != len(right):
            return 0.0
        dot = sum(a * b for a, b in zip(left, right))
        norm = math.sqrt(sum(a * a for a in left) * sum(b * b for b in right))
        return dot / norm if norm else 0.0

    def search(self, query: str, *, channel: str, sources: tuple[SourceUnit, ...], limit: int):
        if channel != "semantic":
            raise NotImplementedError("DenseVectorRetriever only implements semantic search")
        query_vector = self._embed(query, task="query")
        windows = []
        for source in sources:
            for rep in iter_representations(source):
                # Sentence windows localize evidence and permit multiple
                # independently attributable matches inside one document.
                for start, end in _sentence_spans(rep.text):
                    text = rep.text[start:end]
                    windows.append((source, rep, start, end, text))
        document_vectors = self._embed_documents(tuple(window[4] for window in windows))
        hits = []
        for (source, rep, start, end, text), document_vector in zip(windows, document_vectors):
            score = self._cosine(query_vector, document_vector)
            if score <= 0:
                continue
            hits.append(SearchHit(source.source_id, rep.representation_id,
                                  start, end, score, "semantic", text,
                                  rep.structural_context, rep.modality,
                                  score_semantics="cosine_similarity"))
        hits.sort(key=lambda h: (-h.score, h.source_id, h.representation_id, h.start_offset))
        return tuple(hits[:limit])


class VisualVectorRetriever:
    """Cross-modal text-to-image retrieval over immutable source regions.

    Image/text embeddings are supplied by one shared-space encoder. Returned
    links point to page/region metadata and do not invent textual offsets.
    """
    def __init__(self, encoder: ImageTextEmbedder) -> None:
        self.encoder = encoder
        self.version = f"ewv3-visual-{encoder.version}"
        self._cache: OrderedDict[str, tuple[float, ...]] = OrderedDict()
        self.max_cache_entries = 5_000

    def search(self, query: str, *, channel: str, sources: tuple[SourceUnit, ...], limit: int):
        if channel != "visual":
            raise NotImplementedError("VisualVectorRetriever only implements visual search")
        query_vector = tuple(self.encoder.embed_text(query))
        hits = []
        for source in sources:
            for rep in iter_representations(source):
                if rep.modality not in {"image", "figure", "chart", "visual"} or not rep.content_ref:
                    continue
                cache_key = f"{source.source_version}:{rep.representation_id}:{rep.content_ref}"
                if cache_key in self._cache:
                    image_vector = self._cache[cache_key]
                    self._cache.move_to_end(cache_key)
                else:
                    image_vector = tuple(self.encoder.embed_image(rep.content_ref,
                                                                  rep.structural_context))
                    self._cache[cache_key] = image_vector
                    while len(self._cache) > self.max_cache_entries:
                        self._cache.popitem(last=False)
                score = DenseVectorRetriever._cosine(query_vector, image_vector)
                if score <= 0:
                    continue
                hits.append(SearchHit(
                    source.source_id, rep.representation_id, None, None, score,
                    "visual", "", rep.structural_context, rep.modality,
                    score_semantics="cosine_similarity",
                ))
        hits.sort(key=lambda h: (-h.score, h.source_id, h.representation_id))
        return tuple(hits[:limit])


class HybridRetriever:
    """Fuse exact/sparse/dense/table/visual channels with RRF, then rerank.

    `backends` map channel names to retrieval adapters. Table and visual
    adapters return ordinary provenance-bearing SearchHits aligned to a
    SourceRepresentation. A reranker is optional and remains replaceable.
    """
    def __init__(self, backends: dict[str, CorpusRetriever], *,
                 reranker: CandidateReranker | None = None,
                 rrf_k: int = 60, pool_multiplier: int = 4) -> None:
        if not backends:
            raise ValueError("HybridRetriever requires at least one backend")
        if rrf_k < 1 or pool_multiplier < 1:
            raise ValueError("rrf_k and pool_multiplier must be positive")
        self.backends = dict(backends)
        self.reranker = reranker
        self.rrf_k = rrf_k
        self.pool_multiplier = pool_multiplier
        versions = ",".join(f"{k}:{v.version}" for k, v in sorted(self.backends.items()))
        ranker = getattr(reranker, "version", "none")
        self.version = f"ewv3-hybrid-rrf-{rrf_k}[{versions}]-rerank:{ranker}"

    def search(self, query: str, *, channel: str, sources: tuple[SourceUnit, ...], limit: int):
        if channel != "hybrid":
            backend = self.backends.get(channel)
            if backend is None:
                raise NotImplementedError(f"no configured retrieval backend for {channel!r}")
            return backend.search(query, channel=channel, sources=sources, limit=limit)

        pool_limit = max(limit, limit * self.pool_multiplier)
        fused: dict[tuple[str, str, int, int], tuple[float, SearchHit, set[str]]] = {}
        for name, backend in self.backends.items():
            hits = backend.search(query, channel=name, sources=sources, limit=pool_limit)
            for rank, hit in enumerate(hits, start=1):
                key = (hit.source_id, hit.representation_id,
                       hit.start_offset if hit.start_offset is not None else -1,
                       hit.end_offset if hit.end_offset is not None else -1)
                contribution = 1.0 / (self.rrf_k + rank)
                prior, best_hit, contributing = fused.get(key, (0.0, hit, set()))
                if hit.score > best_hit.score:
                    best_hit = hit
                contributing.add(name)
                fused[key] = (prior + contribution, best_hit, contributing)
        candidates = tuple(
            replace(hit, score=score, channel="hybrid",
                    channels=tuple(sorted(contributing)),
                    score_semantics="rrf_rank_fusion")
            for score, hit, contributing in sorted(fused.values(),
                                     key=lambda item: (-item[0], item[1].source_id,
                                                       item[1].representation_id,
                                                       item[1].start_offset if item[1].start_offset is not None else -1))
        )[:pool_limit]
        if self.reranker is not None and candidates:
            return self.reranker.rerank(query, candidates, sources=sources, limit=limit)
        return candidates[:limit]

    @property
    def backend_count(self) -> int:
        return len(self.backends)

    @property
    def backend_versions(self) -> tuple[str, ...]:
        return tuple(f"{name}:{backend.version}" for name, backend in sorted(self.backends.items()))

    @property
    def reranker_version(self) -> str:
        return getattr(self.reranker, "version", "")


class FunctionReranker:
    """Adapter for a local or hosted query-passage scoring model.

    The score callable can wrap a cross-encoder or another validated ranker.
    It sees only candidate excerpts already returned by the configured
    retrievers; it cannot broaden corpus scope or create source links.
    """
    def __init__(self, score: Callable[[str, str], float], *, version: str) -> None:
        if not version.strip():
            raise ValueError("reranker version must be non-empty")
        self.score = score
        self.version = version

    def rerank(self, query: str, hits: tuple[SearchHit, ...], *,
               sources: tuple[SourceUnit, ...], limit: int) -> tuple[SearchHit, ...]:
        rescored = [replace(hit, score=float(self.score(query, hit.excerpt)),
                            score_semantics="reranker_raw_score") for hit in hits]
        rescored.sort(key=lambda hit: (-hit.score, hit.source_id,
                                       hit.representation_id, hit.start_offset))
        return tuple(rescored[:limit])


class NarrowingRetriever:
    """Pick the most relevant documents first, then passages within them.

    A long document can otherwise flood the candidate list with weak matches, and
    a short list from a few relevant documents is what a small model can judge.
    Documents are ranked by their best passage plus half their second best; at most
    `max_documents` documents and `per_document` passages each are returned.
    """
    def __init__(self, base: CorpusRetriever, *, max_documents: int = 5, per_document: int = 3,
                 pool: int = 60) -> None:
        if max_documents < 1 or per_document < 1 or pool < 1:
            raise ValueError("max_documents, per_document and pool must be positive")
        self.base = base
        self.max_documents = max_documents
        self.per_document = per_document
        self.pool = pool
        self.version = f"ewv3-narrow-d{max_documents}-p{per_document}[{base.version}]"

    def search(self, query: str, *, channel: str, sources: tuple[SourceUnit, ...], limit: int):
        hits = self.base.search(query, channel=channel, sources=sources, limit=max(limit, self.pool))
        by_source: dict[str, list[SearchHit]] = {}
        for hit in hits:
            by_source.setdefault(hit.source_id, []).append(hit)
        def document_score(item):
            scores = sorted((h.score for h in item[1]), reverse=True)
            return scores[0] + (0.5 * scores[1] if len(scores) > 1 else 0.0)
        ranked = sorted(by_source.items(), key=lambda item: (-document_score(item), item[0]))
        kept = [hit for _sid, group in ranked[:self.max_documents] for hit in group[:self.per_document]]
        kept.sort(key=lambda h: (-h.score, h.source_id, h.representation_id,
                                 h.start_offset if h.start_offset is not None else -1))
        return tuple(kept[:limit])

    @property
    def backend_count(self) -> int:
        return getattr(self.base, "backend_count", 1)

    @property
    def backend_versions(self) -> tuple[str, ...]:
        return getattr(self.base, "backend_versions", (self.base.version,))

    @property
    def reranker_version(self) -> str:
        return getattr(self.base, "reranker_version", "")


def default_retriever() -> NarrowingRetriever:
    """Word search and BM25 fused by rank, narrowed by document. Exact search stays separate."""
    lexical = InMemoryRetriever()
    hybrid = HybridRetriever({"lexical": lexical, "bm25": BM25Retriever()})
    return NarrowingRetriever(_ExactOrHybrid(lexical, hybrid), max_documents=8, per_document=4)


class _ExactOrHybrid:
    """Route the exact channel to exact search and every other channel to the fused search."""
    def __init__(self, exact: InMemoryRetriever, hybrid: HybridRetriever) -> None:
        self.exact = exact
        self.hybrid = hybrid
        self.version = f"exact:{exact.version}|{hybrid.version}"

    def search(self, query: str, *, channel: str, sources: tuple[SourceUnit, ...], limit: int):
        if channel == "exact":
            return self.exact.search(query, channel="exact", sources=sources, limit=limit)
        return self.hybrid.search(query, channel="hybrid", sources=sources, limit=limit)

    @property
    def backend_count(self) -> int:
        return self.hybrid.backend_count

    @property
    def backend_versions(self) -> tuple[str, ...]:
        return ("exact:" + self.exact.version, *self.hybrid.backend_versions)

    @property
    def reranker_version(self) -> str:
        return self.hybrid.reranker_version
