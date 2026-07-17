"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import {
  ArrowRight,
  Calculator,
  CarFront,
  CheckCircle2,
  Loader2,
} from "lucide-react";

import { DealBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  evaluateListingDeal,
  type ListingDealEvaluation,
} from "@/lib/api";
import { cn, formatCurrency, formatNumber } from "@/lib/utils";

const CREDIT_OPTIONS = [
  { value: "excellent", label: "Excellent (720+)" },
  { value: "good", label: "Good (680–719)" },
  { value: "fair", label: "Fair (620–679)" },
  { value: "poor", label: "Building credit (<620)" },
];

const TERM_OPTIONS = [36, 48, 60, 72];

const AGE_OPTIONS = [
  { value: "18-24", label: "18–24" },
  { value: "25-34", label: "25–34" },
  { value: "35-54", label: "35–54" },
  { value: "55+", label: "55+" },
];

type Props = {
  defaultVin?: string;
  defaultPrice?: string;
  defaultMiles?: string;
  defaultZip?: string;
  defaultUrl?: string;
};

export function ListingDealClient({
  defaultVin = "",
  defaultPrice = "",
  defaultMiles = "",
  defaultZip = "",
  defaultUrl = "",
}: Props) {
  const [vin, setVin] = useState(defaultVin);
  const [listingPrice, setListingPrice] = useState(defaultPrice);
  const [mileage, setMileage] = useState(defaultMiles);
  const [zipCode, setZipCode] = useState(defaultZip);
  const [listingUrl, setListingUrl] = useState(defaultUrl);
  const [downPayment, setDownPayment] = useState("2000");
  const [loanTerm, setLoanTerm] = useState("60");
  const [creditTier, setCreditTier] = useState("good");
  const [ageBand, setAgeBand] = useState("35-54");
  const [result, setResult] = useState<ListingDealEvaluation | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const evaluation = await evaluateListingDeal({
        vin,
        listing_price: Number(listingPrice),
        mileage: Number(mileage),
        zip_code: zipCode,
        down_payment: Number(downPayment || 0),
        loan_term_months: Number(loanTerm),
        credit_tier: creditTier,
        age_band: ageBand,
        listing_url: listingUrl || undefined,
      });
      setResult(evaluation);
      window.setTimeout(
        () =>
          document
            .getElementById("listing-deal-results")
            ?.scrollIntoView({ behavior: "smooth" }),
        0,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not evaluate this listing.");
      setResult(null);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="maskara-ambient relative min-h-[calc(100vh-4rem)] overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(14,165,233,0.1),transparent_42%)]" />
      <div className="relative mx-auto max-w-5xl px-4 py-12 md:py-16">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-xs uppercase tracking-[0.2em] text-slate-500 shadow-sm">
            <CarFront className="h-3.5 w-3.5 text-violet-600" />
            Listing deal check
          </div>
          <h1 className="mt-6 text-4xl font-light tracking-tight text-slate-900 md:text-5xl">
            Is this listing a{" "}
            <span className="maskara-gradient-text">smart monthly buy?</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-slate-600">
            Paste a dealer listing URL for your notes, then enter the VIN and
            numbers. Carvest estimates fair price, loan payments by credit tier,
            and an insurance range—before you commit.
          </p>
        </div>

        <form
          onSubmit={submit}
          className="maskara-glass mx-auto mt-10 max-w-4xl rounded-3xl p-6 md:p-8"
        >
          <div className="grid gap-5 sm:grid-cols-2">
            <label className="space-y-2 sm:col-span-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Listing URL{" "}
                <span className="font-normal normal-case">(optional reference)</span>
              </span>
              <Input
                type="url"
                value={listingUrl}
                onChange={(event) => setListingUrl(event.target.value)}
                placeholder="https://dealer.example/vehicle"
              />
            </label>
            <label className="space-y-2 sm:col-span-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                VIN
              </span>
              <Input
                value={vin}
                onChange={(event) => setVin(event.target.value.toUpperCase())}
                placeholder="17-character VIN"
                minLength={17}
                maxLength={17}
                required
                className="font-mono tracking-wider"
              />
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Asking price
              </span>
              <Input
                type="number"
                min="1"
                value={listingPrice}
                onChange={(event) => setListingPrice(event.target.value)}
                placeholder="24995"
                required
              />
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Mileage
              </span>
              <Input
                type="number"
                min="0"
                value={mileage}
                onChange={(event) => setMileage(event.target.value)}
                placeholder="42500"
                required
              />
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                ZIP code
              </span>
              <Input
                inputMode="numeric"
                pattern="[0-9]{5}"
                value={zipCode}
                onChange={(event) =>
                  setZipCode(event.target.value.replace(/\D/g, "").slice(0, 5))
                }
                placeholder="77087"
                required
              />
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Down payment
              </span>
              <Input
                type="number"
                min="0"
                value={downPayment}
                onChange={(event) => setDownPayment(event.target.value)}
                placeholder="2000"
              />
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Loan term
              </span>
              <select
                value={loanTerm}
                onChange={(event) => setLoanTerm(event.target.value)}
                className="flex h-12 w-full rounded-xl border border-border bg-card px-4 text-sm text-slate-900"
              >
                {TERM_OPTIONS.map((months) => (
                  <option key={months} value={months}>
                    {months} months
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Credit tier
              </span>
              <select
                value={creditTier}
                onChange={(event) => setCreditTier(event.target.value)}
                className="flex h-12 w-full rounded-xl border border-border bg-card px-4 text-sm text-slate-900"
              >
                {CREDIT_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
            <label className="space-y-2">
              <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                Driver age band
              </span>
              <select
                value={ageBand}
                onChange={(event) => setAgeBand(event.target.value)}
                className="flex h-12 w-full rounded-xl border border-border bg-card px-4 text-sm text-slate-900"
              >
                {AGE_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>

          {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

          <Button type="submit" className="mt-6 w-full" disabled={loading}>
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Calculator className="h-4 w-4" />
            )}
            {loading ? "Evaluating this listing..." : "Check deal and monthly cost"}
          </Button>
          <p className="mt-3 text-center text-xs text-slate-400">
            We do not scrape dealer pages. The URL is saved as a reference only.
            Insurance and APR figures are educational estimates, not quotes.
          </p>
        </form>

        {result ? <ListingDealResults result={result} /> : null}
      </div>
    </main>
  );
}

function ListingDealResults({ result }: { result: ListingDealEvaluation }) {
  const vehicle = result.vehicle;
  const signal = result.price_analysis?.deal_signal ?? undefined;

  return (
    <section
      id="listing-deal-results"
      className="mx-auto mt-10 max-w-4xl scroll-mt-24 space-y-6"
    >
      <div className="maskara-glass rounded-3xl p-6 md:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">
              Listing evaluation
            </p>
            <h2 className="mt-2 text-3xl font-light text-slate-900">
              {vehicle.year} {vehicle.make} {vehicle.model}
            </h2>
            <p className="mt-1 font-mono text-xs tracking-wider text-slate-500">
              VIN {vehicle.vin}
            </p>
          </div>
          {signal ? <DealBadge signal={signal} /> : null}
        </div>

        <p className="mt-5 text-base font-medium text-slate-900">
          {result.recommendation.headline}
        </p>
        <p className="mt-2 text-sm leading-7 text-slate-600">
          {result.recommendation.detail}
        </p>
        <p className="mt-3 text-xs text-slate-400">{result.market_note}</p>

        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Metric label="Asking price" value={formatCurrency(result.listing.price)} />
          <Metric
            label="Fair price estimate"
            value={formatCurrency(result.price_analysis?.predicted_fair_price)}
          />
          <Metric
            label="Price delta"
            value={formatCurrency(result.price_analysis?.price_delta)}
          />
          <Metric
            label="Recall campaigns"
            value={
              result.recalls_available === false || result.recall_count == null
                ? "Unavailable"
                : String(result.recall_count)
            }
          />
        </div>
      </div>

      <div className="maskara-glass rounded-3xl p-6 md:p-8">
        <h3 className="text-xl font-semibold text-slate-900">Monthly ownership estimate</h3>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <Metric
            label="Loan payment"
            value={formatCurrency(result.ownership.loan_monthly)}
            highlighted
          />
          <Metric
            label="Insurance mid-range"
            value={formatCurrency(result.ownership.insurance_monthly_mid)}
          />
          <Metric
            label="Combined mid-range"
            value={formatCurrency(result.ownership.estimated_monthly_mid)}
            highlighted
          />
        </div>
        <p className="mt-3 text-sm text-slate-500">
          Combined range:{" "}
          {formatCurrency(result.ownership.estimated_monthly_low)} –{" "}
          {formatCurrency(result.ownership.estimated_monthly_high)} / month
          (loan + insurance estimate). Does not include fuel, maintenance, or taxes.
        </p>
        <p className="mt-2 text-xs text-slate-400">
          Financing {formatCurrency(result.loan.amount_financed)} over{" "}
          {result.loan.term_months} months at an illustrative{" "}
          {result.loan.selected_apr_percent}% APR after a{" "}
          {formatCurrency(result.loan.down_payment)} down payment.
        </p>
      </div>

      <div className="maskara-glass rounded-3xl p-6 md:p-8">
        <h3 className="text-xl font-semibold text-slate-900">Loan scenarios by credit tier</h3>
        <div className="mt-5 overflow-hidden rounded-2xl border border-border">
          {result.loan.scenarios.map((scenario) => (
            <div
              key={scenario.credit_tier}
              className={cn(
                "flex flex-wrap items-center justify-between gap-3 border-b border-border px-4 py-4 last:border-b-0",
                scenario.selected && "bg-violet-50/70",
              )}
            >
              <div>
                <p className="font-medium text-slate-900">{scenario.label}</p>
                <p className="text-xs text-slate-500">
                  Illustrative APR {scenario.apr_percent}%
                  {scenario.selected ? " · selected" : ""}
                </p>
              </div>
              <p className="text-lg font-semibold text-slate-900">
                {formatCurrency(scenario.monthly_payment)}
                <span className="text-sm font-normal text-slate-500"> / mo</span>
              </p>
            </div>
          ))}
        </div>
        <p className="mt-4 text-xs leading-5 text-slate-400">{result.loan.disclaimer}</p>
      </div>

      <div className="maskara-glass rounded-3xl p-6 md:p-8">
        <h3 className="text-xl font-semibold text-slate-900">
          Insurance range · age {result.insurance.age_band_label}
        </h3>
        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <Metric label="Low" value={formatCurrency(result.insurance.monthly_low)} />
          <Metric label="Mid" value={formatCurrency(result.insurance.monthly_mid)} highlighted />
          <Metric label="High" value={formatCurrency(result.insurance.monthly_high)} />
        </div>
        <p className="mt-4 text-xs leading-5 text-slate-400">
          {result.insurance.disclaimer}
        </p>
      </div>

      <div className="maskara-glass rounded-3xl p-6 md:p-8">
        <h3 className="text-xl font-semibold text-slate-900">What to do next</h3>
        <ul className="mt-4 space-y-3">
          {result.recommendation.tips.map((tip) => (
            <li key={tip} className="flex gap-2 text-sm leading-6 text-slate-600">
              <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-emerald-600" />
              {tip}
            </li>
          ))}
        </ul>
        <div className="mt-6 grid gap-3 md:grid-cols-2">
          {result.next_steps.map((step) => (
            <Link
              key={step.id}
              href={step.href}
              className="rounded-2xl border border-border bg-card-subtle p-5 transition hover:border-violet-300 hover:bg-violet-50"
            >
              <p className="flex items-center gap-2 font-medium text-slate-900">
                {step.label}
                <ArrowRight className="h-4 w-4 text-violet-600" />
              </p>
              <p className="mt-2 text-sm leading-6 text-slate-500">{step.description}</p>
            </Link>
          ))}
        </div>
        {result.listing.listing_url ? (
          <p className="mt-5 text-xs text-slate-400">
            Listing reference:{" "}
            <a
              href={result.listing.listing_url}
              target="_blank"
              rel="noreferrer"
              className="underline hover:text-violet-700"
            >
              {result.listing.listing_url}
            </a>
          </p>
        ) : null}
        <p className="mt-6 border-t border-border pt-5 text-xs leading-5 text-slate-400">
          {result.disclaimer} Mileage entered: {formatNumber(result.listing.mileage)} mi.
        </p>
      </div>
    </section>
  );
}

function Metric({
  label,
  value,
  highlighted = false,
}: {
  label: string;
  value: string;
  highlighted?: boolean;
}) {
  return (
    <div
      className={cn(
        "rounded-2xl border p-4",
        highlighted ? "border-violet-200 bg-violet-50" : "border-border bg-card-subtle",
      )}
    >
      <p className="text-xs uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}
