"use client";

import { GoogleOAuthProvider } from "@react-oauth/google";

interface GoogleProviderProps {
  children: React.ReactNode;
}

export default function GoogleProvider({
  children,
}: GoogleProviderProps) {
  return (
    <GoogleOAuthProvider
      clientId={process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID!}
    >
      {children}
    </GoogleOAuthProvider>
  );
}