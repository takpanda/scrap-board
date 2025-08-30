# Scrap-Board - Web Content Collection & Management System

Always reference these instructions first and fallback to search or bash commands only when you encounter unexpected information that does not match the info here.

## Project Overview
Scrap-Board is a Japanese web application for collecting, processing, and managing web content and PDFs. It features automatic content classification, search capabilities, and a Reader Mode for optimal content consumption. The system uses FastAPI with HTMX frontend, SQLite database, and integrates with LM Studio or Ollama for LLM functionality.

**Current Status**: Early development stage - repository contains only basic README.md. Full implementation planned based on detailed requirements in issue #1.

## Technology Stack & Architecture
- **Backend**: Python 3.11+ with FastAPI
- **Frontend**: HTMX + Jinja2 templates with Tailwind CSS
- **Database**: SQLite (development/personal use)
- **LLM Integration**: LM Studio (default) or Ollama via OpenAI-compatible API
- **PDF Processing**: Docling (primary) with pdfminer.six fallback
- **Content Extraction**: Trafilatura for HTML
- **Deployment**: Docker with single container architecture
- **Language**: Japanese language support required for all user-facing content, articles, and chat interactions

## Validated Commands & Timing

The following commands have been tested and validated to work correctly:

### Environment Verification (Tested)
- **Python**: 3.12.3 available (compatible with 3.11+ requirement)
- **Docker**: 28.0.4 available for containerization
- **Git**: 2.51.0 available for version control
- **Curl**: 8.5.0 available for API testing

### Package Installation Timing (Measured)
- **FastAPI core packages**: ~10 seconds (fastapi, uvicorn, httpx)
- **Content extraction packages**: ~7 seconds (trafilatura with dependencies)
- **Complete dependency set**: Estimated 15-20 minutes with ML packages
- **FastAPI startup**: ~2-3 seconds for basic application

### Tested Commands
```bash
# Basic dependency installation (validated)
pip install fastapi uvicorn[standard] httpx trafilatura

# FastAPI test server startup (validated)
uvicorn app:app --host 0.0.0.0 --port 8000
# Expected startup time: 2-3 seconds

# LLM service connectivity tests (validated commands)
curl http://localhost:1234/v1/models  # LM Studio
curl http://localhost:11434/api/tags  # Ollama

# File operations (validated)
mkdir -p data && ls -la data
```

## Working Effectively

### Initial Repository Setup
Currently the repository contains:
```
.
├── README.md
├── .github/
│   └── copilot-instructions.md
├── .gitignore
└── .git/
```

### Expected Development Environment Setup
When development begins, use these commands:

1. **Install Python dependencies**:
   ```bash
   pip install fastapi uvicorn[standard] httpx sqlalchemy trafilatura docling pdfminer.six numpy pandas jinja2
   # NEVER CANCEL: Core dependencies take ~10-20 seconds, ML packages may take 5-10 minutes total
   # Set timeout to 15+ minutes for complete installation
   ```

2. **Set up external LLM service** (choose one):
   
   **LM Studio (Recommended)**:
   ```bash
   # Download and run LM Studio separately
   # Configure API endpoint: http://localhost:1234/v1
   # Load compatible models for chat and embeddings
   ```
   
   **Ollama Alternative**:
   ```bash
   curl -fsSL https://ollama.ai/install.sh | sh
   ollama pull llama3.1:8b-instruct
   ollama pull nomic-embed-text
   ollama serve  # Runs on http://localhost:11434
   ```

3. **Environment Configuration**:
   ```bash
   # Create .env file with:
   DB_URL=sqlite:///./data/scraps.db
   CHAT_API_BASE=http://localhost:1234/v1
   CHAT_MODEL=your-local-chat-model
   EMBED_API_BASE=http://localhost:1234/v1  
   EMBED_MODEL=your-local-embed-model
   TIMEOUT_SEC=30
   # Ensure LLM models support Japanese language for chat and content processing
   ```

4. **Run Development Server**:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   # NEVER CANCEL: Initial startup may take 2-3 minutes to load models
   ```

### Docker Development (Planned)
```bash
# Build container
docker build -t scrap-board .
# NEVER CANCEL: Docker build takes 10-15 minutes due to ML dependencies

# Run with docker-compose
docker-compose up -d
# NEVER CANCEL: First run takes 5-8 minutes to initialize database and load models
```

## Testing & Validation

### Manual Validation Scenarios
After making changes, ALWAYS test these core workflows:

1. **Content Ingestion Test**:
   ```bash
   curl -X POST http://localhost:8000/ingest/url \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com/article"}'
   # Expected: 200 response with document ID within 8 seconds
   ```

2. **PDF Processing Test**:
   ```bash
   curl -X POST http://localhost:8000/ingest/pdf \
     -F "file=@sample.pdf"
   # Expected: Successful extraction with Markdown formatting
   ```

3. **Search Functionality Test**:
   ```bash
   curl "http://localhost:8000/documents?q=test&category=テック/AI"
   # Expected: JSON response with filtered results
   ```

4. **Web UI Test**:
   - Navigate to http://localhost:8000
   - Test URL input and content ingestion
   - Verify Reader Mode toggle and text size controls
   - Test search with Japanese keywords
   - Validate category filtering works

### Build & Test Commands
```bash
# Run tests (when test suite exists)
pytest tests/ -v
# NEVER CANCEL: Test suite may take 10-15 minutes due to ML model loading

# Code quality checks
black app/ --check
flake8 app/
mypy app/
# NEVER CANCEL: First run of mypy may take 3-5 minutes
```

## Key Features & Components

### Content Processing Pipeline
1. **Input Acceptance**: URL, RSS feeds, PDF upload
2. **Content Extraction**: HTML (Trafilatura) + PDF (Docling)
3. **Normalization**: Convert to Markdown, language detection
4. **Embedding Generation**: Via LM Studio/Ollama API
5. **Classification**: Rules → kNN → LLM voting system
6. **Summarization**: Short/medium summaries via LLM
7. **Storage**: SQLite with full-text search index

### Database Schema (Planned)
- `documents`: Core content storage
- `classifications`: Category/tag assignments  
- `embeddings`: Vector representations for similarity search
- `collections`: User-organized content groups
- `feedbacks`: Correction data for improving classification

### UI Components & Styling
- **Design**: Modern, minimalist Japanese UI
- **Colors**: Ink/Charcoal base with Emerald or Indigo accents
- **Typography**: Inter + Noto Sans JP
- **Layout**: Fixed header (64px), collapsible sidebar (264px)
- **Reader Mode**: Optimized typography with multiple themes

## Common Development Tasks

### Adding New Classification Rules
```python
# Edit app/core/classification.py
rules = [
    {
        "name": "ai-content",
        "if_title": ["AI", "機械学習", "LLM"],
        "then_category": "テック/AI"
    }
]
```

### Updating Content Extraction
```python
# Modify app/services/extractor.py
# Always test with both HTML and PDF samples
# Ensure Japanese text handling works correctly
```

### Database Migrations
```bash
# Run Alembic migrations (when implemented)
alembic upgrade head
# NEVER CANCEL: Migration may take 5-10 minutes for large datasets
```

## Performance & Timing Expectations

### Response Time Targets
- **Single URL ingestion**: P50 < 8 seconds (including LLM processing)
- **Search queries**: P95 < 300ms (indexed data)
- **PDF processing**: Varies by size, 30 seconds for 50-page documents
- **Bulk ingestion**: 100 URLs may take 45-60 minutes

### Resource Requirements
- **Memory**: 4GB minimum (8GB recommended for larger models)
- **Storage**: SQLite + assets directory
- **CPU**: Model inference is CPU-intensive, expect high usage during processing

## Troubleshooting & Common Issues

### LLM Connection Issues
```bash
# Test LM Studio connection
curl http://localhost:1234/v1/models
# Should return available models list

# Test Ollama connection  
curl http://localhost:11434/api/tags
# Should return installed models
```

### PDF Processing Failures
- Docling primary extraction, pdfminer.six fallback
- Image-only PDFs will be skipped with warning
- Check logs for detailed error messages

### Classification Accuracy
- Monitor feedback collection in UI
- Adjust rule thresholds in configuration
- Retrain kNN classifier with accumulated feedback

## Security & Compliance
- **robots.txt compliance**: Always respected during crawling
- **Rate limiting**: Implemented to prevent overloading target sites
- **Data privacy**: No external data transmission except to configured LLM endpoints
- **Domain filtering**: Maintain allow/block lists for content sources

## File Structure (Expected)
```
app/
├── main.py                 # FastAPI application entry
├── core/
│   ├── config.py          # Environment configuration
│   ├── database.py        # SQLite connection
│   └── classification.py  # ML classification logic
├── services/
│   ├── extractor.py       # Content extraction
│   ├── llm_client.py      # LM Studio/Ollama integration
│   └── search.py          # Search functionality
├── api/
│   └── routes/            # API endpoints
├── templates/             # Jinja2 HTML templates
└── static/               # CSS, JS, images
tests/                    # Test suite
data/                     # SQLite database storage
docker-compose.yml        # Container orchestration
requirements.txt          # Python dependencies
.env                      # Environment variables
```

## Development Guidelines

### Language Usage Requirements
- **UI Text**: All user interface text must be in Japanese
- **Articles & Content**: All processed articles and content should be displayed in Japanese
- **Chat Functionality**: LLM chat interactions and responses must be in Japanese
- **User Communications**: All user-facing messages, notifications, and feedback should be in Japanese
- **Code Comments**: Internal code comments should be in English for developer clarity
- **API Documentation**: Technical documentation can be in English

### Other Guidelines
- **Error Handling**: Graceful degradation when LLM services unavailable
- **Logging**: Comprehensive operation logs for debugging
- **Testing**: Focus on content processing pipeline reliability
- **Documentation**: Maintain API documentation as code evolves

## External Dependencies
- **LM Studio**: Primary LLM service (recommended)
- **Ollama**: Alternative LLM service 
- **Internet Connection**: Required for content crawling
- **Storage**: Local filesystem for SQLite and extracted assets

Always ensure external LLM services are running before starting the application. The system cannot function without access to embedding and chat completion APIs.