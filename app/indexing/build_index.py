import os, glob, json
from typing import List, Dict, Any, Optional
from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import TextNode

from app.config.settings import get_settings
from app.llm.provider import configure_llm
from app.embeddings.provider import configure_embeddings


def _load_raw_emails(path: str) -> List[Dict[str, Any]]:
    """Load emails from .json (list) or .jsonl (one JSON per line)."""
    emails: List[Dict[str, Any]] = []
    if path.endswith(".jsonl"):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    emails.append(json.loads(line))
    elif path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, list):
                emails = data
            else:
                raise ValueError(f"{path} must contain a JSON list")
    else:
        raise ValueError(f"Unsupported raw format: {path}")
    return emails


def _resolve_latest_raw(explicit_path: Optional[str]) -> str:
    """Pick the explicit file, or newest file in data/raw/, by modified time."""
    if explicit_path and os.path.exists(explicit_path):
        return explicit_path

    candidates = glob.glob("data/raw/*.json") + glob.glob("data/raw/*.jsonl")
    if not candidates:
        raise FileNotFoundError("No raw files found in data/raw/. Run `python main.py ingest` first.")

    latest = max(candidates, key=os.path.getmtime)
    return latest


def build_index(raw_path: Optional[str] = None, persist_dir: str = "data/index") -> VectorStoreIndex:
    settings = get_settings()
    configure_llm(settings)
    configure_embeddings(settings)

    raw_file = _resolve_latest_raw(raw_path)
    print(f"[index] Using raw file: {raw_file}")

    emails = _load_raw_emails(raw_file)

    splitter = SentenceSplitter(chunk_size=800, chunk_overlap=100)
    nodes: List[TextNode] = []
    for e in emails:
        text = (e.get("body_text") or e.get("body") or "").strip()
        if not text:
            continue
        meta = {
            "message_id": e.get("message_id"),
            "uid": e.get("uid"),
            "subject": e.get("subject"),
            "from": e.get("from_") or e.get("from"),
            "date": e.get("date"),
            "sent_at": e.get("sent_at"),
            "folder": e.get("folder"),
        }
        for ch in splitter.split_text(text):
            nodes.append(TextNode(text=ch, metadata=meta))

    os.makedirs(persist_dir, exist_ok=True)
    index = VectorStoreIndex(nodes)
    index.storage_context.persist(persist_dir=persist_dir)
    return index
