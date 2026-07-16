"use client";

import { useEffect, useState } from "react";

import { AppSidebar } from "@/components/app-sidebar";
import { fetchInventoryScale, type InventoryScale } from "@/lib/api";

export function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [inventory, setInventory] = useState<InventoryScale | null>(null);

  useEffect(() => {
    fetchInventoryScale()
      .then(setInventory)
      .catch(() => setInventory(null));
  }, []);

  return (
    <div className="flex min-h-screen bg-[var(--dash-bg)]">
      <AppSidebar inventory={inventory} />
      <div className="flex min-w-0 flex-1 flex-col">{children}</div>
    </div>
  );
}
