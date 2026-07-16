"use client";

import ReactMarkdown from "react-markdown";

import type { AssistantHighlight, FollowUpOption } from "@/lib/api";
import { FollowUpBubbles } from "@/components/follow-up-bubbles";
import { VehicleImage } from "@/components/vehicle-image";
import { spaceLabelSections } from "@/lib/format-assistant-markdown";

export function isOptionFocusPhase(phase?: string, responseMode?: string) {
  return phase === "option_focus" || responseMode === "option_focus";
}

export function OptionFocusPanel({
  summary,
  highlight,
  followUpOptions,
  followUpPrompt,
  onSelectOption,
  optionsDisabled,
}: {
  summary?: string;
  highlight?: AssistantHighlight;
  followUpOptions?: FollowUpOption[];
  followUpPrompt?: string;
  onSelectOption?: (message: string) => void;
  optionsDisabled?: boolean;
}) {
  const rawTrim = highlight?.trim?.trim();
  const vehicleLabel = [highlight?.make, highlight?.model].filter(Boolean).join(" ").toLowerCase();
  const trimLooksLikeVehicle =
    !!rawTrim &&
    (/20\d{2}/.test(rawTrim) ||
      (!!vehicleLabel && vehicleLabel.split(" ").every((part) => !part || rawTrim.toLowerCase().includes(part))));
  const titleBits = [
    highlight?.year,
    highlight?.make,
    highlight?.model,
    trimLooksLikeVehicle ? undefined : rawTrim,
  ].filter(Boolean);

  return (
    <div>
      {titleBits.length > 0 ? (
        <p className="text-base font-semibold text-slate-900">{titleBits.join(" ")}</p>
      ) : null}

      {highlight ? (
        <div className="mt-4">
          <VehicleImage item={highlight} />
        </div>
      ) : null}

      {summary ? (
        <div className="prose-carvest mt-5">
          <ReactMarkdown>{spaceLabelSections(summary)}</ReactMarkdown>
        </div>
      ) : null}

      {(followUpOptions?.length ?? 0) > 0 && onSelectOption ? (
        <FollowUpBubbles
          options={followUpOptions ?? []}
          prompt={followUpPrompt}
          onSelect={onSelectOption}
          disabled={optionsDisabled}
        />
      ) : null}
    </div>
  );
}
