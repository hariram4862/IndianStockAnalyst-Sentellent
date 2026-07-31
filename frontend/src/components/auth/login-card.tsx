"use client";

import { useRouter } from "next/navigation";
import { CredentialResponse, GoogleLogin } from "@react-oauth/google";
import { toast } from "sonner";

import { Card, CardContent } from "@/components/ui/card";
import { getErrorMessage } from "@/lib/errors";
import { loginWithGoogle } from "@/services/auth";
import { useAuthStore } from "@/store/auth-store";

export default function LoginCard() {
  const router = useRouter();
  const { login } = useAuthStore();

  async function handleSuccess(response: CredentialResponse) {
    if (!response.credential) {
      return;
    }

    try {
      const result = await loginWithGoogle(response.credential);
      login(result.access_token, result.user);
      router.push("/dashboard");
    } catch (error) {
      toast.error(getErrorMessage(error, "Could not sign in. Please try again."));
    }
  }

  return (
    <Card className="w-full max-w-[420px] border-border shadow-none">
      <CardContent className="space-y-8 p-8">
        <div className="space-y-3 text-center">
          <div className="mx-auto flex size-10 items-center justify-center rounded-md bg-primary font-mono text-sm font-semibold text-primary-foreground">
            IA
          </div>
          <div className="space-y-1">
            <h1 className="text-xl font-semibold">Indian Stock Analyst</h1>
            <p className="text-sm text-muted-foreground">
              Grounded, cited research for the NSE/BSE.
            </p>
          </div>
        </div>

        <div className="flex justify-center">
          <GoogleLogin
            onSuccess={handleSuccess}
            onError={() => toast.error("Google sign-in failed. Please try again.")}
          />
        </div>
      </CardContent>
    </Card>
  );
}
