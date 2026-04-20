import { formatDistanceToNow as fdn } from 'date-fns';

/**
 * Safely parses an ISO string from the backend, 
 * ensuring it is treated as UTC even if the 'Z' suffix is missing.
 */
export function parseBackendDate(dateString: string | null | undefined): Date | null {
  if (!dateString) return null;

  // If the string doesn't have a timezone indicator, append 'Z' to force UTC
  const normalizedString = (dateString.endsWith('Z') || dateString.includes('+'))
    ? dateString
    : `${dateString}Z`;

  return new Date(normalizedString);
}

/**
 * Formats a backend date string relative to now (e.g., "5 minutes ago")
 */
export function formatRelativeTime(dateString: string | null | undefined): string {
  const date = parseBackendDate(dateString);
  if (!date || isNaN(date.getTime())) return 'Never';

  return fdn(date, { addSuffix: true });
}
