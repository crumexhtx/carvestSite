"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ArrowUp, Loader2, RotateCcw, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";

import { FollowUpBubbles } from "@/components/follow-up-bubbles";
import { ModelFocusPanel, isModelFocusPhase } from "@/components/model-focus-panel";
import { OptionFocusPanel, isOptionFocusPhase } from "@/components/option-focus-panel";
import { RecommendationCards } from "@/components/recommendation-cards";
import { ReliabilityPrompts } from "@/components/reliability-prompts";
import {
  assistantChat,
  searchByCriteria,
  type AssistantCriteria,
  type AssistantHighlight,
  type FollowUpOption,
  type ModelDetails,
  type ReliabilityRankings,
  type SearchResponse,
} from "@/lib/api";
import { DEFAULT_SUGGESTION_CHIPS, pickSuggestionChips } from "@/lib/prompt-suggestions";
import { spaceLabelSections } from "@/lib/format-assistant-markdown";
import { cn } from "@/lib/utils";

type ChatMessage = {
  role: "user" | "assistant";
  content: string;
  response_summary?: string;
  phase?: string;
  response_mode?: string;
  highlights?: AssistantHighlight[];
  competitor_highlights?: AssistantHighlight[];
  model_details?: ModelDetails | null;
  follow_up_options?: FollowUpOption[];
  follow_up_prompt?: string;
};

const SUGGESTION_CHIP_COUNT = 5;

const PLACEHOLDER_HINTS = [
  'Try: "I want a 4x4 truck under $35,000 near Houston"',
  'Try: "Reliable sedan for a 60-mile commute"',
  'Try: "Compare RAV4 vs CR-V for a family of five"',
];

function criteriaPills(criteria: AssistantCriteria): string[] {
  const pills: string[] = [];
  if (criteria.body_type) pills.push(criteria.body_type);
  if (criteria.drivetrain) pills.push(criteria.drivetrain);
  if (criteria.use_case) pills.push(criteria.use_case.replace(/_/g, " "));
  if (criteria.make) pills.push(criteria.make);
  if (criteria.model) pills.push(criteria.model);
  if (criteria.year) pills.push(String(criteria.year));
  if (criteria.year_min || criteria.year_max) {
    pills.push(`${criteria.year_min ?? "any"}–${criteria.year_max ?? "newer"}`);
  }
  if (criteria.max_price) pills.push(`≤ $${criteria.max_price.toLocaleString()}`);
  if (criteria.zip_code) pills.push(`ZIP ${criteria.zip_code}`);
  return pills;
}

export function VehicleAiAssistant({
  onResults,
  reliabilityRankings,
  initialPrompt,
  onInitialPromptConsumed,
}: {
  onResults?: (results: SearchResponse, criteria: AssistantCriteria) => void;
  reliabilityRankings?: ReliabilityRankings | null;
  initialPrompt?: string | null;
  onInitialPromptConsumed?: () => void;
}) {
  const router = useRouter();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const chatEndRef = useRef<HTMLDivElement>(null);

  const [prompt, setPrompt] = useState("");
  const [criteria, setCriteria] = useState<AssistantCriteria>({});
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [readyToSearch, setReadyToSearch] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [focused, setFocused] = useState(false);
  const [placeholderIndex, setPlaceholderIndex] = useState(0);
  const [suggestionChips, setSuggestionChips] = useState(DEFAULT_SUGGESTION_CHIPS);
  const initialPromptSentRef = useRef(false);
  const requestIdRef = useRef(0);
  const inFlightRef = useRef(false);

  const profilePills = useMemo(() => criteriaPills(criteria), [criteria]);
  const inConversation = messages.length > 0;

  const resizeTextarea = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 120)}px`;
  }, []);

  useEffect(() => {
    setSuggestionChips(pickSuggestionChips(SUGGESTION_CHIP_COUNT));
  }, []);

  useEffect(() => {
    resizeTextarea();
  }, [prompt, resizeTextarea]);

  useEffect(() => {
    if (!inConversation) {
      const timer = window.setInterval(() => {
        setPlaceholderIndex((prev) => (prev + 1) % PLACEHOLDER_HINTS.length);
      }, 4200);
      return () => window.clearInterval(timer);
    }
  }, [inConversation]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  async function sendMessage(rawMessage: string) {
    const trimmed = rawMessage.trim();
    if (!trimmed || inFlightRef.current) return;

    const requestId = ++requestIdRef.current;
    inFlightRef.current = true;
    setLoading(true);
    setError(null);
    setPrompt("");

    let nextMessages: ChatMessage[] = [];
    setMessages((prev) => {
      nextMessages = [...prev, { role: "user", content: trimmed }];
      return nextMessages;
    });

    try {
      const response = await assistantChat({
        message: trimmed,
        criteria,
        history: nextMessages.map((item) => ({
          role: item.role,
          content: item.content,
        })),
      });
      if (requestId !== requestIdRef.current) return;

      setCriteria(response.criteria);
      setReadyToSearch(response.ready_to_search);
      setMessages([
        ...nextMessages,
        {
          role: "assistant",
          content: response.assistant_message,
          response_summary: response.response_summary,
          phase: response.phase,
          response_mode: response.response_mode,
          highlights: response.highlights,
          competitor_highlights: response.competitor_highlights,
          model_details: response.model_details,
          follow_up_options: response.follow_up_options,
          follow_up_prompt: response.follow_up_prompt,
        },
      ]);

      if (response.ready_to_search) {
        const results = await searchByCriteria(response.criteria, { rows: 24 });
        if (requestId !== requestIdRef.current) return;
        const listingCount = results.listings?.length ?? 0;

        if (listingCount === 0 || results.match_quality === "none") {
          setReadyToSearch(false);
          setMessages((prev) => [
            ...prev,
            {
              role: "assistant",
              content:
                results.match_notice ||
                "I couldn't find live listings close enough to that mix yet. Try a wider year range, a higher mileage cap, or a nearby ZIP.",
              response_mode: "option_focus",
              phase: "option_focus",
              highlights: response.highlights?.slice(0, 1),
              follow_up_options: [
                {
                  label: "Widen years",
                  message: `Show me nearby years for the ${response.criteria.make ?? ""} ${response.criteria.model ?? ""}`.trim(),
                },
                {
                  label: "Under 100k miles",
                  message: `I want ${response.criteria.make ?? ""} ${response.criteria.model ?? ""} listings under 100,000 miles`.trim(),
                },
                {
                  label: "Raise budget",
                  message: "Increase my budget by about $5,000",
                },
                {
                  label: "Enter ZIP",
                  message: "I want to search listings near my ZIP code",
                },
              ],
              follow_up_prompt: "How should we adjust the search?",
            },
          ]);
        } else {
          onResults?.(results, response.criteria);
          const params = new URLSearchParams({ mode: "results" });
          const searchCriteria =
            (results.applied_criteria as typeof response.criteria | undefined) ??
            response.criteria;
          sessionStorage.setItem(
            "carvest-search",
            JSON.stringify({
              criteria: searchCriteria,
              displayCriteria: response.criteria,
              results,
            }),
          );
          router.push(`/search?${params.toString()}`);
        }
      }
    } catch (err) {
      if (requestId !== requestIdRef.current) return;
      setError(err instanceof Error ? err.message : "Assistant request failed.");
    } finally {
      if (requestId === requestIdRef.current) {
        inFlightRef.current = false;
        setLoading(false);
        textareaRef.current?.focus();
      }
    }
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    await sendMessage(prompt);
  }

  function handleSelectModel(item: AssistantHighlight) {
    void sendMessage(
      `I'm interested in the ${item.make} ${item.model}. Tell me which years are best and what to avoid.`,
    );
  }

  function handleNewChat() {
    requestIdRef.current += 1;
    inFlightRef.current = false;
    setMessages([]);
    setCriteria({});
    setReadyToSearch(false);
    setError(null);
    setPrompt("");
    setLoading(false);
    initialPromptSentRef.current = false;
    textareaRef.current?.focus();
  }

  useEffect(() => {
    const prompt = initialPrompt?.trim();
    if (!prompt || initialPromptSentRef.current || loading || messages.length > 0) {
      return;
    }
    initialPromptSentRef.current = true;
    void sendMessage(prompt);
    onInitialPromptConsumed?.();
  }, [initialPrompt, loading, messages.length, onInitialPromptConsumed]);

  const showSideReliability = Boolean(reliabilityRankings);

  return (
    <div
      className={cn(
        "relative z-10 mx-auto px-4 py-10 pb-16 md:py-14 md:pb-20",
        showSideReliability ? "max-w-7xl" : "max-w-3xl",
      )}
    >
      <div
        className={cn(
          "text-center transition-all duration-300",
          inConversation ? "mb-8 scale-[0.94] opacity-85" : "mb-0",
        )}
      >
        <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-xs uppercase tracking-[0.22em] text-slate-500 shadow-sm">
          <span className="maskara-glow-dot inline-block h-1.5 w-1.5 rounded-full bg-violet-500" />
          Carvest
        </div>

        <h1
          className={cn(
            "mt-6 font-light leading-tight tracking-tight text-slate-900 transition-all duration-300",
            inConversation ? "text-2xl md:text-3xl" : "text-4xl md:text-5xl",
          )}
        >
          Find the right car for{" "}
          <span className="maskara-gradient-text">you</span>
        </h1>

        {!inConversation ? (
          <p className="mx-auto mt-5 max-w-xl text-base leading-7 text-slate-500">
            Carvest compares cars with consumer reports, analysis, recalls, and
            listings.
          </p>
        ) : null}
      </div>

      <div
        className={cn(
          showSideReliability &&
            "mt-10 grid grid-cols-1 items-start gap-8 lg:grid-cols-[minmax(0,12rem)_minmax(0,42rem)_minmax(0,12rem)] lg:justify-center lg:gap-4 xl:grid-cols-[minmax(0,16rem)_minmax(0,42rem)_minmax(0,16rem)] xl:gap-6",
        )}
      >
        {showSideReliability ? (
          <aside className="sticky top-24 hidden lg:block">
            <ReliabilityPrompts
              rankings={reliabilityRankings!}
              section="vehicles"
              side
              onSelectPrompt={(text) => void sendMessage(text)}
              disabled={loading}
            />
          </aside>
        ) : null}

        <div
          className={cn(
            "min-w-0",
            showSideReliability && "mx-auto w-full max-w-3xl lg:max-w-none",
          )}
        >
      <form onSubmit={handleSubmit} className={cn(!inConversation && !showSideReliability && "mt-10", !inConversation && showSideReliability && "mt-0")}>
        <div
          className={cn(
            "maskara-prompt-shell",
            focused && "maskara-prompt-shell--focused",
          )}
        >
          <div className="maskara-prompt-inner flex flex-col">
            <div className="flex items-center justify-between gap-3 border-b border-slate-200 px-4 py-3 md:px-5">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-[0.18em] text-slate-400">
                <Sparkles className="h-3.5 w-3.5 text-violet-600" />
                Ask Carvest anything
              </div>
              {inConversation ? (
                <button
                  type="button"
                  onClick={handleNewChat}
                  disabled={loading}
                  className="inline-flex items-center gap-1.5 rounded-full border border-border px-3 py-1 text-xs text-slate-500 transition hover:border-slate-300 hover:text-slate-800 disabled:opacity-40"
                >
                  <RotateCcw className="h-3 w-3" />
                  New chat
                </button>
              ) : null}
            </div>

            <div className="maskara-prompt-body flex-1 px-4 md:px-5">
              {messages.length > 0 ? (
                <div className="space-y-3 py-4">
                  {messages.map((message, index) => (
                    <div
                      key={`${message.role}-${index}`}
                      className={cn(
                        "px-4 py-3 text-sm leading-7",
                        message.role === "assistant"
                          ? "maskara-msg-assistant w-full"
                          : "maskara-msg-user ml-auto max-w-[94%]",
                      )}
                    >
                      {message.role === "assistant" ? (
                        <div className="prose-carvest">
                          {message.model_details &&
                          isModelFocusPhase(message.phase) &&
                          !isOptionFocusPhase(message.phase, message.response_mode) ? (
                            <ModelFocusPanel
                              details={message.model_details}
                              highlight={message.highlights?.[0]}
                              competitorHighlights={message.competitor_highlights}
                              followUp={message.content}
                              followUpOptions={message.follow_up_options}
                              followUpPrompt={message.follow_up_prompt}
                              onSelectModel={handleSelectModel}
                              onSelectOption={(text) => void sendMessage(text)}
                              optionsDisabled={loading}
                            />
                          ) : isOptionFocusPhase(message.phase, message.response_mode) ? (
                            <OptionFocusPanel
                              summary={message.response_summary || message.content}
                              highlight={message.highlights?.[0]}
                              followUpOptions={message.follow_up_options}
                              followUpPrompt={message.follow_up_prompt}
                              onSelectOption={(text) => void sendMessage(text)}
                              optionsDisabled={loading}
                            />
                          ) : (message.highlights?.length ?? 0) > 0 ||
                            (message.competitor_highlights?.length ?? 0) > 0 ||
                            (message.follow_up_options?.length ?? 0) > 0 ? (
                            <>
                              {message.response_summary ? (
                                <p className="mb-5 text-sm leading-7 text-slate-700">
                                  {message.response_summary}
                                </p>
                              ) : null}
                              <RecommendationCards
                                highlights={message.highlights ?? []}
                                onSelect={handleSelectModel}
                              />
                              {(message.competitor_highlights?.length ?? 0) > 0 ? (
                                <div className="mt-6">
                                  <p className="mb-3 text-[11px] uppercase tracking-[0.2em] text-slate-500">
                                    Competitors
                                  </p>
                                  <RecommendationCards
                                    highlights={message.competitor_highlights ?? []}
                                    onSelect={handleSelectModel}
                                  />
                                </div>
                              ) : null}
                              {(message.follow_up_options?.length ?? 0) > 0 ? (
                                <FollowUpBubbles
                                  options={message.follow_up_options ?? []}
                                  prompt={message.follow_up_prompt}
                                  onSelect={(text) => void sendMessage(text)}
                                  disabled={loading}
                                />
                              ) : message.content ? (
                                <p className="mt-6 text-sm leading-7 text-slate-600">
                                  {message.content}
                                </p>
                              ) : null}
                            </>
                          ) : (
                            <ReactMarkdown>
                              {spaceLabelSections(message.content)}
                            </ReactMarkdown>
                          )}
                        </div>
                      ) : (
                        message.content
                      )}
                    </div>
                  ))}

                  {loading ? (
                    <div className="maskara-msg-assistant inline-flex items-center gap-2 px-4 py-3 text-sm text-slate-500">
                      <span>Carvest is researching</span>
                      <span className="inline-flex gap-1">
                        <span className="maskara-typing-dot inline-block h-1.5 w-1.5 rounded-full bg-violet-500" />
                        <span className="maskara-typing-dot inline-block h-1.5 w-1.5 rounded-full bg-violet-500" />
                        <span className="maskara-typing-dot inline-block h-1.5 w-1.5 rounded-full bg-violet-500" />
                      </span>
                    </div>
                  ) : null}
                  <div ref={chatEndRef} />
                </div>
              ) : null}

              <div
                className={cn(
                  "relative",
                  messages.length > 0 ? "border-t border-slate-200 py-3" : "py-4",
                )}
              >
                <textarea
                  ref={textareaRef}
                  value={prompt}
                  onChange={(event) => setPrompt(event.target.value)}
                  onFocus={() => setFocused(true)}
                  onBlur={() => setFocused(false)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" && !event.shiftKey) {
                      event.preventDefault();
                      void sendMessage(prompt);
                    }
                  }}
                  placeholder={
                    inConversation
                      ? "Add a year, trim, or ask a follow-up…"
                      : PLACEHOLDER_HINTS[placeholderIndex]
                  }
                  rows={inConversation ? 1 : 3}
                  className="maskara-prompt-input pr-14"
                />

                <button
                  type="submit"
                  disabled={loading || !prompt.trim()}
                  aria-label="Send message"
                  className="maskara-send-btn absolute bottom-3 right-0"
                >
                  {loading ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <ArrowUp className="h-4 w-4" strokeWidth={2.5} />
                  )}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between gap-3 border-t border-slate-200 px-4 py-3 text-[11px] text-slate-400 md:px-5">
              <span>Enter to send · Shift + Enter for new line</span>
              {profilePills.length > 0 ? (
                <span className="text-violet-600">
                  {profilePills.length} preference{profilePills.length === 1 ? "" : "s"} saved
                </span>
              ) : null}
            </div>
          </div>
        </div>
      </form>

      {!inConversation ? (
        <div className="mt-5">
          <p className="mb-3 text-center text-[11px] uppercase tracking-[0.2em] text-slate-400">
            Try a prompt
          </p>
          <div className="flex flex-wrap justify-center gap-2">
            {suggestionChips.map((chip) => (
              <button
                key={chip}
                type="button"
                onClick={() => void sendMessage(chip)}
                disabled={loading}
                className="maskara-chip rounded-full px-4 py-2 text-sm disabled:opacity-40"
              >
                {chip}
              </button>
            ))}
          </div>
        </div>
      ) : null}

          {showSideReliability ? (
            <div className="mt-8 space-y-8 lg:hidden">
              <ReliabilityPrompts
                rankings={reliabilityRankings!}
                section="vehicles"
                onSelectPrompt={(text) => void sendMessage(text)}
                disabled={loading}
              />
              <ReliabilityPrompts
                rankings={reliabilityRankings!}
                section="brands"
                onSelectPrompt={(text) => void sendMessage(text)}
                disabled={loading}
              />
              <p className="text-center text-[11px] text-slate-400">
                Source: {reliabilityRankings!.source}
              </p>
            </div>
          ) : null}
        </div>

        {showSideReliability ? (
          <aside className="sticky top-24 hidden lg:block">
            <ReliabilityPrompts
              rankings={reliabilityRankings!}
              section="brands"
              side
              onSelectPrompt={(text) => void sendMessage(text)}
              disabled={loading}
            />
          </aside>
        ) : null}
      </div>

      {profilePills.length > 0 ? (
        <div className="mt-6 flex flex-wrap justify-center gap-2">
          <span className="self-center text-xs uppercase tracking-[0.2em] text-slate-400">
            Your profile
          </span>
          {profilePills.map((pill) => (
            <span
              key={pill}
              className="rounded-full border border-amber-300/60 bg-amber-50 px-3 py-1 text-xs text-amber-800"
            >
              {pill}
            </span>
          ))}
          {readyToSearch ? (
            <span className="rounded-full border border-emerald-300/60 bg-emerald-50 px-3 py-1 text-xs text-emerald-700">
              Ready to search listings
            </span>
          ) : null}
        </div>
      ) : null}

      {error ? (
        <p className="mt-4 text-center text-sm text-rose-600">{error}</p>
      ) : null}
    </div>
  );
}
