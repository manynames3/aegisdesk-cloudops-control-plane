import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AegisDesk CloudOps Control Plane",
  description: "Policy-aware AI gateway demo for CloudOps workflows."
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

