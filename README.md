# AI Email Intelligence System

A simplified AI-powered email intelligence system that helps you search and understand your emails using natural language queries.

## Features

- **Smart Email Parsing**: Quality-filtered email processing with MailParserAdapter
- **Natural Language Search**: Ask questions about your emails in plain English
- **Live Email Sync**: Real-time IMAP synchronization with quality filtering
- **WhatsApp-Style Chat Interface**: Clean, intuitive chat interface for email queries

## Quick Start

### Prerequisites
- Python 3.8+
- Ollama with required models:
  ```bash
  ollama pull llama3.1:8b-instruct-q4_0
  ollama pull mxbai-embed-large:335m-v1
  ```

### Installation
```bash
pip install -r requirements.txt
python run_app.py
```

### Configuration
On first run, configure your IMAP settings:
- IMAP server (e.g., imap.gmail.com)
- Email username
- App-specific password

## Usage

### Example Queries
- "Show me emails from Mount Carmel about my child"
- "Payment reminders from this week"
- "What's new about nursery updates?"
- "Recent meeting requests"

## Architecture

- **Email Parsing**: MailParserAdapter with quality scoring
- **Chunking**: SmartEmailChunker for context-aware text splitting  
- **Search**: Lazy-loaded query engine with vector embeddings
- **Interface**: Single WhatsApp-style chat interface

## System Flow
1. IMAP sync → MailParserAdapter → Quality filtering
2. SmartEmailChunker → Vector embeddings → Index storage
3. Natural language query → Vector search → Ranked results

---

**Status**: Simplified & Production Ready ✅