"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { AlertTriangle, ExternalLink, Newspaper } from "lucide-react";

import { VehicleAiAssistant } from "@/components/vehicle-ai-assistant";
import {
  fetchHomeInsights,
  fetchInventoryScale,
  type HomeInsights,
  type InventoryScale,
} from "@/lib/api";
import { DEFAULT_RELIABILITY_RANKINGS } from "@/lib/reliability-rankings";
import { cn } from "@/lib/utils";

type HomeTab = "search" | "recalls" | "reliability";

const TABS: { id: HomeTab; label: string; href: string }[] = [
  { id: "search", label: "Search", href: "/?tab=search" },
  { id: "recalls", label: "Active Recalls", href: "/?tab=recalls" },
  { id: "reliability", label: "Reliability report", href: "/?tab=reliability" },
];

export function HomePageClient() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const promptParam = searchParams.get("prompt");
  const activeTab: HomeTab =
    tabParam === "recalls" || tabParam === "reliability" ? tabParam : "search";

  const [insights, setInsights] = useState<HomeInsights | null>(null);
  const [insightsError, setInsightsError] = useState<string | null>(null);
  const [inventory, setInventory] = useState<InventoryScale | null>(null);
  const [pendingPrompt, setPendingPrompt] = useState<string | null>(
    () => promptParam,
  );

  const clearPromptParam = useCallback(() => {
    if (!searchParams.get("prompt")) return;
    const nextParams = new URLSearchParams(searchParams.toString());
    nextParams.delete("prompt");
    const query = nextParams.toString();
    router.replace(query ? `/?${query}` : "/");
    setPendingPrompt(null);
  }, [router, searchParams]);

  useEffect(() => {
    fetchHomeInsights()
      .then(setInsights)
      .catch((err) => {
        setInsightsError(
          err instanceof Error ? err.message : "Could not load insights.",
        );
      });
    fetchInventoryScale()
      .then(setInventory)
      .catch(() => setInventory(null));
  }, []);

  useEffect(() => {
    if (promptParam) {
      setPendingPrompt(promptParam);
    }
  }, [promptParam]);

  const reliabilityRankings =
    insights?.reliability_rankings ?? DEFAULT_RELIABILITY_RANKINGS;

  return (
    <main>
      <div className="border-b border-border bg-card/90">
        <div className="mx-auto flex max-w-5xl flex-wrap gap-2 px-4 py-4">
          {TABS.map((tab) => (
            <Link
              key={tab.id}
              href={tab.href}
              className={cn(
                "maskara-tab rounded-full px-5 py-2 text-sm font-medium",
                activeTab === tab.id && "maskara-tab-active",
              )}
            >
              {tab.label}
            </Link>
          ))}
        </div>
      </div>

      {activeTab === "search" ? (
        <section className="maskara-ambient relative min-h-[88vh]">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(99,102,241,0.08),transparent_42%),linear-gradient(180deg,#f7f8fc_0%,#f4f6fa_72%)]" />
          <div className="absolute inset-x-0 top-20 mx-auto h-72 max-w-3xl rounded-full bg-violet-400/10 blur-[100px]" />
          {inventory ? (
            <div className="relative z-10 mx-auto max-w-4xl px-4 pt-8">
              <p className="rounded-full border border-border bg-card px-4 py-2 text-center text-sm text-slate-600 shadow-sm">
                Searching{" "}
                <span className="font-semibold text-slate-900">
                  {inventory.total_listings_nationwide.toLocaleString()}+
                </span>{" "}
                active dealer listings nationwide
              </p>
            </div>
          ) : null}
          <VehicleAiAssistant
            reliabilityRankings={reliabilityRankings}
            initialPrompt={pendingPrompt}
            onInitialPromptConsumed={clearPromptParam}
          />
        </section>
      ) : null}

      {activeTab === "recalls" ? (
        <section className="mx-auto max-w-4xl px-4 py-10">
          <RecallPanel insights={insights} error={insightsError} />
        </section>
      ) : null}

      {activeTab === "reliability" ? (
        <section className="mx-auto max-w-4xl px-4 py-10">
          <ReliabilityPanel insights={insights} error={insightsError} />
        </section>
      ) : null}
    </main>
  );
}

function RecallPanel({
  insights,
  error,
}: {
  insights: HomeInsights | null;
  error: string | null;
}) {
  if (error) {
    return <p className="text-center text-sm text-rose-600">{error}</p>;
  }

  if (!insights) {
    return <div className="h-64 animate-pulse rounded-2xl bg-card-subtle" />;
  }

  return (
    <section className="maskara-glass rounded-2xl p-6">
      <div className="mb-4 flex items-center gap-2">
        <AlertTriangle className="h-4 w-4 text-amber-400" />
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
          Active recall alerts
        </h2>
      </div>
      <div className="space-y-4">
        {insights.recall_snippets.map((item) => (
          <article
            key={`${item.vehicle}-${item.component}`}
            className="rounded-xl border border-border bg-card-subtle p-4"
          >
            <div className="flex flex-wrap items-center justify-between gap-2">
              <p className="font-medium text-slate-900">{item.vehicle}</p>
              {item.recall_count > 0 ? (
                <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700">
                  {item.recall_count} active
                </span>
              ) : null}
            </div>
            <p className="mt-1 text-xs font-medium uppercase tracking-wide text-violet-600">
              {item.component}
            </p>
            <p className="mt-2 text-sm leading-6 text-slate-600">{item.summary}</p>
          </article>
        ))}
      </div>
      <p className="mt-4 text-xs text-slate-400">Source: NHTSA live recall database</p>
    </section>
  );
}

function ReliabilityPanel({
  insights,
  error,
}: {
  insights: HomeInsights | null;
  error: string | null;
}) {
  const reports = insights
    ? (insights.reliability_reports ?? [insights.reliability_article])
    : [];

  return (
    <div className="space-y-6">
      {error ? (
        <p className="text-center text-sm text-rose-600">{error}</p>
      ) : null}

      {insights ? (
        <section className="maskara-glass rounded-2xl p-6">
          <div className="mb-4 flex items-center gap-2">
            <Newspaper className="h-4 w-4 text-sky-400" />
            <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
              Reliability reports
            </h2>
          </div>
          <div className="grid gap-4 md:grid-cols-3">
            {reports.map((report) => (
              <a
                key={report.url}
                href={report.url}
                target="_blank"
                rel="noreferrer"
                className="group flex min-h-64 flex-col rounded-xl border border-border bg-gradient-to-br from-card to-card-subtle p-5 transition hover:-translate-y-0.5 hover:border-violet-300 hover:shadow-[var(--shadow-card)]"
              >
                <p className="text-xs font-medium uppercase tracking-wide text-violet-600">
                  {report.source}
                </p>
                <h3 className="mt-2 text-lg font-semibold leading-snug text-slate-900 group-hover:text-violet-700">
                  {report.title}
                </h3>
                <p className="mt-3 text-sm leading-6 text-slate-600">
                  {report.summary}
                </p>
                <span className="mt-auto inline-flex items-center gap-1.5 pt-5 text-sm font-medium text-violet-600">
                  Read report
                  <ExternalLink className="h-4 w-4" />
                </span>
              </a>
            ))}
          </div>
        </section>
      ) : null}

    </div>
  );
}
