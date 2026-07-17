import Script from "next/script";

/**
 * Env-gated Plausible loader. Set NEXT_PUBLIC_PLAUSIBLE_DOMAIN to enable.
 * Optional NEXT_PUBLIC_PLAUSIBLE_SRC overrides the script URL (self-host / proxy).
 */
export function Analytics() {
  const domain = process.env.NEXT_PUBLIC_PLAUSIBLE_DOMAIN?.trim();
  if (!domain) return null;

  const src =
    process.env.NEXT_PUBLIC_PLAUSIBLE_SRC?.trim() ||
    "https://plausible.io/js/script.js";

  return (
    <Script
      defer
      data-domain={domain}
      src={src}
      strategy="afterInteractive"
    />
  );
}
