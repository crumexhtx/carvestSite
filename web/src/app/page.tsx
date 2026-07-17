import type { Metadata } from "next";
import { Suspense } from "react";

import { HomePageClient } from "@/components/home-page-client";
import {
  buildMetadata,
  defaultSiteDescription,
  defaultSiteTitle,
} from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: defaultSiteTitle,
  description: defaultSiteDescription,
  path: "/",
});

export default function HomePage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-background p-8" />}>
      <HomePageClient />
    </Suspense>
  );
}
