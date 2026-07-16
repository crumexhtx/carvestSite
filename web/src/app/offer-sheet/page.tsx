import { OfferSheetClient } from "./page.client";

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
