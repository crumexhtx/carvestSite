import { ShieldCheck } from "lucide-react";

import type { ReliabilityRankings } from "@/lib/api";
import { cn } from "@/lib/utils";

function reliabilityRowClass(side?: boolean) {
  return cn(
    "group w-full rounded-xl px-4 py-3 text-left transition disabled:opacity-40",
    side ? "maskara-chip" : "maskara-reliability-row",
  );
}

function rankBadgeClass(side?: boolean) {
  return cn(
    "mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-semibold",
    side ? "bg-violet-100 text-violet-700" : "bg-emerald-100 text-emerald-700",
  );
}

function titleClass(side?: boolean) {
  return cn(
    "font-medium",
    side ? "text-slate-700 group-hover:text-violet-700" : "text-slate-900 group-hover:text-emerald-800",
    side && "text-sm",
  );
}

function noteClass(side?: boolean) {
  return cn(
    "mt-0.5 leading-6 text-slate-500",
    side && "text-xs group-hover:text-violet-600/75",
    !side && "text-sm",
  );
}

export function ReliabilityPrompts({
  rankings,
  onSelectPrompt,
  disabled,
  compact,
  section = "all",
  side,
}: {
  rankings: ReliabilityRankings;
  onSelectPrompt: (prompt: string) => void;
  disabled?: boolean;
  compact?: boolean;
  section?: "vehicles" | "brands" | "all";
  side?: boolean;
}) {
  const showVehicles = section === "vehicles" || section === "all";
  const showBrands = section === "brands" || section === "all";

  return (
    <div
      className={
        compact
          ? "space-y-5"
          : side
            ? "space-y-4"
            : section === "all"
              ? "mt-10 space-y-8"
              : "space-y-4"
      }
    >
      {showVehicles ? (
        <section>
          <div className="mb-3 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" />
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
              Most reliable {rankings.reference_year} vehicles
            </h2>
          </div>
          <ol className="space-y-2">
            {rankings.top_vehicles.map((vehicle) => (
              <li key={`${vehicle.make}-${vehicle.model}`}>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onSelectPrompt(vehicle.prompt)}
                  className={reliabilityRowClass(side)}
                >
                  <div className="flex items-start gap-3">
                    <span className={rankBadgeClass(side)}>
                      {vehicle.rank}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className={titleClass(side)}>
                        {vehicle.year} {vehicle.make} {vehicle.model}
                      </p>
                      <p className={noteClass(side)}>
                        {vehicle.note}
                      </p>
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      {showBrands ? (
        <section>
          <div className="mb-3 flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 shrink-0 text-emerald-600" />
            <h2 className="text-[11px] font-semibold uppercase tracking-[0.2em] text-slate-500">
              Most reliable brands
            </h2>
          </div>
          <ol className="space-y-2">
            {rankings.top_brands.map((brand) => (
              <li key={brand.brand}>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onSelectPrompt(brand.prompt)}
                  className={reliabilityRowClass(side)}
                >
                  <div className="flex items-start gap-3">
                    <span className={rankBadgeClass(side)}>
                      {brand.rank}
                    </span>
                    <div className="min-w-0 flex-1">
                      <p className={titleClass(side)}>
                        {brand.brand}
                      </p>
                      <p className={noteClass(side)}>
                        {brand.note}
                      </p>
                    </div>
                  </div>
                </button>
              </li>
            ))}
          </ol>
        </section>
      ) : null}

      {section === "all" ? (
        <p className="text-center text-[11px] text-slate-400">
          Source: {rankings.source}
        </p>
      ) : null}
    </div>
  );
}
