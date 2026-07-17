/**
 * Thin analytics helper. Events no-op unless a provider script is loaded
 * (currently Plausible via NEXT_PUBLIC_PLAUSIBLE_DOMAIN).
 */

type PlausibleFn = (
  event: string,
  options?: { props?: Record<string, string | number | boolean> },
) => void;

declare global {
  interface Window {
    plausible?: PlausibleFn;
  }
}

export function trackEvent(
  event: string,
  props?: Record<string, string | number | boolean>,
): void {
  if (typeof window === "undefined") return;
  if (typeof window.plausible !== "function") return;
  try {
    window.plausible(event, props ? { props } : undefined);
  } catch {
    // Never let analytics break product flows.
  }
}

export function analyticsEnabled(): boolean {
  return Boolean(process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN?.trim());
}
