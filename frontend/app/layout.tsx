import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";

import React from "react";
import Providers from "@/components/providers";
import DevIndicatorSuppressor from "@/components/dev-indicator-suppressor";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "GSSR Dashboard",
  description: "GSSR knowledge graph monitoring dashboard",
};


export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased`}>
        <DevIndicatorSuppressor />
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
