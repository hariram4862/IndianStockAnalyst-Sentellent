"use client";

import LoginCard from "@/components/auth/login-card";
import GuestGuard from "@/components/auth/GuestGuard";

export default function LoginPage() {
  return (
    <GuestGuard>
      <main className="flex min-h-screen items-center justify-center bg-slate-100">
        <LoginCard />
      </main>
    </GuestGuard>
  );
}