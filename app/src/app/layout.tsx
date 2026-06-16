import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Creative AI Feed",
  description: "Weekly curated Reddit feed for generative/creative AI",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="pt-BR">
      <body className="bg-gray-950 text-gray-100 min-h-screen">{children}</body>
    </html>
  );
}
