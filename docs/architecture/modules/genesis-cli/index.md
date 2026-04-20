# CLI Architecture

## Overview

The CLI is a Typer-based command-line interface designed for single-user mode. It bypasses the FastAPI server entirely, allowing direct interaction with the agent and productivity system without authentication or multi-user concerns.

## How It Works

CLI commands are decorated with Typer's `@app.command()`. Each command is a function that constructs and runs the core components — `Agent`, `WorkflowEngine`, and similar — directly via Python imports.

## Single-User Mode

In single-user mode:

- No JWT authentication is required
- Multi-user database features are bypassed
- Configuration is read from environment variables or a local YAML file

## Available Commands

- **Agent chat**: Interactive shell for conversing with the agent
- **Workflow submission**: Submit a workflow for execution
- **Productivity CRUD**: Create, read, update, and delete tasks, projects, and journal entries

## Related Modules

- `genesis_cli/` — CLI package root
- `genesis_cli/main.py` — Typer app and command definitions
