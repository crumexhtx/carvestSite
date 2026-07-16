import type { AssistantHighlight } from "@/lib/api";
import { cn } from "@/lib/utils";

import { VehicleImage } from "@/components/vehicle-image";

export function RecommendationCards({
  highlights,
  onSelect,
  compact = false,
}: {
  highlights: AssistantHighlight[];
  onSelect?: (item: AssistantHighlight) => void;
  compact?: boolean;
}) {
  if (!highlights.length) return null;

  return (
    <div
      className={cn(
        compact ? "mt-3 grid grid-cols-2 gap-3" : "mt-4 space-y-6",
      )}
    >
      {highlights.map((item, index) => {
        const label = item.trim
          ? `${item.make} ${item.model} ${item.trim}`
          : `${item.make} ${item.model}`;

        const content = (
          <>
            <p
              className={cn(
                "leading-6 text-slate-700",
                compact ? "text-xs" : "text-sm leading-7",
              )}
            >
              <span className="font-semibold text-slate-900">{label}:</span>{" "}
              {item.summary || "A strong option worth comparing for your search."}
            </p>
            <div className={cn("mt-2", compact && "max-w-full")}>
              <VehicleImage item={item} size={compact ? "compact" : "default"} />
            </div>
            {onSelect ? (
              <p className="mt-2 text-[10px] uppercase tracking-[0.18em] text-violet-600">
                Tap to research
              </p>
            ) : null}
          </>
        );

        const key =
          item.id ??
          `${item.make}-${item.model}-${item.year ?? "na"}-${item.trim ?? "base"}-${index}`;

        if (!onSelect) {
          return (
            <div key={key} className="text-left">
              {content}
            </div>
          );
        }

        return (
          <button
            key={key}
            type="button"
            onClick={() => onSelect(item)}
            className="group rounded-xl border border-transparent p-1 text-left transition hover:border-violet-300 hover:bg-violet-50"
          >
            {content}
          </button>
        );
      })}
    </div>
  );
}
