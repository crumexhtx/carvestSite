"use client";

import { FormEvent, useState } from "react";
import { CheckCircle2, Loader2, Mail } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { joinWaitlist } from "@/lib/api";
import { trackEvent } from "@/lib/analytics";
import { features } from "@/lib/features";

export function SoftLaunchWaitlist({
  source = "soft_launch",
  title = "Get notified when paid VIN reports launch",
  description = "We're launching free research tools first. Leave your email and we'll tell you when deep-dive buyer reports are ready.",
}: {
  source?: string;
  title?: string;
  description?: string;
}) {
  const [email, setEmail] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  if (!features.waitlistEnabled) {
    return null;
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);
    try {
      const result = await joinWaitlist({ email, source });
      trackEvent("Waitlist Join", { source });
      setSuccess(result.message);
      setEmail("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not join the waitlist.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="rounded-2xl border border-violet-200 bg-violet-50/70 p-5">
      <div className="flex items-start gap-3">
        <Mail className="mt-0.5 h-5 w-5 shrink-0 text-violet-600" />
        <div>
          <h3 className="font-semibold text-slate-900">{title}</h3>
          <p className="mt-1 text-sm leading-6 text-slate-600">{description}</p>
        </div>
      </div>
      {success ? (
        <p className="mt-4 flex items-start gap-2 text-sm text-emerald-700">
          <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" />
          {success}
        </p>
      ) : (
        <form onSubmit={submit} className="mt-4 flex flex-col gap-3 sm:flex-row">
          <Input
            type="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            className="sm:flex-1"
          />
          <Button type="submit" disabled={loading}>
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : null}
            {loading ? "Saving..." : "Notify me"}
          </Button>
        </form>
      )}
      {error ? <p className="mt-3 text-sm text-rose-600">{error}</p> : null}
    </div>
  );
}
