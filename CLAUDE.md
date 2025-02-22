# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

X-Ray Proxy is a Python-based HTTP/HTTPS proxy for KanColle (艦隊これくしょん) built as a mitmproxy addon. It intercepts and processes game traffic to save resources to S3-compatible object storage and send API responses to an X-Ray web application.

## Development Commands

### Core Commands (via uv and poethepoet)

- `uv run poe proxy` - Start the proxy server using mitmproxy
- `uv run poe dump` - Start in dump mode using mitmdump
- `uv run poe web` - Start with web interface using mitmweb

### Database Management

- `uv run poe db:migration:upgrade` - Apply database migrations
- `uv run poe db:migration:revision` - Create new migration

### Code Quality

- `uv run poe lint` - Run all linters (flake8, black, isort, mypy)
- `uv run poe format` - Format code (black + isort)
- `uv run poe test` - Run unit tests (using unittest discover)
- `uv run python -m unittest tests.xrayproxytest.module.test_class.test_method` - Run single test

### Utility Commands

- `uv run poe list_log` - List API logs
- `uv run poe pac` - Generate PAC file
- `uv run poe search` - Search functionality
- `uv run poe sprite` - Sprite operations

### Docker Development

- `docker compose up` - Start full stack (MinIO + proxy)
- `docker compose up minio` - Start only MinIO for storage

## Architecture

### Core Components

**XRayAddon** (`src/xrayproxy/addons/xray.py`): Main mitmproxy addon that orchestrates request/response handling. Uses async handlers and manages database connections, S3 storage, and HTTP sessions.

**Handler System**:

- Request handlers in `src/xrayproxy/handlers/request/` - Process incoming requests
- Response handlers in `src/xrayproxy/handlers/response/` - Process outgoing responses
- All handlers extend `BaseRequestHandler` or `BaseResponseHandler`

**Configuration**: TOML-based config system in `src/xrayproxy/config/` with hierarchical structure for different subsystems (X-Ray, storage, rewrite rules, etc.)

**Database**: SQLite with SQLAlchemy ORM and sqlc for type-safe queries. Schema in `sql/schema.sql`, generated code in `src/xrayproxy/generated/sqlc/`.

### Key Directories

- `src/xrayproxy/addons/` - mitmproxy addon implementations
- `src/xrayproxy/handlers/` - Request/response processing logic
- `src/xrayproxy/config/` - Configuration management
- `src/xrayproxy/lib/` - Utility libraries (HTTP, hashing, ships, etc.)
- `src/xrayproxy/commands/` - CLI command implementations
- `migration/` - Alembic database migrations
- `sql/` - Database schema and queries

## Configuration

The proxy requires a TOML configuration file (default: `config/xrayproxy.toml`). See `config/examples/` for sample configurations.

Key config sections:

- `x_ray` - X-Ray server webhook settings
- `storage` - S3-compatible object storage settings
- `resource` - Resource saving configuration
- `rewrite` - Response rewriting rules
- `logbook_kai` - Integration with logbook-kai

## Development Setup

1. Install dependencies: `uv sync`
2. Set up MinIO for storage: `docker compose up minio`
3. Run database migrations: `uv run poe db:migration:upgrade`
4. Copy and customize config: `cp config/examples/xrayproxy-sample.toml config/xrayproxy.toml`
5. Start proxy: `uv run poe proxy`

## Code Generation

- Database queries are generated via sqlc from `sql/queries/*.sql` to `src/xrayproxy/generated/sqlc/`
- Run `sqlc generate` to regenerate after schema/query changes
- Generated files are excluded from linting (configured in `pyproject.toml`)

## Code Style

- Black formatter with 119 character line length
- isort with black profile for import sorting
- Strict mypy type checking enabled
- Flake8 linting with E203 exception for black compatibility
