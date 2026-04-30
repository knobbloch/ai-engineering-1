# KB Chat — Interview Task

Interview task: add LLM response caching to an internal bank chatbot.

**Start here:** [TASK.md](TASK.md)

## Repository Structure

```
├── src/kb_chat/           # Service source code
├── tests/kb_chat_tests/   # Tests
├── docs/                  # Architecture diagrams
├── TASK.md                # Task description
└── README.md              # This file
```

## Architecture

- [C4 + DDD code-level diagrams](docs/architecture-c4-ddd.md)

## Quick Start

```bash
# Install dependencies
uv sync --all-groups

# Run server
uv run uvicorn kb_chat:create_app --factory --reload --port 8000

# Run tests
uv run pytest tests/ -v

# Test API
curl http://localhost:8000/api/v1/topics
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "How many vacation days?", "topic": "vacation"}'
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/topics` | List available topics |
| POST | `/api/v1/chat` | Chat with knowledge base |

## Code Quality

```bash
uv run ruff check src/ tests/
uv run mypy src/
```
