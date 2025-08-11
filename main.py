import typer
from typing import Optional
from app.ingest.imap_loader import fetch_emails, save_raw_emails
from app.indexing.build_index import build_index
from app.qa.intelligent_query import intelligent_ask as ask

app = typer.Typer(help="School Email Summarizer (POC) CLI")

@app.command()
def ingest(limit: int = 200):
    from app.config.settings import get_settings
    s = get_settings()
    recs = fetch_emails(s, limit=limit)
    path = save_raw_emails(recs)
    typer.echo(f"Saved {len(recs)} emails to {path}")

@app.command()
def index(
    input: Optional[str] = typer.Option(None, "--input", "-i", help="Path to raw emails (.json/.jsonl)"),
    incremental: bool = typer.Option(True, "--incremental/--full", help="Use incremental indexing (default) or rebuild from scratch")
):
    """Build or update the search index"""
    if incremental:
        from app.indexing.incremental_indexer import incremental_indexer
        typer.echo("🔄 Building incremental index...")
        idx = incremental_indexer.build_incremental_index(input)
        if idx:
            stats = incremental_indexer.get_index_stats()
            typer.echo(f"✅ Index updated! Total emails: {stats['total_emails_indexed']:,}")
        else:
            typer.echo("ℹ️ Index is already up to date")
    else:
        typer.echo("🔄 Rebuilding full index...")
        build_index(raw_path=input)
        typer.echo("✅ Full index rebuilt -> data/index")

@app.command()
def query(q: str):
    ans = ask(q)
    typer.echo(f"Confidence: {ans['confidence']}\n\n{ans['answer']}\n\nCitations: {len(ans['citations'])}")

if __name__ == "__main__":
    app()