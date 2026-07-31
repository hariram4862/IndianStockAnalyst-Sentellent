"use client";

import Link from "next/link";
import { ArrowLeft } from "lucide-react";

import LoginCard from "@/components/auth/login-card";
import GuestGuard from "@/components/auth/GuestGuard";

export default function LoginPage() {
  return (
    <GuestGuard>
      <main className="relative flex min-h-svh items-center justify-center overflow-hidden bg-background px-4">
        <div
          className="pointer-events-none absolute inset-0 -z-10 opacity-[0.05]"
          style={{
            backgroundImage:
              "linear-gradient(to right, currentColor 1px, transparent 1px), linear-gradient(to bottom, currentColor 1px, transparent 1px)",
            backgroundSize: "48px 48px",
          }}
        />
        <Link
          href="/"
          className="absolute top-6 left-6 inline-flex items-center gap-1.5 text-sm text-muted-foreground transition-colors hover:text-foreground"
        >
          <ArrowLeft className="size-4" /> Back
        </Link>
        <LoginCard />
      </main>
    </GuestGuard>
  );
}
