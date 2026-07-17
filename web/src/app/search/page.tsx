import type { Metadata } from "next";
import { Suspense } from "react";

import { buildMetadata } from "@/lib/seo";

import SearchPage from "./page.client";

export const metadata: Metadata = buildMetadata({
  title: "Search results",
  description: "Live vehicle listing results from your Carvest search.",
  path: "/search",
  noIndex: true,
});

export default function SearchPageWrapper() {
  return (
    <Suspense fallback={<main className="px-6 py-10 text-slate-500">Loading search...</main>}>
      <SearchPage />
    </Suspense>
  );
}
