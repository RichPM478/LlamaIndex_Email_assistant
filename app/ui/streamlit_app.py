# Ensure project root is importable as a package (so `import app.*` works)
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import streamlit as st
from app.config.settings import get_settings
from app.ingest.imap_loader import fetch_emails, save_raw_emails
from app.indexing.build_index import build_index
from app.qa.query_engine import ask

st.set_page_config(page_title="School Email Summarizer (POC)", layout="wide")
st.title("📬 School Email Summarizer — POC")

settings = get_settings()
st.sidebar.header("Settings")
st.sidebar.text(f"LLM: {settings.llm_provider}")
st.sidebar.text(f"Embeddings: {settings.embeddings_provider}")
st.sidebar.text(f"IMAP Folder: {settings.imap_folder}")

st.header("1) Ingest & Index")
col1, col2 = st.columns(2)
with col1:
    if st.button("Fetch last 200 emails"):
        with st.spinner("Connecting to IMAP and fetching..."):
            recs = fetch_emails(settings, limit=200)
            path = save_raw_emails(recs, "data/raw/emails.jsonl")
        st.success(f"Saved {len(recs)} emails to {path}")
with col2:
    if st.button("Build/Rebuild Index"):
        with st.spinner("Building local semantic index..."):
            idx = build_index("data/raw/emails.jsonl", "data/index")
        st.success("Index built and persisted to data/index")

st.header("2) Ask a Question")
q = st.text_input("Try: What key events are happening this week, and do we need to bring money or equipment?")
if st.button("Ask") and q:
    with st.spinner("Thinking..."):
        result = ask(q)
    st.subheader(f"Answer (confidence: {result['confidence']})")
    st.write(result["answer"])
    st.markdown("---")
    st.subheader("Citations")
    for c in result["citations"]:
        st.markdown(f"**{c['subject']}** — {c['date']}  \nScore: {round(c['score'] or 0, 3)}  \n> {c['snippet']}")

st.caption("By default this uses your local Ollama. You can switch to OpenAI/Azure/Anthropic via .env without changing code.")
