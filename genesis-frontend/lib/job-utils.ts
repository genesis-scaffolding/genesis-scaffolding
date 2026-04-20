/**
 * Heuristic to determine if a result string is actually a PosixPath 
 * or a list of paths that we should hide from the text display.
 */
export function isPathResult(value: string): boolean {
  if (typeof value !== 'string') return false;
  return value.includes('PosixPath(') || value.includes('[PosixPath(');
}

/**
 * Strips Python list brackets and quotes, and fixes escaped newlines.
 * e.g. "['Hello\\nWorld']" -> "Hello\nWorld"
 */
export function cleanPythonResult(value: string): string {
  if (typeof value !== 'string') return value;

  return value
    .replace(/^\[['"]/, '')    // Remove leading [' or ["
    .replace(/['"]\]$/, '')    // Remove trailing '] or "]
    .replace(/\\n/g, '\n')     // Fix escaped newlines
    .replace(/\\'/g, "'")      // Fix escaped single quotes
    .trim();
}
