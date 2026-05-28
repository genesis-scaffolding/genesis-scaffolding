---
name: "file_skill"
description: "Use this skill when user asks to read, write, edit, list, search, delete, or move files in the working directory or sandbox."
version: "1.0"
---

# File Skill

You are operating inside a working directory, also known as a `sandbox`. You can list, read, write, and edit files in this sandbox.

You need to use relative paths to refer to files and directories inside the sandbox. You are located at the root of the sandbox.

## How to write files

Use the write file tool when you need to create a new file in the working directory.

1. Figure out the content you need to write.
2. Figure out a name and path for the file you need to write.
3. Call the file write tool with the correct parameters.
4. Inspect the tool response and clipboard.
5. If the tool response shows that the write operation failed, figure out the reason and retry.
6. If the tool response shows that the write operation succeeded, verify the content of the file in the clipboard and conclude the file write task.

## How to edit files

Use the edit file tool when you need to replace or add content to an existing file.

1. Figure out the new content you want to add or replace.
2. Figure out the file you need to edit.
3. If the file content is not in the clipboard, use the read file tool to add the file content to the clipboard.
4. Figure out the block of text in the existing file that you want to replace. If you need to add text to an existing empty file, use the file header as the text block to replace. If you need to add text to the end of a paragraph, use the last sentence of the paragraph as the text block.
5. Call the file edit tool.
6. If the tool response shows that the edit operation failed, figure out the reason and retry.
7. If the tool response shows that the edit operation was successful, conclude the editing task.

## How to search file content

Use `search_file_content` to find text within files. This is useful when you know what you are looking for but not which file contains it.

## How to list and find files

Use `list_files` to see the directory structure. Use `find_files` to locate specific files by name pattern.