import type { Metadata } from "next";

import { buildMetadata } from "@/lib/seo";

import { BuyerReportClient } from "./page.client";

export const metadata: Metadata = buildMetadata({
  title: "VIN buyer report",
  description:
    "Get a VIN-specific Carvest report covering market pricing, recalls, reliability, and negotiation guidance.",
  path: "/report",
});

export default async function BuyerReportPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const vin = Array.isArray(query.vin) ? query.vin[0] : query.vin;
  return <BuyerReportClient defaultVin={vin ?? ""} />;
}
