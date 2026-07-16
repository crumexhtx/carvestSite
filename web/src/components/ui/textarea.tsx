import * as React from "react";

import { cn } from "@/lib/utils";

export function Textarea({
  className,
  ...props
}: React.ComponentProps<"textarea">) {
  return (
    <textarea
      className={cn(
        "flex min-h-[220px] w-full rounded-2xl border border-border bg-card px-4 py-4 text-sm leading-6 text-slate-800 placeholder:text-slate-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-300",
        className,
      )}
      {...props}
    />
  );
}
