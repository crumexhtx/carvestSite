import type { ReliabilityRankings } from "@/lib/api";

const REFERENCE_YEAR = new Date().getFullYear() - 3;

function vehiclePrompt(make: string, model: string, year: number) {
  return `Tell me about the ${year} ${make} ${model} — reliability, best years to buy, and what to watch for.`;
}

function brandPrompt(brand: string) {
  return `What makes ${brand} one of the most reliable brands? Which ${brand} models should I consider for a used purchase?`;
}

export const DEFAULT_RELIABILITY_RANKINGS: ReliabilityRankings = {
  reference_year: REFERENCE_YEAR,
  source: "Consumer Reports owner-reliability surveys",
  top_vehicles: [
    {
      rank: 1,
      make: "Lexus",
      model: "GX",
      year: REFERENCE_YEAR,
      note: "Top-rated luxury SUV with consistently low problem rates.",
      prompt: vehiclePrompt("Lexus", "GX", REFERENCE_YEAR),
    },
    {
      rank: 2,
      make: "Toyota",
      model: "Corolla Hybrid",
      year: REFERENCE_YEAR,
      note: "Excellent fuel economy with proven hybrid durability.",
      prompt: vehiclePrompt("Toyota", "Corolla Hybrid", REFERENCE_YEAR),
    },
    {
      rank: 3,
      make: "Mazda",
      model: "CX-30",
      year: REFERENCE_YEAR,
      note: "Compact SUV with strong owner satisfaction and few issues.",
      prompt: vehiclePrompt("Mazda", "CX-30", REFERENCE_YEAR),
    },
    {
      rank: 4,
      make: "Toyota",
      model: "Prius",
      year: REFERENCE_YEAR,
      note: "Hybrid icon with low maintenance costs over the long run.",
      prompt: vehiclePrompt("Toyota", "Prius", REFERENCE_YEAR),
    },
    {
      rank: 5,
      make: "Honda",
      model: "Civic",
      year: REFERENCE_YEAR,
      note: "Dependable compact with affordable ownership costs.",
      prompt: vehiclePrompt("Honda", "Civic", REFERENCE_YEAR),
    },
  ],
  top_brands: [
    {
      rank: 1,
      brand: "Lexus",
      note: "Luxury leader with the fewest reported problems.",
      prompt: brandPrompt("Lexus"),
    },
    {
      rank: 2,
      brand: "Toyota",
      note: "Benchmark for long-term durability across segments.",
      prompt: brandPrompt("Toyota"),
    },
    {
      rank: 3,
      brand: "Mazda",
      note: "Strong reliability with engaging driving dynamics.",
      prompt: brandPrompt("Mazda"),
    },
    {
      rank: 4,
      brand: "Subaru",
      note: "All-wheel-drive specialist with loyal owner scores.",
      prompt: brandPrompt("Subaru"),
    },
    {
      rank: 5,
      brand: "Honda",
      note: "Consistent quality in sedans, SUVs, and hybrids.",
      prompt: brandPrompt("Honda"),
    },
  ],
};
