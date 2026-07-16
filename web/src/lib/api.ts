export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";

export type VehicleSearchParams = {
  make: string;
  year: string;
  model: string;
  zip_code?: string;
};

export type Listing = {
  listing_id?: string;
  vin?: string;
  price?: number;
  miles?: number;
  heading?: string;
  exterior_color?: string;
  fuel_type?: string;
  dealer_name?: string;
  city?: string;
  state?: string;
  zip?: string;
  vdp_url?: string;
  primary_photo?: string;
  photo_count?: number;
  dom?: number;
  price_analysis?: {
    predicted_fair_price?: number;
    listing_price?: number;
    price_delta?: number;
    deal_signal?: string;
  };
};

export type SearchResponse = {
  total_found: number;
  market_stats: Record<string, unknown>;
  listings: Listing[];
  search_context?: Record<string, unknown>;
  match_quality?: "exact" | "closest" | "none";
  match_notice?: string | null;
  relaxed_filters?: string[];
  requested_criteria?: Record<string, unknown>;
  applied_criteria?: Record<string, unknown>;
};

export type ReportResponse = {
  report: string;
};

export type BuyerReportVehicle = {
  vin: string;
  make: string;
  model: string;
  year: number;
  trim?: string | null;
  series?: string | null;
  body_class?: string | null;
  drive_type?: string | null;
  fuel_type?: string | null;
  engine?: string | null;
  catalog_verified?: boolean;
};

export type BuyerReportPreview = {
  vehicle: BuyerReportVehicle;
  listing_price?: number | null;
  mileage?: number | null;
  zip_code?: string | null;
  recall_count: number;
  top_recall_component?: string | null;
  summary: string;
  visible_sections: string[];
  locked_sections: string[];
  report_price_cents: number;
};

export type BuyerReportPreviewResponse = {
  report_id: string;
  access_token: string;
  status: string;
  preview: BuyerReportPreview;
  report_price_cents: number;
};

export type BuyerReportFull = {
  vehicle: BuyerReportVehicle;
  request: Record<string, unknown>;
  markdown_report: string;
  price_analysis?: {
    predicted_fair_price?: number | null;
    listing_price?: number | null;
    price_delta?: number | null;
    deal_signal?: string | null;
  } | null;
  recalls?: {
    total_recalls_count?: number;
    recalls_list?: Array<Record<string, string>>;
  };
  inspection_checklist?: string[];
  negotiation_pack?: NegotiationPack | null;
  error?: string;
};

export type BuyerReportResponse = {
  report_id: string;
  status: "pending_payment" | "paid" | "generating" | "ready" | "failed";
  preview: BuyerReportPreview;
  full_report?: BuyerReportFull | null;
  report_price_cents: number;
};

export type BuyerReportCheckoutResponse = {
  checkout_url: string;
  session_id?: string;
  development_unlocked?: boolean;
};

export type OfferSheetCategory =
  | "government_charge"
  | "dealer_fee"
  | "optional_product"
  | "price_adjustment"
  | "unknown";

export type OfferSheetLineItemInput = {
  label: string;
  amount: number;
  notes?: string;
};

export type ClassifiedOfferLineItem = OfferSheetLineItemInput & {
  index: number;
  category: OfferSheetCategory;
  confidence: "high" | "medium" | "low";
  rationale: string;
  review_recommended: boolean;
};

export type OfferSheetAnalysis = {
  classified_items: ClassifiedOfferLineItem[];
  totals: {
    advertised_price: number;
    line_items_subtotal: number;
    out_the_door_total: number;
    potential_review_amount: number;
    by_category: Record<OfferSheetCategory, number>;
  };
  review_level: "low" | "moderate" | "high";
  questions: Array<{
    related_labels: string[];
    question: string;
    context: string;
  }>;
  location: {
    state?: string | null;
    zip_code?: string | null;
  };
  disclaimer: string;
};

export type ListingDealEvaluation = {
  vehicle: BuyerReportVehicle;
  listing: {
    price: number;
    mileage: number;
    zip_code: string;
    listing_url?: string | null;
  };
  price_analysis?: {
    predicted_fair_price?: number | null;
    listing_price?: number | null;
    price_delta?: number | null;
    deal_signal?: string | null;
  } | null;
  market_note: string;
  recall_count: number;
  loan: {
    down_payment: number;
    amount_financed: number;
    term_months: number;
    credit_tier: string;
    selected_apr_percent: number;
    selected_monthly_payment: number;
    scenarios: Array<{
      credit_tier: string;
      label: string;
      apr_percent: number;
      monthly_payment: number;
      selected: boolean;
    }>;
    disclaimer: string;
  };
  insurance: {
    age_band: string;
    age_band_label: string;
    monthly_low: number;
    monthly_mid: number;
    monthly_high: number;
    annual_mid: number;
    disclaimer: string;
  };
  ownership: {
    loan_monthly: number;
    insurance_monthly_low: number;
    insurance_monthly_mid: number;
    insurance_monthly_high: number;
    estimated_monthly_low: number;
    estimated_monthly_mid: number;
    estimated_monthly_high: number;
  };
  recommendation: {
    headline: string;
    detail: string;
    tips: string[];
    deal_signal?: string | null;
  };
  next_steps: Array<{
    id: string;
    label: string;
    href: string;
    description: string;
  }>;
  disclaimer: string;
};

export type CompareResponse = {
  report: string;
  dataset: Record<string, unknown>;
};

export type AssistantCriteria = {
  make?: string | null;
  model?: string | null;
  year?: string | number | null;
  year_min?: string | number | null;
  year_max?: string | number | null;
  zip_code?: string | null;
  body_type?: string | null;
  drivetrain?: string | null;
  doors?: string | number | null;
  fuel_type?: string | null;
  min_mpg?: number | null;
  max_mpg?: number | null;
  max_price?: number | null;
  min_price?: number | null;
  max_miles?: number | null;
  trim?: string | null;
  notes?: string | null;
  use_case?: string | null;
};

export type FollowUpOption = {
  label: string;
  message: string;
};

export type ModelDetailSection = {
  label: string;
  content: string;
};

export type ModelDetails = {
  make: string;
  model: string;
  overview?: string;
  sections: ModelDetailSection[];
};

export type AssistantHighlight = {
  id?: string;
  make: string;
  model: string;
  trim?: string;
  year?: number;
  title: string;
  photo?: string;
  photo_source?: "listing" | "reference" | null;
  summary?: string;
  kind?: "competitor" | "primary";
};

export type AssistantChatResponse = {
  criteria: AssistantCriteria;
  profile_text: string;
  assistant_message: string;
  response_summary?: string;
  phase?: string;
  response_mode?: "discover" | "model_focus" | "option_focus" | "search_ready";
  highlights?: AssistantHighlight[];
  competitor_highlights?: AssistantHighlight[];
  model_details?: ModelDetails | null;
  follow_up_options?: FollowUpOption[];
  follow_up_prompt?: string;
  ready_to_search: boolean;
  missing_fields: string[];
};

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const body = await response.text();
    let detail = body;
    try {
      const parsed = JSON.parse(body) as { detail?: string };
      detail = parsed.detail ?? body;
    } catch {
      // Keep the plain-text response.
    }
    throw new Error(detail || `Request failed (${response.status})`);
  }

  return response.json() as Promise<T>;
}

export function getMakes() {
  return apiFetch<string[]>("/api/makes");
}

export function getModels(make: string, year: string) {
  return apiFetch<string[]>(
    `/api/models?make=${encodeURIComponent(make)}&year=${encodeURIComponent(year)}`,
  );
}

export function searchListings(params: VehicleSearchParams) {
  return apiFetch<SearchResponse>("/api/search/listings", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function generateReport(params: VehicleSearchParams & { trim?: string }) {
  return apiFetch<ReportResponse>("/api/report", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function generateComparison(params: VehicleSearchParams) {
  return apiFetch<CompareResponse>("/api/compare", {
    method: "POST",
    body: JSON.stringify(params),
  });
}

export function assistantChat(payload: {
  message: string;
  criteria?: AssistantCriteria;
  history?: Array<{ role: string; content: string }>;
}) {
  return apiFetch<AssistantChatResponse>("/api/assistant/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function searchByCriteria(
  criteria: AssistantCriteria,
  options?: { start?: number; rows?: number },
) {
  return apiFetch<SearchResponse>("/api/search/criteria", {
    method: "POST",
    body: JSON.stringify({
      criteria,
      start: options?.start ?? 0,
      rows: options?.rows ?? 24,
    }),
  });
}

export type NegotiationPack = {
  summary: string;
  opening_offer: number;
  target_price: number;
  walk_away_price: number;
  talking_points: string[];
  email_script: string;
  text_script: string;
  caution?: string;
  price_analysis?: Listing["price_analysis"];
};

export type InventoryScale = {
  total_listings_nationwide: number;
  label: string;
};

export function fetchInventoryScale() {
  return apiFetch<InventoryScale>("/api/inventory/scale");
}

export function generateNegotiationPack(payload: {
  heading: string;
  price: number;
  miles?: number;
  vin?: string;
  zip_code?: string;
  make?: string;
  model?: string;
  year?: number;
  dom?: number;
  dealer_name?: string;
  city?: string;
  state?: string;
  deal_signal?: string;
  predicted_fair_price?: number;
  listing_price?: number;
  price_delta?: number;
}) {
  return apiFetch<NegotiationPack>("/api/negotiation", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export type RecallSnippet = {
  vehicle: string;
  component: string;
  summary: string;
  recall_count: number;
};

export type ReliableVehicle = {
  rank: number;
  make: string;
  model: string;
  year: number;
  note: string;
  prompt: string;
};

export type ReliableBrand = {
  rank: number;
  brand: string;
  note: string;
  prompt: string;
};

export type ReliabilityRankings = {
  reference_year: number;
  top_vehicles: ReliableVehicle[];
  top_brands: ReliableBrand[];
  source: string;
};

export type ReliabilityReport = {
  title: string;
  summary: string;
  url: string;
  source: string;
};

export type HomeInsights = {
  recall_snippets: RecallSnippet[];
  reliability_article: ReliabilityReport;
  reliability_reports?: ReliabilityReport[];
  reliability_rankings: ReliabilityRankings;
};

export function fetchHomeInsights() {
  return apiFetch<HomeInsights>("/api/home/insights");
}

export function createBuyerReportPreview(payload: {
  vin: string;
  listing_price?: number;
  mileage?: number;
  zip_code?: string;
  email?: string;
  listing_url?: string;
}) {
  return apiFetch<BuyerReportPreviewResponse>("/api/buyer-reports/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function fetchBuyerReport(reportId: string, accessToken: string) {
  return apiFetch<BuyerReportResponse>(
    `/api/buyer-reports/${encodeURIComponent(reportId)}`,
    {
      headers: { Authorization: `Bearer ${accessToken}` },
    },
  );
}

export function checkoutBuyerReport(reportId: string, accessToken: string) {
  return apiFetch<BuyerReportCheckoutResponse>(
    `/api/buyer-reports/${encodeURIComponent(reportId)}/checkout`,
    {
      method: "POST",
      body: JSON.stringify({ access_token: accessToken }),
    },
  );
}

export function analyzeOfferSheet(payload: {
  advertised_price: number;
  line_items: OfferSheetLineItemInput[];
  state?: string;
  zip_code?: string;
}) {
  return apiFetch<OfferSheetAnalysis>("/api/offer-sheet/analyze", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function evaluateListingDeal(payload: {
  vin: string;
  listing_price: number;
  mileage: number;
  zip_code: string;
  down_payment?: number;
  loan_term_months?: number;
  credit_tier?: string;
  age_band?: string;
  listing_url?: string;
}) {
  return apiFetch<ListingDealEvaluation>("/api/listing-deal/evaluate", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export function joinWaitlist(payload: { email: string; source?: string }) {
  return apiFetch<{ status: string; email: string; message: string }>(
    "/api/waitlist",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function submitProductFeedback(payload: {
  message: string;
  category?: "bug" | "idea" | "other";
  email?: string;
  page_path?: string;
}) {
  return apiFetch<{ status: string; id: string; message: string }>(
    "/api/feedback",
    {
      method: "POST",
      body: JSON.stringify(payload),
    },
  );
}

export function fetchVehicleReferenceImage(payload: {
  make: string;
  model: string;
  year?: number;
}) {
  const params = new URLSearchParams({
    make: payload.make,
    model: payload.model,
  });
  if (payload.year) {
    params.set("year", String(payload.year));
  }
  return apiFetch<{
    make: string;
    model: string;
    year?: number | null;
    photo?: string | null;
    photo_source?: "listing" | "reference" | null;
    proxy_photo?: string | null;
  }>(`/api/vehicle-reference-image?${params.toString()}`);
}

/** Same-origin proxy URL so browsers can reliably show Wikipedia reference photos. */
export function vehicleReferenceImageUrl(payload: {
  make: string;
  model: string;
  year?: number | null;
}) {
  const params = new URLSearchParams({
    make: payload.make,
    model: payload.model,
  });
  if (payload.year) {
    params.set("year", String(payload.year));
  }
  return `${API_BASE}/api/vehicle-reference-image/file?${params.toString()}`;
}
