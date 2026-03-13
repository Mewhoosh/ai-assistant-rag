# LLM-Project - RAG AI Assistant

LLM-Project is a production-style GenAI assistant built with FastAPI, LangChain, ChromaDB, and SQLAlchemy.

The application supports two interaction modes:
- standard LLM chat,
- retrieval-augmented Q&A over uploaded PDF/TXT documents with source citations.

## Features

### Chat & RAG
- **Free chat** - ask general questions without uploading documents.
- **Document-grounded answers** - upload PDF/TXT files, run retrieval over relevant chunks, and generate grounded responses.
- **Source citations** - each answer includes chunk-level sources and relevance scores.
- **Conversation memory** - previous messages are included as context in ongoing conversations.

### Session-based history
- Each browser receives a unique `session_id` stored in a cookie.
- Conversation history is isolated per session (no login required).
- Conversations and messages are persisted in SQLite via SQLAlchemy.
- Existing conversations can be reopened or deleted from the sidebar.

### Documents
- Upload `PDF` and `TXT` files via the web UI or REST API.
- Files are parsed and chunked with configurable size/overlap.
- Chunks are embedded and stored in persistent ChromaDB collections.

### Developer-friendly
- **Swagger UI** at `/docs` for endpoint inspection and manual testing.
- **OpenAI** and **Ollama** provider support via `.env` configuration.
- **Dockerized setup** with `docker compose`.
- **16 pytest tests** covering API and document-processing paths.

## Interface Preview
The assistant was tested on `example_company_policy.pdf` uploaded through the UI.<img width="1901" height="921" alt="example" src="https://github.com/user-attachments/assets/a7e9e7e5-dac4-4758-ae64-10f1ec2f277b" />

The answers and cited sources shown in the UI are generated from retrieved chunks of `example_company_policy.pdf`.
## Architecture

```
                         +-------------------+
                         |   Frontend (HTML) |
                         +---------+---------+
                                   |
                                   v
                         +---------+-----------+
                         |   FastAPI (REST)    |
                         |   /api/documents    |
                         |   /api/chat         |
                         |   /api/conversations|
                         +---------+-----------+
                                   |
                    +--------------+---------------+
                    |                              |
           +--------v--------+         +---------v----------+
           | Document Service|         |    RAG Service     |
           | (parse, chunk)  |         | (retrieve, prompt, |
           +---------+-------+         |  generate, persist)|
                     |                 +---------+----------+
                     v                           |
           +---------+-------+          +--------+----------+
           |    ChromaDB     |<---------+   LangChain       |
           | (vector store)  |          | (OpenAI / Ollama) |
           +-----------------+          +-------------------+
                                                  |
                                        +---------v------------+
                                        |   SQLite + SQLAlchemy|
                                        |   (conversations,    |
                                        |    messages, docs)   |
                                        +----------------------+
```

## Request Flow

1. **Document ingestion** (`/api/documents/upload`)
   - The user uploads a PDF/TXT document.
   - Metadata is stored in SQLite and text extraction is handled by `document_service.py`.

2. **Chunking strategy**
   - Extracted text is split into overlapping chunks using configurable `CHUNK_SIZE` and `CHUNK_OVERLAP`.
   - This improves retrieval quality and context efficiency.

3. **Embeddings + vector index**
   - Chunks are embedded and stored in ChromaDB with metadata.
   - The vector index persists on disk across application restarts.

4. **Question answering** (`/api/chat`)
   - The system retrieves top-k relevant chunks from ChromaDB.
   - Retrieved context and conversation history are passed to the selected LLM provider.
   - The API returns the final answer and cited sources.

5. **Conversation persistence**
   - A session cookie (`session_id`) is managed automatically.
   - Conversation and message records are stored in SQLite via SQLAlchemy.

6. **Frontend behavior**
   - Left panel: upload controls, document list, conversation history.
   - Main panel: chat stream with expandable source citations.
   - `New Chat` starts a fresh conversation context.

## Tech Stack

| Layer              | Technology                      |
|--------------------|----------------------------------|
| API framework      | FastAPI, Pydantic v2             |
| LLM orchestration  | LangChain                        |
| LLM providers      | OpenAI API, Ollama (local)       |
| Vector store       | ChromaDB (embedded, persistent)  |
| Database           | SQLAlchemy 2.0 + SQLite          |
| Document parsing   | pypdf                            |
| Testing            | pytest, HTTPX                    |
| Containerization   | Docker, Docker Compose           |
| Frontend           | Vanilla HTML/CSS/JS              |

## Getting Started

### Prerequisites

- Python 3.11+
- An OpenAI API key **or** [Ollama](https://ollama.ai/) running locally

### Local Development

```bash
git clone https://github.com/Mewhoosh/llm-project.git
cd llm_project

python -m venv venv
venv\Scripts\activate

pip install -r requirements.txt

copy .env.example .env

python -m uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 to use the web interface, or http://localhost:8000/docs for the Swagger API explorer.

### Docker

```bash
copy .env.example .env
docker compose up --build
```

## Configuration

```dotenv
LLM_PROVIDER=openai            # openai | ollama
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini       # any supported OpenAI chat model
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
DATABASE_URL=sqlite:///./llm_project.db
CHROMA_PERSIST_DIR=./chroma_data
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
RETRIEVAL_TOP_K=5
RETRIEVAL_MIN_RELEVANCE_SCORE=0.35
```


## Testing

```bash
python -m pytest tests -q
```

## Project Structure

```
llm_project/
├── app/
│   ├── main.py              # FastAPI app, lifespan, routing
│   ├── config.py             # Settings (pydantic-settings)
│   ├── database.py           # SQLAlchemy engine and session
│   ├── models/
│   │   ├── db_models.py      # ORM models (Document, Conversation, Message)
│   │   └── schemas.py        # Pydantic request/response schemas
│   ├── services/
│   │   ├── document_service.py   # PDF/TXT parsing, text chunking
│   │   ├── embedding_service.py  # ChromaDB vector store operations
│   │   └── rag_service.py        # LangChain RAG pipeline
│   └── api/
│       ├── documents.py      # Document upload/list/delete endpoints
│       ├── chat.py           # Chat/question endpoint
│       └── conversations.py  # Conversation history endpoints
├── static/                   # Frontend (HTML, CSS, JS)
├── tests/                    # pytest test suite
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

