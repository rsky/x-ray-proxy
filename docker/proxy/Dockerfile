FROM python:3.13-slim-bookworm

RUN mkdir -p /var/lib/x-ray-proxy/config
RUN mkdir -p /var/lib/x-ray-proxy/data/mitmproxy

WORKDIR /var/lib/x-ray-proxy

## Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    git

# Copy the settings
COPY README.md .python-version pyproject.toml ./
COPY alembic.ini.dist alembic.ini
COPY config/examples/xrayproxy-docker.toml config/xrayproxy.toml
COPY config/xrayproxy-*.toml config/
RUN if [ -f config/xrayproxy-docker.toml ]; then mv config/xrayproxy-docker.toml config/xrayproxy.toml; fi

# Copy the project files
COPY assets assets
COPY migration migration
COPY src src

# Install the project dependencies
RUN pip install uv
RUN uv sync

EXPOSE 8080

CMD uv run poe db:migration:upgrade && \
    uv run poe dump
