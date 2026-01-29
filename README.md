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

## Frontend

The frontend is a React application in the `frontend/` directory.

```bash
# Install dependencies
cd frontend
npm install

# Development server
npm start

# Build for production
npm run build
```

### Environment Variables (Frontend)

```bash
VITE_API_URL=http://localhost:8000  # Backend API URL
```

## Deploy on Railway

### Prerequisites

1. Railway account at https://railway.app
2. Railway CLI installed: `npm install -g @railway/cli`

### Deploy Steps

1. **Create Railway Project**
   ```bash
   railway login
   railway init
   ```

2. **Add PostgreSQL Database**
   - In Railway dashboard, click "New" → "Database" → "PostgreSQL"
   - The `DATABASE_URL` environment variable will be automatically set

3. **Deploy Backend**
   ```bash
   # From project root
   railway up
   ```

4. **Set Backend Environment Variables in Railway Dashboard**
   ```
   SECRET_KEY=<generate-secure-key>
   ACCESS_TOKEN_EXPIRE_MINUTES=480
   VISION_AGENT_API_KEY=<your-landingai-key>
   FRONTEND_URL=<your-frontend-url>
   ```

5. **Deploy Frontend**
   ```bash
   cd frontend
   railway init  # Create separate service
   railway up --build-arg VITE_API_URL=https://<your-backend>.railway.app
   ```

6. **Create Admin User**
   ```bash
   railway run python -m src.cli.create_admin --email admin@example.com --password <secure-password>
   ```

### Architecture on Railway

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│    Frontend     │────▶│    Backend      │────▶│   PostgreSQL    │
│  (React/Nginx)  │     │   (FastAPI)     │     │   (Railway)     │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   LandingAI     │
                        │   (External)    │
                        └─────────────────┘
```

## License

Proprietary - All rights reserved.
