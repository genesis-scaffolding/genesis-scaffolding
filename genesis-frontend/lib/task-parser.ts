import * as chrono from 'chrono-node';
import { addDays, format } from "date-fns";

export interface ParsedTask {
  title: string;
  projectId?: number;
  assignedDate?: string;     // YYYY-MM-DD
  hardDeadline?: string;     // ISO String
  scheduledStart?: string;   // ISO String
}

export function parseTaskInput(text: string, projects: any[]): ParsedTask {
  let title = text;
  let projectId: number | undefined;
  let assignedDate: string | undefined;
  let hardDeadline: string | undefined;
  let scheduledStart: string | undefined;

  // Parse Project by matching against the ACTUAL project list
  // Sort projects by name length (longest first) so we don't match 
  // "#Deploy" if the user typed "#Deployment and CI/CD"
  const sortedProjects = [...projects].sort((a, b) => b.name.length - a.name.length);

  for (const project of sortedProjects) {
    const projectTag = `#${project.name}`;
    // We use case-insensitive matching
    if (title.toLowerCase().includes(projectTag.toLowerCase())) {
      projectId = project.id;

      // Remove the exact project tag from the title
      const escapedName = projectTag.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(escapedName, 'gi');
      title = title.replace(regex, "");
      break; // Stop after the first (longest) match
    }
  }

  // Chrono parse date
  const results = chrono.parse(title);

  results.forEach((result) => {
    const dateValue = result.start.date();
    const dateTimeStr = dateValue.toISOString();
    const dateOnlyStr = format(dateValue, "yyyy-MM-dd");

    // Check the text immediately preceding the date to determine intent
    const textBefore = title.substring(0, result.index).trim().toLowerCase();

    if (textBefore.endsWith("due") || textBefore.endsWith("by") || textBefore.endsWith("deadline")) {
      hardDeadline = dateTimeStr;
      // Also remove the prefix word (due/by/deadline)
      const prefixMatch = title.substring(0, result.index).match(/(due|by|deadline)\s*$/i);
      if (prefixMatch) {
        title = title.replace(prefixMatch[0] + result.text, "");
      }
    }
    else if (textBefore.endsWith("at") || textBefore.endsWith("@")) {
      scheduledStart = dateTimeStr;
      const prefixMatch = title.substring(0, result.index).match(/(at|@)\s*$/i);
      if (prefixMatch) {
        title = title.replace(prefixMatch[0] + result.text, "");
      }
    }
    else {
      // General date (assigned/planning date)
      assignedDate = dateOnlyStr;
      title = title.replace(result.text, "");
    }
  });

  title = title.replace(/\s+/g, " ").trim();

  return {
    title: title || "Untitled Task",
    projectId,
    assignedDate,
    hardDeadline,
    scheduledStart
  };
}
