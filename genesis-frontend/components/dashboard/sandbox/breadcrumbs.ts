import { BreadcrumbItem } from "./breadcrumb";

/**
 * Build breadcrumb items from a sandbox file's relative path.
 * @param baseHref - The base URL for the sandbox, e.g., "/dashboard/files"
 * @param relativePath - The file or folder path, e.g., "folder1/folder2/file.md"
 * @returns Array of breadcrumb items
 */
export function buildSandboxBreadcrumbs(
  baseHref: string,
  relativePath: string
): BreadcrumbItem[] {
  if (!relativePath) {
    return [{ label: "files", href: baseHref }];
  }

  const items: BreadcrumbItem[] = [{ label: "files", href: baseHref }];

  const parts = relativePath.split("/");
  let accumulated = "";

  for (let i = 0; i < parts.length; i++) {
    const part = parts[i];
    accumulated = accumulated ? `${accumulated}/${part}` : part;
    const isLast = i === parts.length - 1;

    items.push({
      label: part,
      href: isLast ? undefined : `${baseHref}?folder=${accumulated}`,
    });
  }

  return items;
}
