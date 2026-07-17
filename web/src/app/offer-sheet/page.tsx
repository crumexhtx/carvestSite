import type { Metadata } from "next";

import { buildMetadata } from "@/lib/seo";

import { OfferSheetClient } from "./page.client";

export const metadata: Metadata = buildMetadata({
  title: "Dealer offer analyzer",
  description:
    "Break down dealer fees, add-ons, and government charges so you know what is negotiable before you sign.",
  path: "/offer-sheet",
});

export default async function OfferSheetPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const priceValue = Array.isArray(query.price) ? query.price[0] : query.price;
  const price = Number(priceValue);

  return (
    <OfferSheetClient
      defaultPrice={Number.isFinite(price) && price > 0 ? String(price) : ""}
    />
  );
}
