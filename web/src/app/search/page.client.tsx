"use client";

import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { SafeMarkdown } from "@/components/safe-markdown";
import { VehicleCard } from "@/components/vehicle-card";
import { Button } from "@/components/ui/button";
import {
  generateComparison,
  generateReport,
  searchByCriteria,
  type AssistantCriteria,
  type CompareResponse,
  type SearchResponse,
} from "@/lib/api";

const PAGE_SIZE = 24;

type StoredSearch = {
  criteria: AssistantCriteria;
  displayCriteria?: AssistantCriteria;
  results: SearchResponse;
};

export default function SearchPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resultsMode = searchParams.get("mode") === "results";
  const rawPage = Number(searchParams.get("page") || "1");
  const page =
    Number.isFinite(rawPage) && rawPage >= 1 ? Math.floor(rawPage) : 1;

  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionMissing, setSessionMissing] = useState(false);
  const [results, setResults] = useState<SearchResponse | null>(null);
  const [criteria, setCriteria] = useState<AssistantCriteria | null>(null);
  const [displayCriteria, setDisplayCriteria] = useState<AssistantCriteria | null>(null);
  const [report, setReport] = useState<string | null>(null);
  const [comparison, setComparison] = useState<CompareResponse | null>(null);
  const [compareMode, setCompareMode] = useState(false);

  useEffect(() => {
    if (!resultsMode) {
      router.replace("/");
    }
  }, [resultsMode, router]);

  useEffect(() => {
    if (!resultsMode) return;

    let cancelled = false;
    const raw = sessionStorage.getItem("carvest-search");
    if (!raw) {
      queueMicrotask(() => {
        if (!cancelled) setSessionMissing(true);
      });
      return () => {
        cancelled = true;
      };
    }

    try {
      const parsed = JSON.parse(raw) as StoredSearch;
      queueMicrotask(() => {
        if (cancelled) return;
        setSessionMissing(false);
        setCriteria(parsed.criteria);
        setDisplayCriteria(parsed.displayCriteria ?? parsed.criteria);
        if (page === 1) {
          setResults(parsed.results);
        }
      });
    } catch {
      queueMicrotask(() => {
        if (cancelled) return;
        setSessionMissing(true);
        setError("Could not load your saved search session.");
      });
    }
    return () => {
      cancelled = true;
    };
  }, [resultsMode, page]);

  useEffect(() => {
    if (!resultsMode || !criteria || page === 1) return;

    let cancelled = false;
    queueMicrotask(() => {
      if (cancelled) return;
      setPageLoading(true);
      setError(null);
    });

    searchByCriteria(criteria, { start: (page - 1) * PAGE_SIZE, rows: PAGE_SIZE })
      .then((data) => {
        if (!cancelled) setResults(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Could not load page.");
        }
      })
      .finally(() => {
        if (!cancelled) setPageLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [resultsMode, criteria, page]);

  async function loadReport(current: AssistantCriteria, useCompare: boolean) {
    if (!(current.make && current.model && current.year)) {
      setError("Buyer reports need a specific make, model, and year.");
      return;
    }

    setLoading(true);
    setError(null);
    setReport(null);
    setComparison(null);

    try {
      if (useCompare) {
        if (!current.zip_code) {
          setError("ZIP code is required for competitive comparison.");
          return;
        }
        const compareData = await generateComparison({
          make: String(current.make),
          year: String(current.year),
          model: String(current.model),
          zip_code: String(current.zip_code),
        });
        setComparison(compareData);
      } else {
        const reportData = await generateReport({
          make: String(current.make),
          year: String(current.year),
          model: String(current.model),
          zip_code: current.zip_code ? String(current.zip_code) : undefined,
        });
        setReport(reportData.report);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }

  function goToPage(nextPage: number) {
    const params = new URLSearchParams({ mode: "results", page: String(nextPage) });
    router.push(`/search?${params.toString()}`);
  }

  if (!resultsMode) {
    return null;
  }

  const titleSource = displayCriteria ?? criteria;
  const titleParts = [
    titleSource?.year,
    titleSource?.make,
    titleSource?.model || titleSource?.body_type,
  ].filter(Boolean);

  const totalFound = results?.total_found ?? 0;
  const totalPages = Math.max(1, Math.ceil(totalFound / PAGE_SIZE));
  const rangeStart = totalFound ? (page - 1) * PAGE_SIZE + 1 : 0;
  const rangeEnd = Math.min(page * PAGE_SIZE, totalFound);

  return (
    <main className="min-h-screen bg-background p-4 md:p-8">
      <div className="mb-8 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">Matched inventory</p>
          <h1 className="mt-3 text-4xl font-light text-slate-900">
            {titleParts.length ? titleParts.join(" ") : "Search results"}
          </h1>
          {totalFound ? (
            <p className="mt-2 text-sm text-slate-600">
              {totalFound.toLocaleString()} active listings
              {criteria?.zip_code ? ` near ZIP ${criteria.zip_code}` : " nationwide"}
            </p>
          ) : null}
        </div>
        <Button variant="outline" onClick={() => router.push("/")}>
          New search
        </Button>
      </div>

      {loading || pageLoading ? (
        <p className="text-slate-500">
          {pageLoading ? "Loading listings..." : "Generating intelligence..."}
        </p>
      ) : null}
      {error ? <p className="text-rose-600">{error}</p> : null}

      {sessionMissing ? (
        <div className="maskara-glass rounded-3xl p-8 text-center">
          <h2 className="text-2xl font-semibold text-slate-900">Search session expired</h2>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            This results link no longer has a saved search in this browser. Start a new
            assistant search to load fresh listings.
          </p>
          <Button className="mt-6" onClick={() => router.push("/")}>
            Start a new search
          </Button>
        </div>
      ) : null}

      {results ? (
        <section>
          {results.match_quality === "closest" && results.match_notice ? (
            <div className="mb-6 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm leading-6 text-amber-950">
              <p className="font-medium">Closest matches</p>
              <p className="mt-1 text-amber-900/90">{results.match_notice}</p>
            </div>
          ) : null}
          <div className="mb-6 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="text-2xl font-light text-slate-900">
                Showing {rangeStart.toLocaleString()}–{rangeEnd.toLocaleString()} of{" "}
                {totalFound.toLocaleString()}
              </h2>
              <p className="mt-1 text-sm text-slate-500">
                Page {page} of {totalPages.toLocaleString()}
              </p>
            </div>
            {criteria?.make && criteria?.model && criteria?.year ? (
              <Button
                variant="outline"
                onClick={() => {
                  const next = !compareMode;
                  setCompareMode(next);
                  loadReport(criteria, next);
                }}
              >
                {compareMode ? "Show Buyer Report" : "Compare Rivals"}
              </Button>
            ) : null}
          </div>

          {totalFound === 0 ? (
            <div className="maskara-glass rounded-3xl px-6 py-10 text-center">
              <p className="text-lg font-medium text-slate-800">No live listings matched</p>
              <p className="mx-auto mt-3 max-w-md text-sm leading-7 text-slate-600">
                Try a wider year range, a higher mileage limit, a nearby ZIP, or a slightly
                higher budget — then search again from the assistant.
              </p>
              <Button className="mt-6" variant="outline" onClick={() => router.push("/")}>
                Adjust search
              </Button>
            </div>
          ) : (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {results.listings.map((listing) => (
              <VehicleCard
                key={listing.listing_id ?? listing.vin ?? listing.heading}
                listing={listing}
                criteria={criteria}
              />
            ))}
          </div>
          )}

          {totalPages > 1 ? (
            <div className="mt-8 flex items-center justify-center gap-3">
              <Button
                variant="outline"
                disabled={page <= 1 || pageLoading}
                onClick={() => goToPage(page - 1)}
              >
                Previous
              </Button>
              <span className="text-sm text-slate-600">
                Page {page} / {totalPages}
              </span>
              <Button
                variant="outline"
                disabled={page >= totalPages || pageLoading}
                onClick={() => goToPage(page + 1)}
              >
                Next
              </Button>
            </div>
          ) : null}
        </section>
      ) : null}

      {report ? (
        <section className="prose-carvest maskara-glass mt-14 rounded-3xl p-8">
          <p className="mb-4 text-xs uppercase tracking-[0.25em] text-slate-500">Carvest report</p>
          <SafeMarkdown>{report}</SafeMarkdown>
        </section>
      ) : null}

      {comparison?.report ? (
        <section className="prose-carvest maskara-glass mt-14 rounded-3xl p-8">
          <p className="mb-4 text-xs uppercase tracking-[0.25em] text-slate-500">
            Competitive comparison
          </p>
          <SafeMarkdown>{comparison.report}</SafeMarkdown>
        </section>
      ) : null}
    </main>
  );
}
