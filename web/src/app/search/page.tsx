import { Suspense } from "react";

import SearchPage from "./page.client";

export default function SearchPageWrapper() {
  return (
    <Suspense fallback={<main className="px-6 py-10 text-slate-500">Loading search...</main>}>
      <SearchPage />
    </Suspense>
  );
}
