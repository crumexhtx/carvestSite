/**
 * Allow only http(s) external URLs and app-relative paths.
 */
export function sanitizeExternalUrl(value: string | null | undefined): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed) return null;

  try {
    const parsed = new URL(trimmed);
    if (parsed.protocol === "http:" || parsed.protocol === "https:") {
      return parsed.toString();
    }
  } catch {
    return null;
  }
  return null;
}

export function sanitizeInternalHref(value: string | null | undefined): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (!trimmed.startsWith("/")) return null;
  if (trimmed.startsWith("//")) return null;
  if (trimmed.includes("\\") || trimmed.includes("\n") || trimmed.includes("\r")) {
    return null;
  }
  return trimmed;
}

export function sanitizeHref(value: string | null | undefined): string | null {
  if (!value) return null;
  const trimmed = value.trim();
  if (trimmed.startsWith("/")) {
    return sanitizeInternalHref(trimmed);
  }
  return sanitizeExternalUrl(trimmed);
}
