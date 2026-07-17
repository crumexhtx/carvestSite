"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { CheckCircle2, Loader2, ShieldAlert } from "lucide-react";
import { SafeMarkdown } from "@/components/safe-markdown";
import { DealBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { fetchBuyerReport, type BuyerReportResponse } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

export function BuyerReportView({
  reportId,
  initialToken,
}: {
  reportId: string;
  initialToken: string;
}) {
  const [report, setReport] = useState<BuyerReportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const hashToken = window.location.hash.startsWith("#token=")
      ? decodeURIComponent(window.location.hash.slice("#token=".length))
      : "";
    const token =
      initialToken ||
      hashToken ||
      sessionStorage.getItem(`carvest-report-${reportId}`) ||
      "";
    if (!token) {
      queueMicrotask(() => {
        if (!cancelled) {
          setError("This report link is missing its access token.");
        }
      });
      return () => {
        cancelled = true;
      };
    }
    sessionStorage.setItem(`carvest-report-${reportId}`, token);
    // Drop token from the visible URL after persisting it for this tab session.
    if (initialToken || hashToken) {
      const url = new URL(window.location.href);
      url.searchParams.delete("token");
      url.hash = "";
      window.history.replaceState({}, "", `${url.pathname}${url.search}`);
    }

    let timer: ReturnType<typeof setTimeout> | undefined;
    let attempts = 0;
    let transientErrors = 0;
    const maxAttempts = 40;

    async function load() {
      try {
        const result = await fetchBuyerReport(reportId, token);
        if (cancelled) return;
        setReport(result);
        setError(null);
        transientErrors = 0;
        attempts += 1;
        const stillBuilding = ["pending_payment", "paid", "generating"].includes(
          result.status,
        );
        if (stillBuilding && attempts < maxAttempts) {
          timer = setTimeout(load, 3000);
        } else if (stillBuilding) {
          setError(
            "This report is taking longer than expected. Refresh this page in a minute, or contact support if it stays stuck.",
          );
        }
      } catch (err) {
        if (cancelled) return;
        transientErrors += 1;
        // Keep polling through brief network blips while the report is generating.
        if (transientErrors <= 3 && attempts < maxAttempts) {
          timer = setTimeout(load, 3000);
          return;
        }
        setError(err instanceof Error ? err.message : "Could not load this report.");
      }
    }

    void load();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [initialToken, reportId]);

  if (error) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-16">
        <div className="maskara-glass rounded-3xl p-8 text-center">
          <ShieldAlert className="mx-auto h-9 w-9 text-rose-500" />
          <h1 className="mt-4 text-2xl font-semibold text-slate-900">
            Report unavailable
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">{error}</p>
          <Button asChild className="mt-6">
            <Link href="/report">Start a new report</Link>
          </Button>
        </div>
      </main>
    );
  }

  if (!report || ["pending_payment", "paid", "generating"].includes(report.status)) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-16">
        <div className="maskara-glass rounded-3xl p-8 text-center">
          <Loader2 className="mx-auto h-9 w-9 animate-spin text-violet-600" />
          <h1 className="mt-4 text-2xl font-semibold text-slate-900">
            Building your buyer report
          </h1>
          <p className="mt-3 text-sm leading-6 text-slate-600">
            Carvest is checking market pricing, recalls, reliability, and negotiation
            leverage. This page updates automatically.
          </p>
        </div>
      </main>
    );
  }

  if (report.status === "failed" || !report.full_report) {
    return (
      <main className="mx-auto max-w-3xl px-4 py-16">
        <div className="maskara-glass rounded-3xl p-8 text-center">
          <ShieldAlert className="mx-auto h-9 w-9 text-amber-600" />
          <h1 className="mt-4 text-2xl font-semibold text-slate-900">
            We could not finish this report
          </h1>
          <p className="mt-3 text-sm text-slate-600">
            {report.full_report?.error ??
              "The report service encountered an error. Please contact support."}
          </p>
        </div>
      </main>
    );
  }

  const full = report.full_report;
  const vehicle = full.vehicle;
  const negotiation = full.negotiation_pack;

  return (
    <main className="mx-auto max-w-5xl px-4 py-10 md:py-14">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="inline-flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-emerald-700">
            <CheckCircle2 className="h-4 w-4" />
            Complete buyer report
          </div>
          <h1 className="mt-3 text-4xl font-light text-slate-900">
            {vehicle.year} {vehicle.make} {vehicle.model}
          </h1>
          <p className="mt-2 font-mono text-xs tracking-wider text-slate-500">
            VIN {vehicle.vin}
          </p>
        </div>
        <Button variant="outline" asChild>
          <Link href="/report">Check another vehicle</Link>
        </Button>
      </div>

      {full.price_analysis ? (
        <section className="mt-8 grid gap-4 sm:grid-cols-3">
          <Metric
            label="Asking price"
            value={formatCurrency(full.price_analysis.listing_price)}
          />
          <Metric
            label="Predicted fair price"
            value={formatCurrency(full.price_analysis.predicted_fair_price)}
          />
          <div className="maskara-glass rounded-2xl p-5">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">
              Market signal
            </p>
            <div className="mt-3">
              <DealBadge signal={full.price_analysis.deal_signal ?? undefined} />
            </div>
          </div>
        </section>
      ) : null}

      <section className="prose-carvest maskara-glass mt-8 rounded-3xl p-6 md:p-8">
        <p className="mb-5 text-xs font-semibold uppercase tracking-[0.2em] text-violet-600">
          Risk and market analysis
        </p>
        <SafeMarkdown>{full.markdown_report}</SafeMarkdown>
      </section>

      {full.inspection_checklist?.length ? (
        <section className="maskara-glass mt-8 rounded-3xl p-6 md:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-600">
            Pre-purchase inspection checklist
          </p>
          <ul className="mt-5 grid gap-3 md:grid-cols-2">
            {full.inspection_checklist.map((item) => (
              <li key={item} className="flex gap-3 text-sm leading-6 text-slate-600">
                <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-emerald-600" />
                {item}
              </li>
            ))}
          </ul>
        </section>
      ) : null}

      {negotiation ? (
        <section className="maskara-glass mt-8 rounded-3xl p-6 md:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-600">
            Negotiation plan
          </p>
          <p className="mt-3 text-sm leading-7 text-slate-600">
            {negotiation.summary}
          </p>
          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <Metric label="Opening offer" value={formatCurrency(negotiation.opening_offer)} />
            <Metric label="Target price" value={formatCurrency(negotiation.target_price)} />
            <Metric label="Walk-away" value={formatCurrency(negotiation.walk_away_price)} />
          </div>
          <div className="mt-6 grid gap-5 lg:grid-cols-2">
            <Script title="Email to dealer" value={negotiation.email_script} />
            <Script title="Text message" value={negotiation.text_script} />
          </div>
        </section>
      ) : null}

      <p className="mx-auto mt-8 max-w-3xl text-center text-xs leading-5 text-slate-400">
        Carvest provides research, not mechanical, legal, or financial advice.
        Confirm recalls, vehicle condition, and pricing with qualified professionals.
      </p>
    </main>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="maskara-glass rounded-2xl p-5">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function Script({ title, value }: { title: string; value: string }) {
  return (
    <div className="rounded-2xl border border-border bg-card-subtle p-5">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
        {title}
      </p>
      <p className="mt-3 whitespace-pre-wrap text-sm leading-6 text-slate-700">
        {value}
      </p>
    </div>
  );
}
