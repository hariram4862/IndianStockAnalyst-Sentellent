"use client";

import LoginCard from "@/components/auth/login-card";
import GuestGuard from "@/components/auth/GuestGuard";

export default function LoginPage() {
  return (
    <GuestGuard>
      <main className="flex min-h-svh items-center justify-center bg-background px-4">
        <LoginCard />
      </main>
    </GuestGuard>
  );
}
