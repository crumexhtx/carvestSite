import type { Metadata } from "next";
import Link from "next/link";

import { buildMetadata } from "@/lib/seo";
import { fetchSeoHubs } from "@/lib/seo-api";

export const metadata: Metadata = buildMetadata({
  title: "Car research hubs",
  description:
    "Browse curated make and model research pages with live NHTSA recall context and next steps before you buy.",
  path: "/cars",
});

export default async function CarsIndexPage() {
  const hubs = await fetchSeoHubs();

  return (
    <main className="maskara-ambient relative min-h-[calc(100vh-4rem)] overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(99,102,241,0.1),transparent_42%)]" />
      <div className="relative mx-auto max-w-3xl px-4 py-12 md:py-16">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-600">
          Carvest
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900 md:text-4xl">
          Car research hubs
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-slate-600">
          Start with popular models — each page includes live recall context and
          clear next steps into Carvest tools.
        </p>

        {hubs.length === 0 ? (
          <p className="mt-10 rounded-2xl border border-border bg-card/80 p-5 text-sm text-slate-600">
            Research hubs are temporarily unavailable. Try the{" "}
            <Link className="font-medium text-violet-700 underline" href="/">
              AI research assistant
            </Link>{" "}
            or{" "}
            <Link
              className="font-medium text-violet-700 underline"
              href="/listing-deal"
            >
              listing deal checker
            </Link>
            .
          </p>
        ) : (
          <ul className="mt-10 space-y-3">
            {hubs.map((hub) => (
              <li key={hub.path}>
                <Link
                  href={hub.path}
                  className="block rounded-2xl border border-border bg-card/80 px-5 py-4 transition hover:border-violet-300 hover:bg-violet-50/60"
                >
                  <div className="flex flex-wrap items-baseline justify-between gap-2">
                    <h2 className="text-lg font-semibold text-slate-900">
                      {hub.title}
                    </h2>
                    <span className="text-xs font-medium uppercase tracking-wide text-violet-700">
                      {hub.reason === "reliability"
                        ? "Reliability pick"
                        : "Recall watch"}
                    </span>
                  </div>
                  {hub.note ? (
                    <p className="mt-1 text-sm leading-relaxed text-slate-600">
                      {hub.note}
                    </p>
                  ) : null}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
