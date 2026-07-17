"use client";

import { FormEvent, useState } from "react";
import {
  AlertTriangle,
  Calculator,
  CheckCircle2,
  CircleDollarSign,
  Loader2,
  Plus,
  ReceiptText,
  ShieldQuestion,
  Trash2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  analyzeOfferSheet,
  type OfferSheetAnalysis,
  type OfferSheetCategory,
} from "@/lib/api";
import { cn, formatCurrency } from "@/lib/utils";

type EditableLine = {
  id: number;
  label: string;
  amount: string;
};

const CATEGORY_LABELS: Record<OfferSheetCategory, string> = {
  government_charge: "Government-related",
  dealer_fee: "Dealer fee",
  optional_product: "Optional product",
  price_adjustment: "Price adjustment",
  unknown: "Needs explanation",
};

const CATEGORY_STYLES: Record<OfferSheetCategory, string> = {
  government_charge: "border-sky-200 bg-sky-50 text-sky-700",
  dealer_fee: "border-amber-200 bg-amber-50 text-amber-700",
  optional_product: "border-violet-200 bg-violet-50 text-violet-700",
  price_adjustment: "border-emerald-200 bg-emerald-50 text-emerald-700",
  unknown: "border-rose-200 bg-rose-50 text-rose-700",
};

export function OfferSheetClient({ defaultPrice = "" }: { defaultPrice?: string }) {
  const [advertisedPrice, setAdvertisedPrice] = useState(defaultPrice);
  const [stateCode, setStateCode] = useState("");
  const [zipCode, setZipCode] = useState("");
  const [lines, setLines] = useState<EditableLine[]>([
    { id: 1, label: "", amount: "" },
    { id: 2, label: "", amount: "" },
    { id: 3, label: "", amount: "" },
  ]);
  const [nextId, setNextId] = useState(4);
  const [analysis, setAnalysis] = useState<OfferSheetAnalysis | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function updateLine(id: number, field: "label" | "amount", value: string) {
    setLines((current) =>
      current.map((line) => (line.id === id ? { ...line, [field]: value } : line)),
    );
    setAnalysis(null);
  }

  function addLine() {
    setLines((current) => [...current, { id: nextId, label: "", amount: "" }]);
    setNextId((current) => current + 1);
    setAnalysis(null);
  }

  function removeLine(id: number) {
    setLines((current) =>
      current.length === 1 ? current : current.filter((line) => line.id !== id),
    );
    setAnalysis(null);
  }

  function loadExample() {
    setAdvertisedPrice("24995");
    setStateCode("TX");
    setZipCode("77087");
    setLines([
      { id: 10, label: "Sales Tax", amount: "1562.19" },
      { id: 11, label: "Documentation Fee", amount: "899" },
      { id: 12, label: "VIN Etching", amount: "499" },
      { id: 13, label: "Protection Package", amount: "1295" },
      { id: 14, label: "Dealer Discount", amount: "-750" },
    ]);
    setNextId(15);
    setAnalysis(null);
    setError(null);
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    const enteredLines = lines.filter((line) => line.label.trim());
    if (!enteredLines.length) {
      setError("Enter at least one line item from the dealer quote.");
      return;
    }
    const missingAmount = enteredLines.some(
      (line) => line.amount.trim() === "" || Number.isNaN(Number(line.amount)),
    );
    if (missingAmount) {
      setError("Enter a numeric amount for every labeled line item.");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeOfferSheet({
        advertised_price: Number(advertisedPrice),
        line_items: enteredLines.map((line) => ({
          label: line.label.trim(),
          amount: Number(line.amount),
        })),
        state: stateCode || undefined,
        zip_code: zipCode || undefined,
      });
      setAnalysis(result);
      window.setTimeout(
        () => document.getElementById("offer-results")?.scrollIntoView({ behavior: "smooth" }),
        0,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not analyze this offer.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="maskara-ambient relative min-h-[calc(100vh-4rem)] overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(217,119,6,0.09),transparent_44%)]" />
      <div className="relative mx-auto max-w-5xl px-4 py-12 md:py-16">
        <div className="mx-auto max-w-3xl text-center">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-xs uppercase tracking-[0.2em] text-slate-500 shadow-sm">
            <ReceiptText className="h-3.5 w-3.5 text-violet-600" />
            Offer sheet analyzer
          </div>
          <h1 className="mt-6 text-4xl font-light tracking-tight text-slate-900 md:text-5xl">
            See what the dealer quote{" "}
            <span className="maskara-gradient-text">really adds up to</span>
          </h1>
          <p className="mx-auto mt-5 max-w-2xl text-base leading-7 text-slate-600">
            Enter each charge from the buyer&apos;s order. Carvest separates taxes,
            dealer fees, optional products, and unclear charges—without assuming a fee
            is improper.
          </p>
        </div>

        <div className="mx-auto mt-10 grid max-w-5xl gap-6 lg:grid-cols-[1fr_0.42fr]">
          <form onSubmit={submit} className="maskara-glass rounded-3xl p-6 md:p-8">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">
                  Dealer quote
                </p>
                <h2 className="mt-2 text-2xl font-light text-slate-900">
                  Enter the advertised price and every added line
                </h2>
              </div>
              <Button type="button" variant="outline" size="sm" onClick={loadExample}>
                Load example
              </Button>
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-3">
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  Advertised price
                </span>
                <Input
                  type="number"
                  min="1"
                  step="0.01"
                  value={advertisedPrice}
                  onChange={(event) => {
                    setAdvertisedPrice(event.target.value);
                    setAnalysis(null);
                  }}
                  placeholder="24995"
                  required
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  State <span className="font-normal normal-case">(optional)</span>
                </span>
                <Input
                  value={stateCode}
                  onChange={(event) => {
                    setStateCode(event.target.value.toUpperCase().slice(0, 2));
                    setAnalysis(null);
                  }}
                  placeholder="TX"
                  maxLength={2}
                />
              </label>
              <label className="space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">
                  ZIP <span className="font-normal normal-case">(optional)</span>
                </span>
                <Input
                  inputMode="numeric"
                  pattern="[0-9]{5}"
                  value={zipCode}
                  onChange={(event) => {
                    setZipCode(event.target.value.replace(/\D/g, "").slice(0, 5));
                    setAnalysis(null);
                  }}
                  placeholder="77087"
                />
              </label>
            </div>

            <div className="mt-7">
              <div className="grid grid-cols-[minmax(0,1fr)_6.5rem_2.25rem] gap-2 px-1 text-xs font-semibold uppercase tracking-[0.16em] text-slate-500 sm:grid-cols-[1fr_8rem_2.25rem]">
                <span>Line-item label</span>
                <span>Amount</span>
                <span />
              </div>
              <div className="mt-2 space-y-2">
                {lines.map((line) => (
                  <div
                    key={line.id}
                    className="grid grid-cols-[minmax(0,1fr)_6.5rem_2.25rem] gap-2 sm:grid-cols-[1fr_8rem_2.25rem]"
                  >
                    <Input
                      value={line.label}
                      onChange={(event) => updateLine(line.id, "label", event.target.value)}
                      placeholder="Documentation fee"
                    />
                    <Input
                      type="number"
                      step="0.01"
                      value={line.amount}
                      onChange={(event) => updateLine(line.id, "amount", event.target.value)}
                      placeholder="899"
                      aria-label={`${line.label || "Line item"} amount`}
                    />
                    <button
                      type="button"
                      onClick={() => removeLine(line.id)}
                      className="flex h-12 items-center justify-center rounded-xl text-slate-400 transition hover:bg-rose-50 hover:text-rose-600"
                      aria-label="Remove line item"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                ))}
              </div>
              <Button type="button" variant="ghost" size="sm" className="mt-3" onClick={addLine}>
                <Plus className="h-4 w-4" />
                Add line item
              </Button>
              <p className="mt-2 text-xs text-slate-400">
                Enter discounts, rebates, and credits as negative amounts.
              </p>
            </div>

            {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

            <Button type="submit" className="mt-6 w-full" disabled={loading}>
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Calculator className="h-4 w-4" />
              )}
              {loading ? "Analyzing the quote..." : "Analyze out-the-door price"}
            </Button>
          </form>

          <aside className="maskara-glass rounded-3xl p-6">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-amber-700">
              What to enter
            </p>
            <ul className="mt-4 space-y-4 text-sm leading-6 text-slate-600">
              {[
                "Taxes, title, registration, and tag charges",
                "Documentation, prep, delivery, and reconditioning fees",
                "Warranties, GAP, protection packages, and accessories",
                "Market adjustments, discounts, rebates, and credits",
              ].map((item) => (
                <li key={item} className="flex gap-2">
                  <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-emerald-600" />
                  {item}
                </li>
              ))}
            </ul>
            <div className="mt-6 rounded-2xl border border-border bg-card-subtle p-4">
              <ShieldQuestion className="h-5 w-5 text-violet-600" />
              <p className="mt-3 text-sm font-medium text-slate-900">
                A flag means “ask for clarity”
              </p>
              <p className="mt-1 text-xs leading-5 text-slate-500">
                It does not mean a fee is illegal or deceptive. Requirements differ by
                state, lender, product, and transaction.
              </p>
            </div>
          </aside>
        </div>

        {analysis ? <OfferResults analysis={analysis} /> : null}
      </div>
    </main>
  );
}

function OfferResults({ analysis }: { analysis: OfferSheetAnalysis }) {
  const levelCopy = {
    low: "The entered charges are mostly clear, but verify the final contract.",
    moderate: "Some charges deserve clarification before you agree to the deal.",
    high: "Several charges or adjustments deserve careful review before signing.",
  }[analysis.review_level];

  return (
    <section id="offer-results" className="mx-auto mt-10 max-w-5xl scroll-mt-24">
      <div className="maskara-glass rounded-3xl p-6 md:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-violet-600">
              Offer analysis
            </p>
            <h2 className="mt-2 text-3xl font-light text-slate-900">
              Estimated out-the-door total
            </h2>
          </div>
          <span
            className={cn(
              "rounded-full border px-3 py-1 text-xs font-semibold uppercase tracking-[0.12em]",
              analysis.review_level === "low" &&
                "border-emerald-200 bg-emerald-50 text-emerald-700",
              analysis.review_level === "moderate" &&
                "border-amber-200 bg-amber-50 text-amber-700",
              analysis.review_level === "high" &&
                "border-rose-200 bg-rose-50 text-rose-700",
            )}
          >
            {analysis.review_level} review level
          </span>
        </div>

        <p className="mt-4 text-sm leading-6 text-slate-600">{levelCopy}</p>

        <div className="mt-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <ResultMetric
            label="Advertised price"
            value={formatCurrency(analysis.totals.advertised_price)}
          />
          <ResultMetric
            label="Net added lines"
            value={formatCurrency(analysis.totals.line_items_subtotal)}
          />
          <ResultMetric
            label="Out-the-door total"
            value={formatCurrency(analysis.totals.out_the_door_total)}
            highlighted
          />
          <ResultMetric
            label="Amount to review"
            value={formatCurrency(analysis.totals.potential_review_amount)}
          />
        </div>
        <p className="mt-3 text-xs leading-5 text-slate-400">
          “Amount to review” is not guaranteed savings. It totals positive dealer
          fees, optional products, positive adjustments, and unclear charges that
          deserve an explanation.
        </p>

        <div className="mt-8 overflow-hidden rounded-2xl border border-border">
          {analysis.classified_items.map((item) => (
            <div
              key={`${item.index}-${item.label}`}
              className="border-b border-border bg-card p-5 last:border-b-0"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div>
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-slate-900">{item.label}</p>
                    <CategoryBadge category={item.category} />
                    {item.review_recommended ? (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-700">
                        <AlertTriangle className="h-3.5 w-3.5" />
                        Review
                      </span>
                    ) : null}
                  </div>
                  <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-500">
                    {item.rationale}
                  </p>
                </div>
                <p className="text-lg font-semibold text-slate-900">
                  {formatCurrency(item.amount)}
                </p>
              </div>
            </div>
          ))}
        </div>

        {analysis.questions.length ? (
          <div className="mt-8">
            <div className="flex items-center gap-2">
              <CircleDollarSign className="h-5 w-5 text-violet-600" />
              <h3 className="text-xl font-semibold text-slate-900">
                Questions to ask before signing
              </h3>
            </div>
            <div className="mt-4 grid gap-3 md:grid-cols-2">
              {analysis.questions.map((item) => (
                <div
                  key={`${item.related_labels.join("-")}-${item.question}`}
                  className="rounded-2xl border border-border bg-card-subtle p-5"
                >
                  <p className="text-sm font-medium leading-6 text-slate-900">
                    “{item.question}”
                  </p>
                  <p className="mt-2 text-xs leading-5 text-slate-500">{item.context}</p>
                </div>
              ))}
            </div>
          </div>
        ) : null}

        <p className="mt-8 border-t border-border pt-5 text-xs leading-5 text-slate-400">
          {analysis.disclaimer}
        </p>
      </div>
    </section>
  );
}

function ResultMetric({
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
        highlighted
          ? "border-violet-200 bg-violet-50"
          : "border-border bg-card-subtle",
      )}
    >
      <p className="text-xs uppercase tracking-[0.14em] text-slate-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-slate-900">{value}</p>
    </div>
  );
}

function CategoryBadge({ category }: { category: OfferSheetCategory }) {
  return (
    <span
      className={cn(
        "rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.1em]",
        CATEGORY_STYLES[category],
      )}
    >
      {CATEGORY_LABELS[category]}
    </span>
  );
}
