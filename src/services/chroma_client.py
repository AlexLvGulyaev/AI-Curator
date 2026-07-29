"""Chroma client factory for health checks and future RAG usage."""

import chromadb

from config import settings


def get_chroma_client() -> chromadb.ClientAPI:
    """Return a configured Chroma HTTP client."""
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)
