import type { Metadata } from "next";

import { buildMetadata } from "@/lib/seo";

export const metadata: Metadata = buildMetadata({
  title: "Privacy notice",
  description: "How Carvest collects and uses information for vehicle research reports.",
  path: "/privacy",
});

export default function PrivacyPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <article className="prose-carvest maskara-glass rounded-3xl p-6 md:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-600">
          Carvest
        </p>
        <h1>Privacy notice</h1>
        <p>Last updated: July 15, 2026</p>
        <h2>Information collected</h2>
        <p>
          Carvest processes the VIN, listing details, ZIP code, email address, payment
          status, and technical request data needed to create and deliver a report.
          Card details are handled by Stripe and are not stored by Carvest.
        </p>
        <h2>How information is used</h2>
        <p>
          Information is used to decode vehicles, obtain recall and market data,
          generate reports, process payments, prevent abuse, and email report links.
        </p>
        <h2>Service providers</h2>
        <p>
          The service may share necessary data with NHTSA, MarketCheck, OpenAI,
          Stripe, Supabase, Render, Vercel, Upstash, and Resend according to the
          operator&apos;s production configuration.
        </p>
        <h2>Retention and requests</h2>
        <p>
          The site operator should define a report retention period and a working
          privacy contact before launch. Users may contact that address to request
          access or deletion where applicable.
        </p>
        <h2>Operator notice</h2>
        <p>
          This is an MVP privacy template and should be reviewed and completed by
          qualified counsel before public launch.
        </p>
      </article>
    </main>
  );
}
