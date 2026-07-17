"use client";

import type { Components } from "react-markdown";
import ReactMarkdown from "react-markdown";

import { sanitizeExternalUrl } from "@/lib/safe-url";

const components: Components = {
  a: ({ href, children }) => {
    const safe = sanitizeExternalUrl(href);
    if (!safe) {
      return <span>{children}</span>;
    }
    return (
      <a href={safe} target="_blank" rel="noopener noreferrer">
        {children}
      </a>
    );
  },
  img: () => null,
  script: () => null,
  iframe: () => null,
};

export function SafeMarkdown({ children }: { children: string }) {
  return <ReactMarkdown components={components}>{children}</ReactMarkdown>;
}
