import type { FollowUpOption } from "@/lib/api";

export function FollowUpBubbles({
  options,
  prompt,
  onSelect,
  disabled,
}: {
  options: FollowUpOption[];
  prompt?: string;
  onSelect: (message: string) => void;
  disabled?: boolean;
}) {
  if (!options.length) return null;

  return (
    <div className="mt-5">
      <p className="mb-3 text-sm leading-6 text-slate-600">
        {prompt ?? "What would you like to explore next?"}
      </p>
      <div className="flex flex-wrap gap-2">
        {options.map((option) => (
          <button
            key={option.label}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(option.message)}
            className="maskara-chip rounded-full border-violet-300 bg-violet-50 px-4 py-2 text-sm text-violet-700 transition hover:border-violet-400 hover:bg-violet-100 disabled:opacity-40"
          >
            {option.label}
          </button>
        ))}
      </div>
    </div>
  );
}
