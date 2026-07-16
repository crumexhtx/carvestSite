/**
 * Soft-launch feature flags.
 * Monetization stays off until NEXT_PUBLIC_MONETIZATION_ENABLED=true.
 */

function truthy(value: string | undefined, defaultValue = false): boolean {
  if (value == null || value === "") return defaultValue;
  return ["1", "true", "yes", "on"].includes(value.trim().toLowerCase());
}

export const features = {
  monetizationEnabled: truthy(
    process.env.NEXT_PUBLIC_MONETIZATION_ENABLED,
    false,
  ),
  waitlistEnabled: truthy(process.env.NEXT_PUBLIC_WAITLIST_ENABLED, true),
};

export type PublicFeatureFlags = {
  monetization_enabled: boolean;
  waitlist_enabled: boolean;
};
