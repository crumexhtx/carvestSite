import { cn } from "@/lib/utils";

const styles = {
  LIKELY_GOOD_DEAL: "bg-emerald-500 text-white border-emerald-500",
  NEAR_MARKET: "bg-card-subtle text-slate-700 border-border",
  LIKELY_OVERPRICED: "bg-rose-500 text-white border-rose-500",
};

export function DealBadge({
  signal,
  className,
}: {
  signal?: string;
  className?: string;
}) {
  if (!signal) return null;

  const label =
    signal === "LIKELY_GOOD_DEAL"
      ? "Great Deal"
      : signal === "NEAR_MARKET"
        ? "Fair Price"
        : signal === "LIKELY_OVERPRICED"
          ? "Above Market"
          : signal.replaceAll("_", " ").toLowerCase();

  const style =
    styles[signal as keyof typeof styles] ??
    "bg-violet-600 text-white border-violet-600";

  return (
    <span
      className={cn(
        "inline-flex rounded-md border px-2.5 py-1 text-[11px] font-semibold uppercase tracking-wide shadow-sm",
        style,
        className,
      )}
    >
      {label}
    </span>
  );
}
