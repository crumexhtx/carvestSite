import type { MetadataRoute } from "next";

import { absoluteUrl } from "@/lib/seo";
import { fetchSeoHubs } from "@/lib/seo-api";

const STATIC_ROUTES: Array<{
  path: string;
  changeFrequency: MetadataRoute.Sitemap[number]["changeFrequency"];
  priority: number;
}> = [
  { path: "/", changeFrequency: "daily", priority: 1 },
  { path: "/cars", changeFrequency: "weekly", priority: 0.9 },
  { path: "/listing-deal", changeFrequency: "weekly", priority: 0.85 },
  { path: "/offer-sheet", changeFrequency: "weekly", priority: 0.85 },
  { path: "/report", changeFrequency: "weekly", priority: 0.7 },
  { path: "/feedback", changeFrequency: "monthly", priority: 0.4 },
  { path: "/privacy", changeFrequency: "yearly", priority: 0.2 },
  { path: "/terms", changeFrequency: "yearly", priority: 0.2 },
];

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const now = new Date();
  const staticEntries: MetadataRoute.Sitemap = STATIC_ROUTES.map((route) => ({
    url: absoluteUrl(route.path),
    lastModified: now,
    changeFrequency: route.changeFrequency,
    priority: route.priority,
  }));

  const hubs = await fetchSeoHubs();
  const hubEntries: MetadataRoute.Sitemap = hubs.map((hub) => ({
    url: absoluteUrl(hub.path),
    lastModified: now,
    changeFrequency: "weekly",
    priority: 0.8,
  }));

  return [...staticEntries, ...hubEntries];
}
