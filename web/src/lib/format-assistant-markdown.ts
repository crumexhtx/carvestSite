const SECTION_LABEL = /^(\s*(?:[-*]\s+)?)([A-Z][A-Za-z0-9\s/&()-]{2,40}:)/;

/**
 * Adds a blank line before section labels like "Generations:" or "Common Features:".
 */
export function spaceLabelSections(content: string): string {
  const spaced = content.replace(
    /([.!?])\s+([A-Z][A-Za-z0-9\s/&()-]{2,40}:)/g,
    "$1\n\n$2",
  );

  const lines = spaced.split("\n");
  const result: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (
      i > 0 &&
      SECTION_LABEL.test(line) &&
      lines[i - 1].trim() !== "" &&
      result[result.length - 1] !== ""
    ) {
      result.push("");
    }
    result.push(line);
  }

  return result.join("\n");
}
