import type { AssistantHighlight, ModelDetails, FollowUpOption } from "@/lib/api";

import { FollowUpBubbles } from "@/components/follow-up-bubbles";
import { RecommendationCards } from "@/components/recommendation-cards";
import { VehicleImage } from "@/components/vehicle-image";

export function ModelFocusPanel({
  details,
  highlight,
  competitorHighlights,
  followUp,
  followUpOptions,
  followUpPrompt,
  onSelectModel,
  onSelectOption,
  optionsDisabled,
}: {
  details: ModelDetails;
  highlight?: AssistantHighlight;
  competitorHighlights?: AssistantHighlight[];
  followUp?: string;
  followUpOptions?: FollowUpOption[];
  followUpPrompt?: string;
  onSelectModel?: (item: AssistantHighlight) => void;
  onSelectOption?: (message: string) => void;
  optionsDisabled?: boolean;
}) {
  const matchedHighlight =
    highlight &&
    highlight.make.toLowerCase() === details.make.toLowerCase() &&
    highlight.model.toLowerCase() === details.model.toLowerCase()
      ? highlight
      : undefined;

  const hero: AssistantHighlight = {
    make: details.make,
    model: details.model,
    year: matchedHighlight?.year,
    title: `${details.make} ${details.model}`,
    summary: details.overview,
    photo: matchedHighlight?.photo,
    photo_source: matchedHighlight?.photo_source,
  };

  return (
    <div>
      <p className="text-base font-semibold text-slate-900">
        {details.make} {details.model}
      </p>

      <div className="mt-4">
        <VehicleImage item={hero} />
      </div>

      {details.overview ? (
        <p className="mt-4 text-sm leading-7 text-slate-600">{details.overview}</p>
      ) : null}

      {details.sections.length > 0 ? (
        <div className="prose-carvest mt-6 space-y-5">
          {details.sections.map((section) => (
            <div key={section.label}>
              <p className="text-sm font-semibold text-violet-700">{section.label}:</p>
              <p className="mt-1 text-sm leading-7 text-slate-600">{section.content}</p>
            </div>
          ))}
        </div>
      ) : null}

      {(competitorHighlights?.length ?? 0) > 0 ? (
        <div className="mt-6">
          <p className="mb-3 text-[11px] uppercase tracking-[0.2em] text-slate-500">
            Competitors
          </p>
          <RecommendationCards
            highlights={competitorHighlights ?? []}
            onSelect={onSelectModel}
            compact
          />
        </div>
      ) : null}

      {(followUpOptions?.length ?? 0) > 0 && onSelectOption ? (
        <FollowUpBubbles
          options={followUpOptions ?? []}
          prompt={followUpPrompt}
          onSelect={onSelectOption}
          disabled={optionsDisabled}
        />
      ) : followUp ? (
        <p className="mt-6 text-sm leading-7 text-slate-600">{followUp}</p>
      ) : null}
    </div>
  );
}

export function isModelFocusPhase(phase?: string) {
  return phase === "model_focus" || phase === "brand_or_model_story";
}
