"use client";

import { Card, CardContent } from "@/components/ui/card";
import { CredentialResponse, GoogleLogin } from "@react-oauth/google";
import { loginWithGoogle } from "@/services/auth";
import { useRouter } from "next/navigation";
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
    } catch (err) {
      console.error(err);
    }
  }

  
  return (
    <Card className="w-[420px] shadow-xl">
      <CardContent className="space-y-6 p-8">
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold">
            Indian Stock Analyst
          </h1>

          <p className="text-muted-foreground">
            AI-powered investment assistant
          </p>
        </div>

        <GoogleLogin
          onSuccess={handleSuccess}
          onError={() => console.error("Login failed")}
        />
      </CardContent>
    </Card>
  );
}
