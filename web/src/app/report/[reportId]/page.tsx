import { BuyerReportView } from "./report-view";

export default async function BuyerReportResultPage({
  params,
  searchParams,
}: {
  params: Promise<{ reportId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const route = await params;
  const query = await searchParams;
  const tokenValue = query.token;
  const token = Array.isArray(tokenValue) ? tokenValue[0] : tokenValue;

  return (
    <BuyerReportView
      reportId={route.reportId}
      initialToken={token ?? ""}
    />
  );
}
