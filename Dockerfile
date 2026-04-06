# --- Stage 1: Base Python & UV ---
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS backend-builder
WORKDIR /app
# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy only the files needed for installing dependencies to cache them
COPY pyproject.toml uv.lock ./
COPY src ./src
COPY myproject-cli ./myproject-cli
COPY myproject-core ./myproject-core
COPY myproject-server ./myproject-server
COPY myproject-tui ./myproject-tui
COPY myproject-tools ./myproject-tools
# Install dependencies
RUN uv sync --frozen --no-dev --no-install-workspace

# --- Stage 2: Frontend Build ---
FROM node:20-slim AS frontend-builder
WORKDIR /app
# Install pnpm
RUN corepack enable && corepack prepare pnpm@latest --activate
# Copy frontend files
COPY myproject-frontend/package.json myproject-frontend/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY myproject-frontend ./
# Build the Next.js app
RUN pnpm build

# --- Stage 3: Final Runtime ---
FROM python:3.11-slim-bookworm
WORKDIR /app

# Install Node.js in the final image (needed to run Next.js)
RUN apt-get update && apt-get install -y curl && \
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
    apt-get install -y nodejs && \
    rm -rf /var/lib/apt/lists/*

# Copy the uv binary directly from the official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy backend from builder
COPY --from=backend-builder /app /app
# Copy frontend from builder
COPY --from=frontend-builder /app/ /app/myproject-frontend/

# Copy README to ensure the myproject package has all declared components
COPY README.md /app/README.md

# Copy agents and workflow declarations
COPY agents ./agents
COPY workflows ./workflows

# Prepare data directories (where volumes will be mounted)
RUN mkdir -p /app/database /app/workspaces

# Environment variables
ENV PATH="/app/.venv/bin:$PATH"
ENV NODE_ENV=production
ENV PORT=3000

# Create a startup script to run both processes
RUN echo '#!/bin/bash\n\
# Function to handle shutdown signals\n\
_term() {\n\
  echo "Stopping container..."\n\
  kill -TERM "$backend_pid" 2>/dev/null\n\
  kill -TERM "$frontend_pid" 2>/dev/null\n\
  exit 0\n\
}\n\
\n\
# Trap SIGTERM and SIGINT\n\
trap _term SIGTERM SIGINT\n\
\n\
# Track process health\necho "Starting Backend..."\n\
uv run myproject serve &\n\
backend_pid=$!\n\
\n\
# Wait briefly to check backend started\n\
sleep 2\n\
if ! kill -0 "$backend_pid" 2>/dev/null; then\n\
  echo "Backend failed to start!"\n\
  exit 1\n\
fi\n\
\n\
echo "Starting Frontend..."\n\
cd /app/myproject-frontend && npm run start -- -p 3000 &\n\
frontend_pid=$!\n\
\n\
# Wait briefly to check frontend started\n\
sleep 2\n\
if ! kill -0 "$frontend_pid" 2>/dev/null; then\n\
  echo "Frontend failed to start!"\n\
  kill -TERM "$backend_pid" 2>/dev/null\n\
  exit 1\n\
fi\n\
\n\
echo "All services started successfully"\n\
\n\
# Wait for processes to exit, but keep the script alive to catch signals\n\
wait -n\n\
\n\
# If one process dies, kill the other and exit\n\
_term' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Healthcheck - verify both processes are still running
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
  CMD ps aux | grep -q "[u]v run myproject serve" && ps aux | grep -q "[n]ext start"

# Expose ports: Backend (usually 8000) and Frontend (3000)
EXPOSE 8000
EXPOSE 3000

CMD ["/app/entrypoint.sh"]
