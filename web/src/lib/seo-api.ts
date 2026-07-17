import { API_BASE } from "@/lib/api";

export type SeoHub = {
  make: string;
  model: string;
  year: number;
  make_slug: string;
  model_slug: string;
  path: string;
  reason: string;
  note?: string | null;
  title: string;
};

export type ModelBrief = {
  make: string;
  model: string;
  year: number;
  make_slug: string;
  model_slug: string;
  path: string;
  title: string;
  description: string;
  reliability_note?: string | null;
  research_prompt: string;
  recalls: {
    available: boolean;
    total_recalls_count: number | null;
    items: Array<{
      component: string;
      summary: string;
      consequence: string;
      remedy: string;
    }>;
  };
};

export async function fetchSeoHubs(): Promise<SeoHub[]> {
  try {
    const response = await fetch(`${API_BASE}/api/seo/hubs`, {
      next: { revalidate: 3600 },
    });
    if (!response.ok) return [];
    const data = (await response.json()) as { hubs?: SeoHub[] };
    return Array.isArray(data.hubs) ? data.hubs : [];
  } catch {
    return [];
  }
}

export async function fetchModelBrief(
  make: string,
  model: string,
  year: string,
): Promise<ModelBrief | null> {
  const params = new URLSearchParams({ make, model, year });
  try {
    const response = await fetch(`${API_BASE}/api/seo/model-brief?${params}`, {
      next: { revalidate: 900 },
    });
    if (response.status === 404) return null;
    if (!response.ok) return null;
    return (await response.json()) as ModelBrief;
  } catch {
    return null;
  }
}
