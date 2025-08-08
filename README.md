# LlamaIndex Email Assistant

A minimal, modular email summarizer/search assistant built on **LlamaIndex**.  
Use **Ollama** locally (e.g., `llama3.2:3b`) or switch to **OpenAI / Azure OpenAI / Anthropic** via `.env`.

## Features
- Ingest emails from IMAP and store as JSON
- Build a vector index (LlamaIndex)
- Query via CLI or a small Streamlit UI
- Pluggable LLMs + embeddings
- Works offline with Ollama

## Quickstart (Windows / PowerShell)

```powershell
python -m venv .venv
. .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt

copy .env.example .env   # edit .env with your IMAP + LLM settings

# Ingest emails
python .\main.py ingest --limit 200

# Query from CLI
python .\main.py query "summarise the latest email"
