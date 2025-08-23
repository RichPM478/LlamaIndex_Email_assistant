"""
MCP Server for Smart Home Assistant

Exposes existing ingestion, indexing, retrieval, and document processing
capabilities as MCP tools for agent interoperability.

Tools:
- query_emails(question, top_k): Run semantic/hybrid query over the index
- ingest_emails(limit): Fetch emails via IMAP and save to raw JSON
- build_index(raw_path, persist_dir): Build vector index from raw emails
- process_document(path): Extract content from a document (PDF/Doc/Image)
- add_documents_to_index(paths, persist_dir): Index one or more documents
- calendar_import_ics(paths, persist_dir): Import .ics files as nodes
- whatsapp_import_txt(paths, persist_dir): Import exported WhatsApp chats

Run:
  python -m app.mcp.server

Requires `mcp` Python package. Install with:
  pip install mcp
"""

from __future__ import annotations

import os
import json
from typing import List, Dict, Any, Optional


def _lazy_import_mcp():
    try:
        # FastMCP is the recommended minimal server wrapper in the mcp package
        from mcp.server.fastmcp import FastMCP  # type: ignore
        from mcp.types import Tool  # noqa: F401  # for type hints only
        return FastMCP
    except Exception as e:
        raise RuntimeError(
            "The 'mcp' package is required. Install it with: pip install mcp\n"
            f"Import error: {e}"
        )


# Core app imports kept lazy to minimize startup overhead
def _ensure_llamaindex_ready():
    from app.config.settings import get_settings  # noqa: F401
    from app.llm.provider import configure_llm  # noqa: F401
    from app.embeddings.provider import configure_embeddings  # noqa: F401

    settings = get_settings()
    configure_llm(settings)
    configure_embeddings(settings)


def _load_index(persist_dir: str = "data/index"):
    from llama_index.core import StorageContext, load_index_from_storage
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    return load_index_from_storage(storage_context)


def _insert_nodes(index, texts: List[str], metadatas: Optional[List[Dict[str, Any]]] = None):
    from llama_index.core.schema import TextNode
    nodes = []
    for i, text in enumerate(texts):
        meta = (metadatas[i] if metadatas and i < len(metadatas) else {}) or {}
        nodes.append(TextNode(text=text, metadata=meta))
    if nodes:
        index.insert_nodes(nodes)
        index.storage_context.persist()
    return len(nodes)


def _process_single_document(path: str) -> Dict[str, Any]:
    from app.ingest.docling_processor import docling_processor
    # Read file bytes
    with open(path, "rb") as f:
        data = f.read()
    filename = os.path.basename(path)
    processed = docling_processor.process_attachment(
        attachment_data=data,
        filename=filename,
        content_type=None,
    )
    # Prepare payload
    content_for_index = docling_processor.extract_content_for_indexing(processed)
    return {
        "filename": filename,
        "metadata": content_for_index.get("metadata", {}),
        "content": content_for_index.get("content", ""),
        "has_tables": bool(processed.tables),
        "language": processed.language,
        "page_count": processed.page_count,
        "word_count": processed.word_count,
        "error": processed.error,
        "warnings": processed.warnings or [],
    }


def build_app():
    FastMCP = _lazy_import_mcp()
    app = FastMCP("smart_home_assistant")

    @app.tool()
    def query_emails(question: str, top_k: int = 5, include_sources: bool = True) -> Dict[str, Any]:
        """Query the email/document index and return an answer with optional citations."""
        from app.qa.query import ask
        _ensure_llamaindex_ready()
        result = ask(question, top_k=top_k, include_sources=include_sources)
        return result

    @app.tool()
    def ingest_emails(limit: int = 200) -> Dict[str, Any]:
        """Fetch emails via IMAP and save to raw JSON. Returns saved path and count."""
        from app.config.settings import get_settings
        from app.ingest.imap_loader import fetch_emails, save_raw_emails

        settings = get_settings()
        records = fetch_emails(settings, limit=limit)
        path = save_raw_emails(records)
        return {"saved_path": path, "count": len(records)}

    @app.tool()
    def build_index(raw_path: Optional[str] = None, persist_dir: str = "data/index") -> Dict[str, Any]:
        """Build the vector index from raw emails at raw_path. Persists to persist_dir."""
        from app.indexing.build_index import build_index as _build
        _ensure_llamaindex_ready()
        _build(raw_path=raw_path, persist_dir=persist_dir)
        return {"status": "ok", "persist_dir": persist_dir}

    @app.tool()
    def process_document(path: str) -> Dict[str, Any]:
        """Process a document (PDF/Word/Image/etc) and return extracted content and metadata."""
        if not os.path.exists(path):
            return {"error": f"File not found: {path}"}
        try:
            result = _process_single_document(path)
            return result
        except Exception as e:
            return {"error": str(e)}

    @app.tool()
    def add_documents_to_index(paths: List[str], persist_dir: str = "data/index") -> Dict[str, Any]:
        """Process and index one or more documents. Returns count indexed and any errors."""
        _ensure_llamaindex_ready()
        indexed = 0
        errors: List[str] = []
        texts: List[str] = []
        metas: List[Dict[str, Any]] = []
        for p in paths:
            try:
                res = _process_single_document(p)
                if res.get("error"):
                    errors.append(f"{os.path.basename(p)}: {res['error']}")
                    continue
                text = res.get("content", "").strip()
                if not text:
                    errors.append(f"{os.path.basename(p)}: no extractable text")
                    continue
                meta = {"source": os.path.basename(p), **(res.get("metadata") or {})}
                texts.append(text)
                metas.append(meta)
            except Exception as e:
                errors.append(f"{os.path.basename(p)}: {e}")

        if texts:
            index = _load_index(persist_dir=persist_dir)
            added = _insert_nodes(index, texts, metas)
            indexed += added

        return {"indexed": indexed, "errors": errors}

    @app.tool()
    def calendar_import_ics(paths: List[str], persist_dir: str = "data/index") -> Dict[str, Any]:
        """Import .ics calendar files as searchable nodes and add to the index."""
        from ics import Calendar
        _ensure_llamaindex_ready()
        texts: List[str] = []
        metas: List[Dict[str, Any]] = []
        errors: List[str] = []
        for p in paths:
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    c = Calendar(f.read())
                for ev in c.events:
                    summary = getattr(ev, "name", "Event") or "Event"
                    begin = getattr(ev, "begin", None)
                    end = getattr(ev, "end", None)
                    location = getattr(ev, "location", None)
                    desc = getattr(ev, "description", "") or ""
                    text = f"Calendar Event: {summary}\n\nWhen: {begin} to {end}\nLocation: {location or 'N/A'}\n\n{desc}"
                    texts.append(text)
                    metas.append({"source": os.path.basename(p), "type": "calendar_event", "summary": summary})
            except Exception as e:
                errors.append(f"{os.path.basename(p)}: {e}")

        indexed = 0
        if texts:
            index = _load_index(persist_dir=persist_dir)
            indexed = _insert_nodes(index, texts, metas)

        return {"indexed": indexed, "errors": errors}

    @app.tool()
    def whatsapp_import_txt(paths: List[str], persist_dir: str = "data/index") -> Dict[str, Any]:
        """Import exported WhatsApp chat .txt files and add as searchable conversation nodes."""
        _ensure_llamaindex_ready()
        texts: List[str] = []
        metas: List[Dict[str, Any]] = []
        errors: List[str] = []
        for p in paths:
            try:
                with open(p, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()
                if not content or len(content.strip()) < 20:
                    errors.append(f"{os.path.basename(p)}: empty or too short")
                    continue
                # Keep raw content; indexing will chunk
                texts.append(content)
                metas.append({"source": os.path.basename(p), "type": "whatsapp_chat"})
            except Exception as e:
                errors.append(f"{os.path.basename(p)}: {e}")

        indexed = 0
        if texts:
            index = _load_index(persist_dir=persist_dir)
            indexed = _insert_nodes(index, texts, metas)

        return {"indexed": indexed, "errors": errors}

    return app


def main():
    app = build_app()
    # FastMCP provides a default run method that reads stdio JSON-RPC
    app.run()


if __name__ == "__main__":
    main()




