# genesis-server

FastAPI REST API for the application. Depends on `genesis-core` and `genesis-tools`.

## Key Components

- **Routers** — All REST endpoints organized by domain
- **Auth** — JWT-based authentication with access/refresh token strategy
- **Scheduler** — APScheduler integration for cron jobs
- **SSE Streaming** — ChatManager and ActiveRun for real-time agent output

## Documentation

See [docs/architecture/genesis-server/](docs/architecture/genesis-server/) for detailed architecture documentation.
