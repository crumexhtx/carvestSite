import type { Metadata } from "next";

const DEFAULT_SITE_URL = "http://localhost:3000";
const DEFAULT_TITLE = "Carvest | Investigate before you invest";
const DEFAULT_DESCRIPTION =
  "Premium car research with live listings, recall intelligence, fair-price signals, and competitive comparisons.";

export function getSiteUrl(): string {
  const configured =
    process.env.NEXT_PUBLIC_SITE_URL?.trim() ||
    process.env.SITE_URL?.trim() ||
    process.env.VERCEL_PROJECT_PRODUCTION_URL?.trim();

  if (!configured) return DEFAULT_SITE_URL;

  if (configured.startsWith("http://") || configured.startsWith("https://")) {
    return configured.replace(/\/$/, "");
  }
  return `https://${configured.replace(/\/$/, "")}`;
}

export function absoluteUrl(path = "/"): string {
  const base = getSiteUrl();
  if (!path || path === "/") return base;
  return `${base}${path.startsWith("/") ? path : `/${path}`}`;
}

type BuildMetadataOptions = {
  title: string;
  description: string;
  path?: string;
  noIndex?: boolean;
  ogType?: "website" | "article";
  /** When true, skip the root layout "%s | Carvest" template. */
  absoluteTitle?: boolean;
};

export function buildMetadata({
  title,
  description,
  path = "/",
  noIndex = false,
  ogType = "website",
  absoluteTitle = false,
}: BuildMetadataOptions): Metadata {
  const url = absoluteUrl(path);
  const useAbsolute = absoluteTitle || title === DEFAULT_TITLE;
  const resolvedTitle = useAbsolute
    ? ({ absolute: title } as const)
    : title;

  return {
    title: resolvedTitle,
    description,
    alternates: {
      canonical: url,
    },
    openGraph: {
      type: ogType,
      url,
      siteName: "Carvest",
      title: useAbsolute ? title : `${title} | Carvest`,
      description,
    },
    twitter: {
      card: "summary_large_image",
      title: useAbsolute ? title : `${title} | Carvest`,
      description,
    },
    robots: noIndex
      ? {
          index: false,
          follow: false,
          googleBot: {
            index: false,
            follow: false,
          },
        }
      : {
          index: true,
          follow: true,
        },
  };
}

export const defaultSiteDescription = DEFAULT_DESCRIPTION;
export const defaultSiteTitle = DEFAULT_TITLE;
