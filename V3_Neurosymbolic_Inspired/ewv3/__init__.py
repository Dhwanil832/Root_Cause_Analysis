"""Standalone V3 Evidence Worker package."""

from .config import WorkerConfig
from .contracts import (
    AnswerSlot, CandidateLink, ComparisonSpec, CorpusManifest, EvidenceAssignment,
    EvidenceWorkerResult, InformationNeed, SourceRepresentation, SourceUnit,
)
from .engine import EvidenceWorkerEngine
from .lifecycle import WorkItemLifecycleStore
from .optional_models import (LocalCLIPImageTextEncoder, SentenceTransformerEmbedder,
                              SentenceTransformerReranker)
from .proposal import ArchiveEvidencePlanner
from .retrieval import (BM25Retriever, DenseVectorRetriever, FunctionReranker,
                        HybridRetriever, InMemoryRetriever, VisualVectorRetriever)

__all__ = [
    "AnswerSlot", "ArchiveEvidencePlanner", "CandidateLink", "ComparisonSpec", "CorpusManifest",
    "EvidenceAssignment", "EvidenceWorkerEngine", "EvidenceWorkerResult",
    "InformationNeed", "InMemoryRetriever", "DenseVectorRetriever", "HybridRetriever",
    "FunctionReranker", "SourceRepresentation", "SourceUnit", "WorkItemLifecycleStore", "WorkerConfig",
    "SentenceTransformerEmbedder", "SentenceTransformerReranker",
    "VisualVectorRetriever", "LocalCLIPImageTextEncoder",
    "BM25Retriever",
]
