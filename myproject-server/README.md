# myproject-server

FastAPI REST API for the application. Depends on `myproject-core` and `myproject-tools`.

## Key Components

- **Routers** — All REST endpoints organized by domain
- **Auth** — JWT-based authentication with access/refresh token strategy
- **Scheduler** — APScheduler integration for cron jobs
- **SSE Streaming** — ChatManager and ActiveRun for real-time agent output

## Documentation

See [docs/architecture/myproject-server/](docs/architecture/myproject-server/) for detailed architecture documentation.
