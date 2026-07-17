import { BuyerReportView } from "./report-view";

function firstString(value: string | string[] | undefined): string {
  if (Array.isArray(value)) return value[0] ?? "";
  return value ?? "";
}

export default async function BuyerReportResultPage({
  params,
  searchParams,
}: {
  params: Promise<{ reportId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const route = await params;
  const query = await searchParams;
  // Prefer query token from Stripe checkout return; the client also reads #token=
  // for email links and then strips secrets from the visible URL.
  const token = firstString(query.token);

  return (
    <BuyerReportView
      reportId={route.reportId}
      initialToken={token}
    />
  );
}
