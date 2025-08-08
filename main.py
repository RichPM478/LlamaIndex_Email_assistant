import typer
from typing import Optional
from app.ingest.imap_loader import fetch_emails, save_raw_emails
from app.indexing.build_index import build_index
from app.qa.query_engine import ask

app = typer.Typer(help="School Email Summarizer (POC) CLI")

@app.command()
def ingest(limit: int = 200):
    from app.config.settings import get_settings
    s = get_settings()
    recs = fetch_emails(s, limit=limit)
    path = save_raw_emails(recs)
    typer.echo(f"Saved {len(recs)} emails to {path}")

@app.command()
def index(input: Optional[str] = typer.Option(None, "--input", "-i", help="Path to raw emails (.json/.jsonl)")):
    build_index(raw_path=input)
    typer.echo("Index built -> data/index")

@app.command()
def query(q: str):
    ans = ask(q)
    typer.echo(f"Confidence: {ans['confidence']}\n\n{ans['answer']}\n\nCitations: {len(ans['citations'])}")

if __name__ == "__main__":
    app()