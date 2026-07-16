"use client";

import { useEffect, useMemo, useState } from "react";
import { Car } from "lucide-react";

import type { AssistantHighlight } from "@/lib/api";
import { vehicleReferenceImageUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

export function VehicleImage({
  item,
  size = "default",
}: {
  item: AssistantHighlight;
  size?: "default" | "compact";
}) {
  const proxyUrl = useMemo(() => {
    if (!item.make || !item.model) return null;
    return vehicleReferenceImageUrl({
      make: item.make,
      model: item.model,
      year: item.year,
    });
  }, [item.make, item.model, item.year]);

  const listingPhoto =
    item.photo_source === "listing" && item.photo ? item.photo : null;

  const [src, setSrc] = useState<string | null>(listingPhoto ?? proxyUrl);
  const [failed, setFailed] = useState(false);
  const [usedProxy, setUsedProxy] = useState(!listingPhoto);

  useEffect(() => {
    setSrc(listingPhoto ?? proxyUrl);
    setFailed(false);
    setUsedProxy(!listingPhoto);
  }, [listingPhoto, proxyUrl]);

  const shellClass = cn(
    "relative overflow-hidden rounded-xl border border-border bg-gradient-to-b from-slate-100/80 to-card-subtle",
    // Taller frame + contain so roofs/wheels aren't cropped off.
    size === "compact" ? "aspect-[16/10] w-full" : "aspect-[16/9] w-full",
  );

  if (src && !failed) {
    return (
      <div className={shellClass}>
        <img
          src={src}
          alt={item.title}
          className="h-full w-full object-contain object-center"
          loading="lazy"
          decoding="async"
          referrerPolicy="no-referrer"
          onError={() => {
            if (!usedProxy && proxyUrl) {
              setUsedProxy(true);
              setSrc(proxyUrl);
              return;
            }
            setFailed(true);
          }}
        />
        {(usedProxy || item.photo_source === "reference") && (
          <span className="absolute bottom-2 left-2 rounded-full border border-border bg-card/90 px-2 py-0.5 text-[10px] font-medium uppercase tracking-[0.14em] text-slate-500 backdrop-blur">
            Reference look
          </span>
        )}
      </div>
    );
  }

  const label = [item.year, item.make, item.model].filter(Boolean).join(" ");

  return (
    <div
      className={cn(
        shellClass,
        "flex items-center justify-center bg-gradient-to-br from-card-subtle via-card to-violet-100/50",
      )}
    >
      <div
        className={cn(
          "flex flex-col items-center gap-2 px-4 text-center text-slate-500",
          size === "compact" && "scale-90",
        )}
      >
        <Car className={cn(size === "compact" ? "h-7 w-7" : "h-10 w-10")} strokeWidth={1.25} />
        <span className="text-sm font-medium text-slate-700">{label || item.title}</span>
        <span className="text-[10px] uppercase tracking-[0.18em] text-slate-400">
          Reference look
        </span>
      </div>
    </div>
  );
}
