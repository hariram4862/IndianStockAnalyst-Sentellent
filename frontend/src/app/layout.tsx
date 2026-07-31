import type { Metadata } from "next";
import { Cormorant_Garamond, IBM_Plex_Mono } from "next/font/google";
import "./globals.css";

import GoogleProvider from "@/providers/google-provider";

const displayFont = Cormorant_Garamond({
  subsets: ["latin"],
  variable: "--font-display",
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
      <body className={`${displayFont.variable} ${monoFont.variable}`}>
        <GoogleProvider>{children}</GoogleProvider>
      </body>
    </html>
  );
}
