import { BuyerReportClient } from "./page.client";

export default async function BuyerReportPage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const query = await searchParams;
  const vin = Array.isArray(query.vin) ? query.vin[0] : query.vin;
  return <BuyerReportClient defaultVin={vin ?? ""} />;
}
