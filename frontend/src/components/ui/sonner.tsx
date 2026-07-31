"use client";

import { Toaster as SonnerToaster } from "sonner";

export function Toaster() {
  return (
    <SonnerToaster
      position="bottom-right"
      toastOptions={{
        classNames: {
          toast:
            "rounded-md border border-border bg-card text-card-foreground shadow-none font-sans text-sm",
          title: "font-medium",
          description: "text-muted-foreground",
          actionButton: "bg-primary text-primary-foreground",
          cancelButton: "bg-secondary text-secondary-foreground",
          success: "border-foreground/20",
          error: "border-foreground/40",
        },
      }}
      icons={{
        success: <span className="text-foreground">✓</span>,
        error: <span className="text-foreground">✕</span>,
      }}
    />
  );
}
