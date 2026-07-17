import type { Metadata } from "next";

import { buildMetadata } from "@/lib/seo";

import { ListingDealClient } from "./page.client";

export const metadata: Metadata = buildMetadata({
  title: "Listing deal checker",
  description:
    "Paste a VIN and asking price to see fair-market signal, payment estimates, and what to do next before you buy.",
  path: "/listing-deal",
});

export default async function ListingDealPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const get = (key: string) => {
    const value = query[key];
    return Array.isArray(value) ? value[0] : value ?? "";
  };

  return (
    <ListingDealClient
      defaultVin={get("vin")}
      defaultPrice={get("price")}
      defaultMiles={get("miles")}
      defaultZip={get("zip")}
      defaultUrl={get("url")}
    />
  );
}
