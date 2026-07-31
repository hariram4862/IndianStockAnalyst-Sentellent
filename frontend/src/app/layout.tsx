import type { Metadata } from "next";
import { Inter, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

import { Toaster } from "@/components/ui/sonner";
import GoogleProvider from "@/providers/google-provider";
import QueryProvider from "@/providers/query-provider";

const sansFont = Inter({
  subsets: ["latin"],
  variable: "--font-sans-display",
  weight: ["400", "500", "600", "700"],
})

const monoFont = IBM_Plex_Mono({
  subsets: ["latin"],
  variable: "--font-mono-display",
  weight: ["400", "500"],
})

export const metadata: Metadata = {
  title: "Indian Stock Analyst",
  description: "AI Powered Stock Analysis Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${sansFont.variable} ${monoFont.variable}`}>
        <QueryProvider>
          <GoogleProvider>
            {children}
            <Toaster />
          </GoogleProvider>
        </QueryProvider>
      </body>
    </html>
  );
}
