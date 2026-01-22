# AuditEng V2

Automated validation system for electrical commissioning reports in data centers.

## Quick Start

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended) or pip

### Installation

```bash
# Clone and enter directory
git clone <repository-url>
cd auditeng-v2

# Install dependencies with uv (recommended)
uv sync

# Or with pip
pip install -e ".[dev]"
```

### Running the Server

```bash
# Development server with auto-reload
uvicorn src.api.main:app --reload --port 8000

# Production
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### Verify Installation

```bash
# Health check
curl http://localhost:8000/health
# Expected: {"status":"ok","version":"0.1.0"}

# API documentation
open http://localhost:8000/docs
```

## Development

### Code Quality

```bash
# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/

# Run tests
pytest

# Run tests with coverage
pytest --cov=src --cov-report=html
```

### Project Structure

```
auditeng-v2/
├── src/
│   ├── api/              # FastAPI routes and app
│   │   ├── main.py       # Application entry point
│   │   ├── routes/       # API endpoints
│   │   └── dependencies.py
│   ├── pipeline/         # Validation pipeline (Phase 2+)
│   ├── domain/
│   │   ├── schemas/      # Pydantic API models
│   │   └── rules/        # Validation rules (Phase 4+)
│   ├── storage/
│   │   ├── database.py   # Async SQLite setup
│   │   └── models.py     # SQLModel ORM models
│   └── context/          # Claude persona and rules
├── tests/
├── data/                 # SQLite database and uploads
├── pyproject.toml
└── README.md
```

### Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
cp .env.example .env
```

See `.env.example` for available configuration options.

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## License

Proprietary - All rights reserved.
