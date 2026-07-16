const ALL_SUGGESTION_CHIPS = [
  "I want a 4x4 truck under $35,000",
  "Good SUV for a large family",
  "Great on gas for daily commuting",
  "Best cars for road trips",
  "Tell me about the Toyota Tacoma",
  "Reliable sedan for a 60-mile commute",
  "Compare RAV4 vs CR-V for a family of five",
  "Used hybrid under $25,000",
  "Safest three-row SUV for kids",
  "Best truck for towing a boat",
  "Low-mileage Lexus under $40,000",
  "Minivan with the best cargo space",
  "AWD crossover with strong resale",
  "Tell me about the Honda CR-V",
  "Electric car with the best range under $45k",
  "Pickup with the best reliability",
  "Compact car for city parking",
  "Tell me about the Ford F-150",
  "Family SUV with third-row seating",
  "Best used Mazda for reliability",
];

export const DEFAULT_SUGGESTION_CHIPS = ALL_SUGGESTION_CHIPS.slice(0, 5);

function shuffle<T>(items: T[]): T[] {
  const copy = [...items];
  for (let index = copy.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1));
    [copy[index], copy[swapIndex]] = [copy[swapIndex], copy[index]];
  }
  return copy;
}

export function pickSuggestionChips(count = 5): string[] {
  return shuffle(ALL_SUGGESTION_CHIPS).slice(0, count);
}
