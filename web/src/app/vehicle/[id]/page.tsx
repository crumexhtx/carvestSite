import { VehicleDetailView } from "@/components/vehicle-detail-view";

type VehiclePageProps = {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
  params: Promise<{ id: string }>;
};

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
    />
  );
}
