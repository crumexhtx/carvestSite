import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";

import { absoluteUrl, buildMetadata } from "@/lib/seo";
import { fetchModelBrief } from "@/lib/seo-api";

type RouteParams = {
  make: string;
  model: string;
  year: string;
};

type PageProps = {
  params: Promise<RouteParams>;
};

export async function generateMetadata({
  params,
}: PageProps): Promise<Metadata> {
  const route = await params;
  const brief = await fetchModelBrief(route.make, route.model, route.year);
  if (!brief) {
    return buildMetadata({
      title: "Vehicle research",
      description: "Carvest vehicle research hub.",
      path: `/cars/${route.make}/${route.model}/${route.year}`,
      noIndex: true,
    });
  }

  return buildMetadata({
    title: `${brief.title} research`,
    description: brief.description,
    path: brief.path,
  });
}

export default async function CarHubPage({ params }: PageProps) {
  const route = await params;
  const brief = await fetchModelBrief(route.make, route.model, route.year);
  if (!brief) notFound();

  const assistantHref = `/?prompt=${encodeURIComponent(brief.research_prompt)}`;
  const dealHref = "/listing-deal";
  const reportHref = "/report";
  const jsonLd = {
    "@context": "https://schema.org",
    "@type": "Vehicle",
    name: brief.title,
    brand: {
      "@type": "Brand",
      name: brief.make,
    },
    model: brief.model,
    vehicleModelDate: String(brief.year),
    url: absoluteUrl(brief.path),
    description: brief.description,
  };

  const recallCount = brief.recalls.total_recalls_count;
  const recallsAvailable = brief.recalls.available;

  return (
    <main className="maskara-ambient relative min-h-[calc(100vh-4rem)] overflow-hidden">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(jsonLd) }}
      />
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(99,102,241,0.1),transparent_42%)]" />
      <div className="relative mx-auto max-w-3xl px-4 py-12 md:py-16">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-600">
          <Link href="/cars" className="hover:underline">
            Research hubs
          </Link>
          <span className="mx-2 text-slate-300">/</span>
          Carvest
        </p>
        <h1 className="mt-3 text-3xl font-semibold tracking-tight text-slate-900 md:text-4xl">
          {brief.title}
        </h1>
        <p className="mt-3 max-w-2xl text-base leading-relaxed text-slate-600">
          {brief.description}
        </p>

        {brief.reliability_note ? (
          <section className="mt-8 rounded-2xl border border-emerald-200 bg-emerald-50/70 px-5 py-4">
            <h2 className="text-sm font-semibold uppercase tracking-wide text-emerald-800">
              Reliability context
            </h2>
            <p className="mt-2 text-sm leading-relaxed text-emerald-950">
              {brief.reliability_note}
            </p>
          </section>
        ) : null}

        <section className="mt-8 rounded-2xl border border-border bg-card/80 px-5 py-5">
          <h2 className="text-lg font-semibold text-slate-900">
            NHTSA recalls
          </h2>
          {!recallsAvailable ? (
            <p className="mt-2 text-sm text-slate-600">
              Live recall data is temporarily unavailable for this vehicle.
              Check again shortly, or research with the assistant for the latest
              campaigns.
            </p>
          ) : recallCount === 0 ? (
            <p className="mt-2 text-sm text-slate-600">
              No open NHTSA recall campaigns were returned for this exact
              make/model/year.
            </p>
          ) : (
            <>
              <p className="mt-2 text-sm text-slate-600">
                {recallCount} recall campaign{recallCount === 1 ? "" : "s"} on
                record for this vehicle.
              </p>
              <ul className="mt-4 space-y-3">
                {brief.recalls.items.map((item, index) => (
                  <li
                    key={`${item.component}-${index}`}
                    className="rounded-xl border border-border bg-background/70 px-4 py-3"
                  >
                    <p className="text-sm font-semibold text-slate-900">
                      {item.component}
                    </p>
                    {item.summary ? (
                      <p className="mt-1 text-sm leading-relaxed text-slate-600">
                        {item.summary}
                      </p>
                    ) : null}
                  </li>
                ))}
              </ul>
            </>
          )}
        </section>

        <section className="mt-8">
          <h2 className="text-lg font-semibold text-slate-900">Next steps</h2>
          <p className="mt-2 text-sm text-slate-600">
            Move from research into a specific listing check or full VIN report
            when you are ready.
          </p>
          <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
            <Link
              href={assistantHref}
              className="inline-flex items-center justify-center rounded-full bg-violet-700 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-violet-800"
            >
              Research with AI
            </Link>
            <Link
              href={dealHref}
              className="inline-flex items-center justify-center rounded-full border border-violet-200 bg-violet-50 px-5 py-2.5 text-sm font-medium text-violet-700 transition hover:border-violet-300 hover:bg-violet-100"
            >
              Check a listing deal
            </Link>
            <Link
              href={reportHref}
              className="inline-flex items-center justify-center rounded-full border border-border bg-card px-5 py-2.5 text-sm font-medium text-slate-700 transition hover:border-violet-300 hover:bg-violet-50 hover:text-violet-700"
            >
              VIN report
            </Link>
          </div>
        </section>
      </div>
    </main>
  );
}
