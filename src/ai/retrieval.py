from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import json
import math
from typing import Any

from langchain_core.documents import Document
from sklearn.feature_extraction.text import HashingVectorizer


REGIME_MODEL_DISCLOSURE = (
    "HMM regime probability measures how well the latest observed features fit an inferred "
    "hidden state. It is not the probability of a future market move and is not a measured "
    "out-of-sample prediction accuracy. Predictive accuracy remains unverified until the model "
    "is evaluated with time-ordered walk-forward tests and independently defined regime labels."
)


@dataclass(frozen=True)
class RetrievalResult:
    context: str
    selected_sources: list[str]
    available_documents: int
    context_characters: int
    estimated_input_tokens: int

    def metadata(self) -> dict[str, Any]:
        return {
            "strategy": "local_hash_embeddings",
            "selected_sources": self.selected_sources,
            "selected_documents": len(self.selected_sources),
            "available_documents": self.available_documents,
            "context_characters": self.context_characters,
            "estimated_input_tokens": self.estimated_input_tokens,
            "external_embedding_tokens": 0,
        }


class LocalContextRetriever:
    """Selects compact context locally without sending text to an embedding API."""

    def __init__(self, *, top_k: int = 4, character_budget: int = 6000):
        self.top_k = max(2, top_k)
        self.character_budget = max(1200, character_budget)
        self.vectorizer = HashingVectorizer(
            n_features=1024,
            alternate_sign=False,
            norm="l2",
            ngram_range=(1, 2),
            stop_words="english",
        )

    def retrieve(self, query: str, context: dict[str, Any]) -> RetrievalResult:
        documents = self._documents(context)
        disclosure = next(
            document for document in documents if document.metadata["source"] == "model_disclosure"
        )
        candidates = [document for document in documents if document is not disclosure]
        ranked = self._rank(query, candidates)
        selected = [disclosure, *ranked[: self.top_k - 1]]

        rendered: list[str] = []
        selected_sources: list[str] = []
        used = 0
        for document in selected:
            source = str(document.metadata["source"])
            block = f"[{source}]\n{document.page_content.strip()}"
            remaining = self.character_budget - used
            if remaining <= 0:
                break
            if len(block) > remaining:
                block = block[: max(0, remaining - 1)].rstrip() + "…"
            rendered.append(block)
            selected_sources.append(source)
            used += len(block)

        compact_context = "\n\n".join(rendered)
        estimated_tokens = math.ceil((len(query) + len(compact_context)) / 4)
        return RetrievalResult(
            context=compact_context,
            selected_sources=selected_sources,
            available_documents=len(documents),
            context_characters=len(compact_context),
            estimated_input_tokens=estimated_tokens,
        )

    def _rank(self, query: str, documents: list[Document]) -> list[Document]:
        if not documents:
            return []
        query_vector = self.vectorizer.transform([query])
        document_vectors = self.vectorizer.transform(
            [f"{document.metadata['source']} {document.page_content}" for document in documents]
        )
        scores = (document_vectors @ query_vector.T).toarray().ravel()
        ranked = sorted(
            zip(scores, documents),
            key=lambda item: (float(item[0]), str(item[1].metadata["source"])),
            reverse=True,
        )
        return [document for _, document in ranked]

    def _documents(self, context: dict[str, Any]) -> list[Document]:
        documents = [
            Document(
                page_content=REGIME_MODEL_DISCLOSURE,
                metadata={"source": "model_disclosure"},
            )
        ]
        data_as_of = context.get("data_as_of")
        if data_as_of:
            documents.append(
                Document(
                    page_content=f"Portfolio analytics data as of {data_as_of}.",
                    metadata={"source": "data_freshness"},
                )
            )

        for name, payload in (context.get("tool_results") or {}).items():
            documents.append(
                Document(
                    page_content=self._json(payload),
                    metadata={"source": str(name)},
                )
            )

        for index, recommendation in enumerate(context.get("recommendations") or []):
            documents.append(
                Document(
                    page_content=self._json(recommendation),
                    metadata={"source": f"recommendation_{index + 1}"},
                )
            )

        warnings = context.get("warnings") or []
        if warnings:
            documents.append(
                Document(
                    page_content=self._json(warnings),
                    metadata={"source": "data_warnings"},
                )
            )
        return documents

    @classmethod
    def _json(cls, value: Any) -> str:
        return json.dumps(
            cls._compact(value),
            default=cls._json_default,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )

    @classmethod
    def _compact(cls, value: Any) -> Any:
        if isinstance(value, dict):
            compacted = {}
            for key, item in value.items():
                if key in {"series", "returns", "regime_history"} and isinstance(item, (list, dict)):
                    compacted[key] = cls._series_summary(item)
                else:
                    compacted[key] = cls._compact(item)
            return compacted
        if isinstance(value, (list, tuple)):
            rows = [cls._compact(item) for item in value[:8]]
            if len(value) > 8:
                rows.append({"omitted_rows": len(value) - 8})
            return rows
        if isinstance(value, float):
            return round(value, 8)
        return value

    @classmethod
    def _series_summary(cls, value: Any) -> dict[str, Any]:
        if isinstance(value, dict):
            return {
                str(key): cls._series_summary(item)
                for key, item in value.items()
            }
        if not isinstance(value, list):
            return {"value": cls._compact(value)}
        return {
            "row_count": len(value),
            "first": cls._compact(value[0]) if value else None,
            "latest": cls._compact(value[-1]) if value else None,
        }

    @staticmethod
    def _json_default(value: Any) -> str:
        if isinstance(value, (date, datetime)):
            return value.isoformat()
        return str(value)
