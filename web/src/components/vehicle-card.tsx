import Image from "next/image";
import Link from "next/link";
import { Heart, MapPin } from "lucide-react";

import { DealBadge } from "@/components/ui/badge";
import type { AssistantCriteria, Listing } from "@/lib/api";
import { formatCurrency, formatNumber } from "@/lib/utils";

function estimatedMonthly(price?: number) {
  if (!price) return null;
  return Math.round((price * 0.065) / 12);
}

export function VehicleCard({
  listing,
  criteria,
}: {
  listing: Listing;
  criteria?: AssistantCriteria | null;
}) {
  const title = listing.heading ?? "Vehicle listing";
  const monthly = estimatedMonthly(listing.price);
  const href = `/vehicle/${encodeURIComponent(listing.listing_id ?? listing.vin ?? "unknown")}?${new URLSearchParams(
    {
      heading: title,
      price: String(listing.price ?? ""),
      miles: String(listing.miles ?? ""),
      photo: listing.primary_photo ?? "",
      dealer: listing.dealer_name ?? "",
      city: listing.city ?? "",
      state: listing.state ?? "",
      signal: listing.price_analysis?.deal_signal ?? "",
      vdp: listing.vdp_url ?? "",
      vin: listing.vin ?? "",
      zip: listing.zip ?? String(criteria?.zip_code ?? ""),
      dom: String(listing.dom ?? ""),
      make: String(criteria?.make ?? ""),
      model: String(criteria?.model ?? ""),
      year: String(criteria?.year ?? ""),
      fair: String(listing.price_analysis?.predicted_fair_price ?? ""),
      delta: String(listing.price_analysis?.price_delta ?? ""),
    },
  ).toString()}`;

  return (
    <Link href={href} className="carvana-card group block overflow-hidden">
      <div className="relative aspect-[4/3] bg-card-subtle">
        {listing.primary_photo ? (
          <Image
            src={listing.primary_photo}
            alt={title}
            fill
            className="object-cover transition duration-500 group-hover:scale-[1.02]"
            sizes="(max-width: 768px) 100vw, 25vw"
            unoptimized
          />
        ) : (
          <div className="flex h-full items-center justify-center text-sm text-slate-400">
            Photos coming soon
          </div>
        )}

        <button
          type="button"
          aria-label="Save listing"
          className="absolute right-3 top-3 rounded-full bg-card/95 p-2 text-slate-600 shadow-sm transition hover:text-violet-600"
          onClick={(event) => event.preventDefault()}
        >
          <Heart className="h-4 w-4" />
        </button>

        <div className="absolute left-3 top-3">
          <DealBadge signal={listing.price_analysis?.deal_signal} />
        </div>
      </div>

      <div className="space-y-2 p-4">
        <h3 className="line-clamp-2 text-base font-semibold leading-snug text-slate-900">
          {title}
        </h3>

        <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
          <p className="text-2xl font-bold tracking-tight text-slate-900">
            {formatCurrency(listing.price)}
          </p>
          {monthly ? (
            <p className="text-sm text-slate-500">
              Est. ${monthly.toLocaleString()}/mo
            </p>
          ) : null}
        </div>

        <p className="text-sm text-slate-600">
          {formatNumber(listing.miles)} mi
          {listing.fuel_type ? ` · ${listing.fuel_type}` : ""}
        </p>

        {(listing.city || listing.dealer_name) && (
          <p className="flex items-center gap-1.5 text-sm text-slate-500">
            <MapPin className="h-3.5 w-3.5 shrink-0" />
            <span className="truncate">
              {[listing.dealer_name, listing.city, listing.state].filter(Boolean).join(" · ")}
            </span>
          </p>
        )}
      </div>
    </Link>
  );
}
