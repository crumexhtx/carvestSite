import type { Metadata } from "next";

import { VehicleDetailView } from "@/components/vehicle-detail-view";
import { buildMetadata } from "@/lib/seo";

type VehiclePageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
  params: Promise<{ id: string }>;
};

export async function generateMetadata({
  params,
}: VehiclePageProps): Promise<Metadata> {
  const routeParams = await params;
  return buildMetadata({
    title: "Vehicle details",
    description: "Listing detail snapshot from a Carvest search session.",
    path: `/vehicle/${routeParams.id}`,
    noIndex: true,
  });
}

export default async function VehicleDetailPage({ searchParams, params }: VehiclePageProps) {
  const query = await searchParams;
  const routeParams = await params;

  const get = (key: string) => {
    const value = query[key];
    return Array.isArray(value) ? value[0] : value ?? "";
  };

  const num = (key: string) => {
    const value = Number(get(key));
    return Number.isFinite(value) ? value : 0;
  };

  return (
    <VehicleDetailView
      id={routeParams.id}
      heading={get("heading") || "Vehicle details"}
      price={num("price")}
      miles={num("miles")}
      photo={get("photo")}
      dealer={get("dealer")}
      city={get("city")}
      state={get("state")}
      signal={get("signal")}
      vdp={get("vdp")}
      vin={get("vin")}
      zipCode={get("zip")}
      dom={num("dom")}
      make={get("make")}
      model={get("model")}
      year={num("year")}
      fairPrice={num("fair")}
      priceDelta={num("delta")}
      listingId={get("listing_id") || routeParams.id}
      trustSig={get("trust_sig")}
    />
  );
}
