"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { CredentialResponse, GoogleLogin } from "@react-oauth/google";
import { motion } from "framer-motion";
import { BadgeIndianRupee, Quote, Sparkles } from "lucide-react";
import { toast } from "sonner";

import { Card, CardContent } from "@/components/ui/card";
import { getErrorMessage } from "@/lib/errors";
import { loginWithGoogle } from "@/services/auth";
import { useAuthStore } from "@/store/auth-store";

const TRUST_BULLETS = [
  { icon: Quote, label: "Cited sources" },
  { icon: BadgeIndianRupee, label: "INR figures" },
  { icon: Sparkles, label: "Learns your profile" },
];

export default function LoginCard() {
  const router = useRouter();
  const { login } = useAuthStore();
  const [signingIn, setSigningIn] = useState(false);

  // Not useSearchParams -- reading window.location directly avoids the
  // Suspense-boundary requirement that hook forces on the whole page, for a
  // one-off "why am I here" message after the api client's 401 handler
  // bounced the user back from an expired session.
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (new URLSearchParams(window.location.search).get("sessionExpired")) {
      toast.info("Your session expired. Please sign in again.");
      window.history.replaceState({}, "", "/login");
    }
  }, []);

  async function handleSuccess(response: CredentialResponse) {
    if (!response.credential) {
      return;
    }

    setSigningIn(true);
    try {
      const result = await loginWithGoogle(response.credential);
      login(result.access_token, result.user);
      router.push("/dashboard");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not sign in. Please try again."));
      setSigningIn(false);
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 16, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
    >
      <Card className="w-full max-w-[420px] border-border shadow-none">
        <CardContent className="space-y-8 p-8">
          <div className="space-y-3 text-center">
            <div className="mx-auto flex size-10 items-center justify-center rounded-md bg-accent-brand font-mono text-sm font-semibold text-accent-brand-foreground">
              IA
            </div>
            <div className="space-y-1">
              <h1 className="text-xl font-semibold">Indian Stock Analyst</h1>
              <p className="text-sm text-muted-foreground">
                Grounded, cited research for the NSE/BSE.
              </p>
            </div>
          </div>

          <div className="flex flex-col items-center gap-3">
            <div className="relative flex justify-center">
              <GoogleLogin
                onSuccess={handleSuccess}
                onError={() => toast.error("Google sign-in failed. Please try again.")}
              />
              {signingIn && (
                <div className="absolute inset-0 flex items-center justify-center rounded-md bg-background/80 text-xs font-medium text-muted-foreground">
                  Signing in…
                </div>
              )}
            </div>
          </div>

          <div className="flex items-center justify-center gap-4 border-t border-border pt-5">
            {TRUST_BULLETS.map(({ icon: Icon, label }) => (
              <span key={label} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                <Icon className="size-3.5 text-accent-brand" />
                {label}
              </span>
            ))}
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
