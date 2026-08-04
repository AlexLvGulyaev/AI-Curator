"""RAG pipeline: embeddings + Chroma vector search for AI Curator Knowledge Base."""

import asyncio
import hashlib
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import chromadb
from langchain_openai import OpenAIEmbeddings

from config import settings
from services.chroma_client import get_chroma_client
from services.document_processor import ProcessedChunk


@dataclass
class SearchResult:
    """A single semantic search result."""

    chunk_id: str
    content: str
    metadata: Dict[str, Any]
    distance: float


class RagPipelineError(Exception):
    """Base exception for RAG pipeline operations."""

    pass


class _EmbeddingCache:
    """Simple in-memory LRU cache with TTL for query embeddings."""

    def __init__(self, maxsize: int = 1000, ttl_seconds: float = 300.0):
        self.maxsize = maxsize
        self.ttl_seconds = ttl_seconds
        self._store: Dict[str, Tuple[List[float], float]] = {}
        self._order: List[str] = []

    def _normalize(self, text: str) -> str:
        # Stable hash of normalized query text.
        normalized = " ".join(text.lower().split())
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get(self, text: str) -> Optional[List[float]]:
        key = self._normalize(text)
        now = time.monotonic()
        if key in self._store:
            vector, expires = self._store[key]
            if expires > now:
                # Move to MRU position.
                self._order.remove(key)
                self._order.append(key)
                return vector
            # Expired: remove below.
        self._delete(key)
        return None

    def set(self, text: str, vector: List[float]) -> None:
        key = self._normalize(text)
        now = time.monotonic()
        self._delete(key)
        self._store[key] = (vector, now + self.ttl_seconds)
        self._order.append(key)
        self._evict()

    def _delete(self, key: str) -> None:
        if key in self._store:
            del self._store[key]
        if key in self._order:
            self._order.remove(key)

    def _evict(self) -> None:
        now = time.monotonic()
        # Evict expired entries first.
        expired = [k for k, (_, exp) in self._store.items() if exp <= now]
        for k in expired:
            self._delete(k)
        # Then evict LRU if still over size.
        while len(self._store) > self.maxsize and self._order:
            lru = self._order.pop(0)
            self._delete(lru)


class RagPipeline:
    """Manage embeddings indexing and semantic search over Chroma."""

    COLLECTION_NAME = "ai_curator_kb"
    # Shared process-level cache across pipeline instances.
    _embedding_cache = _EmbeddingCache(maxsize=1000, ttl_seconds=300.0)

    def __init__(
        self,
        embedding_model: str | None = None,
        collection_name: str | None = None,
        client: chromadb.ClientAPI | None = None,
        embedding_cache: Optional[_EmbeddingCache] = None,
    ):
        self.embedding_model = embedding_model or settings.openai_embedding_model
        self.collection_name = collection_name or settings.chroma_collection_name or self.COLLECTION_NAME
        self.client = client or get_chroma_client()
        self.embeddings = OpenAIEmbeddings(
            model=self.embedding_model,
            api_key=settings.openai_api_key,
        )
        self._collection: chromadb.Collection | None = None
        self._embedding_cache = embedding_cache or self._embedding_cache

    @property
    def collection(self) -> chromadb.Collection:
        """Lazy-initialized Chroma collection."""
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def _chunk_id(self, version_id: int, chunk_index: int) -> str:
        return f"{version_id}:{chunk_index}"

    def _build_metadata(
        self,
        document_id: int,
        version_id: int,
        chunk_index: int,
        course_id: Optional[int],
        module_id: Optional[int],
        topic_id: Optional[int],
        difficulty: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Build a Chroma metadata dict (JSON-serializable, no nulls)."""
        metadata: Dict[str, Any] = {
            "document_id": document_id,
            "version_id": version_id,
            "chunk_index": chunk_index,
            "status": "indexed",
        }
        if difficulty is not None:
            metadata["difficulty"] = difficulty
        if course_id is not None:
            metadata["course_id"] = course_id
        if module_id is not None:
            metadata["module_id"] = module_id
        if topic_id is not None:
            metadata["topic_id"] = topic_id
        return metadata

    async def index_chunks(
        self,
        chunks: List[ProcessedChunk],
        document_id: int,
        version_id: int,
        course_id: Optional[int] = None,
        module_id: Optional[int] = None,
        topic_id: Optional[int] = None,
        difficulty: str = "beginner",
        embedding_timeout_ms: Optional[int] = None,
    ) -> int:
        """Embed and store chunks in Chroma. Returns number of indexed chunks."""
        if not chunks:
            return 0

        ids = [self._chunk_id(version_id, chunk.chunk_index) for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            self._build_metadata(
                document_id=document_id,
                version_id=version_id,
                chunk_index=chunk.chunk_index,
                course_id=course_id,
                module_id=module_id,
                topic_id=topic_id,
                difficulty=difficulty,
            )
            for chunk in chunks
        ]

        # OpenAIEmbeddings.embed_documents is sync — run in a thread with timeout.
        try:
            timeout_seconds = embedding_timeout_ms / 1000 if embedding_timeout_ms else None
            if timeout_seconds:
                embeddings = await asyncio.wait_for(
                    asyncio.to_thread(self.embeddings.embed_documents, documents),
                    timeout=timeout_seconds,
                )
            else:
                embeddings = await asyncio.to_thread(self.embeddings.embed_documents, documents)
        except asyncio.TimeoutError as exc:
            raise RagPipelineError(
                f"Embedding indexing timed out after {embedding_timeout_ms}ms"
            ) from exc
        except Exception as exc:
            raise RagPipelineError(f"Embedding indexing failed: {exc}") from exc

        self.collection.upsert(
            ids=ids,
            embeddings=embeddings,
            metadatas=metadatas,
            documents=documents,
        )
        return len(chunks)

    def delete_version_chunks(self, version_id: int) -> None:
        """Remove all chunks belonging to a specific document version."""
        try:
            self.collection.delete(where={"version_id": version_id})
        except Exception as exc:
            # Collection may not exist yet or deletion may fail on empty collection.
            raise RagPipelineError(
                f"Failed to delete chunks for version {version_id}: {exc}"
            ) from exc

    def _build_where_filter(
        self,
        document_id: Optional[int] = None,
        version_id: Optional[int] = None,
        course_id: Optional[int] = None,
        module_id: Optional[int] = None,
        topic_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        status: Optional[str] = "indexed",
        strict_course: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Compose a Chroma where-clause from optional filters.

        Args:
            strict_course: If False, course_id is omitted from the Chroma where-clause
                so the semantic search can return relevant chunks from any course.
                The caller is expected to boost course-matching chunks at ranking stage.
        """
        filters: Dict[str, Any] = {}
        if document_id is not None:
            filters["document_id"] = document_id
        if version_id is not None:
            filters["version_id"] = version_id
        if course_id is not None and strict_course:
            filters["course_id"] = course_id
        if module_id is not None:
            filters["module_id"] = module_id
        if topic_id is not None:
            filters["topic_id"] = topic_id
        if difficulty is not None:
            filters["difficulty"] = difficulty
        if status is not None:
            filters["status"] = status
        if not filters:
            return None
        if len(filters) == 1:
            key, value = next(iter(filters.items()))
            return {key: value}
        # Chroma where-clauses with more than one field require a logical operator.
        return {"$and": [{key: value} for key, value in filters.items()]}

    async def search(
        self,
        query: str,
        k: int = 5,
        document_id: Optional[int] = None,
        version_id: Optional[int] = None,
        course_id: Optional[int] = None,
        module_id: Optional[int] = None,
        topic_id: Optional[int] = None,
        difficulty: Optional[str] = None,
        strict_course: bool = True,
        course_boost_enabled: bool = False,
        course_boost_factor: float = 0.15,
        embedding_timeout_ms: Optional[int] = None,
        retrieval_timeout_ms: Optional[int] = None,
    ) -> tuple[List[SearchResult], Dict[str, float]]:
        """Run semantic search and return ranked chunks.

        Args:
            strict_course: When True, Chroma query is filtered by course_id.
                When False, the filter is relaxed and course-matching chunks are
                boosted at the ranking stage (if course_boost_enabled is True).
            course_boost_enabled: Whether to apply a distance penalty/bonus for
                chunks whose course_id matches the requested course.
            course_boost_factor: Fraction of the raw distance used as a boost for
                course-matching chunks. Smaller values make the boost weaker.
            embedding_timeout_ms: Optional timeout for the embedding call.
            retrieval_timeout_ms: Optional timeout for the Chroma vector search.
        """
        where_strict = self._build_where_filter(
            document_id=document_id,
            version_id=version_id,
            course_id=course_id,
            module_id=module_id,
            topic_id=topic_id,
            difficulty=difficulty,
            strict_course=True,
        )

        # Try process-level embedding cache first to avoid repeated OpenAI API calls.
        t_embed_start = time.perf_counter()
        cached = self._embedding_cache.get(query)
        if cached is not None:
            query_embedding = cached
            embedding_ms = round((time.perf_counter() - t_embed_start) * 1000, 2)
        else:
            try:
                timeout_seconds = embedding_timeout_ms / 1000 if embedding_timeout_ms else None
                if timeout_seconds:
                    query_embedding = await asyncio.wait_for(
                        asyncio.to_thread(self.embeddings.embed_query, query),
                        timeout=timeout_seconds,
                    )
                else:
                    query_embedding = await asyncio.to_thread(self.embeddings.embed_query, query)
                self._embedding_cache.set(query, query_embedding)
                embedding_ms = round((time.perf_counter() - t_embed_start) * 1000, 2)
            except asyncio.TimeoutError as exc:
                raise RagPipelineError(
                    f"Embedding request timed out after {embedding_timeout_ms}ms"
                ) from exc
            except Exception as exc:
                raise RagPipelineError(f"Embedding request failed: {exc}") from exc

        results: List[SearchResult] = []
        seen_ids: set = set()

        def _add_results(raw_results: Any) -> None:
            ids = raw_results.get("ids", [[]])[0]
            documents = raw_results.get("documents", [[]])[0]
            metadatas = raw_results.get("metadatas", [[]])[0]
            distances = raw_results.get("distances", [[]])[0]
            for idx, chunk_id in enumerate(ids):
                if chunk_id in seen_ids:
                    continue
                seen_ids.add(chunk_id)
                meta = metadatas[idx] if idx < len(metadatas) else {}
                distance = distances[idx] if idx < len(distances) else 0.0
                if course_boost_enabled and course_id is not None:
                    # Cosine distance: smaller is better. Reduce distance for
                    # chunks that match the requested course_id.
                    if meta.get("course_id") == course_id:
                        distance = max(0.0, distance * (1.0 - course_boost_factor))
                results.append(
                    SearchResult(
                        chunk_id=chunk_id,
                        content=documents[idx] if idx < len(documents) else "",
                        metadata=meta,
                        distance=distance,
                    )
                )

        t_chroma_start = time.perf_counter()

        def _query_chroma(where_filter, n_results):
            return self.collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where_filter,
                include=["documents", "metadatas", "distances"],
            )

        # Phase 1: strict search with course filter (when requested).
        if strict_course and where_strict is not None:
            try:
                timeout_seconds = retrieval_timeout_ms / 1000 if retrieval_timeout_ms else None
                if timeout_seconds:
                    strict_results = await asyncio.wait_for(
                        asyncio.to_thread(_query_chroma, where_strict, k),
                        timeout=timeout_seconds,
                    )
                else:
                    strict_results = await asyncio.to_thread(_query_chroma, where_strict, k)
                _add_results(strict_results)
            except asyncio.TimeoutError as exc:
                raise RagPipelineError(
                    f"Chroma query timed out after {retrieval_timeout_ms}ms"
                ) from exc
            except Exception as exc:
                raise RagPipelineError(f"Chroma query failed: {exc}") from exc

        # Phase 2: relaxed search without course filter to find relevant generic
        # materials that may not be tagged with the exact course_id.
        if not strict_course and course_id is not None:
            where_relaxed = self._build_where_filter(
                document_id=document_id,
                version_id=version_id,
                course_id=None,
                module_id=module_id,
                topic_id=topic_id,
                difficulty=difficulty,
                strict_course=False,
            )
            if where_relaxed is not None:
                try:
                    timeout_seconds = retrieval_timeout_ms / 1000 if retrieval_timeout_ms else None
                    if timeout_seconds:
                        relaxed_results = await asyncio.wait_for(
                            asyncio.to_thread(_query_chroma, where_relaxed, k * 2),
                            timeout=timeout_seconds,
                        )
                    else:
                        relaxed_results = await asyncio.to_thread(_query_chroma, where_relaxed, k * 2)
                    _add_results(relaxed_results)
                except asyncio.TimeoutError as exc:
                    raise RagPipelineError(
                        f"Chroma query timed out after {retrieval_timeout_ms}ms"
                    ) from exc
                except Exception as exc:
                    raise RagPipelineError(f"Chroma query failed: {exc}") from exc

        # strict_course means strict: do not fall back to generic cross-course materials.

        chroma_ms = round((time.perf_counter() - t_chroma_start) * 1000, 2)

        # Re-rank by adjusted distance (course-boosted chunks move up).
        results.sort(key=lambda r: r.distance)

        return results[:k], {"embedding_ms": embedding_ms, "chroma_ms": chroma_ms}
