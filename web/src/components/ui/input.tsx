import * as React from "react";

import { cn } from "@/lib/utils";

export function Input({
  className,
  type,
  ...props
}: React.ComponentProps<"input">) {
  return (
    <input
      type={type}
      className={cn(
        "flex h-12 w-full rounded-xl border border-border bg-card px-4 text-sm text-slate-900 placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-300",
        className,
      )}
      {...props}
    />
  );
}
