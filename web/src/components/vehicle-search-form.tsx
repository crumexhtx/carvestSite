"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function VehicleSearchForm({
  defaults,
  showCompare = false,
}: {
  defaults?: {
    make?: string;
    year?: string;
    model?: string;
    zip_code?: string;
  };
  showCompare?: boolean;
}) {
  const router = useRouter();
  const [make, setMake] = useState(defaults?.make ?? "Toyota");
  const [year, setYear] = useState(defaults?.year ?? "2020");
  const [model, setModel] = useState(defaults?.model ?? "Camry");
  const [zipCode, setZipCode] = useState(defaults?.zip_code ?? "");

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    const params = new URLSearchParams({
      make,
      year,
      model,
    });
    if (zipCode) params.set("zip_code", zipCode);
    if (showCompare) params.set("compare", "1");
    router.push(`/search?${params.toString()}`);
  }

  return (
    <form
      onSubmit={onSubmit}
      className="grid gap-4 rounded-3xl border border-border bg-card p-6 shadow-[var(--shadow-card)] md:grid-cols-4"
    >
      <label className="space-y-2">
        <span className="text-xs uppercase tracking-[0.2em] text-slate-500">Make</span>
        <Input value={make} onChange={(e) => setMake(e.target.value)} placeholder="Toyota" />
      </label>
      <label className="space-y-2">
        <span className="text-xs uppercase tracking-[0.2em] text-slate-500">Year</span>
        <Input value={year} onChange={(e) => setYear(e.target.value)} placeholder="2020" />
      </label>
      <label className="space-y-2">
        <span className="text-xs uppercase tracking-[0.2em] text-slate-500">Model</span>
        <Input value={model} onChange={(e) => setModel(e.target.value)} placeholder="Camry" />
      </label>
      <label className="space-y-2">
        <span className="text-xs uppercase tracking-[0.2em] text-slate-500">ZIP</span>
        <Input value={zipCode} onChange={(e) => setZipCode(e.target.value)} placeholder="77087" />
      </label>
      <div className="md:col-span-4 flex flex-wrap gap-3">
        <Button type="submit">Search Listings</Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => {
            const params = new URLSearchParams({ make, year, model, compare: "1" });
            if (zipCode) params.set("zip_code", zipCode);
            router.push(`/search?${params.toString()}`);
          }}
        >
          Compare Rivals
        </Button>
      </div>
    </form>
  );
}
