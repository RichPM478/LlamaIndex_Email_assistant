# 📧 LlamaIndex Email Assistant

An intelligent email assistant that uses AI to help you search, summarize, and understand your emails through natural language queries. Built with **LlamaIndex**, supporting both local (Ollama) and cloud LLMs.

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![LlamaIndex](https://img.shields.io/badge/LlamaIndex-Latest-green.svg)
![GPU Support](https://img.shields.io/badge/GPU-Supported-orange.svg)

## ✨ Features

### Core Functionality
- 🔍 **Natural Language Search**: Query emails like "Show me payment reminders" or "What events are coming up?"
- 📝 **Smart Summarization**: Get concise summaries of long email threads
- 🏷️ **Intelligent Categorization**: Automatically understand email context
- ⚡ **GPU Acceleration**: Full CUDA support for faster embeddings
- 🔐 **Secure**: Email encryption, credential management, and auth support

### Performance
- **Fast Responses**: 1-3 seconds after initial model load
- **Optimized Caching**: Models stay loaded in memory
- **HTML Parsing**: Clean text extraction from HTML emails
- **Batch Processing**: Efficient handling of 1000+ emails

### User Interfaces
1. **Modern Chat Interface** - WhatsApp-style conversation UI
2. **Analytics Dashboard** - Original interface with insights and metrics
3. **CLI Tool** - Command-line interface for automation

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- NVIDIA GPU (optional, for acceleration)
- Ollama installed (for local LLMs)
- Email account with IMAP access

### Installation

```bash
# Clone the repository
git clone https://github.com/RichPM478/LlamaIndex_Email_assistant.git
cd LlamaIndex_Email_assistant

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.\.venv\Scripts\Activate.ps1
# Or Linux/Mac
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
copy .env.example .env  # Windows
# cp .env.example .env  # Linux/Mac

# Edit .env with your settings
```

### Configuration (.env)

```env
# Email Settings
IMAP_HOST=imap.gmail.com
IMAP_PORT=993
IMAP_USER=your.email@gmail.com
IMAP_PASSWORD=your-app-password
IMAP_FOLDER=INBOX

# LLM Settings (Ollama - default)
LLM_PROVIDER=ollama
OLLAMA_MODEL=llama3.2:3b
OLLAMA_BASE_URL=http://localhost:11434

# Embeddings
EMBEDDINGS_PROVIDER=local_hf
EMBEDDING_MODEL=BAAI/bge-small-en-v1.5
```

## 📊 Usage

### Step 1: Ingest Emails

```bash
# Ingest last 500 emails
python main.py ingest --limit 500

# Or ingest from specific folder
python main.py ingest --folder "Sent" --limit 200
```

### Step 2: Build Index

```bash
# Build vector index (automatically uses GPU if available)
python main.py index
```

### Step 3: Query Your Emails

#### Option A: Interactive UI (Recommended)

```bash
# Launch the app selector
python run_app.py

# Or directly launch specific UI:
python -m streamlit run app/ui/chat_interface.py     # Modern chat UI
python -m streamlit run app/ui/streamlit_app.py      # Dashboard UI
```

#### Option B: Command Line

```bash
# Quick query
python main.py query "What was my latest email about?"

# More examples
python main.py query "Show me emails about payments"
python main.py query "Any emails from Amazon about orders?"
python main.py query "Find meeting invitations this week"
```

#### Option C: Python Script

```python
from app.qa.optimized_query import optimized_ask

result = optimized_ask("What events are coming up?")
print(result["answer"])
for source in result["citations"]:
    print(f"- {source['from']}: {source['subject']}")
```

## 🎯 Example Queries

- 📅 "What events are coming up?"
- 💳 "Show me bills and payment reminders"
- 📦 "Any shipping notifications?"
- 👔 "Find emails from LinkedIn about jobs"
- 🎫 "Show me travel confirmations"
- 📝 "Summarize emails from my manager"
- 🔔 "Any important notifications today?"

## 🏗️ Architecture

```
app/
├── ingest/          # Email ingestion & parsing
│   ├── imap_client.py      # IMAP connection handler
│   └── email_parser.py     # HTML to text extraction
├── indexing/        # Vector index creation
│   ├── build_index.py      # Index builder with clean text
│   └── incremental_indexer.py  # Smart incremental updates
├── qa/              # Query engines
│   ├── optimized_query.py  # Cached, fast query engine
│   └── simple_query.py     # Basic query interface
├── ui/              # User interfaces
│   ├── chat_interface.py   # Modern chat UI
│   └── streamlit_app.py    # Analytics dashboard
├── llm/             # LLM providers
│   └── provider.py         # Multi-provider support
└── embeddings/      # Embedding models
    └── provider.py         # GPU-accelerated embeddings

data/
├── raw/             # Raw email JSON files
└── index/           # Vector store indices
```

## ⚡ Performance

| Metric | Performance | Notes |
|--------|------------|-------|
| First Query | ~20 seconds | Model loading time |
| Subsequent Queries | 1-3 seconds | Models cached in memory |
| Email Processing | ~250 emails/sec | With GPU acceleration |
| Index Size | ~2MB per 1000 emails | After text extraction |
| Memory Usage | ~4GB | With models loaded |
| GPU VRAM | ~2GB | For embeddings |

## 🔧 Advanced Configuration

### GPU Acceleration
The system automatically detects and uses NVIDIA GPUs. Check status:

```python
python -c "import torch; print(f'GPU Available: {torch.cuda.is_available()}')"
```

### Model Selection

| Model | Size | Speed | Quality | Use Case |
|-------|------|-------|---------|----------|
| llama3.2:3b | 2GB | Fast | Good | Default, balanced |
| mistral:7b | 4GB | Medium | Better | Complex queries |
| llama3.1:8b | 5GB | Slower | Best | High accuracy needed |

### Embedding Models

| Model | Dimensions | Speed | Use Case |
|-------|------------|-------|----------|
| BAAI/bge-small-en-v1.5 | 384 | Fast | Default, general use |
| BAAI/bge-base-en-v1.5 | 768 | Medium | Better accuracy |
| sentence-transformers/all-MiniLM-L6-v2 | 384 | Very Fast | Quick searches |

## 🐛 Troubleshooting

### Common Issues

1. **Slow first query**: Normal - models loading. Subsequent queries will be fast.

2. **GPU not detected**:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

3. **IMAP connection failed**: 
   - Gmail: Use app-specific password
   - Outlook: Enable IMAP in settings
   - Corporate: May need `IMAP_SSL=False`

4. **Out of memory**:
   - Reduce `OLLAMA_NUM_CTX` in .env
   - Use smaller model (llama3.2:3b)
   - Reduce batch size

5. **HTML in responses**: Rebuild index:
   ```bash
   python main.py index --rebuild
   ```

## 📈 Recent Improvements

- ✅ Fixed HTML/CSS appearing in responses
- ✅ 95% performance improvement (61s → 3s)
- ✅ GPU acceleration properly configured
- ✅ Modern chat interface added
- ✅ Model caching implemented
- ✅ Clean text extraction from HTML emails

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

MIT License - see LICENSE file for details

## 🙏 Acknowledgments

- Built with [LlamaIndex](https://www.llamaindex.ai/)
- LLMs via [Ollama](https://ollama.ai/)
- UI with [Streamlit](https://streamlit.io/)
- GPU acceleration via [PyTorch](https://pytorch.org/)

## 📬 Support

For issues or questions, please open an issue on [GitHub](https://github.com/RichPM478/LlamaIndex_Email_assistant/issues).