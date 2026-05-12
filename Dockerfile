# --- Stage 1: Base Python & UV ---
# UV version sourced from pyproject.toml build-system.requires (e.g. uv_build>=0.9.27)
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS backend-builder
WORKDIR /app
# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy only the files needed for installing dependencies to cache them
COPY pyproject.toml uv.lock ./
COPY README.md ./
COPY src ./src
COPY genesis-cli ./genesis-cli
COPY genesis-core ./genesis-core
COPY genesis-server ./genesis-server
COPY genesis-tui ./genesis-tui
COPY genesis-tools ./genesis-tools
# Install dependencies (no --no-install-workspace to allow proper venv linkage)
RUN uv sync --frozen --no-dev

# --- Stage 2: Frontend Build ---
# Node version sourced from .nvmrc (also in .node-version)
# pnpm version sourced from package.json "packageManager" field
FROM node:22.13.0-slim AS frontend-builder
WORKDIR /app
# Install pnpm (pinned version, using npm to avoid corepack signature issues)
RUN npm install -g pnpm@10.28.2
# Copy frontend files
COPY genesis-frontend/package.json genesis-frontend/pnpm-lock.yaml ./
RUN pnpm install
COPY genesis-frontend ./
# Build the Next.js app
RUN pnpm build

# --- Stage 3: Final Runtime ---
FROM python:3.11-slim-bookworm
WORKDIR /app

# Install Node.js in the final image (needed to run Next.js)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy the uv binary directly from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy backend from builder
COPY --from=backend-builder /app /app
# Copy frontend from builder
COPY --from=frontend-builder /app/ /app/genesis-frontend/

# Copy README to ensure the genesis package has all declared components
COPY README.md /app/README.md

# Prepare data directories (where volumes will be mounted)
RUN mkdir -p /app/.genesis /app/user_directories

# Environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV NODE_ENV=production
ENV PORT=3000

# Create a startup script to run both processes
# Using direct binary invocation (genesis serve) instead of 'uv run' to avoid runtime re-sync
RUN cat > /app/entrypoint.sh << 'SCRIPT' && chmod +x /app/entrypoint.sh
#!/bin/bash

# Function to handle shutdown signals
_term() {
  echo "Stopping container..."
  kill -TERM "$backend_pid" 2>/dev/null
  kill -TERM "$frontend_pid" 2>/dev/null
  exit 0
}

# Trap SIGTERM and SIGINT
trap _term SIGTERM SIGINT

# Track process health
echo "Starting Backend..."
genesis serve &
backend_pid=$!

# Wait briefly to check backend started
sleep 3
if ! kill -0 "$backend_pid" 2>/dev/null; then
  echo "Backend failed to start!"
  exit 1
fi

echo "Starting Frontend..."
cd /app/genesis-frontend && npm run start -- -p 3000 &
frontend_pid=$!

# Wait briefly to check frontend started
sleep 3
if ! kill -0 "$frontend_pid" 2>/dev/null; then
  echo "Frontend failed to start!"
  kill -TERM "$backend_pid" 2>/dev/null
  exit 1
fi

echo "All services started successfully"

# Wait for processes to exit, but keep the script alive to catch signals
wait -n

# If one process dies, kill the other and exit
_term
SCRIPT

# Healthcheck - verify both processes are still running
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD ps aux | grep -q "[g]enesis serve" && ps aux | grep -q "[n]ext start"

# Expose ports: Backend (usually 8000) and Frontend (3000)
EXPOSE 8000
EXPOSE 3000

CMD ["/app/entrypoint.sh"]