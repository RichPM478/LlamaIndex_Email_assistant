# app/qa/query_engine.py
from typing import Dict, Any
from llama_index.core import StorageContext, load_index_from_storage
from llama_index.core.response_synthesizers import get_response_synthesizer, ResponseMode

from app.config.settings import get_settings
from app.llm.provider import configure_llm
from app.embeddings.provider import configure_embeddings


def load_index(persist_dir: str = "data/index"):
    storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
    return load_index_from_storage(storage_context)


def ask(question: str, top_k: int = 6) -> Dict[str, Any]:
    # ensure LLM + embeddings configured
    s = get_settings()
    configure_llm(s)
    configure_embeddings(s)

    index = load_index()

    # Build synthesizer; let LlamaIndex create the retriever internally
    synth = get_response_synthesizer(response_mode=ResponseMode.COMPACT)

    # IMPORTANT: don't pass a 'retriever' arg; just set the knobs here
    query_engine = index.as_query_engine(
        similarity_top_k=top_k,
        response_synthesizer=synth,      # or use response_mode=ResponseMode.COMPACT
    )

    resp = query_engine.query(question)

    return {
        "answer": str(resp),
        "confidence": getattr(resp, "score", None),
        "citations": [sn.node.metadata for sn in getattr(resp, "source_nodes", [])],
    }
