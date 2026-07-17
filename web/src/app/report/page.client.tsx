"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import {
  ArrowRight,
  Calculator,
  CheckCircle2,
  Loader2,
  LockKeyhole,
  ReceiptText,
  SearchCheck,
  ShieldCheck,
} from "lucide-react";

import { SoftLaunchWaitlist } from "@/components/soft-launch-waitlist";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  checkoutBuyerReport,
  createBuyerReportPreview,
  type BuyerReportPreviewResponse,
} from "@/lib/api";
import { features } from "@/lib/features";
import { formatCurrency, formatNumber } from "@/lib/utils";

export function BuyerReportClient({ defaultVin = "" }: { defaultVin?: string }) {
  if (!features.monetizationEnabled) {
    return <SoftLaunchReportPage />;
  }

  return <MonetizedBuyerReportClient defaultVin={defaultVin} />;
}

function SoftLaunchReportPage() {
  return (
    <main className="maskara-ambient relative min-h-[calc(100vh-4rem)] overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(99,102,241,0.1),transparent_42%)]" />
      <div className="relative mx-auto max-w-3xl px-4 py-12 md:py-16">
        <div className="text-center">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-xs uppercase tracking-[0.2em] text-slate-500 shadow-sm">
            Soft launch
          </div>
          <h1 className="mt-6 text-4xl font-light tracking-tight text-slate-900 md:text-5xl">
            Paid VIN reports are{" "}
            <span className="maskara-gradient-text">coming soon</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-slate-600">
            Carvest is launching free educational tools first. Use them to check
            listing value, monthly cost, and dealer fees—then unlock deep-dive VIN
            reports once we have steady usage.
          </p>
        </div>

        <div className="maskara-glass mt-10 space-y-4 rounded-3xl p-6 md:p-8">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">
            Free tools available now
          </p>
          <Link
            href="/listing-deal"
            className="flex items-start gap-3 rounded-2xl border border-border bg-card-subtle p-4 transition hover:border-violet-300 hover:bg-violet-50"
          >
            <Calculator className="mt-0.5 h-5 w-5 shrink-0 text-violet-600" />
            <div>
              <p className="font-medium text-slate-900">Listing deal check</p>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                Fair-price signal, loan scenarios, and insurance ranges for a
                specific VIN.
              </p>
            </div>
            <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-violet-600" />
          </Link>
          <Link
            href="/offer-sheet"
            className="flex items-start gap-3 rounded-2xl border border-border bg-card-subtle p-4 transition hover:border-violet-300 hover:bg-violet-50"
          >
            <ReceiptText className="mt-0.5 h-5 w-5 shrink-0 text-violet-600" />
            <div>
              <p className="font-medium text-slate-900">Offer sheet analyzer</p>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                Break down taxes, dealer fees, and optional add-ons before you sign.
              </p>
            </div>
            <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-violet-600" />
          </Link>
          <Link
            href="/"
            className="flex items-start gap-3 rounded-2xl border border-border bg-card-subtle p-4 transition hover:border-violet-300 hover:bg-violet-50"
          >
            <SearchCheck className="mt-0.5 h-5 w-5 shrink-0 text-violet-600" />
            <div>
              <p className="font-medium text-slate-900">AI vehicle research</p>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                Narrow budget, reliability needs, and local listings with the assistant.
              </p>
            </div>
            <ArrowRight className="mt-1 h-4 w-4 shrink-0 text-violet-600" />
          </Link>

          <div className="pt-2">
            <SoftLaunchWaitlist source="report_page" />
          </div>
        </div>
      </div>
    </main>
  );
}

function MonetizedBuyerReportClient({ defaultVin = "" }: { defaultVin?: string }) {
  const [vin, setVin] = useState(defaultVin);
  const [listingPrice, setListingPrice] = useState("");
  const [mileage, setMileage] = useState("");
  const [zipCode, setZipCode] = useState("");
  const [email, setEmail] = useState("");
  const [preview, setPreview] = useState<BuyerReportPreviewResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [checkoutLoading, setCheckoutLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      const result = await createBuyerReportPreview({
        vin,
        listing_price: Number(listingPrice),
        mileage: Number(mileage),
        zip_code: zipCode,
        email,
      });
      sessionStorage.setItem(
        `carvest-report-${result.report_id}`,
        result.access_token,
      );
      setPreview(result);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not create the preview.");
    } finally {
      setLoading(false);
    }
  }

  async function checkout() {
    if (!preview) return;
    setCheckoutLoading(true);
    setError(null);
    try {
      const result = await checkoutBuyerReport(
        preview.report_id,
        preview.access_token,
      );
      if (!result.checkout_url) {
        throw new Error("Checkout did not return a redirect URL.");
      }
      window.location.assign(result.checkout_url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start checkout.");
      setCheckoutLoading(false);
    }
  }

  return (
    <main className="maskara-ambient relative min-h-[calc(100vh-4rem)] overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(99,102,241,0.1),transparent_42%)]" />
      <div className="relative mx-auto max-w-5xl px-4 py-12 md:py-16">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-xs uppercase tracking-[0.2em] text-slate-500 shadow-sm">
            <ShieldCheck className="h-3.5 w-3.5 text-violet-600" />
            VIN buyer report
          </div>
          <h1 className="mt-6 text-4xl font-light tracking-tight text-slate-900 md:text-5xl">
            Know this car{" "}
            <span className="maskara-gradient-text">before you buy</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-slate-600">
            Decode the VIN, check recalls, compare the asking price, and get a
            negotiation plan built around the exact vehicle.
          </p>
        </div>

        {!preview ? (
          <div className="mx-auto mt-10 grid max-w-4xl gap-6 lg:grid-cols-[1fr_0.65fr]">
            <form
              onSubmit={submit}
              className="maskara-glass rounded-3xl p-6 md:p-8"
            >
              <div className="grid gap-5 sm:grid-cols-2">
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
                    onChange={(event) => setZipCode(event.target.value)}
                    placeholder="77087"
                    required
                  />
                </label>
                <label className="space-y-2">
                  <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                    Email
                  </span>
                  <Input
                    type="email"
                    value={email}
                    onChange={(event) => setEmail(event.target.value)}
                    placeholder="you@example.com"
                    required
                  />
                </label>
              </div>
              <p className="mt-4 text-xs text-slate-400">
                Want monthly payment and insurance estimates first? Use the{" "}
                <Link className="underline hover:text-violet-700" href="/listing-deal">
                  Listing deal check
                </Link>
                .
              </p>

              {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

              <Button type="submit" className="mt-6 w-full" disabled={loading}>
                {loading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <SearchCheck className="h-4 w-4" />
                )}
                {loading ? "Checking this VIN..." : "Generate free preview"}
              </Button>
              <p className="mt-3 text-center text-xs text-slate-400">
                The free preview does not call paid market-pricing or AI services.
                By continuing, you agree to the{" "}
                <Link className="underline hover:text-violet-700" href="/terms">
                  terms
                </Link>{" "}
                and acknowledge the{" "}
                <Link className="underline hover:text-violet-700" href="/privacy">
                  privacy notice
                </Link>
                .
              </p>
            </form>

            <aside className="maskara-glass rounded-3xl p-6">
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">
                Complete report · $19
              </p>
              <h2 className="mt-3 text-xl font-semibold text-slate-900">
                A decision, not another search result
              </h2>
              <ul className="mt-5 space-y-3 text-sm leading-6 text-slate-600">
                {[
                  "VIN identity and model-year risk",
                  "Active recall breakdown",
                  "Fair-price estimate and deal signal",
                  "Inspection checklist",
                  "Opening, target, and walk-away prices",
                  "Dealer email and text scripts",
                ].map((item) => (
                  <li key={item} className="flex gap-2">
                    <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-emerald-600" />
                    {item}
                  </li>
                ))}
              </ul>
            </aside>
          </div>
        ) : (
          <section className="mx-auto mt-10 max-w-4xl">
            <div className="maskara-glass rounded-3xl p-6 md:p-8">
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">
                    Free VIN preview
                  </p>
                  <h2 className="mt-2 text-3xl font-light text-slate-900">
                    {preview.preview.vehicle.year} {preview.preview.vehicle.make}{" "}
                    {preview.preview.vehicle.model}
                  </h2>
                  {preview.preview.vehicle.trim ? (
                    <p className="mt-1 text-sm text-slate-500">
                      {preview.preview.vehicle.trim}
                    </p>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={() => setPreview(null)}
                  className="text-sm text-slate-500 transition hover:text-violet-700"
                >
                  Check another VIN
                </button>
              </div>

              <p className="mt-5 text-sm leading-7 text-slate-600">
                {preview.preview.summary}
              </p>

              <div className="mt-6 grid gap-3 sm:grid-cols-3">
                <Stat label="Asking price" value={formatCurrency(preview.preview.listing_price)} />
                <Stat label="Mileage" value={`${formatNumber(preview.preview.mileage)} mi`} />
                <Stat
                  label="Recall campaigns"
                  value={
                    preview.preview.recalls_available === false ||
                    preview.preview.recall_count == null
                      ? "Unavailable"
                      : String(preview.preview.recall_count)
                  }
                />
              </div>

              <div className="mt-7 rounded-2xl border border-violet-200 bg-violet-50/70 p-5">
                <div className="flex items-center gap-2">
                  <LockKeyhole className="h-4 w-4 text-violet-600" />
                  <h3 className="font-semibold text-slate-900">
                    Unlock the complete buyer report
                  </h3>
                </div>
                <div className="mt-4 grid gap-2 sm:grid-cols-2">
                  {preview.preview.locked_sections.map((section) => (
                    <p key={section} className="flex items-center gap-2 text-sm text-slate-600">
                      <CheckCircle2 className="h-4 w-4 text-violet-500" />
                      {section}
                    </p>
                  ))}
                </div>
                {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}
                <Button
                  type="button"
                  className="mt-5 w-full sm:w-auto"
                  onClick={() => void checkout()}
                  disabled={checkoutLoading}
                >
                  {checkoutLoading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <LockKeyhole className="h-4 w-4" />
                  )}
                  {checkoutLoading
                    ? "Preparing your report..."
                    : `Unlock for ${formatCurrency(preview.report_price_cents / 100)}`}
                  {!checkoutLoading ? <ArrowRight className="h-4 w-4" /> : null}
                </Button>
              </div>
            </div>
          </section>
        )}
      </div>
    </main>
  );
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl border border-border bg-card-subtle px-4 py-3">
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-1 text-lg font-semibold text-slate-900">{value}</p>
    </div>
  );
}
