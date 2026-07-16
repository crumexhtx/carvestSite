export default function TermsPage() {
  return (
    <main className="mx-auto max-w-3xl px-4 py-12">
      <article className="prose-carvest maskara-glass rounded-3xl p-6 md:p-8">
        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-violet-600">
          Carvest
        </p>
        <h1>Terms of use</h1>
        <p>Last updated: July 15, 2026</p>
        <h2>Research service</h2>
        <p>
          Carvest provides informational vehicle research. Reports are not mechanical
          inspections, warranties, appraisals, legal advice, or financial advice.
          Vehicle condition, recall status, history, and price must be independently
          verified before purchase.
        </p>
        <h2>Third-party data</h2>
        <p>
          Reports may use NHTSA, MarketCheck, dealer, and AI-generated information.
          Data can be incomplete, delayed, or inaccurate. A model-year recall result
          does not establish whether a specific VIN has an open recall.
        </p>
        <h2>Payments and refunds</h2>
        <p>
          Paid reports are digital products generated for the submitted VIN and
          listing details. Contact the support address configured by the site operator
          if a purchased report cannot be delivered or is technically defective.
        </p>
        <h2>Operator notice</h2>
        <p>
          This is an MVP terms template and should be reviewed by qualified counsel
          before public launch.
        </p>
      </article>
    </main>
  );
}
