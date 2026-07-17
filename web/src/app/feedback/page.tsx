import type { Metadata } from "next";

import { buildMetadata } from "@/lib/seo";

import { FeedbackClient } from "./page.client";

export const metadata: Metadata = buildMetadata({
  title: "Feedback",
  description: "Share product feedback to help improve Carvest research tools.",
  path: "/feedback",
});

export default function FeedbackPage() {
  return <FeedbackClient />;
}
