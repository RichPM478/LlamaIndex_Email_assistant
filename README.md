# AI Email Intelligence Assistant

A production-ready AI-powered email assistant that brings ChatGPT-like intelligence to your inbox. Search, summarize, and interact with your emails using natural language.

## ✨ Features

### 🎯 Advanced Search & Retrieval
- **Hybrid Search**: Combines semantic understanding with keyword matching
- **Smart Reranking**: AI-powered result prioritization for better relevance
- **Natural Language Queries**: Ask questions like "What did Amazon ship last week?"

### 💬 Intelligent Responses
- **ChatGPT-style Interface**: Clean, conversational UI
- **Formatted Summaries**: Organized responses with headers, bullets, and structure
- **Source Attribution**: See exactly which emails were used for each answer

### ⚡ Performance
- **GPU Acceleration**: 30x faster with NVIDIA GPU support
- **Lazy Loading**: Sub-second startup times
- **Local Processing**: Everything runs on your machine - no cloud dependencies

### 🔒 Privacy First
- **100% Local**: Your emails never leave your computer
- **Encrypted Storage**: Credentials stored securely
- **No Tracking**: Complete privacy, no analytics

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- NVIDIA GPU (optional but recommended)
- Email account with IMAP access

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/RichPM478/LlamaIndex_Email_assistant.git
cd LlamaIndex_Email_assistant
```

2. **Create virtual environment**
```bash
python -m venv .venv
.venv\Scripts\activate  # Windows
# or
source .venv/bin/activate  # Linux/Mac
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your email credentials
```

5. **Run the assistant**
```bash
python run_app.py
```

## 📧 Email Setup

### Gmail
1. Enable 2-factor authentication
2. Generate an [App Password](https://myaccount.google.com/apppasswords)
3. Use the app password in `.env`

### Outlook/Office365
1. Use your email and password directly
2. Set `IMAP_HOST=outlook.office365.com`

### Other Providers
Check your provider's IMAP settings and update the `.env` accordingly.

## 🎮 Usage

### Starting the Application
```bash
python run_ui.py
```

### Basic Queries
- "Summarize today's emails"
- "Show me all Amazon orders"
- "What meetings do I have this week?"
- "Find urgent emails from my boss"

### Advanced Features
- **Time-based**: "What happened last Monday?"
- **Sender-specific**: "Emails from John about the project"
- **Topic search**: "Anything about machine learning"
- **Action items**: "What do I need to do today?"

## 🏗️ Architecture

### Technology Stack
- **LlamaIndex**: Orchestration framework
- **Embeddings**: mixedbread-ai/mxbai-embed-large-v1 (1024-dim)
- **Search**: Hybrid vector + BM25 with cross-encoder reranking
- **LLM**: Ollama (local) or OpenAI/Anthropic (cloud)
- **UI**: Streamlit chat interface

### Key Components
```
app/
├── indexing/          # Smart chunking & embedding generation
├── retrieval/         # Hybrid search with reranking
├── qa/                # Query processing & response formatting
├── ui/                # Chat interface
└── ingest/            # Email parsing & cleaning
```

## ⚙️ Configuration

### Embedding Models
Default uses high-quality local embeddings. For lighter models:
```python
# In .env
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # Faster, lower quality
```

### LLM Providers
```python
# Local (default)
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b

# OpenAI
LLM_PROVIDER=openai
OPENAI_API_KEY=your_key_here

# Anthropic
LLM_PROVIDER=anthropic
ANTHROPIC_API_KEY=your_key_here
```

## 📊 Performance

- **Indexing**: ~1000 emails in 3 minutes (GPU)
- **Query Response**: 1-2 seconds
- **Memory Usage**: ~2GB RAM + model size
- **GPU VRAM**: 4-6GB for embeddings

## 🛠️ Development

### Building Index
```bash
# Fetch emails
python main.py ingest --limit 1000

# Build index
python main.py index --full
```

### Running Tests
```bash
python main.py query "test query"
```

## 📝 License

MIT License - See LICENSE file for details

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## ⚠️ Important Notes

- **Never commit** `.env` files or `data/` directories
- **GPU Recommended**: CPU-only works but is significantly slower
- **Email Limits**: Start with 100-500 emails for testing

## 🐛 Troubleshooting

### Common Issues

**"No module named 'xyz'"**
```bash
pip install -r requirements.txt
```

**"CUDA out of memory"**
- Reduce batch size in embeddings
- Use smaller embedding model

**"Cannot connect to email"**
- Check IMAP settings
- Verify app password (not regular password)
- Check firewall/antivirus

## 📚 Resources

- [LlamaIndex Documentation](https://docs.llamaindex.ai/)
- [Streamlit Documentation](https://docs.streamlit.io/)
- [IMAP Setup Guides](https://support.google.com/mail/answer/7126229)

---

Built with ❤️ for email productivity