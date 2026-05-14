import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AegisDesk CloudOps Control Plane",
  description: "AI help for CloudOps teams with identity, redaction, approvals, model routing, and audit trails."
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
