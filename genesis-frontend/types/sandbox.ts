export interface SandboxFile {
  relative_path: string;
  name: string;
  is_dir: boolean;
  size: number | null;
  mime_type: string | null;
  mtime: number | null;
  created_at: string | null;
}

// filter the display and uploads
export const ALLOWED_EXTENSIONS = ['.pdf', '.txt', '.md'];
export const ALLOWED_MIME_TYPES = ['application/pdf', 'text/plain', 'text/markdown'];

// text file extensions for content preview
export const TEXT_EXTENSIONS = new Set([
  ".md", ".txt", ".json", ".yaml", ".yml", ".csv", ".xml", ".html", ".css",
  ".js", ".ts", ".tsx", ".jsx", ".py", ".rb", ".go", ".java", ".c", ".cpp",
  ".h", ".sh", ".bash", ".zsh"
]);

// --- File ID encoding utilities ---

function base64UrlEncode(str: string): string {
  const encoded = btoa(str);
  return encoded.replace(/\+/g, '-').replace(/\//g, '_').replace(/=/g, '');
}

function base64UrlDecode(str: string): string {
  const remainder = str.length % 4;
  const padded = str + '='.repeat(remainder === 0 ? 0 : 4 - remainder);
  return atob(padded.replace(/-/g, '+').replace(/_/g, '/'));
}

export function encodeFileId(relativePath: string): string {
  return base64UrlEncode(relativePath);
}

export function decodeFileId(encoded: string): string {
  return base64UrlDecode(encoded);
}
