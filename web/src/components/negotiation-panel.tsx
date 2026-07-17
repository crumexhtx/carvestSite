"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Copy, Loader2, MessageSquare } from "lucide-react";

import { SafeMarkdown } from "@/components/safe-markdown";
import { Button } from "@/components/ui/button";
import { generateNegotiationPack, type NegotiationPack } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";

type NegotiationPanelProps = {
  heading: string;
  price: number;
  miles?: number;
  vin?: string;
  zipCode?: string;
  make?: string;
  model?: string;
  year?: number;
  dom?: number;
  dealerName?: string;
  city?: string;
  state?: string;
  dealSignal?: string;
  predictedFairPrice?: number;
  priceDelta?: number;
};

export function NegotiationPanel(props: NegotiationPanelProps) {
  const listingKey = useMemo(
    () =>
      JSON.stringify({
        heading: props.heading,
        price: props.price,
        miles: props.miles,
        vin: props.vin,
        zipCode: props.zipCode,
        make: props.make,
        model: props.model,
        year: props.year,
        dom: props.dom,
        dealerName: props.dealerName,
        city: props.city,
        state: props.state,
        dealSignal: props.dealSignal,
        predictedFairPrice: props.predictedFairPrice,
        priceDelta: props.priceDelta,
      }),
    [props],
  );

  const [pack, setPack] = useState<NegotiationPack | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<"email" | "text" | null>(null);
  const [trackedKey, setTrackedKey] = useState(listingKey);
  const requestIdRef = useRef(0);
  const listingKeyRef = useRef(listingKey);

  if (trackedKey !== listingKey) {
    setTrackedKey(listingKey);
    setPack(null);
    setError(null);
    setLoading(false);
  }

  useEffect(() => {
    listingKeyRef.current = listingKey;
  }, [listingKey]);

  async function generatePack() {
    if (!props.price || loading) return;
    const requestId = ++requestIdRef.current;
    const keyAtStart = listingKey;
    setLoading(true);
    setError(null);

    try {
      const result = await generateNegotiationPack({
        heading: props.heading,
        price: props.price,
        miles: props.miles,
        vin: props.vin,
        zip_code: props.zipCode,
        make: props.make,
        model: props.model,
        year: props.year,
        dom: props.dom,
        dealer_name: props.dealerName,
        city: props.city,
        state: props.state,
        deal_signal: props.dealSignal,
        predicted_fair_price: props.predictedFairPrice,
        listing_price: props.price,
        price_delta: props.priceDelta,
      });
      if (
        requestId !== requestIdRef.current ||
        keyAtStart !== listingKeyRef.current
      ) {
        return;
      }
      setPack(result);
    } catch (err) {
      if (
        requestId !== requestIdRef.current ||
        keyAtStart !== listingKeyRef.current
      ) {
        return;
      }
      setError(err instanceof Error ? err.message : "Negotiation failed.");
    } finally {
      if (requestId === requestIdRef.current) {
        setLoading(false);
      }
    }
  }

  async function copyText(kind: "email" | "text", value: string) {
    await navigator.clipboard.writeText(value);
    setCopied(kind);
    setTimeout(() => setCopied(null), 2000);
  }

  return (
    <section className="maskara-glass rounded-2xl p-6">
      <div className="mb-4 flex items-center gap-2">
        <MessageSquare className="h-4 w-4 text-violet-600" />
        <h2 className="text-sm font-semibold uppercase tracking-[0.18em] text-slate-500">
          Negotiation coach
        </h2>
      </div>

      {!pack && !loading ? (
        <div className="space-y-3">
          <p className="text-sm leading-6 text-slate-600">
            Generate opening offers, talking points, and dealer scripts for this
            listing when you are ready to negotiate.
          </p>
          <Button onClick={() => void generatePack()} disabled={!props.price}>
            Build negotiation pack
          </Button>
        </div>
      ) : null}

      {loading ? (
        <div className="flex items-center gap-2 text-sm text-slate-500">
          <Loader2 className="h-4 w-4 animate-spin" />
          Building your negotiation scripts...
        </div>
      ) : null}

      {error ? <p className="text-sm text-rose-600">{error}</p> : null}

      {pack ? (
        <div className="space-y-5">
          <p className="text-sm leading-7 text-slate-600">{pack.summary}</p>

          <div className="grid gap-3 sm:grid-cols-3">
            <OfferCard label="Opening offer" value={pack.opening_offer} />
            <OfferCard label="Target price" value={pack.target_price} highlight />
            <OfferCard label="Walk-away" value={pack.walk_away_price} />
          </div>

          {pack.talking_points?.length ? (
            <div>
              <p className="mb-2 text-xs uppercase tracking-[0.18em] text-slate-500">
                Leverage points
              </p>
              <ul className="space-y-2 text-sm text-slate-600">
                {pack.talking_points.map((point) => (
                  <li key={point} className="rounded-lg bg-card-subtle px-3 py-2">
                    {point}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="space-y-3">
            <ScriptBlock
              title="Email to dealer"
              script={pack.email_script}
              copied={copied === "email"}
              onCopy={() => void copyText("email", pack.email_script)}
            />
            <ScriptBlock
              title="Text message"
              script={pack.text_script}
              copied={copied === "text"}
              onCopy={() => void copyText("text", pack.text_script)}
            />
          </div>

          {pack.caution ? (
            <p className="text-xs text-slate-500">{pack.caution}</p>
          ) : null}

          <Button variant="ghost" size="sm" onClick={() => void generatePack()}>
            Regenerate
          </Button>
        </div>
      ) : null}
    </section>
  );
}

function OfferCard({
  label,
  value,
  highlight = false,
}: {
  label: string;
  value: number;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border px-4 py-3 ${
        highlight
          ? "border-violet-300 bg-violet-50"
          : "border-border bg-card-subtle"
      }`}
    >
      <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{label}</p>
      <p className="mt-1 text-xl font-semibold text-slate-900">{formatCurrency(value)}</p>
    </div>
  );
}

function ScriptBlock({
  title,
  script,
  copied,
  onCopy,
}: {
  title: string;
  script: string;
  copied: boolean;
  onCopy: () => void;
}) {
  return (
    <div className="rounded-xl border border-border bg-card-subtle p-4">
      <div className="mb-2 flex items-center justify-between gap-2">
        <p className="text-xs uppercase tracking-[0.16em] text-slate-500">{title}</p>
        <Button variant="ghost" size="sm" onClick={onCopy}>
          <Copy className="h-3.5 w-3.5" />
          {copied ? "Copied" : "Copy"}
        </Button>
      </div>
      <div className="prose-carvest text-sm">
        <SafeMarkdown>{script}</SafeMarkdown>
      </div>
    </div>
  );
}
