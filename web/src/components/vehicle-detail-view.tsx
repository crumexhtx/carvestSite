import Image from "next/image";
import Link from "next/link";

import { NegotiationPanel } from "@/components/negotiation-panel";
import { DealBadge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { features } from "@/lib/features";
import { formatCurrency, formatNumber } from "@/lib/utils";

type VehicleDetailProps = {
  id: string;
  heading: string;
  price: number;
  miles: number;
  photo: string;
  dealer: string;
  city: string;
  state: string;
  signal: string;
  vdp: string;
  vin: string;
  zipCode: string;
  dom: number;
  make: string;
  model: string;
  year: number;
  fairPrice: number;
  priceDelta: number;
};

export function VehicleDetailView({
  id,
  heading,
  price,
  miles,
  photo,
  dealer,
  city,
  state,
  signal,
  vdp,
  vin,
  zipCode,
  dom,
  make,
  model,
  year,
  fairPrice,
  priceDelta,
}: VehicleDetailProps) {
  return (
    <main className="mx-auto max-w-6xl p-4 md:p-6 lg:p-8">
      <Link href="/search?mode=results" className="text-sm text-slate-500 transition hover:text-violet-700">
        ← Back to listings
      </Link>

      <div className="mt-8 grid gap-8 lg:grid-cols-[1.2fr_0.8fr]">
        <Card className="overflow-hidden">
          <div className="relative aspect-[16/10] bg-card-subtle">
            {photo ? (
              <Image
                src={photo}
                alt={heading}
                fill
                className="object-cover"
                sizes="(max-width: 1024px) 100vw, 60vw"
                unoptimized
              />
            ) : (
              <div className="flex h-full items-center justify-center text-slate-400">
                No photo available
              </div>
            )}
          </div>
        </Card>

        <Card>
          <CardContent className="space-y-6">
            <div>
              <p className="text-xs uppercase tracking-[0.25em] text-slate-500">Vehicle profile</p>
              <h1 className="mt-3 text-3xl font-light text-slate-900">{heading}</h1>
            </div>
            <DealBadge signal={signal} />
            <div className="grid grid-cols-2 gap-4">
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Price</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">
                  {formatCurrency(price || null)}
                </p>
              </div>
              <div>
                <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Mileage</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">
                  {formatNumber(miles || null)}
                </p>
              </div>
              {fairPrice ? (
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Fair value</p>
                  <p className="mt-2 text-lg font-semibold text-slate-900">
                    {formatCurrency(fairPrice)}
                  </p>
                </div>
              ) : null}
              {dom ? (
                <div>
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Days on lot</p>
                  <p className="mt-2 text-lg font-semibold text-slate-900">{dom}</p>
                </div>
              ) : null}
            </div>
            {(dealer || city) && (
              <p className="text-sm text-slate-600">
                {[dealer, city, state].filter(Boolean).join(" · ")}
              </p>
            )}
            <div className="flex flex-wrap gap-3">
              {vdp ? (
                <Button asChild>
                  <a href={vdp} target="_blank" rel="noreferrer">
                    View Dealer Listing
                  </a>
                </Button>
              ) : null}
              <Button variant="outline" asChild>
                <Link href="/">Research Similar Cars</Link>
              </Button>
              {vin || price ? (
                <Button variant="outline" asChild>
                  <Link
                    href={`/listing-deal?${new URLSearchParams({
                      ...(vin ? { vin } : {}),
                      ...(price ? { price: String(price) } : {}),
                      ...(miles ? { miles: String(miles) } : {}),
                      ...(zipCode ? { zip: zipCode } : {}),
                      ...(vdp ? { url: vdp } : {}),
                    }).toString()}`}
                  >
                    Check Listing Deal
                  </Link>
                </Button>
              ) : null}
              {features.monetizationEnabled && vin ? (
                <Button variant="outline" asChild>
                  <Link href={`/report?vin=${encodeURIComponent(vin)}`}>
                    Get VIN Buyer Report
                  </Link>
                </Button>
              ) : null}
              {price ? (
                <Button variant="outline" asChild>
                  <Link href={`/offer-sheet?price=${encodeURIComponent(price)}`}>
                    Analyze Dealer Offer
                  </Link>
                </Button>
              ) : null}
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="mt-8">
        <NegotiationPanel
          heading={heading}
          price={price}
          miles={miles || undefined}
          vin={vin || undefined}
          zipCode={zipCode || undefined}
          make={make || undefined}
          model={model || undefined}
          year={year || undefined}
          dom={dom || undefined}
          dealerName={dealer || undefined}
          city={city || undefined}
          state={state || undefined}
          dealSignal={signal || undefined}
          predictedFairPrice={fairPrice || undefined}
          priceDelta={priceDelta || undefined}
        />
      </div>
    </main>
  );
}
