"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import {
  AlertTriangle,
  Bot,
  Car,
  LayoutGrid,
  Newspaper,
  Search,
  type LucideIcon,
} from "lucide-react";

import type { InventoryScale } from "@/lib/api";
import { cn } from "@/lib/utils";

type NavItem = {
  id: string;
  label: string;
  href: string;
  icon: LucideIcon;
  match?: (pathname: string, tab: string | null) => boolean;
};

const NAV: NavItem[] = [
  {
    id: "search",
    label: "AI Assistant",
    href: "/?tab=search",
    icon: Bot,
    match: (pathname, tab) => pathname === "/" && (!tab || tab === "search"),
  },
  {
    id: "recalls",
    label: "Active Recalls",
    href: "/?tab=recalls",
    icon: AlertTriangle,
    match: (pathname, tab) => pathname === "/" && tab === "recalls",
  },
  {
    id: "reliability",
    label: "Reliability",
    href: "/?tab=reliability",
    icon: Newspaper,
    match: (pathname, tab) => pathname === "/" && tab === "reliability",
  },
  {
    id: "results",
    label: "Listings",
    href: "/search?mode=results",
    icon: LayoutGrid,
    match: (pathname) => pathname.startsWith("/search"),
  },
];

export function AppSidebar({ inventory }: { inventory?: InventoryScale | null }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const tab = searchParams.get("tab");

  return (
    <>
      <div className="flex items-center gap-2 overflow-x-auto border-b border-[var(--dash-border)] bg-[var(--dash-sidebar)] p-3 lg:hidden">
        {NAV.map((item) => {
          const Icon = item.icon;
          const active = item.match
            ? item.match(pathname, tab)
            : pathname === item.href;
          return (
            <Link
              key={item.id}
              href={item.href}
              className={cn(
                "inline-flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium",
                active
                  ? "bg-violet-50 text-violet-700"
                  : "text-slate-500",
              )}
            >
              <Icon className="h-3.5 w-3.5" />
              {item.label}
            </Link>
          );
        })}
      </div>

      <aside className="dashboard-sidebar hidden w-[248px] shrink-0 flex-col border-r border-[var(--dash-border)] bg-[var(--dash-sidebar)] lg:flex">
      <div className="flex h-16 items-center gap-3 border-b border-[var(--dash-border)] px-5">
        <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-[var(--dash-accent)] text-white">
          <Car className="h-4 w-4" />
        </div>
        <div>
          <p className="text-sm font-semibold tracking-[0.18em] text-slate-900">CARVEST</p>
          <p className="text-[11px] text-[var(--dash-muted)]">AI Auto Research</p>
        </div>
      </div>

      <nav className="flex-1 space-y-1 p-4">
        <p className="mb-3 px-3 text-[11px] font-semibold uppercase tracking-[0.2em] text-[var(--dash-muted)]">
          Menu
        </p>
        {NAV.map((item) => {
          const Icon = item.icon;
          const active = item.match
            ? item.match(pathname, tab)
            : pathname === item.href;

          return (
            <Link
              key={item.id}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition",
                active
                  ? "bg-violet-50 text-violet-700"
                  : "text-slate-500 hover:bg-card-subtle hover:text-slate-900",
              )}
            >
              <Icon
                className={cn(
                  "h-4 w-4",
                  active ? "text-violet-600" : "text-slate-400",
                )}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="border-t border-[var(--dash-border)] p-4">
        {inventory ? (
          <div className="dashboard-stat-card p-4">
            <div className="mb-2 flex items-center gap-2 text-[var(--dash-accent)]">
              <Search className="h-3.5 w-3.5" />
              <span className="text-[11px] font-semibold uppercase tracking-[0.16em]">
                Inventory
              </span>
            </div>
            <p className="text-2xl font-semibold text-slate-900">
              {inventory.total_listings_nationwide.toLocaleString()}+
            </p>
            <p className="mt-1 text-xs leading-5 text-[var(--dash-muted)]">
              Active dealer listings nationwide
            </p>
          </div>
        ) : (
          <div className="h-24 animate-pulse rounded-xl bg-[var(--dash-card)]" />
        )}
      </div>
    </aside>
    </>
  );
}
