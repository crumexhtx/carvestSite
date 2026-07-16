"use client";

import { FormEvent, useState } from "react";
import { CheckCircle2, Loader2, MessageSquareHeart } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { submitProductFeedback } from "@/lib/api";

const CATEGORIES = [
  { value: "idea", label: "Product idea" },
  { value: "bug", label: "Bug / something broken" },
  { value: "other", label: "Other" },
] as const;

export function FeedbackClient() {
  const [category, setCategory] = useState<(typeof CATEGORIES)[number]["value"]>("idea");
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await submitProductFeedback({
        category,
        email: email || undefined,
        message,
        page_path: typeof window !== "undefined" ? window.location.pathname : "/feedback",
      });
      setSuccess(result.message);
      setMessage("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not send feedback.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="maskara-ambient relative min-h-[calc(100vh-4rem)] overflow-hidden">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(99,102,241,0.08),transparent_42%)]" />
      <div className="relative mx-auto max-w-2xl px-4 py-12 md:py-16">
        <div className="text-center">
          <div className="mx-auto inline-flex items-center gap-2 rounded-full border border-border bg-card px-4 py-1.5 text-xs uppercase tracking-[0.2em] text-slate-500 shadow-sm">
            <MessageSquareHeart className="h-3.5 w-3.5 text-violet-600" />
            Feedback
          </div>
          <h1 className="mt-6 text-4xl font-light tracking-tight text-slate-900">
            Help shape{" "}
            <span className="maskara-gradient-text">Carvest</span>
          </h1>
          <p className="mx-auto mt-4 max-w-xl text-base leading-7 text-slate-600">
            During the soft launch we&apos;re collecting ideas, bugs, and what would
            make this more useful before buying a used car.
          </p>
        </div>

        <form onSubmit={submit} className="maskara-glass mt-10 rounded-3xl p-6 md:p-8">
          {success ? (
            <div className="flex items-start gap-3 text-sm leading-6 text-emerald-700">
              <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0" />
              <div>
                <p className="font-medium">{success}</p>
                <button
                  type="button"
                  className="mt-3 text-violet-700 underline"
                  onClick={() => setSuccess(null)}
                >
                  Send more feedback
                </button>
              </div>
            </div>
          ) : (
            <>
              <label className="block space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Category
                </span>
                <select
                  value={category}
                  onChange={(event) =>
                    setCategory(event.target.value as (typeof CATEGORIES)[number]["value"])
                  }
                  className="flex h-12 w-full rounded-xl border border-border bg-card px-4 text-sm text-slate-900"
                >
                  {CATEGORIES.map((option) => (
                    <option key={option.value} value={option.value}>
                      {option.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="mt-5 block space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Email{" "}
                  <span className="font-normal normal-case">(optional, if we can reply)</span>
                </span>
                <Input
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  placeholder="you@example.com"
                />
              </label>

              <label className="mt-5 block space-y-2">
                <span className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-500">
                  Your feedback
                </span>
                <Textarea
                  required
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="What worked, what confused you, or what you wish Carvest did next?"
                  rows={6}
                />
              </label>

              {error ? <p className="mt-4 text-sm text-rose-600">{error}</p> : null}

              <Button type="submit" className="mt-6 w-full" disabled={loading}>
                {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
                {loading ? "Sending..." : "Send feedback"}
              </Button>
            </>
          )}
        </form>
      </div>
    </main>
  );
}
