import Link from "next/link";

import { features } from "@/lib/features";

export function SiteHeader() {
  return (
    <header className="sticky top-0 z-50 border-b border-border bg-card/90 backdrop-blur-xl">
      <div className="mx-auto flex h-16 max-w-5xl items-center justify-between gap-4 px-6">
        <Link href="/" className="text-lg font-semibold tracking-[0.2em] text-slate-900">
          CARVEST
        </Link>
        <nav className="flex items-center gap-1 sm:gap-2">
          <Link
            href="/listing-deal"
            className="rounded-full px-2.5 py-2 text-xs font-medium text-slate-600 transition hover:bg-card-subtle hover:text-violet-700 sm:px-3 sm:text-sm"
          >
            Listing deal
          </Link>
          <Link
            href="/offer-sheet"
            className="rounded-full px-2.5 py-2 text-xs font-medium text-slate-600 transition hover:bg-card-subtle hover:text-violet-700 sm:px-3 sm:text-sm"
          >
            Offer analyzer
          </Link>
          {features.monetizationEnabled ? (
            <Link
              href="/report"
              className="rounded-full border border-violet-200 bg-violet-50 px-2.5 py-2 text-xs font-medium text-violet-700 transition hover:border-violet-300 hover:bg-violet-100 sm:px-3 sm:text-sm"
            >
              VIN report
            </Link>
          ) : (
            <Link
              href="/report"
              className="rounded-full border border-border bg-card px-2.5 py-2 text-xs font-medium text-slate-600 transition hover:border-violet-300 hover:bg-violet-50 hover:text-violet-700 sm:px-3 sm:text-sm"
            >
              Coming soon
            </Link>
          )}
        </nav>
      </div>
    </header>
  );
}
