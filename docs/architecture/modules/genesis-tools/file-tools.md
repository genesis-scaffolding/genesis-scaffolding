# File Tools

## Overview

File tools provide sandboxed filesystem access to the agent. All paths are resolved relative to the user's sandbox working directory, preventing access to files outside the user's isolated directory tree.

## Available Tools

| Tool | Description |
|---|---|
| `read_file` | Read the contents of a file |
| `write_file` | Write content to a file (creates or overwrites) |
| `edit_file` | Replace a specific string within a file (exact-match, first occurrence) |
| `delete_file` | Delete a file |
| `move_file` | Move or rename a file |
| `search_files` | Grep-like content search across files |
| `list_directory` | List contents of a directory |

## Sandbox Enforcement

Every file tool calls `_validate_path()` before performing any filesystem operation. This checks that the resolved path stays within the sandbox root. Path traversal attacks (`../etc/passwd`) are blocked by checking the resolved path stays within the sandbox root.

## Path Resolution

All paths are resolved relative to the user's working directory:
- `{working_directory}/` — user's sandbox root
- `{working_directory}/jobs/{job_id}/input/` — workflow job input files
- `{working_directory}/jobs/{job_id}/output/` — workflow job output files
- `{working_directory}/jobs/{job_id}/internal/` — intermediate workflow artifacts

## Related Modules

- `genesis_core.tools.file_tools` — File tool implementations
