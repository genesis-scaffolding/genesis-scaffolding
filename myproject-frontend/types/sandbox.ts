export interface SandboxFile {
  id: number;
  filename: string;
  relative_path: string;
  folder: string | null;
  mime_type: string;
  size: number;
  created_at: string;
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
