import Link from "next/link";

export function SiteFooter() {
  return (
    <footer className="border-t border-border bg-card">
      <div className="mx-auto flex max-w-5xl flex-col gap-3 px-6 py-6 text-xs text-slate-500 sm:flex-row sm:items-center sm:justify-between">
        <p>© {new Date().getFullYear()} Carvest. Research before you invest.</p>
        <nav className="flex flex-wrap gap-5">
          <Link className="transition hover:text-violet-700" href="/cars">
            Research hubs
          </Link>
          <Link className="transition hover:text-violet-700" href="/feedback">
            Feedback
          </Link>
          <Link className="transition hover:text-violet-700" href="/privacy">
            Privacy
          </Link>
          <Link className="transition hover:text-violet-700" href="/terms">
            Terms
          </Link>
        </nav>
      </div>
    </footer>
  );
}
