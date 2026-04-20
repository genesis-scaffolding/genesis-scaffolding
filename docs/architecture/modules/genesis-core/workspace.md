# Workspace

## Overview

The workspace is the filesystem location where user-facing agent operations take place — file reads, writes, and script executions. Its assignment is determined by deployment mode, and the isolation is enforced through configuration rather than operating system mechanisms.

## Single-User Mode

In single-user mode, the process working directory is used directly. All file operations occur within the same directory tree the server process was started in. There is no redirection of paths and no isolation layer.

## Multi-User Mode

In multi-user mode, each user is assigned a sandboxed working directory:

```
{users_directory}/{user_id}/working/
```

This path is set through the deep-merge of `path.internal_state_dir` and `path.working_directory` in the user-level config layer. The result is that each user's agent operates in a completely isolated filesystem view, preventing accidental cross-user data leakage.

The isolation is not enforced by the operating system but by the config layer ensuring that no user-level configuration ever points back to a shared or another user's directory.

## Job Directory (Workflows)

When workflows execute, each job gets its own isolated workspace within the user's working directory:

```
{working_directory}/jobs/{job_id}/
├── input/      ← user-provided files
├── internal/   ← intermediate artifacts between steps
└── output/     ← final workflow artifacts
```

## Related Modules

- `genesis_core.config` — Working directory path resolution via config layers
- `genesis_core.workflow.workflow_workspace` — Workspace path management and sandboxing utilities
