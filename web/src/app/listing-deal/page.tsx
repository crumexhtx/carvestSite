import { ListingDealClient } from "./page.client";

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
